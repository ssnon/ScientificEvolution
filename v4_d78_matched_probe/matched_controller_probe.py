#!/usr/bin/env python3
"""One operator-triggered V4 Controller decision from an existing paired fork.

This is a matched *decision* audit, NOT proof that the ordinary autonomous
scheduler would select this timing. Never rewrites history or FRESH inputs.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from e2core.core import EvolutionJournal, EvidenceError, guard, sha, canon
from e2core.engine import Engine
from e2core.provider import DurableModel
import scientific_closed_loop_v3 as v3
import scientific_research_readiness_v4 as v4
import scientific_problem_evolution as spe

EXPERIMENT_RECEIPT = 'OPERATOR_CONTROLLED_PAIRED_RESEARCH_BRANCH_20261029'
MODEL_DEFAULT = 'openai/gpt-5.6-luna'

def preflight(root):
    v3.source_code_guard()
    v4.inspect(root)
    j=EvolutionJournal(root)
    s=j.verify()
    events=j._events()
    receipts=[r for r in events if r['kind']=='OPERATIONAL_PAUSE'
              and r['payload'].get('reason')==EXPERIMENT_RECEIPT]
    guard(len(receipts)==1,'PAIRED_RECEIPT_REQUIRED')
    rec=receipts[0]['payload']
    condition=rec.get('condition')
    guard(condition in {'CONTROL','OPERATOR_EVIDENCE'},'INVALID_PAIR_CONDITION')
    guard(len(s.controller_decisions)==77 and s.controller_decisions[-1]['id']=='D00078',
          'NOT_UNMODIFIED_D00078_DECISION_STATE')
    guard(len(s.assets)==123,'ASSETS_CHANGED_SINCE_PAIRED_FORK')
    guard(sum(w['status'] in {'QUEUED','ACTIVE'} and w['mode']=='FRESH' for w in s.work.values())==1,
          'EXPECTED_ONE_UNFINISHED_FRESH_WORK')
    guard(not any(w['mode']=='INFORMED' and w['status'] in {'QUEUED','ACTIVE'} for w in s.work.values()),
          'PREEXISTING_INFORMED_WORK')
    prior=[sid for sid in s.sources if sid.startswith('SRC_PRIOR_PMC4129422_')]
    guard(len(prior)==(7 if condition=='OPERATOR_EVIDENCE' else 0),
          'INCONSISTENT_OPERATOR_SOURCE_COUNT')
    # Operator receipt is at seq 1871 in both, followed only by the 7 evidence
    # registration events in the evidence condition. Nothing paid or scientific
    # has been committed in these paired probe roots yet.
    guard(receipts[0]['seq']==1871 and len(events)==(1878 if condition=='OPERATOR_EVIDENCE' else 1871),
          'FORK_CHANGED_AFTER_PREPARATION')
    replacement=v3._recovery_receipt(j)
    guard({cid for cid,x in s.model_calls.items() if x['state']!='SAVED'}=={replacement['original_call_id']},
          'UNACCOUNTED_UNCERTAIN_OR_PENDING_MODEL_CALL')
    return {
        'root':str(root),'condition':condition,
        'head_sha256':sha(canon(events[-1])),
        'last_controller':'D00078',
        'prior_art_records':len(prior),
        'fresh_worker_unchanged':True,
        'model_outcome_uncertainty_historical_only':True,
        'controller_probe':'EXPLICIT_OPERATOR_TRIGGER_NOT_AUTONOMOUS_SCHEDULING',
    }

def decision_report(root,starting,model_result,paid_count):
    j=EvolutionJournal(root)
    s=j.verify()
    last=s.controller_decisions[-1]['id']
    entry=None
    if last!='D00078':
        r=spe.audit(str(root))['records'][-1]
        assessed=[]
        for x in r.get('claim_assessments',[]):
            ids=x.get('evidence_ids',[])
            if x.get('asset_id') in {
                    'A_mode_specific_covariance_test_003',
                    'A_temporal_SERS_mechanism_ambiguity_002',
                    'A_NPoM_gap_dielectric_confound_001',
                    'A_conditional_scattering_normalization_test_001',
                } or any(y.startswith('SRC_PRIOR_PMC4129422_') for y in ids):
                assessed.append({k:x.get(k) for k in (
                    'asset_id','relation','evidence_ids','remaining_conditional_claim',
                    'specific_differentiating_prediction','strongest_competing_explanation')})
        entry={
            'decision_id':last,
            'controller_disposition':r.get('controller_disposition'),
            'actions':r.get('controller_actions',[]),
            'novelty_assessments':assessed,
            'prior_art_delta':r.get('prior_art_delta'),
            'problem_impact_delta':r.get('problem_impact_delta'),
            'problem_level_impact':r.get('problem_level_impact'),
            'rejected_prior_art_assessments':r.get('rejected_prior_art_assessments',[]),
            'rejected_impact_inferences':r.get('rejected_impact_inferences',[]),
        }
    return {
        'scientific_certification':False,
        'experiment':'ONE_MATCHED_CONTROLLER_DECISION_WITH_OPERATOR_TRIGGER',
        'not_autonomous_scheduling':True,
        'starting_state':starting,
        'new_paid_calls':paid_count,
        'result':model_result,
        'decisions_added':len(s.controller_decisions)-77,
        'science_assets_added':len(s.assets)-123,
        'new_works':[w['id'] for w in s.work.values() if w['id']!='W_fresh_primary_temporal_sers_baseline_001' and w.get('status') in {'QUEUED','ACTIVE'}],
        'decision_audit':entry,
        'head_sha256':sha(canon(j._events()[-1]))
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path)
    p.add_argument('--preflight',action='store_true')
    p.add_argument('--paid',action='store_true')
    p.add_argument('--model',default=MODEL_DEFAULT)
    p.add_argument('--max-new-calls',type=int,default=6)
    p.add_argument('--max-tokens',type=int,default=16000)
    a=p.parse_args()
    root=a.root.expanduser().resolve(strict=True)
    start=preflight(root)
    print(json.dumps({'event':'MATCHED_CONTROLLER_PREFLIGHT',**start},ensure_ascii=False),flush=True)
    if a.preflight:return
    guard(a.paid and os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES',
          'EXPLICIT_PAID_APPROVAL_REQUIRED')
    guard(4<=a.max_new_calls<=8,'MAX_NEW_CALLS_RANGE_4_TO_8')
    output=a.out.expanduser().absolute() if a.out else None
    guard(output is not None and not output.exists() and output.parent.is_dir(),
          'NEW_OUTPUT_PATH_REQUIRED')
    # Original V4 controller function and its patched V4 advisories are used.
    # Intentional diagnostic intervention: bypass scheduler ONCE, not the model's
    # independent choice of which Work to create. No Work is automatically run.
    with v3._source_locks(root):
        guard(preflight(root)==start,'SOURCE_CHANGED_DURING_PROBE_SETUP')
        j=EvolutionJournal(root)
        gateway=DurableModel(j,approved=True,max_new_calls=a.max_new_calls,
                             model=a.model,max_tokens=a.max_tokens)
        engine=Engine(j,gateway,serial_fair=False,
                      science_cpu_seconds=120,science_wall_seconds=160)
        ident=engine._next_controller_id()
        guard(ident=='D00079','UNEXPECTED_NEXT_DECISION_ID')
        with v4.runtime():
            try:
                result=v3.controller_v3(engine,ident)
            except EvidenceError as exc:
                result={'status':'OPERATIONAL_ERROR','detail':str(exc)}
        report=decision_report(root,start,result,gateway.new_calls)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'event':'MATCHED_CONTROLLER_REPORT_SAVED',
                      'path':str(output),'decision_added':report['decisions_added'],
                      'new_paid_calls':report['new_paid_calls'],
                      'controller_status':result.get('status'),
                      'new_works':report['new_works']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
