"""M28-A2 no-paid actual Journal/Controller collaboration contract tests."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from e2core.core import EvolutionJournal, canon
from e2core.engine import Engine
from e2core.meta_autonomy import POLICY as A1_POLICY, MODE_BLIND, materialize_requests, verify_receipts
from e2core.meta_collaboration import (
    POLICY as A2_POLICY, observe_children, import_selected,
    latest_program_disposition, recover_committed_a2, controller_context,
)


def decision(*, organization=None, collaboration=None, review=None, disposition='ONGOING', actions=None):
    status = ('CONTINUING' if disposition == 'ONGOING'
              else ('COMPLETED' if disposition in {'SCOPED_NEGATIVE','REVIEW_WORTHY_CANDIDATE'}
                    else 'PAUSED_EVIDENCE'))
    objective = ('PROVEN_NEGATIVE_IN_SCOPE' if disposition == 'SCOPED_NEGATIVE' else
                 'REVIEW_WORTHY_CANDIDATE' if disposition == 'REVIEW_WORTHY_CANDIDATE' else 'UNRESOLVED')
    return {'rationale': 'Evidence-aware research and collaboration plan',
        'new_problems': [], 'reviews': [], 'actions': list(actions or []),
        'portfolio_decisions': [], 'organization_requests': list(organization or []),
        'collaboration_requests': list(collaboration or []),
        **({'program_portfolio_review':review} if review is not None else {}),
        'disposition': disposition, 'unresolved_opportunities': [],
        'objective_assessment': {'objective_status':objective,'research_status':status,
            'resolved_scope':'none','objective_coverage':'NO_OBJECTIVE_RESULT',
            'supporting_asset_ids':[], 'remaining_questions':['P0 is still open'],
            'untried_approaches_considered':[],
            'reason':'Scientific conclusion scoped and not automatically certified'}}


def spawn_request():
    return {'id':'ORG_child_request','mode': MODE_BLIND,
        'purpose':'Investigate a genuinely independent counterexample',
        'evidence_asset_ids':[], 'target_asset_ids':[]}


class OfflineController:
    def __init__(self,j, reply):
        self.j=j;self.reply=reply;self.new_calls=0
    def call(self,ident,actor,work_id,prompt,payload):
        self.j.append('MODEL_CALL_INTENT',{
            'id':ident,'actor':actor,'work_id':work_id,
            'request_blob':self.j.blob({'prompt':prompt,'context':payload}),
            'model':'MOCK','billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED',{
            'id':ident,'response_blob':self.j.blob({'mock_reply':self.reply}),
            'usage':{'cost':0}})
        return json.dumps(self.reply)


class TestM28A2(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.exp=Path(self.tmp.name)/'A2'
        roots=self.exp/'ROOTS';roots.mkdir(parents=True)
        self.parent=roots/'PRIMARY'
        self.j=EvolutionJournal(self.parent)
        self.j.init('Original P0 scientifically unresolved',
                    origin='NEW_META_RESEARCH_AUTONOMY_RESEARCH',
                    criteria='External independent review')
        self.j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        self.j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        self.j.append('META_RESEARCH_AUTONOMY_ACTIVATED',{'policy':A1_POLICY})
        self.j.append('META_RESEARCH_COLLABORATION_ACTIVATED',{'policy':A2_POLICY})

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self,n,raw):
        result=Engine(self.j,OfflineController(self.j,raw)).controller(f'D{n:05d}')
        self.assertEqual(result['status'],'CONTROLLER_COMMITTED',result)

    def spawn_child(self):
        self.commit(1,decision(organization=[spawn_request()]))
        receipt=materialize_requests(self.exp,self.parent,8)[0]
        cj=EvolutionJournal(receipt['root'])
        self.assertTrue(cj.verify().meta_collaboration)
        self.assertEqual(verify_receipts(self.exp,self.parent),1)
        return cj

    def child_work(self,cj, ident='A_child_science', extra=False):
        w='W_child_real_mock_work'
        cj.evolve('EV_child','DECOMPOSE',[],{
            'id':w,'mode':'INFORMED','problem_id':'P0',
            'question':'Independent mathematical counterexample exploration',
            'research_rationale':'Quantifiable conditional counterexample',
            'source_ids':[]},'Do original P0 work')
        cj.start(w)
        call='W_CALL_1'
        cj.append('MODEL_CALL_INTENT',{'id':call,'actor':'WORKER','work_id':w,
             'request_blob':cj.blob({'offline':'worker'}),
             'model':'MOCK','billing_mode':'MOCK'})
        cj.append('MODEL_CALL_SAVED',{'id':call,'response_blob':cj.blob({'mock':True}),
             'usage':{'cost':0}})
        cj.step(w,'MODEL_RESPONSE',{'call_id':call,'text':'Toy claim generated; unverified'})
        cj.asset(ident,w,'CALCULATION','P0','A conditional mathematical claim',
                 'Finite toy model only','Conditional setup',predictions=[],limitations=['Not proven'])
        if extra:
            cj.asset('A_child_second',w,'COUNTEREXAMPLE','P0',
                     'Counterexample to a narrower assertion',
                     'Finite toy model only','Conditional setup',predictions=[],limitations=['Not proven'])
        cj.finish(w,'RETURN','Scientific result is provisional')
        return ident

    def report(self,cj):
        reports=observe_children(self.exp,self.parent)
        self.assertEqual(len(reports),1)
        return reports[0]['report_id']

    def selection(self,report_id, assets):
        return {'id':'COL_select_once', 'organization_request_id':'ORG_child_request',
                'report_id':report_id, 'asset_ids':assets,
                'purpose':'Scientifically compare selected conditional results and strong nulls'}

    def test_child_with_no_work_is_not_auto_imported_or_scientific_report(self):
        self.spawn_child()
        self.assertEqual(observe_children(self.exp,self.parent),[])
        self.assertEqual(self.j.verify().child_research_reports,{})
        self.assertEqual(self.j.verify().assets,{})
        self.assertFalse(self.j.verify().program_portfolio_reviews)

    def test_actual_worker_report_selective_import_and_provenance(self):
        cj=self.spawn_child()
        self.child_work(cj,extra=True)
        rid=self.report(cj)
        self.assertEqual(len(controller_context(self.j)['child_research_reports'][0]['report']['candidate_assets']),2)
        self.assertFalse(self.j.verify().assets)
        self.assertEqual(observe_children(self.exp,self.parent),[])
        self.commit(2,decision(collaboration=[self.selection(rid,['A_child_science'])]))
        imports=import_selected(self.exp,self.parent)
        self.assertEqual(len(imports),1)
        self.assertEqual(import_selected(self.exp,self.parent),[])
        state=self.j.verify()
        self.assertEqual(len(state.assets),1)
        self.assertEqual(len(state.collaboration_imports),1)
        self.assertFalse(any(x.get('claim')=='Counterexample to a narrower assertion' for x in state.assets.values()))
        source=state.sources[imports[0]['source_id']]
        content=json.loads(self.j.raw(source['blob']))
        self.assertEqual(content['origin_billing_mode'],'MOCK')
        self.assertEqual(content['original_asset_id'],'A_child_science')
        a=state.assets[imports[0]['local_asset_id']]
        self.assertEqual(a['origin'],'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK')
        self.assertNotEqual(a['certification'],'EXPERIMENTALLY_VERIFIED')
        self.assertEqual(state.program_reviews[-1]['scientific_status'],'ONGOING')
        self.assertEqual(verify_receipts(self.exp,self.parent),1)

    def test_controller_can_propose_followup_science_without_automatic_fuse(self):
        cj=self.spawn_child();self.child_work(cj,extra=True)
        rid=self.report(cj)
        self.commit(2,decision(collaboration=[self.selection(rid,['A_child_science','A_child_second'])]))
        imports=import_selected(self.exp,self.parent)
        self.assertEqual(len(imports),2)
        self.assertFalse(self.j.verify().work)  # importing claims does not create FUSE
        aids=[x['local_asset_id'] for x in imports]
        proposal={'id':'EV_selected_fusion','operation':'FUSE','asset_ids':aids,
                  'reason':'Test whether the two claims yield a meaningful new discriminator',
                  'work':{'id':'W_selected_fusion','mode':'INFORMED','problem_id':'P0',
                          'question':'Compare child result and conditional counterexample',
                          'research_rationale':'Evaluate explicit overlap and nulls',
                          'source_ids':[]}}
        self.commit(3,decision(actions=[proposal]))
        self.assertEqual(self.j.verify().work['W_selected_fusion']['status'],'QUEUED')

    def test_operational_pause_alone_does_not_trigger_scientific_report_reassessment(self):
        cj=self.spawn_child();self.child_work(cj)
        self.report(cj)
        cj.append('OPERATIONAL_PAUSE',{'reason':'OPERATIONAL_CALL_BUDGET_REACHED'})
        self.assertEqual(observe_children(self.exp,self.parent),[])

    def test_new_child_evidence_marks_previous_global_pause_stale(self):
        cj=self.spawn_child();self.child_work(cj)
        rid=self.report(cj)
        review={'disposition':'PAUSE_WITH_RATIONALE',
                'rationale':'Scoped evidence requires new measurements',
                'considered_organization_request_ids':['ORG_child_request'],
                'considered_report_ids':[rid], 'unresolved_frontiers':['More tests']}
        self.commit(2,decision(review=review,disposition='HOLD_WITH_RATIONALE'))
        self.assertFalse(latest_program_disposition(self.parent)['stale'])
        cj.append('ASSET_REVIEWED',{'id':'A_child_science','decision':'CHALLENGED',
                  'rationale':'Independent counterargument was found',
                  'reviewer_id':'D99999','source_ids':[]})
        self.assertEqual(len(observe_children(self.exp,self.parent)),1)
        self.assertTrue(latest_program_disposition(self.parent)['stale'])

    def test_stale_or_unreported_child_selection_rejected(self):
        cj=self.spawn_child();self.child_work(cj)
        rid=self.report(cj)
        broken=self.selection(rid,['A_not_reported'])
        bad=Engine(self.j,OfflineController(self.j,decision(collaboration=[broken]))).controller('D00002')
        self.assertEqual(bad['status'],'CONTROLLER_PLAN_REJECTED')
        self.assertFalse(self.j.verify().collaboration_requests)
        self.assertFalse(self.j.verify().assets)

    def test_child_local_hold_not_global_stop_then_explicit_program_pause(self):
        cj=self.spawn_child();self.child_work(cj)
        cj.append('PROGRAM_REVIEWED',{'reviewer_id':'D99999',
           'scientific_status':'HOLD_WITH_RATIONALE',
           'rationale':'Local method requires missing observations',
           'considered_asset_ids':['A_child_science'],
           'unresolved_opportunities':['Other methods may remain useful']})
        rid=self.report(cj)
        self.assertIsNone(latest_program_disposition(self.parent))
        review={'disposition':'PAUSE_WITH_RATIONALE',
           'rationale':'Current resources cannot settle P0; a future new measurement may change this',
           'considered_organization_request_ids':['ORG_child_request'],
           'considered_report_ids':[rid],
           'unresolved_frontiers':['Unknown experimental parameter','Other theoretical approaches']}
        self.commit(2,decision(review=review,disposition='HOLD_WITH_RATIONALE'))
        saved=latest_program_disposition(self.parent)
        self.assertEqual(saved['disposition'],'PAUSE_WITH_RATIONALE')
        self.assertTrue(saved['program_level_model_judgment_only'])

    def test_primary_terminal_without_program_portfolio_review_rejected(self):
        cj=self.spawn_child();self.child_work(cj);self.report(cj)
        result=Engine(self.j,OfflineController(self.j,decision(
                 disposition='HOLD_WITH_RATIONALE'))).controller('D00002')
        self.assertEqual(result['status'],'CONTROLLER_PLAN_REJECTED')
        self.assertIsNone(latest_program_disposition(self.parent))

    def test_program_scope_requires_all_children_and_current_reports(self):
        cj=self.spawn_child();self.child_work(cj);rid=self.report(cj)
        review={'disposition':'PAUSE_WITH_RATIONALE','rationale':'No further justified information now',
                'considered_organization_request_ids':[],
                'considered_report_ids':[rid], 'unresolved_frontiers':['Open follow-up']}
        result=Engine(self.j,OfflineController(self.j,decision(
                 review=review,disposition='HOLD_WITH_RATIONALE'))).controller('D00002')
        self.assertEqual(result['status'],'CONTROLLER_PLAN_REJECTED')
        self.assertFalse(self.j.verify().program_portfolio_reviews)

    def test_crash_after_controller_saved_replays_without_new_paid_calls(self):
        cj=self.spawn_child();self.child_work(cj);rid=self.report(cj)
        raw=decision(collaboration=[self.selection(rid,['A_child_science'])])
        model=OfflineController(self.j,raw)
        model.call('CTRL_D00002','CONTROLLER',None,'offline',{})
        self.j.append('CONTROLLER_DECISION',{'id':'D00002','call_id':'CTRL_D00002',
                  'parsed_blob':self.j.blob(raw),'rationale':raw['rationale']})
        calls=len(self.j.verify().model_calls)
        self.assertEqual(recover_committed_a2(self.j),['COL_select_once'])
        self.assertEqual(recover_committed_a2(self.j),[])
        self.assertEqual(len(self.j.verify().model_calls),calls)
        self.assertEqual(len(import_selected(self.exp,self.parent)),1)


if __name__=='__main__':unittest.main()
