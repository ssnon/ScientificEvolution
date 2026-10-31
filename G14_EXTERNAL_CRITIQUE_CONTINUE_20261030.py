#!/usr/bin/env python3
"""G14-only external scientist-review handoff to one *INFORMED* active worker.

No mutation of prior Journal events, no fabricated TOOL_RESULT/SOURCE_REGISTERED,
no forced model scientific choice, and no injection into FRESH/Controller calls.
A new saved DurableModel request carries the external critique as *review data*.
The existing native G14 runner and exact-ID guard remain authoritative.
"""
from __future__ import annotations
import argparse,contextlib,hashlib,json,os,sys
from pathlib import Path

WORK_ID='W_P0_redox_mechanochemical_symmetry_001'
CHECKPOINT_EVENTS=1483
CHECKPOINT_HEAD='e47a0e3af57c443848a43044838d3aa13f2dd43646f34edeb861d0ac0f99b5ce'
CRITIQUE_SHA256='a6eba9ac7d3f3b066b7e57890f646d9eac13e2a4c1e9e4e6792c3616d78d9798'


def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()


def load_critique(path):
    raw=Path(path).expanduser().resolve(strict=True).read_bytes()
    assert sha(raw)==CRITIQUE_SHA256, 'EXTERNAL_REVIEW_CONTENT_CHANGED'
    data=json.loads(raw)
    assert data['reference_checkpoint_events']==CHECKPOINT_EVENTS
    assert data['reference_checkpoint_head']==CHECKPOINT_HEAD
    assert data['report_type']=='EXTERNAL_INDEPENDENT_SCIENTIFIC_CRITIQUE_NOT_JOURNAL_EVIDENCE'
    assert data['target_work_mode']=='INFORMED' and data['target_work_id']==WORK_ID
    assert data['model_calls_sent_for_review']==0 and data['original_journal_modified'] is False
    assert all(k in data for k in ('finding_1','finding_2','finding_3','registration_history','scientific_discretion'))
    return data


def verify_current_state(experiment):
    import G14_LEVEL2_TRACE_CONTINUATION_20261030 as trace
    exp,cycle,mods,j,s,events=trace.verify(experiment,expect_stage=True)
    assert len(events)>=CHECKPOINT_EVENTS,'G14_JOURNAL_BEFORE_REVIEW_BASELINE'
    head=mods.sha(mods.canon(events[CHECKPOINT_EVENTS-1]))
    assert head==CHECKPOINT_HEAD,'G14_JOURNAL_1483_PREFIX_CHANGED'
    assert Path(cycle['population_root']).resolve()==(exp/'CYCLE_014'/'POPULATION').resolve()
    assert WORK_ID in s.work,'INTENDED_WORK_NOT_FOUND'
    assert s.work[WORK_ID]['mode']=='INFORMED' and s.work[WORK_ID]['status']=='ACTIVE','INTENDED_INFORMED_WORK_NOT_ACTIVE'
    assert all(c['state']=='SAVED' for c in s.model_calls.values()),'UNCERTAIN_OR_PENDING_PROVIDER_CALL'
    return exp,mods,j,s,events


def review_already_saved(j,s):
    for info in s.model_calls.values():
        if info.get('work_id')==WORK_ID and info.get('state')=='SAVED':
            if CRITIQUE_SHA256.encode() in j.raw(info['request_blob']):
                return True
    return False


def review_message(system,payload,critique):
    assert isinstance(system,str) and isinstance(payload,dict),'UNEXPECTED_INPUT_SHAPE'
    assert 'operator_external_scientific_review' not in payload,'DUPLICATE_EXTERNAL_REVIEW'
    updated=dict(payload)
    updated['operator_external_scientific_review']={
       'type':'INDEPENDENT_OPERATOR_SCIENTIFIC_CRITIQUE_NOT_PRIOR_ART_NOT_CERTIFICATION',
       'review_sha256':CRITIQUE_SHA256,
       'reference_journal_head':CHECKPOINT_HEAD,
       'feedback':critique,
       'review_terms':('This is an external critic, not a system correction or an empirical measurement. '
                       'Check each mathematical/physical claim independently; you may disagree with a '
                       'worked counterexample, correct prior claims via new assets, supply alternative '
                       'derivations, return a scoped negative, pivot, or continue. Do not rewrite history '
                       'or count this as literature_research evidence.')}
    appendix=('\nEXTERNAL SCIENTIFIC PEER REVIEW AVAILABLE: Read the payload field '
       'operator_external_scientific_review. The reviewer flags a mismatched observation index '
       'in the previous toy Fisher calculation and an integrated-capacitive-charge issue in '
       'the zero-ramp-rate proposal. Inspect the exact counterexamples and independently decide '
       'whether to accept, qualify, correct, or refute them. Preserve prior assets and failed '
       'problem proposals as historical records; any new claim must be its own authored artifact. '
       'This external review is NOT a primary paper, native tool receipt, or Level-II certification.\n')
    return system+appendix,updated


