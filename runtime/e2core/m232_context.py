"""M23.2 bounded PMI presentation, not loss or reclassification of Journal evidence.

Novelty continues to see its original complete input. PMI receives detailed source
text for the novelty citations relevant to the current claims and an exhaustive
PROVENANCE-ONLY catalog of other sources. Indexed entries are NOT inspected evidence.
P0 is unchanged. All scientific outcomes remain model-authored, provisional.
"""
from __future__ import annotations
import hashlib
import json


def _canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')


def _hash(obj):
    return hashlib.sha256(_canon(obj)).hexdigest()


def build_impact_context(*, program, problems, novelty, evidence, prior_state,
                         prior_art_delta, focus_problem_ids=(), active_problem_ids=()):
    """Deterministic conservative projection for *PMI*, never a source mutation.

    Full source evidence is in the original immutable Journal. For cited evidence,
    preserve the exact input record. For remaining items, only expose identity,
    provenance and class, without a misleading quoted excerpt. The PMI assessor
    must not turn catalog entries into evidence-supported conclusions.
    """
    assert isinstance(program, dict) and isinstance(problems, list)
    assert isinstance(novelty, dict) and isinstance(evidence, list)
    assert isinstance(prior_state, dict)

    inspected = set()
    assessed_ids = set()
    for row in novelty.get('claim_assessments', []):
        if not isinstance(row, dict):
            continue
        assessed_ids.add(row.get('asset_id'))
        inspected.update(x for x in row.get('evidence_ids', []) if isinstance(x, str))
    past = prior_state.get('current_claim_assessments') or {}
    for ident in assessed_ids:
        record = past.get(ident) or {}
        inspected.update(x for x in record.get('evidence_ids', []) if isinstance(x, str))

    focused_sources = []
    catalog_sources = []
    for item in evidence:
        sid = item['evidence_id']
        if sid in inspected:
            focused_sources.append(dict(item))
        else:
            # Claiming PRIOR_OVERLAP based on just this catalog entry must be
            # impossible. Even if the historical source contained full text,
            # PMI did not inspect it in the current call.
            catalog_sources.append({
                'evidence_id': sid,
                'source_kind': item.get('source_kind'),
                'inspection_class': 'CATALOG_ONLY_NOT_INSPECTED_IN_THIS_CALL',
                'registered_inspection_class': item.get('inspection_class'),
                'original_tool_id': item.get('original_tool_id'),
                'original_tool_source_id': item.get('original_tool_source_id'),
                'original_root': item.get('original_root'),
                'source_entry_sha256': _hash(item),
                'detail_present_in_this_call': False,
                'not_independently_certified': True,
            })

    by_id = {p['id']: p for p in problems}
    focused_problems = {'P0'}
    focused_problems.update(x for x in focus_problem_ids if x in by_id)
    focused_problems.update(x for x in active_problem_ids if x in by_id)
    # Full ancestry of the related problem is important for original-P0 impact.
    frontier = list(focused_problems)
    while frontier:
        ident = frontier.pop()
        for parent in by_id.get(ident, {}).get('parents', []):
            if parent in by_id and parent not in focused_problems:
                focused_problems.add(parent)
                frontier.append(parent)

    projected_problems = []
    catalog_problem_ids = []
    for p in problems:
        if p['id'] in focused_problems:
            projected_problems.append(dict(p))
        else:
            catalog_problem_ids.append(p['id'])
            projected_problems.append({
                'id': p['id'],
                'status': p.get('status'),
                'parents': p.get('parents', []),
                'question_preview_not_full_problem': str(p.get('question', ''))[:180],
                'source_entry_sha256': _hash(p),
                'detail_present_in_this_call': False,
            })
    assert len(projected_problems) == len(problems)
    assert {p['id'] for p in projected_problems} == set(by_id)
    assert len(focused_sources) + len(catalog_sources) == len(evidence)

    result = {
        'program': program,
        'current_problems': projected_problems,
        'novelty': novelty,
        'evidence': focused_sources + catalog_sources,
        'original_p0_unchanged': True,
        'prior_working_problem_state': prior_state,
        'prior_art_delta': prior_art_delta,
        'context_scope': {
            'protocol': 'M232_PMI_SCIENTIFICALLY_CONSERVATIVE_SCOPED_EVIDENCE_V1',
            'original_p0_is_present_unchanged': True,
            'all_problem_ids_catalogued': True,
            'all_evidence_ids_catalogued': True,
            'full_evidence_ids': sorted(x['evidence_id'] for x in focused_sources),
            'catalog_only_evidence_ids': sorted(x['evidence_id'] for x in catalog_sources),
            'full_problem_ids': sorted(focused_problems & set(by_id)),
            'catalog_only_problem_ids': catalog_problem_ids,
            'scientific_rule': (
                'Catalog entries are references, not inspected scientific evidence. '
                'Do not infer absence of prior art or absence of a mechanism from this '
                'scoped view. When missing details could change a claim or its P0 '
                'consequences, report UNCHANGED/UNCERTAIN and propose evidence '
                'inspection. No scientific conclusion is certified by this index.'
            ),
        },
    }
    return result
