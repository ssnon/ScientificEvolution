#!/usr/bin/env python3
"""Read-only lineage and decision audit for the first E2E Scientific Evolution experiment.

No new science or calls. Requires installed ScientificEvolution runtime on PYTHONPATH.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from e2core.core import EvolutionJournal


def decode_model_request(j, c):
    try:
        wire = json.loads(j.raw(c['request_blob']))
        return json.loads(wire['messages'][1]['content'])
    except (TypeError, ValueError, KeyError, IndexError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--experiment', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    p = Path(a.experiment).expanduser().resolve()
    integration = json.loads((p/'integration.json').read_text(encoding='utf8'))
    syn_root = Path(integration['syn_root'])
    j = EvolutionJournal(syn_root)
    s = j.verify()
    imported = {}
    for cohort in integration['cohort_receipts']:
        for x in cohort['imported_ids']:
            imported[x['new_asset_id']] = {
                'cohort': cohort['cohort'], 'original_asset_id': x['old_asset_id'],
                'original_work_mode': x.get('original_work_mode'),
            }
    hist = {aid for aid,v in s.assets.items() if v.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
    if set(imported)!=hist:
        raise ValueError(f'IMPORTED_MAPPING_MISMATCH: receipts={len(imported)} journal={len(hist)}')
    decisions=[]
    for d in s.controller_decisions:
        obj = json.loads(j.raw(d['parsed_blob']))
        req = decode_model_request(j, s.model_calls[d['call_id']])
        referenced=[]
        for action in obj.get('actions',[]):
            ids = action.get('asset_ids',[])
            referenced.append({
                'operation':action.get('operation'),
                'work_id':(action.get('work') or {}).get('id'),
                'original_assets_used':[{'asset_id':x,**imported[x]} for x in ids if x in imported],
                'all_parent_asset_ids':ids,
                'reason':action.get('reason','')[:1500],
                'question':(action.get('work') or {}).get('question','')[:1200]
            })
        decisions.append({
            'decision':d['id'], 'seq':next((e['seq'] for e in j._events() if e['kind']=='CONTROLLER_DECISION' and e['payload']['id']==d['id']),None),
            'disposition':obj.get('disposition'),
            'rationale':obj.get('rationale'),
            'action_count':len(referenced), 'actions':referenced,
            'context_contains_historical_ai_assets':len([x for x in req.get('assets',[]) if x.get('id') in imported]),
            'cohort_receipts_exposed':len(req.get('independent_cohort_history',[])),
            'assessor_opportunities':[(x.get('operation'),x.get('question'),x.get('expected_information_value')) for x in (req.get('independent_opportunity_assessment') or {}).get('opportunities',[])][:12],
            'source_review_changes':(req.get('prior_art_delta') or {}).get('new_or_changed_claims',[])[:12]
        })
    works=[]
    for wid,w in s.work.items():
        pa=w.get('asset_input_ids',[])
        works.append({'id':wid,'mode':w['mode'],'operation':w['operation'],'status':w['status'],
            'question':w.get('question'),
            'parent_asset_ids':pa,'original_cohort_parents':[{'asset_id':x,**imported[x]} for x in pa if x in imported],
            'published':w.get('published',[])})
    live={aid:v for aid,v in s.assets.items() if aid not in hist}
    directly_import_parent=[{'asset_id':aid,'historical_parent_ids':list(set(rec.get('parent_ids',[]))&hist)}
                           for aid,rec in live.items() if set(rec.get('parent_ids',[]))&hist]
    # Count only demonstrated cross-cohort provenance, not any local parent link.
    actual_inherited_work={w['id'] for w in works if w['original_cohort_parents']}
    direct_by_work={aid for aid,v in live.items() if v.get('work_id') in actual_inherited_work}
    seeds=set(x['asset_id'] for x in directly_import_parent)|direct_by_work
    descendants=set(seeds)
    while True:
        new={aid for aid,v in live.items() if set(v.get('parent_ids',[]))&descendants}-descendants
        if not new:break
        descendants|=new
    tool_statuses=Counter()
    for tr in s.tool_results.values():
        try:result=json.loads(j.raw(tr['result_blob']))
        except (ValueError,TypeError):result={}
        tool_statuses[str(result.get('status','UNKNOWN'))]+=1
    report={
        'status':'READ_ONLY_CROSS_GENERATION_TRUTH_AUDIT',
        'root':str(syn_root), 'journal_events':len(j._events()),
        'historical_G0_assets_imported':len(hist),'live_SYN_assets':len(live),
        'cross_cohort_parent_works':sorted(actual_inherited_work),
        'live_assets_with_direct_G0_asset_parents':directly_import_parent,
        'true_G0_inherited_live_descendant_ids':sorted(descendants),
        'true_G0_inherited_live_descendant_count':len(descendants),
        'note':'An INFORMED worker using only SYN-local parents is NOT a G0 descendant. The prior structural_signals count of all assets with parent_ids is not evidence of cross-cohort inheritance.',
        'tool_result_statuses':dict(tool_statuses),
        'decisions':decisions,'works':works,
        'actual_model_calls_uncertain':[x for x,c in s.model_calls.items() if c['state']!='SAVED'],
        'scientific_certification':False
    }
    out=Path(a.out).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError('NO_OVERWRITE:'+str(out))
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('status','journal_events','historical_G0_assets_imported',
         'live_SYN_assets','cross_cohort_parent_works','true_G0_inherited_live_descendant_count',
         'tool_result_statuses','actual_model_calls_uncertain')},indent=2,ensure_ascii=False))

if __name__=='__main__':main()
