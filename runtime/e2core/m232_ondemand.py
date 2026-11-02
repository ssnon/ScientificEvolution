"""M23.2 Part B on-demand controller context *protocol prototype*.

NO integration into paid controller yet.  This module handles only explicit,
read-only model requests.  The native Opportunity/Controller validator remains
responsible for scientific assessment, actions and final plan acceptance.

Cost-aware: a separate retrieval-planning LLM call is NOT mandatory.  The
first response to the compact view may be a native scientific answer; only a
model-authored REQUEST_DETAILS incurs another model turn in a later adapter.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from .m232_partb import (
    TAG, MARKER, ShadowProjectionError, project_context, expand_context,
)

PROTOCOL = 'M232_ON_DEMAND_DETAIL_V1'
REQUEST_DETAILS = 'REQUEST_DETAILS'
REQUEST_FULL = 'REQUEST_FULL_CONTEXT'
STAGES = {'OPPORTUNITY', 'CONTROLLER'}


class DetailProtocolError(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf8')


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def _id_map(records, kind):
    if not isinstance(records, list):
        raise DetailProtocolError('INVALID_' + kind + '_ARRAY')
    mapping = {}
    for record in records:
        if (not isinstance(record, dict) or not isinstance(record.get('id'), str)
                or not record['id'] or record['id'] in mapping):
            raise DetailProtocolError('INVALID_' + kind + '_ID')
        mapping[record['id']] = record
    return mapping


class DetailSession:
    """One independent scientific assessor's retrieval view.

    Construction, requests and snapshots never perform I/O or paid calls.
    No detail-count limit is introduced.  Each pass is explicitly advanced by
    the caller, so a later durable adapter can journal every call separately.
    """

    def __init__(self, full_context, stage):
        if stage not in STAGES:
            raise DetailProtocolError('UNKNOWN_STAGE')
        if not isinstance(full_context, dict):
            raise DetailProtocolError('CONTEXT_NOT_OBJECT')
        self._full = deepcopy(full_context)
        self._view = project_context(self._full)
        self.stage = stage
        self._asset_ids = _id_map(self._full['assets'], 'ASSET')
        self._problem_ids = _id_map(self._full['problems'], 'PROBLEM')
        self._events = []
        self._finished = False
        self._full_hash = digest(self._full)

    def model_input(self):
        """Preview only. Explicitly NOT approved for live paid research."""
        if self._finished:
            raise DetailProtocolError('SESSION_ALREADY_FINISHED')
        if digest(self._full) != self._full_hash:
            raise DetailProtocolError('FULL_CONTEXT_CHANGED')
        result = deepcopy(self._view)
        result['m232_model_detail_request_contract'] = {
            'protocol': PROTOCOL,
            'stage': self.stage,
            'status': 'DEVELOPMENT_SHADOW_NOT_ENABLED_FOR_PAID_RESEARCH',
            'first_response_may_be_native_scientific_answer': True,
            'request_more_data_instead_of_guessing': {
                'm232_action': REQUEST_DETAILS,
                'asset_ids': ['CURRENT_ROOT_ASSET_ID'],
                'problem_ids': ['CURRENT_ROOT_PROBLEM_ID'],
                'reason': 'state why the original full fields matter',
            },
            'request_all_if_needed': {
                'm232_action': REQUEST_FULL,
                'reason': 'explain why broad coverage is necessary',
            },
            'all_asset_problem_ids_visible': True,
            'no_fixed_detail_selection_quota': True,
            'all_original_omitted_fields_available_for_exact_expansion': True,
            'source_status_and_model_claims_are_not_certified_evidence': True,
            'final_scientific_answer_remains_subject_to_existing_native_validator': True,
            'missing_critical_counterexamples_should_trigger_detail_request': True,
            'original_p0_immutable': True,
        }
        return result

    def _missing(self):
        return {
            'asset_ids': [r['id'] for r in self._view['assets'] if TAG in r],
            'problem_ids': [r['id'] for r in self._view['problems'] if TAG in r],
        }

    def status(self):
        remaining = self._missing()
        return {
            'protocol': PROTOCOL,
            'stage': self.stage,
            'full_context_sha256': self._full_hash,
            'current_projection_sha256': digest(self._view),
            'indexed_asset_count': len(remaining['asset_ids']),
            'indexed_problem_count': len(remaining['problem_ids']),
            'request_events': deepcopy(self._events),
            'finished': self._finished,
            'scientific_equivalence_certified': False,
            'paid_runtime_enabled': False,
        }

    def process(self, response):
        """Process a native answer or a request, never edit the model's science.

        A final scientific answer is only *recognized*, not accepted.  The
        existing validate_opp/controller_plan must still validate it.
        """
        if self._finished:
            raise DetailProtocolError('SESSION_ALREADY_FINISHED')
        if not isinstance(response, dict):
            raise DetailProtocolError('MODEL_RESPONSE_NOT_OBJECT')
        action = response.get('m232_action')
        if action is None:
            is_opp = self.stage == 'OPPORTUNITY' and isinstance(response.get('opportunities'), list)
            is_ctrl = (self.stage == 'CONTROLLER' and isinstance(response.get('actions'), list)
                       and isinstance(response.get('disposition'), str)
                       and isinstance(response.get('rationale'), str))
            if not (is_opp or is_ctrl):
                raise DetailProtocolError('INVALID_NATIVE_ASSESSMENT_SHAPE')
            self._finished = True
            self._events.append({
                'event': 'NATIVE_ASSESSMENT_PRODUCED',
                'assessor_stage': self.stage,
                'assessment_sha256': digest(response),
                'remaining_indexed': {k:len(v) for k,v in self._missing().items()},
                'not_scientifically_certified': True,
                'requires_unchanged_native_validation': True,
            })
            return {'status': 'NATIVE_ASSESSMENT_NEEDS_ORIGINAL_VALIDATOR',
                    'model_authored_answer': deepcopy(response),
                    'advisory_coverage': self.status()}
        if action not in (REQUEST_DETAILS, REQUEST_FULL):
            raise DetailProtocolError('UNKNOWN_M232_ACTION')
        if not isinstance(response.get('reason'), str) or not response['reason'].strip():
            raise DetailProtocolError('DETAIL_REQUEST_NEEDS_REASON')
        if action == REQUEST_DETAILS:
            a = response.get('asset_ids', [])
            p = response.get('problem_ids', [])
            if not isinstance(a, list) or not isinstance(p, list):
                raise DetailProtocolError('DETAIL_IDS_MUST_BE_LISTS')
            if any(not isinstance(x, str) for x in a+p):
                raise DetailProtocolError('DETAIL_IDS_MUST_BE_STRINGS')
            if len(set(a)) != len(a) or len(set(p)) != len(p):
                raise DetailProtocolError('DUPLICATE_DETAIL_ID')
            if not a and not p:
                raise DetailProtocolError('EMPTY_DETAIL_REQUEST')
            if set(a)-self._asset_ids.keys() or set(p)-self._problem_ids.keys():
                raise DetailProtocolError('UNKNOWN_CURRENT_ROOT_DETAIL_ID')
            missing = self._missing()
            new_a = set(a) & set(missing['asset_ids'])
            new_p = set(p) & set(missing['problem_ids'])
            if not new_a and not new_p:
                raise DetailProtocolError('NO_NEW_DETAIL_REQUESTED')
        else:
            if response.get('asset_ids') or response.get('problem_ids'):
                raise DetailProtocolError('FULL_REQUEST_MUST_NOT_HIDE_PARTIAL_IDS')
            missing = self._missing()
            a, p = missing['asset_ids'], missing['problem_ids']
            new_a, new_p = set(a), set(p)
            if not new_a and not new_p:
                raise DetailProtocolError('ALREADY_FULLY_EXPANDED')
        old_hash = digest(self._view)
        try:
            updated = expand_context(self._full, self._view,
                                     asset_ids=a, problem_ids=p)
        except ShadowProjectionError as exc:
            raise DetailProtocolError('EXPANSION_FAILED:'+str(exc)) from exc
        self._view = updated
        after = self._missing()
        self._events.append({
            'event': 'MODEL_REQUESTED_DETAIL_EXPANSION',
            'assessor_stage': self.stage,
            'request_sha256': digest(response),
            'reason': response['reason'],
            'requested_asset_ids': list(a),
            'requested_problem_ids': list(p),
            'newly_expanded_asset_count': len(new_a),
            'newly_expanded_problem_count': len(new_p),
            'previous_projection_sha256': old_hash,
            'new_projection_sha256': digest(self._view),
            'remaining_indexed_assets': len(after['asset_ids']),
            'remaining_indexed_problems': len(after['problem_ids']),
        })
        return {'status': 'DETAILS_EXPANDED_NO_PAID', 'view': self.model_input(),
                'retrieval_trace': self.status()}

    def verify_all_reconstructable(self):
        """Check immutable exact round-trip, not model comprehension."""
        all_view = expand_context(self._full, self._view,
                                  asset_ids=self._asset_ids, problem_ids=self._problem_ids)
        all_view.pop(MARKER)
        return digest(all_view) == self._full_hash


def single_or_multi_turn_input_bytes(full_context, requests=(), stage='OPPORTUNITY'):
    """Offline byte accounting: wire/prompt/token billing will differ.

    Assumes the first call receives the index, then each request produces a
    new call with the expanded index.  Native final reply does NOT add a new
    call; its input was the most recent view.  Comparisons exclude system
    prompt and per-call output tokens.
    """
    session = DetailSession(full_context, stage)
    sizes = [len(canonical(session.model_input()))]
    for response in requests:
        out = session.process(response)
        if out['status'] != 'DETAILS_EXPANDED_NO_PAID':
            raise DetailProtocolError('COST_PROJECTION_EXPECTS_ONLY_DETAIL_REQUESTS')
        sizes.append(len(canonical(out['view'])))
    return {
        'full_one_call_context_bytes': len(canonical(full_context)),
        'adaptive_input_bytes_by_turn': sizes,
        'adaptive_input_bytes_total': sum(sizes),
        'estimated_input_byte_saving_pct': round(
            100*(len(canonical(full_context))-sum(sizes))/len(canonical(full_context)), 2),
        'not_token_or_actual_cost_estimate': True,
        'scientific_quality_certified': False,
    }
