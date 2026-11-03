"""M23.6: work-private reference contract and bounded metadata-delivery correction.

This module cannot authorize assets, repair citations, change scientific dispositions,
or see any other Work's model-authored history. Journal State.apply is authoritative.
"""
from __future__ import annotations

import json

REPAIR_MARKER = 'METADATA_REPAIR_REQUIRED'
REPAIR_PENDING = 'METADATA_REPAIR_PENDING'


def parent_reference_contract(state, work):
    """Exact Work-scoped publication parents, never historical names or aliases.

    State.apply('ASSET_PUBLISHED') authorizes pinned asset_input_ids and only
    assets already published by this Work, after their global registration.
    """
    pinned = list(dict.fromkeys(work.get('asset_input_ids', [])))
    self_published = list(dict.fromkeys(work.get('published', [])))
    # A journal with a missing authorized parent is corrupt, not a new alias
    # opportunity. Fail closed instead of silently hiding an inconsistency.
    missing = [x for x in pinned + self_published if x not in state.assets]
    if missing:
        raise ValueError('M236_AUTHORIZED_PARENT_NOT_REGISTERED:' + repr(missing))
    registered = list(dict.fromkeys(pinned + self_published))
    if work['mode'] == 'FRESH':
        if pinned or any(state.assets[a].get('work_id') != work['id'] for a in self_published):
            raise ValueError('M236_FRESH_LINEAGE_INVARIANT_VIOLATED')
    return {
        'scope': 'CURRENT_WORK_ONLY',
        'work_id': work['id'],
        'mode': work['mode'],
        'allowed_registered_parent_ids': registered,
        'pinned_input_parent_ids': pinned,
        'own_published_parent_ids': self_published,
        'registered_asset_count_in_root': len(state.assets),
        'not_automatically_authorized': (
            'historical author IDs, carried/upstream IDs, unregistered proposals, '
            'and other current-root assets not pinned to this Work'
        ),
        'parentless_new_asset_permitted': True,
        'scientific_lineage_instruction': (
            'For assets[].parent_ids use ONLY exact allowed_registered_parent_ids '
            'or IDs of new assets actually accepted earlier in this same response. '
            'Do not invent A_CARRY_ IDs or assume a historical asset name is '
            'an authorized parent. Use parent_ids=[] only when the scientific '
            'claim is genuinely independent; do not remove a necessary parent '
            'just to pass validation. This contract is not permission to cite '
            'other sources or a judgement about scientific truth.'
        ),
    }


def metadata_repair_notices(journal, work):
    """Persisted count survives engine/model process restart without new DB."""
    count = 0
    for step in work.get('steps', []):
        if step.get('kind') != 'OUTPUT_VALIDATION':
            continue
        data = json.loads(journal.raw(step['raw_blob']))
        if isinstance(data, dict) and data.get('status') == REPAIR_MARKER:
            count += 1
    return count


def metadata_repair_context(journal, work):
    count = metadata_repair_notices(journal, work)
    return {
        'scope': 'THIS_WORK_ONLY',
        'repair_notice_count': count,
        'previous_metadata_delivery_repair_notice': bool(count),
        'further_metadata_only_repair_notices_available': count == 0,
        'not_a_science_step_or_generation_limit': True,
        'may_repropose_with_authorized_parents': True,
        'may_withdraw_rejected_asset': True,
        'may_continue_research_or_use_tools': True,
        'may_return_or_hold_without_asset_if_scientifically_appropriate': True,
        'instructions': (
            'A RETURN/HOLD containing rejected assets with no accepted asset is '
            'not treated as successfully delivered science. After one recorded '
            'metadata delivery notice, independently decide to revise, withdraw, '
            'continue research, request a tool, or return without a new asset. '
            'An additional all-rejected RETURN/HOLD will be blocked as an '
            'operational metadata delivery failure; this is not proof a '
            'hypothesis was false. Prior raw responses remain preserved.'
        ),
    }


def all_asset_publications_rejected(rejected, accepted):
    """True when a final response offered assets but delivered no asset.

    Successfully registered PROBLEM metadata alone must not hide the loss of
    every proposed ASSET. A partially accepted ASSET batch needs no forced
    correction; its accepted results already reached the Journal.
    """
    return (any(isinstance(r, dict) and r.get('kind') == 'ASSET' for r in rejected)
            and not any(k == 'ASSET_PUBLISHED' for k, _ in accepted))
