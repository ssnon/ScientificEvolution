#!/usr/bin/env python3
"""Bounded, fail-closed multi-segment G14 continuation.

Runs the EXISTING G14_LEVEL2_TRACE_CONTINUATION_20261030.py once per
segment, preserves its exact-ID guard and journal provenance, and checks
read-only Level-II traces between segments. Does not alter scientific
prompts, validate or rewrite assets, or explicitly request G15. It checks phase between segments. No science verdict
is inferred from a stalled operational batch.

Usage after setting PYTHONPATH as for the existing G14 command:
    python G14_BATCH_CONTINUATION_20261030.py --segments 4 --paid
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

EXPECTED_EVENTS = 1333
EXPECTED_HEAD = '08c1b3a1c311f9f1d0e7acef0ad783802d6001707b764e2a4910209137e8adb3'
EXPECTED_ACTIVE = 'W_P0_primary_literature_matrix_003'
RUNNER_NAME = 'G14_LEVEL2_TRACE_CONTINUATION_20261030.py'


def state_summary(snapshot: dict) -> dict:
    works = snapshot.get('work_research_traces') or {}
    decisions = snapshot.get('controller_decisions') or []
    calls = snapshot.get('model_call_manifest') or []
    head = snapshot.get('journal_head') or {}
    return {
        'generation': snapshot.get('generation'),
        'phase': snapshot.get('phase'),
        'events': head.get('events'),
        'head_sha256': head.get('head_sha256'),
        'assets': snapshot.get('asset_count'),
        'actual_fulltext_receipts': snapshot.get('actual_fulltext_receipts'),
        'work_statuses': {k:v.get('status') for k,v in works.items()},
        'active_work_ids': [k for k,v in works.items() if v.get('status') in {'ACTIVE','QUEUED'}],
        'controller_disposition': decisions[-1].get('disposition') if decisions else None,
        'not_all_model_calls_saved': [x.get('id') for x in calls if x.get('state')!='SAVED'],
        'new_population_assets': snapshot.get('assets_added_during_population') or [],
        'tool_receipts': len(snapshot.get('tool_receipts') or []),
        'validation_failures': len(snapshot.get('validation_failures') or []),
    }


def reason_to_pause(previous: dict, current: dict, *, first: bool = False) -> str | None:
    if current['generation'] != 14 or current['phase'] != 'POPULATION':
        return 'G14_PHASE_OR_GENERATION_CHANGED'
    if current['not_all_model_calls_saved']:
        return 'UNSAVED_OR_UNCERTAIN_PROVIDER_CALL'
    if current['controller_disposition'] != 'ONGOING':
        return 'SCIENTIFIC_DISPOSITION_NOT_ONGOING'
    if not current['active_work_ids']:
        return 'NO_ACTIVE_OR_QUEUED_WORK'
    if first:
        if current['events'] != EXPECTED_EVENTS or current['head_sha256'] != EXPECTED_HEAD:
            return 'INITIAL_JOURNAL_HEAD_UNEXPECTED'
        if EXPECTED_ACTIVE not in current['active_work_ids']:
            return 'EXPECTED_LITERATURE_WORK_NOT_ACTIVE'
    else:
        if not isinstance(current['events'],int) or current['events']<=previous['events']:
            return 'JOURNAL_NOT_ADVANCED'
        if current['assets'] < previous['assets'] or current['actual_fulltext_receipts']<previous['actual_fulltext_receipts']:
            return 'AUDIT_COUNTER_REGRESSION'
    return None


def is_tangible_progress(a,b):
    """An OPERATIONAL signal only; does not judge real scientific merit."""
    return any([
        b['assets'] > a['assets'],
        b['actual_fulltext_receipts'] > a['actual_fulltext_receipts'],
        b['work_statuses'] != a['work_statuses'],
    ])


def check_simulated():
    raw={'generation':14,'phase':'POPULATION',
         'journal_head':{'events':EXPECTED_EVENTS,'head_sha256':EXPECTED_HEAD},
         'asset_count':429,'actual_fulltext_receipts':2,
         'work_research_traces':{EXPECTED_ACTIVE:{'status':'ACTIVE'}},
         'controller_decisions':[{'disposition':'ONGOING'}],
         'model_call_manifest':[{'id':'M','state':'SAVED'}],
         'assets_added_during_population':[]}
    x=state_summary(raw)
    assert reason_to_pause(x,x,first=True) is None
    next_raw={**raw,'journal_head':{'events':1344,'head_sha256':'a'*64},'asset_count':430}
    y=state_summary(next_raw)
    assert reason_to_pause(x,y) is None
    assert is_tangible_progress(x,y)
    bad={**next_raw,'controller_decisions':[{'disposition':'HOLD_WITH_RATIONALE'}]}
    assert reason_to_pause(y,state_summary(bad))=='SCIENTIFIC_DISPOSITION_NOT_ONGOING'
    assert reason_to_pause(x,x)=='JOURNAL_NOT_ADVANCED'
    unknown={**raw,'model_call_manifest':[{'id':'M','state':'UNCERTAIN'}]}
    assert reason_to_pause(x,state_summary(unknown),first=True)=='UNSAVED_OR_UNCERTAIN_PROVIDER_CALL'
    print(json.dumps({'status':'G14_BATCH_SELFTEST_OK','checks':6,
                      'paid_calls':0,'journal_modified':False},ensure_ascii=False))


def checkpoint(runner: Path, experiment: Path, trace_dir: Path, env: dict, log_dir: Path, label:str):
    cmd=[sys.executable,str(runner),'checkpoint','--experiment',str(experiment),'--trace-dir',str(trace_dir)]
    proc=subprocess.run(cmd,text=True,encoding='utf-8',errors='replace',capture_output=True,env=env)
    (log_dir/f'{label}_checkpoint_output.txt').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
    if proc.returncode:raise RuntimeError(f'CHECKPOINT_FAILED_{label}: '+proc.stderr[-1500:])
    lines=[line for line in proc.stdout.splitlines() if line.strip().startswith('{')]
    if not lines:raise RuntimeError('CHECKPOINT_NO_JSON_'+label)
    info=json.loads(lines[-1]);assert info['status']=='G14_SCIENTIFIC_PROVENANCE_CHECKPOINT_NO_PAID',info
    path=Path(info['file']).resolve(strict=True)
    if not path.is_relative_to(trace_dir.resolve()):raise RuntimeError('UNEXPECTED_TRACE_DESTINATION')
    with path.open(encoding='utf-8') as f: report=json.load(f)
    return state_summary(report),str(path)


def run_segment(runner,exp,trace_dir,env,log_path):
    cmd=[sys.executable,str(runner),'run','--experiment',str(exp),
         '--trace-dir',str(trace_dir),'--paid','--model','openai/gpt-5.6-luna',
         '--bootstrap-peers','2','--slice-budget','8','--checkpoint-iterations','12',
         '--max-parallel','2','--max-tokens','16000',
         '--science-cpu-seconds','120','--science-wall-seconds','160',
         '--notice-every-segments','1','--max-operational-segments','1']
    paid_env={**env,'FAKG_RESEARCH_ALLOW_PAID':'YES'}
    with log_path.open('x',encoding='utf-8') as log:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding='utf-8',errors='replace',env=paid_env,bufsize=1)
        try:
            for line in proc.stdout:
                sys.stdout.write(line);sys.stdout.flush()
                log.write(line);log.flush()
            return proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            raise


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--segments',type=int,default=4)
    ap.add_argument('--paid',action='store_true',help='Explicit authorization for paid model calls')
    ap.add_argument('--selftest',action='store_true')
    args=ap.parse_args()
    if args.selftest:return check_simulated()
    if not 1<=args.segments<=6:ap.error('--segments must be in 1..6')
    if not args.paid:ap.error('Explicit --paid is required to run any segment')
    project=Path.home()/'ScientificEvolution'
    runner=project/RUNNER_NAME
    exp=Path.home()/'ScientificEvolution_runs'/'AUTONOMOUS_POPULATION_20261029'
    trace_dir=Path.home()/'ScientificEvolution_level2_traces'/'G14'
    if not runner.is_file():raise RuntimeError('G14_RUNNER_NOT_FOUND:'+str(runner))
    if not exp.is_dir():raise RuntimeError('EXPERIMENT_MISSING:'+str(exp))
    trace_dir.mkdir(parents=True,exist_ok=True)
    session_dir=trace_dir/('G14_BATCH_FROM_1333_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    session_dir.mkdir(parents=False,exist_ok=False)
    stopper=exp/'STOP_REQUESTED'
    env=os.environ.copy();env.pop('FAKG_RESEARCH_ALLOW_PAID',None)
    env['PYTHONPATH']=':'.join(str(p) for p in (
        project/'G14_DOI_OPEN_PDF_BRIDGE_20261030',
        project/'SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_REPAIR_20261030',
        project/'SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030',
        project/'AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029',
        project/'runtime'))
    history=[];last=None;stalled=0;reason='BOUNDED_SEGMENTS_COMPLETE'
    # Keeping marker in place through the free preflight prevents accidental
    # continuation while the current head is being verified.
    stopper.touch(exist_ok=True)
    try:
        before,path=checkpoint(runner,exp,trace_dir,env,session_dir,'initial')
        reason_to_stop=reason_to_pause(before,before,first=True)
        if reason_to_stop:
            raise RuntimeError('BATCH_PREFLIGHT_PAUSE:'+reason_to_stop)
        print(json.dumps({'status':'G14_BATCH_PREFLIGHT_OK_NO_PAID',
                          'segments_requested':args.segments,'start':before,
                          'trace':path},ensure_ascii=False),flush=True)
        last=before
        for i in range(1,args.segments+1):
            # Marker is absent only during the paid execution. User may touch
            # STOP_REQUESTED; we detect it after this operational segment.
            stopper.unlink(missing_ok=True)
            print(json.dumps({'status':'G14_BATCH_SEGMENT_BEGIN',
                              'segment':i,'of':args.segments},ensure_ascii=False),flush=True)
            code=run_segment(runner,exp,trace_dir,env,session_dir/f'segment_{i:02d}.log')
            user_stop=stopper.exists()
            stopper.touch(exist_ok=True)
            curr,trace_file=checkpoint(runner,exp,trace_dir,env,session_dir,f'after_{i:02d}')
            row={'segment':i,'exit_code':code,'trace':trace_file,
                 'before':last,'after':curr,'tangible_progress':is_tangible_progress(last,curr)}
            history.append(row)
            (session_dir/'batch_summary.json').write_text(json.dumps({'history':history,'reason':reason},
                                  indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            print(json.dumps({'status':'G14_BATCH_SEGMENT_SUMMARY','segment':i,
                  'exit_code':code,'events':curr['events'],'assets':curr['assets'],
                  'fulltext_receipts':curr['actual_fulltext_receipts'],
                  'active_work_ids':curr['active_work_ids'],
                  'disposition':curr['controller_disposition'],
                  'tangible_progress':row['tangible_progress'],
                  'trace':trace_file},ensure_ascii=False),flush=True)
            if code!=0:reason='RUNNER_NONZERO_EXIT';break
            if user_stop:reason='USER_STOP_REQUESTED';break
            safety=reason_to_pause(last,curr)
            if safety:reason=safety;break
            stalled=0 if row['tangible_progress'] else stalled+1
            if stalled>=2:
                reason='TWO_SEGMENTS_WITHOUT_TANGIBLE_OUTPUT_OPERATOR_PAUSE';break
            last=curr
        print(json.dumps({'status':'G14_BATCH_FINISHED','reason':reason,
            'segments_completed':len(history),'session_dir':str(session_dir),
            'stop_marker':str(stopper),'journal_modified_by_audit':False},
            ensure_ascii=False),flush=True)
        (session_dir/'batch_summary.json').write_text(json.dumps({'history':history,'reason':reason},
                                  indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    finally:
        stopper.touch(exist_ok=True)
        os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)


if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as ex:
        print(json.dumps({'status':'G14_BATCH_PAUSED_OR_FAILED','error_type':type(ex).__name__,
                          'detail':str(ex)[:700],'not_scientific_hold':True},ensure_ascii=False),
                          file=sys.stderr)
        sys.exit(3)
