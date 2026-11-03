"""M23.5: factual, work-private history of rejected scientific asset proposals.

The source of truth remains the append-only Journal. This module neither repairs
references nor adopts rejected science. It reconstructs a Work's OWN model-authored
asset IDs from saved MODEL_RESPONSE and OUTPUT_VALIDATION events, even when those
steps fall outside the ordinary short worker context window.
"""
from __future__ import annotations
import json
from .worker_json import parse_worker_response


def rejected_asset_fields(asset, state):
    """Deterministic diagnostics for one rejected model-authored asset.

    Never fabricate source/parent aliases or infer scientific truth.
    """
    if not isinstance(asset, dict):
        return {'model_asset_id': None, 'missing_source_ids': [], 'missing_parent_ids': []}
    sid = asset.get('source_ids', [])
    pid = asset.get('parent_ids', [])
    sid = sid if isinstance(sid, list) else []
    pid = pid if isinstance(pid, list) else []
    return {
        'model_asset_id': asset.get('id') if isinstance(asset.get('id'), str) else None,
        'missing_source_ids': [v for v in sid if isinstance(v, str) and v not in state.sources],
        'missing_parent_ids': [v for v in pid if isinstance(v, str) and v not in state.assets],
        'asset_registered': False,
        'raw_model_proposal_preserved': True,
    }


def own_lineage_feedback(j, state, wid):
    """Provide only a Work's own rejected proposals, not sibling/ancestor responses.

    A later successful re-proposal may cause an old ID to be registered; the
    output distinguishes historical rejection from its CURRENT registration.
    """
    work = state.work[wid]
    seen_rejected = set()
    own_registered = set(work.get('published', []))
    # A collided model-local ID in a DIFFERENT Work must never masquerade as
    # this Work's successfully registered rejected proposal.
    own_registered_aliases = {state.assets[x].get('original_model_local_id')
                              for x in own_registered if x in state.assets}
    items = []
    last_model_blob = None
    for step in work['steps']:
        kind = step.get('kind')
        if kind == 'MODEL_RESPONSE':
            last_model_blob = step['raw_blob']
            continue
        if kind != 'OUTPUT_VALIDATION':
            continue
        payload = json.loads(j.raw(step['raw_blob']))
        if not isinstance(payload, dict) or not any(
                isinstance(v, dict) and v.get('kind') == 'ASSET'
                for v in payload.get('rejected', [])):
            continue
        if last_model_blob is None:
            continue
        model_text = json.loads(j.raw(last_model_blob)).get('text', '')
        parsed, _audit = parse_worker_response(model_text)
        model_assets = (parsed.get('assets', [])
                        if isinstance(parsed, dict) and isinstance(parsed.get('assets'), list)
                        else [])
        for reason in payload.get('rejected', []):
            if not isinstance(reason, dict) or reason.get('kind') != 'ASSET':
                continue
            idx = reason.get('index')
            if type(idx) is not int or idx < 0 or idx >= len(model_assets):
                continue
            asset = model_assets[idx]
            if not isinstance(asset, dict):
                continue
            aid = asset.get('id')
            parents = asset.get('parent_ids', [])
            parents = parents if isinstance(parents, list) else []
            sources = asset.get('source_ids', [])
            sources = sources if isinstance(sources, list) else []
            if not isinstance(aid, str):
                continue
            items.append({
                'validation_step': step.get('step'),
                'model_asset_id': aid,
                'error': reason.get('error'),
                'source_ids_as_authored': [v for v in sources if isinstance(v, str)],
                'parent_ids_as_authored': [v for v in parents if isinstance(v, str)],
                'currently_missing_source_ids': [v for v in sources if isinstance(v, str) and v not in state.sources],
                'currently_missing_parent_ids': [v for v in parents if isinstance(v, str) and v not in state.assets],
                'parents_rejected_earlier_in_this_work': [v for v in parents if isinstance(v, str) and v in seen_rejected],
                'currently_registered_as_asset': (aid in own_registered or aid in own_registered_aliases),
                'model_proposal_still_preserved': True,
            })
            seen_rejected.add(aid)
    # Deduplicate unresolved IDs by latest rejection without hiding earlier
    # history: all rejection events stay listed, and every unresolved ID is
    # returned, not merely the last 5 steps.
    unresolved = {}
    for item in items:
        if not item['currently_registered_as_asset']:
            unresolved[item['model_asset_id']] = item
    return {
        'scope': 'OWN_WORK_ONLY',
        'work_id': wid,
        'rejected_asset_events': items,
        'unregistered_proposals': list(unresolved.values()),
        'registered_parent_ids': list(dict.fromkeys(work.get('asset_input_ids', []) + work.get('published', []))),
        'historical_rejections_do_not_certify_science': True,
        'instructions': (
            'A saved MODEL_RESPONSE proposal is NOT a registered scientific Asset. '
            'Only published IDs in the current Journal may be used as registered parents. '
            'Never cite a source ID that is absent or unauthorized in this root. '
            'A historical source_catalog/source_lookup record is not automatically '
            'an authorized publication citation. Reassess, re-propose with valid '
            'provenance or explicitly limit/abandon the hypothesis as you judge '
            'scientifically appropriate. No ID is silently substituted, no '
            'rejected claim automatically accepted, and no further work is forced.'
        ),
    }
