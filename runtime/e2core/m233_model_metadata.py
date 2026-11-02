"""Experimental, reversible *presentation-only* reduction of M23.2 index metadata.

The scientific Journal, source identity and DetailSession retain every original
hash and full record. This module never changes scientific content, evidence,
parent/source IDs or the science validator. Newly pinned ON_DEMAND roots only.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
import re

from .core import EvidenceError
from .m232_partb import TAG, HASH, MARKER

ENV = 'M233_MODEL_METADATA_MODE'
FULL = 'FULL'
SEPARATE = 'SEPARATE'
MODE_KEY = 'm233_model_metadata_mode'
VIEW_KEY = 'm233_indexed'
CONTRACT_KEY = 'm233_index_metadata_contract'
KNOWN_TAGS = {
    'assets': 'INDEX_ONLY_NOT_FULL_SCIENTIFIC_EVIDENCE',
    'problems': 'INDEX_ONLY_NOT_FULL_SCIENTIFIC_CONTEXT',
}


def _fail(text):
    raise EvidenceError('M233_MODEL_METADATA_' + text)


def digest(obj):
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf8')
    return hashlib.sha256(data).hexdigest()


def verify_metadata_mode(j, controller_mode):
    """Pin presentation mode to previous OPP/CTRL requests, including INTENT."""
    mode = os.environ.get(ENV, FULL) or FULL
    if mode not in {FULL, SEPARATE}:
        _fail('INVALID_MODE')
    if mode == SEPARATE and controller_mode != 'ON_DEMAND':
        _fail('REQUIRES_ON_DEMAND')
    if j is None:
        if mode == SEPARATE:
            _fail('JOURNAL_REQUIRED')
        return mode
    for ident, record in j.verify().model_calls.items():
        if not ident.startswith(('OPP_', 'CTRL_')):
            continue
        try:
            wire = json.loads(j.raw(record['request_blob']))
            users = [m for m in wire['messages'] if m.get('role') == 'user']
            if len(users) != 1:
                _fail('AMBIGUOUS_PREVIOUS_USER_CONTENT')
            older = json.loads(users[0]['content']).get(MODE_KEY, FULL)
        except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
            raise EvidenceError('M233_MODEL_METADATA_PRIOR_REQUEST_UNREADABLE') from exc
        if older not in {FULL, SEPARATE}:
            _fail('UNKNOWN_PRIOR_MODE')
        if older != mode:
            _fail('MODE_DRIFT')
    return mode


def compact_presentation_metadata(payload):
    """Remove INDEX hash/verbose tag from wire *only*, keep indexedness explicit.

    Caller MUST verify DetailSession.verify_all_reconstructable() before this;
    the source of truth is the full Journal / unmodified DetailSession. Every
    model-visible science field and the array ordering remain unchanged.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get(MARKER), dict):
        _fail('NOT_A_VERIFIED_ON_DEMAND_VIEW')
    if MODE_KEY in payload or CONTRACT_KEY in payload:
        _fail('ALREADY_PROJECTED')
    revised = copy.deepcopy(payload)
    counts = {}
    for category, expected_tag in KNOWN_TAGS.items():
        rows = revised.get(category)
        if not isinstance(rows, list):
            _fail('RECORDS_NOT_ARRAY:' + category)
        indexed = 0
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str):
                _fail('MALFORMED_RECORD:' + category)
            if row['id'] in seen:
                _fail('DUPLICATE_ID:' + category)
            seen.add(row['id'])
            if VIEW_KEY in row:
                _fail('PRESENTATION_FLAG_CONFLICT')
            tag_present = TAG in row
            hash_present = HASH in row
            if tag_present != hash_present:
                _fail('INCONSISTENT_INDEX_MARKERS:' + category)
            if not tag_present:
                continue  # full scientific record is unchanged, including P0
            if row[TAG] != expected_tag:
                _fail('UNRECOGNIZED_INDEX_TAG:' + category)
            if not isinstance(row[HASH], str) or re.fullmatch('[0-9a-f]{64}', row[HASH]) is None:
                _fail('INVALID_INDEX_HASH:' + category)
            row.pop(TAG)
            row.pop(HASH)
            row[VIEW_KEY] = True
            indexed += 1
        counts[category] = indexed
    revised[MODE_KEY] = SEPARATE
    revised[CONTRACT_KEY] = {
        'status': 'OPT_IN_PRESENTATION_NOT_SCIENCE_CERTIFICATION',
        'indexed_marker': VIEW_KEY,
        'indexed_marker_true_means_original_assumptions_predictions_limitations_or_derivations_may_be_omitted': True,
        'indexed_asset_count': counts['assets'],
        'indexed_problem_count': counts['problems'],
        'original_index_hashes_retained_in_unmodified_DetailSession_and_Journal': True,
        'REQUEST_DETAILS_or_REQUEST_FULL_CONTEXT_restores_scientific_details': True,
        'do_not_treat_indexed_row_as_full_scientific_evidence': True,
    }
    # Fail-closed check: reconstruct every field using ONLY saved original values;
    # this verifies that there are no additional differences.
    expected = copy.deepcopy(payload)
    for category in KNOWN_TAGS:
        for row in expected[category]:
            if TAG in row:
                del row[TAG]
                del row[HASH]
                row[VIEW_KEY] = True
    expected[MODE_KEY] = SEPARATE
    expected[CONTRACT_KEY] = copy.deepcopy(revised[CONTRACT_KEY])
    if expected != revised or payload.get('program') != revised.get('program'):
        _fail('ROUNDTRIP_MISMATCH')
    return revised


def restore_from_unmodified_view(original, projected):
    """Read-only audit; refuse to reconstruct if *any* projected byte differs."""
    if compact_presentation_metadata(original) != projected:
        _fail('RESTORE_FAILED_MISMATCH')
    return copy.deepcopy(original)
