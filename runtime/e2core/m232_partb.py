"""M23.2 Part B: reversible, no-paid OPPORTUNITY/CONTROLLER shadow projection.

This module is NOT connected to the live paid controller. It deliberately
separates potential savings measurement from a change to scientific judgement.
All original source content remains in its immutable Journal; indexed entries
explicitly announce omitted fields and retain ID, claim, provenance and hashes.
"""
from __future__ import annotations
import hashlib
import json
from copy import deepcopy

ASSET_INDEX_FIELDS = (
    'id', 'kind', 'claim', 'scope', 'status', 'origin',
    'parent_ids', 'source_ids', 'source_evidence_classes',
)
PROBLEM_INDEX_FIELDS = (
    'id', 'question', 'parents', 'status', 'original_problem_id',
)
TAG = 'm232_detail_level'
HASH = 'm232_original_sha256'
MARKER = 'm232_shadow_projection'
HISTORICAL = 'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'

class ShadowProjectionError(ValueError):
    pass


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')


def _hash(obj):
    return hashlib.sha256(_canon(obj)).hexdigest()


def _id_map(records, label):
    if not isinstance(records, list):
        raise ShadowProjectionError('INVALID_' + label + '_COLLECTION')
    out={}
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or item['id'] in out:
            raise ShadowProjectionError('INVALID_OR_DUPLICATE_' + label + '_ID')
        out[item['id']] = item
    return out


def _requested(ids, available, label):
    s=set(ids)
    if any(not isinstance(x, str) for x in s) or not s.issubset(available):
        raise ShadowProjectionError('UNKNOWN_' + label + '_EXPANSION_REQUEST')
    return s


def _asset_index(a):
    out={k:deepcopy(a[k]) for k in ASSET_INDEX_FIELDS if k in a}
    out[TAG] = 'INDEX_ONLY_NOT_FULL_SCIENTIFIC_EVIDENCE'
    out[HASH] = _hash(a)
    return out


def _problem_index(p):
    out={k:deepcopy(p[k]) for k in PROBLEM_INDEX_FIELDS if k in p}
    out[TAG]='INDEX_ONLY_NOT_FULL_SCIENTIFIC_CONTEXT'
    out[HASH]=_hash(p)
    return out


def _active_references(ctx, asset_ids):
    """Only ensure directly referenced current work is expanded, not prioritized."""
    keep=set()
    for row in ctx.get('assets',[]):
        if row.get('origin') != HISTORICAL:
            keep.add(row['id'])
    for row in ctx.get('objective_assessments',[]) or []:
        for aid in row.get('supporting_asset_ids',[]) or []:
            if aid in asset_ids:
                keep.add(aid)
    for row in (ctx.get('claim_prior_art_assessment') or {}).get('claim_assessments',[]) or []:
        aid=row.get('asset_id')
        if aid in asset_ids:
            keep.add(aid)
    for row in (ctx.get('problem_level_impact') or {}).get('claim_to_problem',[]) or []:
        aid=row.get('asset_id')
        if aid in asset_ids:
            keep.add(aid)
    return keep


def project_context(full_context, *, expanded_asset_ids=(), expanded_problem_ids=()):
    """Return a reversible *shadow* context; never use as a live model input yet.

    No fixed selection quota; an independent assessor could request *all* IDs.
    This routine alone does not implement that model-facing retrieval protocol.
    """
    if not isinstance(full_context,dict) or MARKER in full_context:
        raise ShadowProjectionError('EXPECTED_UNPROJECTED_FULL_CONTEXT')
    assets=_id_map(full_context.get('assets'), 'ASSET')
    problems=_id_map(full_context.get('problems'), 'PROBLEM')
    if 'P0' not in problems:
        raise ShadowProjectionError('IMMUTABLE_P0_MISSING')
    req_a=_requested(expanded_asset_ids,assets,'ASSET')
    req_p=_requested(expanded_problem_ids,problems,'PROBLEM')
    req_a|=_active_references(full_context,assets)
    req_p.add('P0')
    projected=deepcopy(full_context)
    projected['assets']=[deepcopy(x) if x['id'] in req_a else _asset_index(x)
                         for x in full_context['assets']]
    projected['problems']=[deepcopy(x) if x['id'] in req_p else _problem_index(x)
                           for x in full_context['problems']]
    # A precise, explicit disclosure to reviewers about inaccessible details.
    projected[MARKER]={
        'status':'OFFLINE_SHADOW_NOT_AUTHORIZED_FOR_PAID_RESEARCH',
        'catalog_record_is_not_a_full_scientific_assessment':True,
        'complete_original_records_held_in_pinned_append_only_journal':True,
        'source_citation_registration_is_not_changed':True,
        'indexed_assets_have_omitted_assumptions_predictions_limitations_delta':True,
        'indexed_problems_have_omitted_decomposition_and_contribution':True,
        'no_fixed_quota_on_details_to_expand':True,
        'not_evidence_of_equivalent_scientific_judgement':True,
    }
    if _id_map(projected['assets'],'ASSET').keys()!=assets.keys():
        raise ShadowProjectionError('ASSET_ID_COVERAGE_LOST')
    if _id_map(projected['problems'],'PROBLEM').keys()!=problems.keys():
        raise ShadowProjectionError('PROBLEM_ID_COVERAGE_LOST')
    if projected['program'] != full_context['program'] or \
       next(x for x in projected['problems'] if x['id']=='P0') != problems['P0']:
        raise ShadowProjectionError('P0_OR_PROGRAM_CHANGED')
    return projected


