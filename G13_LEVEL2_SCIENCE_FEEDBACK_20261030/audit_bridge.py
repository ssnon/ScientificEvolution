#!/usr/bin/env python3
"""Opt-in externally audited science feedback for a single G13 INFORMED step.

Modes: preview (read-only), register (explicit append-only source registration),
run (existing evolution_memory.py with one narrow worker-input disclosure).
No past model, tool, or Work event is rewritten. No FRESH sees external feedback.
"""
from __future__ import annotations
import argparse, contextlib, fcntl, hashlib, json, os, sys
from pathlib import Path
from types import SimpleNamespace

PACKET_FILE=Path(__file__).with_name('SCIENTIFIC_AUDIT_PACKET.json')
EXPECTED_TOOL='TOOL_W_develop_finite_exposure_adversarial_model_001_00002'
WORK='W_develop_finite_exposure_adversarial_model_001'
EXPECTED_STEP=4

def emit(obj):print(json.dumps(obj,ensure_ascii=False,indent=2),flush=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def packet_load():
    b=PACKET_FILE.read_bytes();p=json.loads(b)
    assert p['schema']=='EXTERNAL_SCIENTIFIC_PEER_FEEDBACK_V1'
    assert p['target_work_id']==WORK and p['target_step_number']==EXPECTED_STEP
    return p,sha(b)
def source_id(digest):return 'SRC_AUDIT_G13_MC_'+digest[:24]
def head(mods,j):
    events=j._events()
    return {'events':len(events),'head_sha256':mods.sha(mods.canon(events[-1]))}

def load(experiment):
    import population_run as pop
    mods=pop.gen.modules()
    root=Path(experiment).expanduser().resolve()
    cycle=root/'CYCLE_013'/'POPULATION'
    if not cycle.is_dir():raise RuntimeError('G13_POPULATION_ROOT_MISSING')
    j,s=pop.root_status(mods,cycle)
    return root,mods,j,s

def check(experiment,require_registered=False, require_stop=True):
    root,mods,j,s=load(experiment)
    pkt,d=packet_load();sid=source_id(d)
    if require_stop and not (root/'STOP_REQUESTED').is_file():raise RuntimeError('STOP_MARKER_REQUIRED_NO_CONCURRENT_PAID_RUN')
    if not require_stop and (root/'STOP_REQUESTED').is_file():raise RuntimeError('REMOVE_STOP_MARKER_ONLY_BEFORE_INTENTIONAL_PAID_RUN')
    if any(v['state']!='SAVED' for v in s.model_calls.values()):
        raise RuntimeError('UNRESOLVED_CALL_REQUIRES_MANUAL_REVIEW')
    w=s.work.get(WORK)
    if not w or w['status']!='ACTIVE' or w['mode']!='INFORMED':
        raise RuntimeError('TARGET_WORK_NOT_ACTIVE_INFORMED')
    if len(w['steps'])!=EXPECTED_STEP-1:raise RuntimeError('TARGET_WORK_ADVANCED_OR_RESET_REVIEW_FIRST')
    orig=json.loads(j.raw(w['steps'][1]['raw_blob']))
    req=json.loads(orig['text'])['tool_request']
    code=req['arguments']['code']
    if sha(code.encode())!=pkt['original_calculation']['code_sha256']:
        raise RuntimeError('ORIGINAL_EXECUTED_CODE_SHA_MISMATCH')
    last=json.loads(j.raw(w['steps'][2]['raw_blob']))
    if w['steps'][2]['kind']!='TOOL_RESULT' or last['tool_id']!=EXPECTED_TOOL:
        raise RuntimeError('WORK_TOOL_RESULT_NOT_PINNED')
    got=last.get('result') or {}
    if got.get('status')!='EXECUTED' or (got.get('result') or {}).get('code_sha256')!=sha(code.encode()):
        raise RuntimeError('ACTUAL_EXECUTED_TOOL_RECEIPT_INCONSISTENT')
    if 'WK_'+WORK+'_00004' in s.model_calls:
        raise RuntimeError('NEXT_WORKER_MODEL_CALL_ALREADY_EXISTS_MANUAL_REVIEW')
    stored=s.sources.get(sid)
    if stored:
        if stored['kind']!='EXTERNAL_AUDIT':raise RuntimeError('AUDIT_ID_KIND_COLLISION')
        contents=json.loads(j.raw(stored['blob']))
        if contents.get('packet_file_sha256')!=d or contents.get('record')!=pkt:
            raise RuntimeError('AUDIT_ID_CONTENT_COLLISION')
    if require_registered and not stored:raise RuntimeError('AUDIT_NOT_REGISTERED_EXPLICIT_REGISTER_FIRST')
    return {'experiment':str(root),'journal':str(j.root),'journal_head':head(mods,j),
            'target_work':WORK,'target_next_step':EXPECTED_STEP,
            'original_tool_id':EXPECTED_TOOL,'original_code_sha256':sha(code.encode()),
            'audit_source_id':sid,'audit_packet_sha256':d,'audit_registered':bool(stored),
            'fresh_isolation_policy':'ONLY_INFORMED_WORKER_EXACT_ID_RECEIVES_AUDIT',
            'scientific_certification':False},j,s,pkt

@contextlib.contextmanager
def locks(experiment,j):
    paths=[Path(experiment)/'.autonomous_population.lock',j.root/'.e2run.lock',j.root/'.scientific_feedback_autorun.lock']
    with contextlib.ExitStack() as stack:
        for path in paths:
            f=stack.enter_context(open(path,'a+b'))
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('CURRENT_RESEARCH_RUNTIME_BUSY:'+str(path))
            stack.callback(fcntl.flock,f,fcntl.LOCK_UN)
        yield

def register(experiment,expected_head):
    info,j,s,pkt=check(experiment)
    with locks(experiment,j):
        info,j,s,pkt=check(experiment)
        if info['journal_head']['head_sha256']!=expected_head:
            raise RuntimeError('SOURCE_JOURNAL_HEAD_CHANGED_REPREVIEW_REQUIRED')
        if info['audit_registered']:
            emit({'status':'AUDIT_ALREADY_REGISTERED_NO_MUTATION',**info});return
        content={'kind':'EXTERNAL_COMPUTATIONAL_AUDIT_NOT_EXPERIMENTAL_EVIDENCE',
                 'record':pkt,'packet_file_sha256':info['audit_packet_sha256'],
                 'original_tool_id':EXPECTED_TOOL,
                 'not_new_tool_execution':True,'not_sers_primary_literature':True,
                 'not_an_ai_worker_asset':True,
                 'scope':'Informational independent peer review of an executed calculation'}
        digest=j.add_source(info['audit_source_id'],'EXTERNAL_AUDIT',content,
            'External analytic review of G13 executed Monte Carlo; not a live tool result or primary study')
        emit({'status':'EXTERNAL_SCIENTIFIC_AUDIT_REGISTERED_APPEND_ONLY',
              'source_id':info['audit_source_id'],'blob_sha256':digest,
              'new_journal_head':head(load(experiment)[1],j),
              'no_historical_event_rewritten':True,'provider_requests_sent':0})

def inject_into_payload(payload,packet,sid):
    if 'independent_external_science_audit' in payload:raise RuntimeError('AUDIT_FIELD_ALREADY_EXISTS')
    copy=dict(payload)
    # Redox result is included only as a notice, NEVER promoted to asset.
    for_worker={k:v for k,v in packet.items() if k!='redox_unregistered_candidate_notice'}
    copy['independent_external_science_audit']={
       'id':sid,'origin':'EXTERNAL_AUDIT not original Worker output',
       'evidence_grade':'INDEPENDENT_ANALYSIS_NOT_PRIMARY_SERS_MEASUREMENT',
       'researcher_autonomy':'May correct, contest or deprioritize after independent evaluation',
       'packet':for_worker,
       'cannot_treat_as_primary_source_or_as_a_PUBLISHED_ASSET':True}
    return copy

@contextlib.contextmanager
def worker_injection(experiment, paid_run=False):
    import e2core.engine as eng
    info,j,s,pkt=check(experiment,require_registered=True,require_stop=not paid_run)
    old=eng._worker_input
    def wrapped(journal,wid,tool_capabilities=None):
        payload=old(journal,wid,tool_capabilities)
        if wid!=WORK:return payload
        ws=journal.verify().work[wid]
        if ws['mode']!='INFORMED':raise RuntimeError('AUDIT_CANNOT_ENTER_FRESH')
        step=len(ws['steps'])+1
        if step!=EXPECTED_STEP:return payload
        # New call must not have been recorded under a different input.
        if 'WK_'+WORK+'_00004' in journal.verify().model_calls:
            raise RuntimeError('AUDIT_WORKER_REQUEST_ALREADY_STARTED')
        return inject_into_payload(payload,pkt,info['audit_source_id'])
    eng._worker_input=wrapped
    try:yield info
    finally:eng._worker_input=old

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['preview','register','verify-disclosure','run'])
    p.add_argument('--experiment',required=True)
    p.add_argument('--expected-head')
    args,remaining=p.parse_known_args()
    try:
        if args.command=='preview':
            if remaining:raise RuntimeError('UNEXPECTED_PREVIEW_ARGS:'+str(remaining))
            info,_,_,_=check(args.experiment)
            emit({'status':'SCIENTIFIC_AUDIT_SAFE_PREVIEW_NO_PAID',**info,
                  'journal_unchanged':True,'provider_requests_sent':0})
        elif args.command=='register':
            if remaining or not args.expected_head:raise RuntimeError('EXPLICIT_EXPECTED_HEAD_REQUIRED')
            register(args.experiment,args.expected_head)
        elif args.command=='verify-disclosure':
            if remaining:raise RuntimeError('UNEXPECTED_VERIFY_ARGS:'+str(remaining))
            info,j,s,pkt=check(args.experiment,require_registered=True)
            import e2core.engine as eng
            original=eng._worker_input(j,WORK,'NATIVE_RESEARCH_TOOLS')
            with worker_injection(args.experiment):
                enriched=eng._worker_input(j,WORK,'NATIVE_RESEARCH_TOOLS')
                fresh_id='W_fresh_sers_joint_evidence_audit_001'
                fresh=eng._worker_input(j,fresh_id,'NATIVE_RESEARCH_TOOLS')
            assert 'independent_external_science_audit' not in original
            assert enriched['independent_external_science_audit']['id']==info['audit_source_id']
            assert 'independent_external_science_audit' not in fresh
            assert 'redox_unregistered_candidate_notice' not in enriched['independent_external_science_audit']['packet']
            emit({'status':'SCIENTIFIC_FEEDBACK_WORKER_DISCLOSURE_VERIFIED_NO_PAID',
                  'target_worker':WORK,'target_step':EXPECTED_STEP,
                  'audit_source_id':info['audit_source_id'],
                  'fresh_worker_unexposed':True,'redox_notice_not_injected_into_finite_exposure':True,
                  'journal_head':info['journal_head'],'journal_unchanged':True,
                  'provider_requests_sent':0})
        else:
            if not remaining or '--paid' not in remaining:
                raise RuntimeError('EXPLICIT_PAID_RUN_ARGS_REQUIRED')
            import evolution_memory as em
            with worker_injection(args.experiment,paid_run=True):
                oldargv=sys.argv
                sys.argv=['evolution_memory.py','run','--experiment',args.experiment]+remaining
                try:return em.main()
                finally:sys.argv=oldargv
        return 0
    except Exception as e:
        emit({'status':'SCIENTIFIC_AUDIT_OPERATIONAL_BLOCK_NO_SCIENTIFIC_HOLD',
             'exception':type(e).__name__,'detail':str(e),
             'provider_requests_sent_by_this_script':0})
        return 3
if __name__=='__main__':sys.exit(main())
