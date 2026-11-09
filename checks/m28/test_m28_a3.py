"""M28-A3 no-paid scheduling, crash-recovery and scientific re-review tests."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from e2core.core import EvolutionJournal
from e2core.engine import Engine
from e2core.meta_autonomy import POLICY as A1_POLICY, MODE_BLIND, materialize_requests
from e2core.meta_collaboration import POLICY as A2_POLICY, observe_children, latest_program_disposition
from e2core.meta_scheduler import (
    PROTOCOL, CHECKPOINT, _read_state, _write_state, _event_head,
    _recover_flight, reassessment_pending, request_evidence_reassessment,
    root_ready, run_dynamic, _incomplete_controller_decisions)


def init_research(root,origin='NEW_META_RESEARCH_AUTONOMY_RESEARCH'):
    j=EvolutionJournal(root)
    j.init('An unresolved original scientific question',origin=origin,criteria='External review')
    j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
    j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
    j.append('META_RESEARCH_AUTONOMY_ACTIVATED',{'policy':A1_POLICY})
    j.append('META_RESEARCH_COLLABORATION_ACTIVATED',{'policy':A2_POLICY})
    return j


def raw_decision(*,organization=None,review=None,collaboration=None,
                 disposition='ONGOING',actions=None):
    research='CONTINUING' if disposition=='ONGOING' else 'PAUSED_EVIDENCE'
    assessment={'objective_status':'UNRESOLVED','research_status':research,
                'resolved_scope':'none','objective_coverage':'NO_OBJECTIVE_RESULT',
                'supporting_asset_ids':[],'remaining_questions':['The P0 remains open'],
                'untried_approaches_considered':[],
                'reason':'Explicitly scoped, fallible scientific judgement'}
    response={'rationale':'Autonomous science based on disclosed uncertainty',
              'new_problems':[],'reviews':[],'actions':actions or [],
              'portfolio_decisions':[], 'organization_requests':organization or [],
              'collaboration_requests':collaboration or [],
              'disposition':disposition,'unresolved_opportunities':[],
              'objective_assessment':assessment}
    if review is not None:response['program_portfolio_review']=review
    return response


class SavedOfflineModel:
    def __init__(self,j,response):self.j=j;self.response=response;self.new_calls=0
    def call(self,ident,actor,work_id,prompt,payload):
        self.j.append('MODEL_CALL_INTENT',{
             'id':ident,'actor':actor,'work_id':work_id,
             'request_blob':self.j.blob({'prompt':prompt,'payload':payload}),
             'model':'MOCK','billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED',{'id':ident,
             'response_blob':self.j.blob({'choices':[{'message':{'content':json.dumps(self.response)}}]}),
             'usage':{'cost':0}})
        return json.dumps(self.response)


class TestM28A3Reassessment(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.exp=Path(self.tmp.name)/'EXP'
        (self.exp/'ROOTS').mkdir(parents=True)
        self.root=self.exp/'ROOTS'/'PRIMARY'
        self.j=init_research(self.root)

    def tearDown(self):self.tmp.cleanup()

    def commit(self,num,answer,expected='CONTROLLER_COMMITTED'):
        outcome=Engine(self.j,SavedOfflineModel(self.j,answer)).controller('D'+str(num).zfill(5))
        self.assertEqual(outcome['status'],expected,outcome)
        return outcome

    def create_science(self):
        org={'id':'ORG_offline_child','mode':MODE_BLIND,
             'purpose':'Independently challenge the original P0',
             'evidence_asset_ids':[],'target_asset_ids':[]}
        self.commit(1,raw_decision(organization=[org]))
        child=materialize_requests(self.exp,self.root,8)[0]['root']
        cj=EvolutionJournal(child)
        cj.evolve('EV_child','DECOMPOSE',[],{
              'id':'W_child','mode':'INFORMED','problem_id':'P0',
              'question':'Compute a counterexample under explicit assumptions',
              'research_rationale':'Independent mathematical result',
              'source_ids':[]},'Independent original question')
        cj.start('W_child')
        cj.append('MODEL_CALL_INTENT',{
            'id':'WK_child','actor':'WORKER','work_id':'W_child',
            'request_blob':cj.blob({'mock':'worker'}),
            'model':'MOCK','billing_mode':'MOCK'})
        cj.append('MODEL_CALL_SAVED',{'id':'WK_child',
            'response_blob':cj.blob({'response':'toy claim'}),'usage':{'cost':0}})
        cj.step('W_child','MODEL_RESPONSE',{'call_id':'WK_child','text':'An unverified claim'})
        cj.asset('A_child','W_child','CALCULATION','P0','Conditional counterexample',
                 'finite toy regime','conditional regime',predictions=[],limitations=['unverified'])
        cj.finish('W_child','RETURN','Scoped result')
        old=observe_children(self.exp,self.root)
        self.assertEqual(len(old),1)
        return cj,old[0]['report_id']

    def test_new_child_science_permits_rejudgement_not_automatic_continue(self):
        cj,rid=self.create_science()
        review={'disposition':'PAUSE_WITH_RATIONALE',
                'rationale':'Current observational evidence cannot yet distinguish candidates',
                'considered_organization_request_ids':['ORG_offline_child'],
                'considered_report_ids':[rid],
                'unresolved_frontiers':['An independent calculation may later change this']}
        self.commit(2,raw_decision(review=review,disposition='HOLD_WITH_RATIONALE'))
        self.assertFalse(reassessment_pending(self.j))
        cj.append('ASSET_REVIEWED',{
            'id':'A_child','decision':'CHALLENGED',
            'rationale':'A new counterargument narrows the original claim',
            'reviewer_id':'D99999','source_ids':[]})
        new_report=observe_children(self.exp,self.root)
        self.assertEqual(len(new_report),1)
        res=request_evidence_reassessment(self.j)
        self.assertIsNotNone(res)
        self.assertEqual(request_evidence_reassessment(self.j),None)
        self.assertTrue(reassessment_pending(self.j))
        self.assertEqual(self.j.verify().program_reviews[-1]['scientific_status'],
                         'HOLD_WITH_RATIONALE')
        self.assertTrue(root_ready(self.root))
        now=new_report[0]['report_id']
        # A model is *required* to author a renewed whole-program judgement.
        selection={'id':'COL_reconsidered','organization_request_id':'ORG_offline_child',
                   'report_id':now,'asset_ids':['A_child'],
                   'purpose':'Scientifically compare this corrected child claim'}
        self.commit(3,raw_decision(collaboration=[selection]),
                    expected='CONTROLLER_PLAN_REJECTED')
        updated={'disposition':'CONTINUE',
                 'rationale':'New independent criticism warrants a fresh comparison',
                 'considered_organization_request_ids':['ORG_offline_child'],
                 'considered_report_ids':[now],
                 'unresolved_frontiers':['Test corrected bound against the null']}
        self.commit(4,raw_decision(collaboration=[selection],review=updated))
        self.assertFalse(reassessment_pending(self.j))
        latest=latest_program_disposition(self.root)
        self.assertEqual(latest['disposition'],'CONTINUE')
        self.assertFalse(latest['stale'])

    def test_operational_only_event_does_not_trigger_reassessment(self):
        cj,rid=self.create_science()
        review={'disposition':'PAUSE_WITH_RATIONALE',
                'rationale':'Need independent experimental information',
                'considered_organization_request_ids':['ORG_offline_child'],
                'considered_report_ids':[rid],'unresolved_frontiers':['New data']}
        self.commit(2,raw_decision(review=review,disposition='HOLD_WITH_RATIONALE'))
        cj.append('OPERATIONAL_PAUSE',{'reason':'OPERATIONAL_CALL_BUDGET_REACHED'})
        self.assertEqual(observe_children(self.exp,self.root),[])
        self.assertIsNone(request_evidence_reassessment(self.j))
        self.assertFalse(root_ready(self.root))


class TestM28A3Scheduler(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.exp=Path(self.tmp.name)/'EXP'
        (self.exp/'ROOTS').mkdir(parents=True)
        self.primary=init_research(self.exp/'ROOTS'/'PRIMARY')
        self.other=init_research(self.exp/'ROOTS'/'ORG_second',
                                 'TARGETED_INDEPENDENT_CHALLENGE_NOT_BLIND')
        self.args=SimpleNamespace(max_roots=8,max_new_calls=6,max_root_visits=6,
                                  slice_budget=1,model='MOCK',checkpoint_iterations=1,
                                  max_parallel=1,max_tokens=1000,
                                  science_cpu_seconds=2,science_wall_seconds=8)

    def tearDown(self):self.tmp.cleanup()
    def roots(self,e):return sorted((e/'ROOTS').iterdir())
    def sync(self,e,maximum):return {'created':[]}
    def preflight(self,e,m):pass
    def execute(self,driver):
        return run_dynamic(self.exp,{},self.args,driver,lambda:None,
                           self.sync,self.preflight,self.roots)

    def test_round_robin_revisits_roots_without_generations(self):
        order=[]
        def fake_drive(mods,root,args,phase):
            order.append(root.name)
            EvolutionJournal(root).append('OPERATIONAL_PAUSE',{
                 'reason':'SIMULATED_PAID_SLICE_OFFLINE_TEST'})
            return {'new_calls_this_launch':1,'stop_reason':'CALL_BUDGET'}
        result=self.execute(fake_drive)
        self.assertEqual(result['new_model_calls'],6)
        self.assertEqual(len(order),6)
        self.assertEqual(len(set(order)),2)
        self.assertTrue(all(order[i]!=order[i-1] for i in range(1,6)))
        self.assertEqual(_read_state(self.exp)['visits_total'],6)

    def test_checkpoint_recovery_when_saved_journal_changed(self):
        first=[]
        def interrupted(mods,root,args,phase):
            first.append(root.name)
            EvolutionJournal(root).append('OPERATIONAL_PAUSE',{'reason':'SIMULATED_CRASH_AFTER_JOURNAL_WRITE'})
            raise RuntimeError('simulated process crash')
        with self.assertRaisesRegex(RuntimeError,'simulated process crash'):
            self.execute(interrupted)
        self.assertIsNotNone(_read_state(self.exp)['in_flight'])
        second=[]
        self.args.max_root_visits=1
        def resumed(mods,root,args,phase):
            second.append(root.name)
            return {'new_calls_this_launch':1}
        self.execute(resumed)
        self.assertEqual(len(second),1)
        self.assertNotEqual(first[0],second[0])
        self.assertIsNone(_read_state(self.exp)['in_flight'])
        self.assertEqual(_read_state(self.exp)['visits_total'],2)

    def test_retry_same_root_when_crash_preceded_any_journal_progress(self):
        calls=[]
        def interrupted(mods,root,args,phase):
            calls.append(root.name)
            raise RuntimeError('before any work')
        with self.assertRaisesRegex(RuntimeError,'before any work'):
            self.execute(interrupted)
        self.args.max_root_visits=1
        def resumed(mods,root,args,phase):
            calls.append(root.name)
            return {'new_calls_this_launch':1}
        self.execute(resumed)
        self.assertEqual(calls[0],calls[1])
        self.assertEqual(_read_state(self.exp)['visits_total'],1)

    def test_incomplete_saved_controller_plan_fails_closed(self):
        j=self.primary
        response=raw_decision(actions=[{
            'id':'EV_missing','operation':'DECOMPOSE','asset_ids':[],
            'reason':'This scientific Work was never actually applied',
            'work':{'id':'W_missing','mode':'INFORMED','problem_id':'P0',
                    'question':'An unexecuted proposal',
                    'research_rationale':'A hypothetical research task',
                    'source_ids':[]}}])
        cid='CTRL_D00001'
        j.append('MODEL_CALL_INTENT',{'id':cid,'actor':'CONTROLLER','work_id':None,
            'request_blob':j.blob({'offline':'controller'}),
            'model':'MOCK','billing_mode':'MOCK'})
        j.append('MODEL_CALL_SAVED',{'id':cid,
            'response_blob':j.blob({'reply':response}),'usage':{'cost':0}})
        j.append('CONTROLLER_DECISION',{'id':'D00001','call_id':cid,
            'parsed_blob':j.blob(response),'rationale':response['rationale']})
        j.append('PROGRAM_REVIEWED',{'reviewer_id':'D00001',
            'scientific_status':'ONGOING','rationale':'Incomplete original scientific decision',
            'considered_asset_ids':[],'unresolved_opportunities':[]})
        j.append('PROGRAM_OBJECTIVE_ASSESSED',{
            'reviewer_id':'D00001','objective_status':'UNRESOLVED',
            'research_status':'CONTINUING','resolved_scope':'none',
            'objective_coverage':'NO_OBJECTIVE_RESULT','supporting_asset_ids':[],
            'remaining_questions':[],'untried_approaches_considered':[],
            'reason':'Original action still has not actually been applied'})
        missing=_incomplete_controller_decisions(j)
        self.assertTrue(any('SCIENTIFIC_WORK_PLAN_INCOMPLETE' in x for x in missing),missing)
        with self.assertRaisesRegex(Exception,'META_A3_INCOMPLETE_CONTROLLER'):
            self.execute(lambda *args: {'new_calls_this_launch':0})

    def test_unresolved_provider_call_fails_closed(self):
        j=self.other
        j.append('MODEL_CALL_INTENT',{
             'id':'CTRL_D00001','actor':'CONTROLLER','work_id':None,
             'request_blob':j.blob({'unresolved':'true'}),
             'model':'MOCK','billing_mode':'MOCK'})
        with self.assertRaisesRegex(Exception,'META_A3_UNRESOLVED_MODEL_CALL'):
            root_ready(j.root)

    def test_checkpoint_rejects_corrupt_data(self):
        (self.exp/CHECKPOINT).write_text('{"incorrect":true}',encoding='utf8')
        with self.assertRaises(Exception):_read_state(self.exp)


if __name__=='__main__':unittest.main()