@contextlib.contextmanager
def activate(root,critique,stats):
    from e2core.provider import DurableModel
    root=Path(root).expanduser().resolve(strict=True)
    original=DurableModel.call
    def wrapped(self,ident,actor,work_id,system,payload):
        if (Path(self.j.root).resolve()!=root or actor!='WORKER' or work_id!=WORK_ID
            or not str(ident).startswith('WK_'+WORK_ID+'_')):
            return original(self,ident,actor,work_id,system,payload)
        state=self.j.verify()
        # CRITICAL: a previously committed request must be replayed byte-for-byte.
        if ident in state.model_calls:
            return original(self,ident,actor,work_id,system,payload)
        if stats['review_attempted'] or review_already_saved(self.j,state):
            return original(self,ident,actor,work_id,system,payload)
        assert state.work[WORK_ID]['mode']=='INFORMED'
        assert state.work[WORK_ID]['status']=='ACTIVE'
        assert all(v['state']=='SAVED' for v in state.model_calls.values()),'UNSAVED_PROVIDER_CALL'
        system,payload=review_message(system,payload,critique)
        stats['review_attempted']=True
        stats['call_id']=ident
        print(json.dumps({'status':'EXTERNAL_SCIENCE_REVIEW_NEW_REQUEST_ATTEMPT',
            'work_id':WORK_ID,'call_id':ident,'review_sha256':CRITIQUE_SHA256,
            'journal_evidence_fabricated':False},ensure_ascii=False),flush=True)
        answer=original(self,ident,actor,work_id,system,payload)
        if self.j.verify().model_calls.get(ident,{}).get('state')=='SAVED':
            stats['review_saved']=True
            print(json.dumps({'status':'EXTERNAL_SCIENCE_REVIEW_MODEL_REQUEST_SAVED',
               'work_id':WORK_ID,'call_id':ident,'review_sha256':CRITIQUE_SHA256},ensure_ascii=False),flush=True)
        return answer
    DurableModel.call=wrapped
    try:yield
    finally:DurableModel.call=original


