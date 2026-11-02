"""M23.2 Part B experimental on-demand Opportunity/Controller gateway.

IMPORTANT: opt-in ONLY. FULL leaves the exact original model-call arguments
unchanged. All rounds use DurableModel.call and therefore preserve durable
requests, saved responses, budgets, and UNKNOWN fail-closed behavior.

This does NOT prove scientific equivalence. Never enable on a historical ROOT.
"""
from __future__ import annotations
import json
import os

from .core import EvidenceError
from .provider import strict_envelope
from .m232_ondemand import DetailSession, DetailProtocolError, PROTOCOL
from .m232_partb import MARKER
from .m232_namespace import (COMPACT, verify_mode, compact_payload,
    full_after_request)

ENV = 'M232_CONTROLLER_DETAIL_MODE'
FULL = 'FULL'
ON_DEMAND = 'ON_DEMAND'
SOURCE_MARKER = 'm232_live_detail_mode'
ADDENDUM = '''\nM23.2 EXPERIMENTAL ON-DEMAND SOURCE ACCESS (advisory only):
Some indexed Asset/Problem entries omit scientific assumptions, predictions,
limitations, and derivations; this is NOT evidence that those details do not
exist. You may answer directly using the exact native Opportunity/Controller
JSON schema if you have sufficiently examined competing mechanisms, opposing
claims, counterexamples and source uncertainty. Alternatively, to inspect
omitted material BEFORE making your decision, return ONLY one JSON object:
{"m232_action":"REQUEST_DETAILS","asset_ids":["current-root asset ID"],
 "problem_ids":[],"reason":"why additional scientific detail is necessary"}
Or request everything with:
{"m232_action":"REQUEST_FULL_CONTEXT","reason":"why broad context is needed"}.
Never invent missing scientific evidence; use only available current-root IDs.
Requests cost additional model calls and must have a substantive reason.
Neither indexed provenance nor this protocol certifies scientific correctness.
No fixed count of detail requests is imposed. A final decision still passes
all ordinary native scientific validators.
'''


def selected_mode(j, model):
    """Disallow mixing FULL and ON_DEMAND in the same research Journal.

    This is evaluated before a candidate assessor call, not after a payment.
    Historical source-pinned Journals must never be migrated in place.
    """
    mode = os.environ.get(ENV, FULL)
    if mode not in {FULL, ON_DEMAND}:
        raise EvidenceError('M232_CONTROLLER_DETAIL_INVALID_MODE')
    if (mode == ON_DEMAND and getattr(model, 'mode', 'EXTERNAL') == 'EXTERNAL'
            and os.environ.get('M232_BUDGET_REQUIRED') != 'YES'):
        raise EvidenceError('M232_ONDEMAND_REQUIRES_EXPLICIT_DEVELOPMENT_BUDGET')
    for ident, rec in j.verify().model_calls.items():
        if not ident.startswith(('OPP_', 'CTRL_')):
            continue
        try:
            request = json.loads(j.raw(rec['request_blob']))
            msgs = request['messages']
            body = json.loads(next(m['content'] for m in msgs if m.get('role') == 'user'))
            older = ON_DEMAND if body.get(SOURCE_MARKER) == ON_DEMAND else FULL
        except (ValueError, TypeError, KeyError, StopIteration) as exc:
            raise EvidenceError('M232_UNREADABLE_PREVIOUS_CONTROLLER_REQUEST') from exc
        if older != mode:
            raise EvidenceError('M232_CONTROLLER_DETAIL_MODE_DRIFT')
    verify_mode(j, mode)
    return mode


def assessor_call(model, j, ident, prompt, full_context, stage, *, mode):
    """Exactly one baseline call if FULL, adaptive rounds ONLY if explicitly requested.

    Return native model text, actual FINAL durable call id, and a provenance
    trace. All model calls are journalled by DurableModel, no direct network IO.
    Strict/unknown failures abort without a scientific decision.
    """
    if mode == FULL:
        return model.call(ident, 'CONTROLLER', None, prompt, full_context), ident, None
    if mode != ON_DEMAND:
        raise EvidenceError('M232_CONTROLLER_DETAIL_INVALID_MODE')
    if stage not in {'OPPORTUNITY', 'CONTROLLER'}:
        raise EvidenceError('M232_INVALID_ASSESSOR_STAGE')
    try:
        session = DetailSession(full_context, stage)
        if not session.verify_all_reconstructable():
            raise EvidenceError('M232_CONTEXT_ROUNDTRIP_FAILED')
    except (DetailProtocolError, ValueError, KeyError) as exc:
        raise EvidenceError('M232_CONTEXT_PREPARATION_FAILED:' + str(exc)) from exc
    namespace_mode = verify_mode(j, mode)
    registered_sources = (set(j.verify().sources) if namespace_mode == COMPACT else None)
    full_namespace_requested = False
    round_no = 0
    current_id = ident
    while True:
        # The stored DetailSession view is immutable to model presentation.
        # Disclose that this is an *opt-in experiment*, no science certification.
        payload = session.model_input()
        payload[MARKER]['status'] = 'EXPERIMENTAL_OPT_IN_LIVE_UNCERTIFIED'
        payload['m232_model_detail_request_contract']['status'] = (
            'EXPERIMENTAL_OPT_IN_LIVE_UNCERTIFIED')
        payload[SOURCE_MARKER] = ON_DEMAND
        payload['m232_detail_origin'] = {
            'first_call_id': ident,
            'stage': stage,
            'round': round_no,
            'initial_full_context_sha256': session.status()['full_context_sha256'],
        }
        if namespace_mode == COMPACT:
            if full_namespace_requested:
                payload = full_after_request(payload)
            else:
                payload = compact_payload(payload, registered_sources)
        namespace_advisory = (
            "\nM23.2 canonical-only namespace view: all visible Asset IDs are "
            "current-root canonical IDs. The detailed historical alias "
            "map is available through REQUEST_FULL_CONTEXT, which also "
            "restores all indexed scientific details. Missing aliases do "
            "not indicate absent historical evidence.\n"
            if namespace_mode == COMPACT else "")
        text = model.call(current_id, 'CONTROLLER', None,
                          prompt + ADDENDUM + namespace_advisory, payload)
        obj = strict_envelope(text)
        if obj is None:
            raise EvidenceError('M232_ADAPTIVE_MODEL_INVALID_JSON_SAVED_NO_AUTO_RETRY')
        try:
            result = session.process(obj)
        except DetailProtocolError as exc:
            raise EvidenceError('M232_INVALID_MODEL_DETAIL_RESPONSE:' + str(exc)) from exc
        if result['status'] == 'NATIVE_ASSESSMENT_NEEDS_ORIGINAL_VALIDATOR':
            trace = session.status()
            return text, current_id, trace
        if result['status'] != 'DETAILS_EXPANDED_NO_PAID':
            raise EvidenceError('M232_UNHANDLED_DETAIL_PROTOCOL_RESULT')
        if namespace_mode == COMPACT and obj.get('m232_action') == 'REQUEST_FULL_CONTEXT':
            full_namespace_requested = True
        # Never reuse a prior model ID for a different wire payload. The old
        # request/response stay in the source Journal, even after crashes.
        round_no += 1
        current_id = f'{ident}_M232R{round_no:04d}'
