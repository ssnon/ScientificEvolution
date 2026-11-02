"""M23.2 opt-in canonical-only namespace projection for ON_DEMAND assessors.

Only a presentation change; never modifies scientific records, journals,
resolver behavior or a native model-authored scientific response. Every
compaction is validated against current-Journal source receipts before a call.

FULL (default) preserves historical wire format. COMPACT is intended only
for a newly pinned experimental research ROOT; do not migrate old roots.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os

from .core import EvidenceError

ENV = 'M232_NAMESPACE_MODE'
FULL = 'FULL'
COMPACT = 'COMPACT'
NS_KEY = 'm23_root_scoped_asset_namespace'
MODE_KEY = 'm232_namespace_mode'
VIEW_KEY = 'm232_namespace_view'


def digest(value):
    b = json.dumps(value, ensure_ascii=False, sort_keys=True,
                   separators=(',', ':'), allow_nan=False).encode('utf8')
    return hashlib.sha256(b).hexdigest()


def _fail(reason):
    raise EvidenceError('M232_NAMESPACE_' + reason)


def _mode():
    mode = os.environ.get(ENV, FULL)
    if mode not in {FULL, COMPACT}:
        _fail('INVALID_MODE')
    return mode


def verify_mode(j, controller_mode):
    """Reject namespace-presentation drift across SAVED/INTENT/UNCERTAIN calls.

    This is additional to the original FULL vs ON_DEMAND guard. It must run
    before initiating another paid call, including when it would be cached.
    """
    mode = _mode()
    if mode == COMPACT and controller_mode != 'ON_DEMAND':
        _fail('COMPACT_REQUIRES_ON_DEMAND')
    if j is None:
        if mode == COMPACT:
            _fail('COMPACT_REQUIRES_JOURNAL')
        return mode
    for ident, rec in j.verify().model_calls.items():
        if not ident.startswith(('OPP_', 'CTRL_')):
            continue
        try:
            wire = json.loads(j.raw(rec['request_blob']))
            users = [m for m in wire['messages'] if m['role'] == 'user']
            if len(users) != 1:
                _fail('PRIOR_USER_MESSAGE_AMBIGUOUS')
            previous = json.loads(users[0]['content']).get(MODE_KEY, FULL)
        except (ValueError, TypeError, KeyError) as exc:
            raise EvidenceError('M232_NAMESPACE_PRIOR_REQUEST_UNREADABLE') from exc
        if previous not in {FULL, COMPACT}:
            _fail('PRIOR_REQUEST_UNKNOWN_MODE')
        if previous != mode:
            _fail('MODE_DRIFT')
    return mode


def compact_payload(payload, registered_sources):
    """Remove only repeated canonical IDs and verified original-ID aliases.

    No asset, problem, science content, source contract or other field is
    transformed. There is no arbitrary truncation or ranking of hypotheses.
    Only current-root canonical IDs may be used by the model. Native aliases
    remain in the Journal's verified resolver and can be redisclosed by an
    explicit REQUEST_FULL_CONTEXT in a later model round.
    """
    if not isinstance(payload, dict):
        _fail('PAYLOAD_NOT_OBJECT')
    ns = payload.get(NS_KEY)
    if not isinstance(ns, dict):
        _fail('MISSING_NAMESPACE')
    assets = payload.get('assets')
    if not isinstance(assets, list):
        _fail('ASSETS_NOT_LIST')
    try:
        ids = [a['id'] for a in assets]
    except (TypeError, KeyError) as exc:
        raise EvidenceError('M232_NAMESPACE_ASSET_ID_INVALID') from exc
    ns_ids = ns.get('canonical_asset_ids')
    if (not isinstance(ns_ids, list) or
            len(set(ids)) != len(ids) or len(set(ns_ids)) != len(ns_ids) or
            len(ids) != len(ns_ids) or set(ids) != set(ns_ids)):
        _fail('CANONICAL_ID_MISMATCH')
    aliases = ns.get('verified_original_to_canonical')
    if not isinstance(aliases, dict):
        _fail('ALIAS_MAP_MISSING')
    if not isinstance(registered_sources, (set, frozenset)):
        _fail('REGISTERED_SOURCES_MISSING')
    active_ids = set(ids)
    for historical, row in aliases.items():
        if not isinstance(historical, str) or not isinstance(row, dict):
            _fail('MALFORMED_ALIAS')
        if row.get('canonical_id') not in active_ids:
            _fail('ALIAS_TARGET_NOT_CURRENT')
        proof = row.get('receipt_source_id')
        additional = row.get('supporting_receipt_source_ids', [])
        if (not isinstance(proof, str) or proof not in registered_sources or
                not isinstance(additional, list) or
                any(not isinstance(s, str) or s not in registered_sources
                    for s in additional)):
            _fail('ALIAS_PROOF_INVALID')
    reduced = copy.deepcopy(payload)
    original_digest = digest(payload)
    reduced_ns = reduced[NS_KEY]
    reduced_ns.pop('canonical_asset_ids')
    reduced_ns.pop('verified_original_to_canonical')
    reduced_ns['m232_namespace_index_projection'] = {
        'scope': 'CURRENT_ROOT_ONLY',
        'status': 'EXPERIMENTAL_OPT_IN_LIVE_UNCERTIFIED',
        'canonical_ids_are_the_assets_array_ids': True,
        'current_root_aliases_omitted_count': len(aliases),
        'alias_map_digest_sha256': digest(aliases),
        'backend_receipts_and_reference_validator_unchanged': True,
        'use_current_root_canonical_asset_ids_only': True,
        'request_full_context_for_historical_alias_resolution': True,
        'omission_is_not_absent_science_or_negative_evidence': True,
    }
    reduced[MODE_KEY] = COMPACT
    reduced[VIEW_KEY] = 'CANONICAL_ONLY'
    # Roundtrip of all original model-visible fields, including every
    # science statement, is exact; new mode-only metadata is permitted.
    back = copy.deepcopy(reduced)
    back[NS_KEY] = copy.deepcopy(ns)
    back.pop(MODE_KEY)
    back.pop(VIEW_KEY)
    if digest(back) != original_digest or back != payload:
        _fail('ROUNDTRIP_FAILED')
    if reduced['assets'] != payload['assets'] or reduced['problems'] != payload['problems']:
        _fail('SCIENTIFIC_CONTENT_CHANGED')
    return reduced


def full_after_request(payload):
    """Return the unmodified namespace after model REQUEST_FULL_CONTEXT."""
    if not isinstance(payload, dict) or not isinstance(payload.get(NS_KEY), dict):
        _fail('FULL_REQUEST_MISSING_NAMESPACE')
    result = copy.deepcopy(payload)
    result[MODE_KEY] = COMPACT  # run mode stays pinned even after full rescue
    result[VIEW_KEY] = 'FULL_AFTER_MODEL_REQUEST'
    return result