def selftest():
    import tempfile,types
    from types import SimpleNamespace
    review={'reference_checkpoint_events':1483,'scientific_discretion':'free','finding_1':{'id':'INDEX_SEMANTICS_DISCREPANCY'}}
    original={'immutable_old_context':'DO_NOT_MODIFY'}
    sys_msg,new=review_message('S',original,review)
    assert original=={'immutable_old_context':'DO_NOT_MODIFY'}
    assert new is not original and sys_msg.startswith('S')
    assert new['operator_external_scientific_review']['feedback'] is review
    call_log=[]
    pkg=types.ModuleType('e2core');pkg.__path__=[]
    provider=types.ModuleType('e2core.provider')
    class Mock:
        def call(self,ident,actor,work_id,system,payload):
            call_log.append((ident,actor,work_id,system,payload))
            self.j._model_calls[ident]={'state':'SAVED','work_id':work_id,'request_blob':ident}
            return {'status':'MOCK'}
    provider.DurableModel=Mock
    old_pkg=sys.modules.get('e2core')
    old_pro=sys.modules.get('e2core.provider')
    sys.modules['e2core']=pkg;sys.modules['e2core.provider']=provider
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            class MockJournal:
                def __init__(self):self.root=root;self._model_calls={}
                def raw(self,blob):
                    return json.dumps(next(c[-1] for c in call_log if c[0]==blob)).encode()
                def verify(self):return SimpleNamespace(model_calls=self._model_calls,
                    work={WORK_ID:{'mode':'INFORMED','status':'ACTIVE'}})
            mdl=Mock();mdl.j=MockJournal(); stats={'review_attempted':False,'review_saved':False,'call_id':None}
            with activate(root,review,stats):
                mdl.call('WK_'+WORK_ID+'_00013','WORKER',WORK_ID,'SYSTEM',original)
                assert stats['review_attempted'] and stats['review_saved']
                assert 'operator_external_scientific_review' in call_log[-1][-1]
                assert original=={'immutable_old_context':'DO_NOT_MODIFY'}
                mdl.call('WK_'+WORK_ID+'_00013','WORKER',WORK_ID,'SYSTEM',original)
                assert call_log[-1][-1] is original # saved call replay was not altered
                mdl.call('WK_'+WORK_ID+'_00014','WORKER',WORK_ID,'SYSTEM',original)
                assert call_log[-1][-1] is original # critique already stored in Journal, do not repeat
                mdl.call('WK_OTHER_00013','WORKER','W_OTHER','SYSTEM',original)
                assert call_log[-1][-1] is original
                mdl.call('CTRL_D00022','CONTROLLER',None,'SYSTEM',original)
                assert call_log[-1][-1] is original
            assert Mock.call is not None
    finally:
        if old_pkg is None:sys.modules.pop('e2core',None)
        else:sys.modules['e2core']=old_pkg
        if old_pro is None:sys.modules.pop('e2core.provider',None)
        else:sys.modules['e2core.provider']=old_pro
    print(json.dumps({'status':'G14_EXTERNAL_CRITIQUE_SELFTEST_OK','checks':11,
       'paid_calls':0,'journal_modified':False},ensure_ascii=False))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=['selftest','preflight','run'])
    ap.add_argument('--experiment')
    ap.add_argument('--trace-dir')
    ap.add_argument('--critique',default=str(Path.home()/'ScientificEvolution'/'G14_EXTERNAL_SCIENTIFIC_CRITIQUE_20261030.json'))
    args,forward=ap.parse_known_args()
    if args.command=='selftest':
        assert not forward,'UNEXPECTED_SELFTEST_ARGS'
        return selftest()
    assert args.experiment,'EXPERIMENT_REQUIRED'
    critique=load_critique(args.critique)
    exp,mods,j,state,events=verify_current_state(args.experiment)
    already=review_already_saved(j,state)
    report={'status':'G14_EXTERNAL_CRITIQUE_PREFLIGHT_OK_NO_PAID',
        'events':len(events),'baseline_head_at_1483':CHECKPOINT_HEAD,
        'current_journal_head':mods.sha(mods.canon(events[-1])),
        'review_already_saved_to_worker_request':already,
        'work_id':WORK_ID,'work_status':state.work[WORK_ID]['status'],
        'review_sha256':CRITIQUE_SHA256,'original_journal_modified':False,
        'provider_calls_sent':0,'FRESH_ISOLATION_UNCHANGED':True}
    if args.command=='preflight':
        assert not forward,'UNEXPECTED_PREFLIGHT_ARGS'
        assert (exp/'STOP_REQUESTED').is_file(),'OPERATOR_STOP_MARKER_REQUIRED_FOR_PREFLIGHT'
        print(json.dumps(report,ensure_ascii=False,indent=2));return
    assert args.command=='run'
    assert not already,'EXTERNAL_CRITIQUE_ALREADY_DELIVERED_DO_NOT_REPEAT_PAID_RUN'
    assert args.trace_dir,'TRACE_DIR_REQUIRED'
    assert '--paid' in forward and os.getenv('FAKG_RESEARCH_ALLOW_PAID')=='YES', 'EXPLICIT_PAID_APPROVAL_REQUIRED'
    assert not (exp/'STOP_REQUESTED').exists(),'STOP_REQUESTED_PRESENT'
    assert '--max-operational-segments' in forward,'BOUNDED_SEGMENT_REQUIRED'
    i=forward.index('--max-operational-segments')
    assert i+1<len(forward) and forward[i+1]=='1','ONE_SEGMENT_ONLY'
    import G14_LEVEL2_TRACE_CONTINUATION_20261030 as trace
    import G14_EXACT_ID_REQUEST_GUARD_20261030 as guard
    old_activate=guard.activate
    stats={'review_attempted':False,'review_saved':False,'call_id':None}
    @contextlib.contextmanager
    def composed_activate(root):
        with old_activate(root):
            with activate(root,critique,stats):
                yield
    try:
        guard.activate=composed_activate
        sys.argv=[str(Path(trace.__file__).resolve()),'run','--experiment',str(exp),
                  '--trace-dir',str(args.trace_dir),*forward]
        print(json.dumps(report|{'status':'G14_EXTERNAL_CRITIQUE_RUN_BEGIN'},ensure_ascii=False),flush=True)
        result=trace.main()
        print(json.dumps({'status':'G14_EXTERNAL_CRITIQUE_HANDOFF_RESULT',**stats,
            'replay_safe':True,'no_forced_science':True},ensure_ascii=False),flush=True)
        return result
    finally:
        guard.activate=old_activate


if __name__=='__main__':
    try:sys.exit(main() or 0)
    except Exception as e:
        print(json.dumps({'status':'G14_EXTERNAL_CRITIQUE_OPERATIONAL_PAUSE',
            'error_type':type(e).__name__,'detail':str(e),
            'not_scientific_hold':True},ensure_ascii=False),file=sys.stderr)
        sys.exit(3)