def expand_context(full_context, projected, *, asset_ids=(), problem_ids=()):
    """Simulate exact detail retrieval from verified full context, fail closed."""
    if not isinstance(projected,dict) or MARKER not in projected:
        raise ShadowProjectionError('NOT_A_SHADOW_CONTEXT')
    original_assets=_id_map(full_context['assets'],'ASSET')
    original_problems=_id_map(full_context['problems'],'PROBLEM')
    if (_id_map(projected.get('assets'),'ASSET').keys()!=original_assets.keys() or
            _id_map(projected.get('problems'),'PROBLEM').keys()!=original_problems.keys()):
        raise ShadowProjectionError('SHADOW_COVERAGE_CHANGED')
    requested_assets=_requested(asset_ids,original_assets,'ASSET')
    requested_problems=_requested(problem_ids,original_problems,'PROBLEM')
    updated=deepcopy(projected)
    for field,original,req in (('assets',original_assets,requested_assets),
                              ('problems',original_problems,requested_problems)):
        for i,row in enumerate(updated[field]):
            true=original[row['id']]
            if row.get(TAG) is not None:
                expected=_asset_index(true) if field=='assets' else _problem_index(true)
                if row!=expected:
                    raise ShadowProjectionError('INDEX_OR_RECORD_TAMPER')
            elif row!=true:
                raise ShadowProjectionError('FULL_RECORD_TAMPER')
            if row['id'] in req:
                updated[field][i]=deepcopy(true)
    if updated.get('program')!=full_context['program']:
        raise ShadowProjectionError('PROGRAM_CHANGED')
    for k,v in full_context.items():
        if k not in ('assets','problems') and updated.get(k)!=v:
            raise ShadowProjectionError('NONINDEXED_CONTEXT_CHANGED:'+k)
    return updated


def audit_shadow(full_context, projected):
    if MARKER not in projected:
        raise ShadowProjectionError('EXPECTED_SHADOW_CONTEXT')
    a_full=_id_map(full_context['assets'],'ASSET')
    p_full=_id_map(full_context['problems'],'PROBLEM')
    a_shadow=_id_map(projected['assets'],'ASSET')
    p_shadow=_id_map(projected['problems'],'PROBLEM')
    expanded=expand_context(full_context,projected,
                            asset_ids=a_full, problem_ids=p_full)
    reconstructed=deepcopy(expanded)
    reconstructed.pop(MARKER)
    if reconstructed!=full_context:
        raise ShadowProjectionError('FULL_ROUNDTRIP_FAILED')
    full_bytes=len(_canon(full_context));shadow_bytes=len(_canon(projected))
    return {
        'status':'PART_B_SHADOW_NO_PAID_NO_RUNTIME_CHANGE',
        'full_context_bytes':full_bytes,
        'shadow_context_bytes':shadow_bytes,
        'projected_byte_reduction_pct':round(100*(full_bytes-shadow_bytes)/full_bytes,2),
        'asset_ids_preserved':len(a_full)==len(a_shadow),
        'problem_ids_preserved':len(p_full)==len(p_shadow),
        'historical_assets':sum(1 for x in a_full.values() if x.get('origin')==HISTORICAL),
        'full_assets':sum(1 for x in a_shadow.values() if x.get(TAG) is None),
        'index_assets':sum(1 for x in a_shadow.values() if x.get(TAG) is not None),
        'full_problems':sum(1 for x in p_shadow.values() if x.get(TAG) is None),
        'index_problems':sum(1 for x in p_shadow.values() if x.get(TAG) is not None),
        'full_roundtrip_exact':True,
        'original_full_context_sha256':_hash(full_context),
        'reexpanded_context_sha256':_hash(reconstructed),
        'paid_model_calls':0,
        'quality_certified':False,
        'warning':'This does NOT change Opportunity/Controller yet and does NOT prove scientific equivalence.',
    }
