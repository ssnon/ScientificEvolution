"""No-paid native continuity tests. All science and tool outputs are synthetic."""
from __future__ import annotations
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'runtime'))

from e2core.core import EvolutionJournal, EvidenceError
from e2core.engine import controller_plan, _worker_input, _external_context
from e2core.research_continuity import (
    ContinuityError, VERSION, PIN_NAME, digest, canonical, validate_record,
    normalize_problem, live_opportunities, opportunities_for_journal,
    check_work_handoff, worker_handoff, pin_archive,
)


def synthetic_response():
    return {'scientific_text':'SYNTHETIC ONLY: no real evidence',
            'next_action':'CONTINUE', 'assets':[],
            'new_problems':[{'id':'P_BAD_LOCAL',
                'parents':['P0','A_FAKE'], 'question':'Synthetic rejected question',
                'scope':'Synthetic', 'decomposition_rationale':'Synthetic',
                'contribution_to_parent':'Synthetic'}],
            'tool_request':None}


def make_root(path):
    j=EvolutionJournal(path);j.init('Synthetic P0 for code test only')
    j.evolve('EV_SOURCE','FRESH',[],{
        'id':'W_SOURCE','mode':'FRESH','problem_id':'P0',
        'question':'Synthetic parent hypothesis','research_rationale':'Mock only',
        'source_ids':[]},'Synthetic fixture')
    j.start('W_SOURCE')
    raw=json.dumps(synthetic_response(),ensure_ascii=False)
    j.step('W_SOURCE','MODEL_RESPONSE',{'call_id':'WK_W_SOURCE_00001',
        'text':raw,'parse_ok':True})
    j.step('W_SOURCE','OUTPUT_VALIDATION',{
        'status':'REJECTED','accepted':0,
        'rejected':[{'kind':'PROBLEM','index':0,'error':'INVALID_PROBLEM_PARENTS'}]})
    j.asset('A_SOURCE','W_SOURCE','HYPOTHESIS','P0','Synthetic claim',
        'Synthetic assumption','Synthetic scope',[],[],[], '',[])
    return j


def informed_action(opp_id,mode='INFORMED'):
    return {'rationale':'Synthetic planning only', 'new_problems':[], 'reviews':[],
        'disposition':'ONGOING','unresolved_opportunities':[],
        'actions':[{'id':'EV_FOLLOW','operation':'DEVELOP' if mode=='INFORMED' else 'FRESH',
            'asset_ids':['A_SOURCE'] if mode=='INFORMED' else [],
            'reason':'SYNTHETIC ONLY',
            'work':{'id':'W_FOLLOW','mode':mode,'problem_id':'P0',
                'question':'Inspect prior rejection, synthetic only',
                'research_rationale':'Inspect/reject autonomously',
                'source_ids':[],'opportunity_input_ids':[opp_id]}}]}


class TestRealNativeJournal(unittest.TestCase):
    def test_rejected_proposal_index_is_not_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root')
            idx=live_opportunities(j)
            self.assertEqual(len(idx),1)
            o=next(iter(idx.values()))
            self.assertEqual(o['status'],'UNREGISTERED_PROPOSAL_REJECTED')
            self.assertFalse(o['science_certification'])
            self.assertEqual(o['validation_errors'],['INVALID_PROBLEM_PARENTS'])
            self.assertNotIn(o['opportunity_id'],j.verify().assets)
            self.assertEqual(j.verify().sources,{})
            self.assertIn('A_FAKE',o['original_submission']['parents'])

    def test_controller_explicit_handoff_and_worker_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root');idx=live_opportunities(j)
            ident=next(iter(idx))
            plan=controller_plan(j,informed_action(ident),'CTRL_D00001','D00001')
            for kind,payload in plan:j.append(kind,payload)
            s=j.verify();work=s.work['W_FOLLOW']
            self.assertEqual(work['opportunity_input_ids'],[ident])
            self.assertEqual(work['opportunity_handoff_records'][0]['original_submission'],
                             idx[ident]['original_submission'])
            self.assertEqual(work['opportunity_handoff_digest'],digest(work['opportunity_handoff_records']))
            j.start('W_FOLLOW')
            data=_worker_input(j,'W_FOLLOW')
            self.assertEqual(len(data['explicit_unregistered_opportunity_handoff']['records']),1)
            self.assertEqual(data['explicit_unregistered_opportunity_handoff']['not_primary_evidence'],True)
            self.assertFalse(data['explicit_unregistered_opportunity_handoff']['records'][0]['science_certification'])
            self.assertIn('unregistered_opportunity_index',_external_context(j))
            self.assertEqual(j.verify().sources,{})

    def test_unknown_and_fresh_handoff_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root');original=len(j._events())
            ident=next(iter(live_opportunities(j)))
            with self.assertRaisesRegex((EvidenceError,ContinuityError),'FRESH'):
                controller_plan(j,informed_action(ident,'FRESH'),'CTRL_D00001','D00001')
            with self.assertRaisesRegex((EvidenceError,ContinuityError),'UNKNOWN'):
                controller_plan(j,informed_action('OPP_MISSING'),'CTRL_D00001','D00001')
            self.assertEqual(len(j._events()),original)

    def test_typed_problem_motivation_checked_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root')
            j.evolve('EV_INFORMED','DEVELOP',['A_SOURCE'],{'id':'W_INFORMED',
                'mode':'INFORMED','problem_id':'P0','question':'synthetic follow up',
                'research_rationale':'synthetic','source_ids':[]},'Synthetic')
            s=j.verify()
            proposed={'id':'P_TYPED','parent_problem_ids':['P0'],
                'motivating_asset_ids':['A_SOURCE'],
                'question':'Synthetic typed problem','scope':'Synthetic',
                'decomposition_rationale':'Synthetic','contribution_to_parent':'Synthetic'}
            normalized=normalize_problem(proposed,s,mode='INFORMED',
                origin_work_id='W_INFORMED',allowed_assets={'A_SOURCE'})
            j.append('PROBLEM_CREATED',normalized)
            again=j.verify().problems['P_TYPED']
            self.assertEqual(again['parents'],['P0'])
            self.assertEqual(again['motivating_asset_ids'],['A_SOURCE'])
            self.assertNotIn('A_SOURCE',again['parents'])
            own=normalize_problem(proposed,j.verify(),mode='FRESH',
                origin_work_id='W_SOURCE',allowed_assets={'A_SOURCE'})
            self.assertEqual(own['motivating_asset_ids'],['A_SOURCE'])
            with self.assertRaisesRegex(ContinuityError,'FRESH'):
                normalize_problem(proposed,j.verify(),mode='FRESH',
                                  origin_work_id='W_SOURCE',allowed_assets=set())
            with self.assertRaisesRegex(ContinuityError,'UNAUTHORIZED'):
                normalize_problem(proposed,j.verify(),mode='INFORMED',origin_work_id='W_X',allowed_assets=set())

    def test_handoff_integrity_and_no_spoofing(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root')
            opp=next(iter(live_opportunities(j).values()))
            record={'id':'W_NEW','mode':'INFORMED','opportunity_input_ids':[opp['opportunity_id']],
                'opportunity_handoff_records':[opp],
                'opportunity_handoff_digest':'a'*64,
                'continuity_contract_version':VERSION}
            with self.assertRaisesRegex(ContinuityError,'DIGEST'):
                check_work_handoff(record)
            record['opportunity_handoff_digest']=digest([opp]);check_work_handoff(record)
            record['mode']='FRESH'
            with self.assertRaisesRegex(ContinuityError,'FRESH'):
                check_work_handoff(record)

    def test_carry_visible_to_population_not_independent_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            exp=Path(tmp)/'EXPERIMENT'
            orig=make_root(exp/'ORIGINAL')
            record=next(iter(live_opportunities(orig).values()))
            for name in ('POPULATION','SYN_01'):
                loc=exp/'CYCLE_001'/name
                j=EvolutionJournal(loc);j.init('Synthetic P0 only')
                j.append('OPPORTUNITY_CARRIED',{'opportunity':record,
                    'upstream_root':str(orig.root),'upstream_head_sha256':digest(canonical(orig._events()[-1])),
                    'not_registered_science':True})
                indexed=opportunities_for_journal(j)
                if name=='POPULATION':self.assertIn(record['opportunity_id'],indexed)
                else:self.assertNotIn(record['opportunity_id'],indexed)
                self.assertEqual(j.verify().sources,{})
                self.assertEqual(j.verify().assets,{})


class TestNativeWorkerTypedSubmission(unittest.TestCase):
    def test_actual_engine_registers_typed_problem_without_legacy_parents(self):
        from e2core.engine import Engine
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root')
            j.evolve('EV_FOLLOWUP','DEVELOP',['A_SOURCE'],{
                'id':'W_FOLLOWUP','mode':'INFORMED','problem_id':'P0',
                'question':'Synthetic investigation',
                'research_rationale':'Synthetic only','source_ids':[]},
                'Synthetic research fixture')
            payload={'scientific_text':'Synthetic typed problem created',
                'next_action':'RETURN','assets':[],
                'new_problems':[{'id':'P_TYPED_WORKER',
                    'parent_problem_ids':['P0'],
                    'motivating_asset_ids':['A_SOURCE'],
                    'question':'Synthetic typed research question',
                    'scope':'Mock scope only',
                    'decomposition_rationale':'Synthetic decomposition',
                    'contribution_to_parent':'Synthetic motivation only'}],
                'tool_request':None}
            class SavedMock:
                def call(self, ident, actor, work_id, system, context):
                    j.append('MODEL_CALL_INTENT',{'id':ident,'actor':actor,
                        'work_id':work_id,'request_blob':j.blob({'MOCK':True}),
                        'model':'MOCK','billing_mode':'MOCK'})
                    j.append('MODEL_CALL_SAVED',{'id':ident,
                        'response_blob':j.blob({'choices':[{'message':{
                            'content':json.dumps(payload)}}]}),'usage':{}})
                    return json.dumps(payload)
            result=Engine(j,SavedMock()).worker_step('W_FOLLOWUP')
            self.assertEqual(result['status'],'RETURN')
            problem=j.verify().problems['P_TYPED_WORKER']
            self.assertEqual(problem['parents'],['P0'])
            self.assertEqual(problem['motivating_asset_ids'],['A_SOURCE'])
            self.assertEqual(problem['continuity_origin_work_id'],'W_FOLLOWUP')
            self.assertFalse(j.verify().sources)


class TestProviderReplayBoundary(unittest.TestCase):
    def test_new_index_is_pinned_and_saved_replay_is_exact(self):
        from unittest.mock import patch
        from e2core.provider import DurableModel
        from e2core.core import canon
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root')
            wires=[]
            def mock_only(wire,timeout=180):
                wires.append(json.loads(wire))
                return json.dumps({'choices':[{'message':{'content':'{"result":"MOCK"}'}}],
                                   'usage':{'total_tokens':0}}).encode()
            model=DurableModel(j,provider=mock_only,approved=True,max_new_calls=1,
                               model='TEST_MODEL_ONLY',max_tokens=100,mode='MOCK')
            args=('CTRL_D00001','CONTROLLER',None,'synthetic system',{'prompt':'Synthetic only'})
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'}):
                self.assertEqual(model.call(*args),'{"result":"MOCK"}')
                self.assertEqual(model.call(*args),'{"result":"MOCK"}')
            self.assertEqual(len(wires),1)
            text=wires[0]['messages'][1]['content']
            self.assertEqual(json.loads(text)['unregistered_opportunity_index']['count'],1)
            self.assertEqual(j.verify().model_calls['CTRL_D00001']['state'],'SAVED')
            # The provider itself is an in-memory fake, no real API request.
            self.assertEqual(j.verify().model_calls['CTRL_D00001']['billing_mode'],'MOCK')

    def test_preexisting_saved_controller_request_is_not_rewritten(self):
        from e2core.provider import DurableModel
        from e2core.core import canon
        with tempfile.TemporaryDirectory() as tmp:
            j=make_root(Path(tmp)/'root')
            payload={'prompt':'Older saved request without opportunity index'}
            wire=canon({'model':'TEST_MODEL_ONLY','temperature':0.7,
                'max_tokens':100,'response_format':{'type':'json_object'},
                'messages':[{'role':'system','content':'synthetic system'},
                    {'role':'user','content':json.dumps(payload,ensure_ascii=False,
                        sort_keys=True,allow_nan=False)}]})
            j.append('MODEL_CALL_INTENT',{'id':'CTRL_D00001','actor':'CONTROLLER',
                'work_id':None,'request_blob':j.blob(wire),
                'model':'TEST_MODEL_ONLY','billing_mode':'MOCK'})
            response={'choices':[{'message':{'content':'{"result":"SAVED"}'}}]}
            j.append('MODEL_CALL_SAVED',{'id':'CTRL_D00001',
                'response_blob':j.blob(response),'usage':{}})
            def must_never_call(*args,**kwargs):
                raise AssertionError('SAVED_REPLAY_MUST_NOT_CALL_PROVIDER')
            model=DurableModel(j,provider=must_never_call,approved=False,
                               max_new_calls=0,model='TEST_MODEL_ONLY',
                               max_tokens=100,mode='MOCK')
            self.assertEqual(model.call('CTRL_D00001','CONTROLLER',None,
                                        'synthetic system',payload),'{"result":"SAVED"}')
            self.assertEqual(j.verify().model_calls['CTRL_D00001']['request_blob'],
                             j.blob(wire))


class TestPinnedHistoricalArchive(unittest.TestCase):
    def test_g14_fixture_archive_population_only_if_configured(self):
        path=os.environ.get('M15_G14_ARCHIVE_FOR_TEST')
        if not path or not Path(path).exists():
            self.skipTest('set M15_G14_ARCHIVE_FOR_TEST for optional real historical archive check')
        with tempfile.TemporaryDirectory() as tmp:
            exp=Path(tmp)/'EXPERIMENT';exp.mkdir()
            (exp/'persistent.json').write_text('{}')
            (exp/'STOP_REQUESTED').touch()
            cfg=pin_archive(exp,path)
            self.assertEqual(cfg['entries'],19)
            pop=EvolutionJournal(exp/'CYCLE_000'/'POPULATION');pop.init('Synthetic P0')
            peer=EvolutionJournal(exp/'CYCLE_000'/'SYN_01');peer.init('Synthetic P0')
            idx=opportunities_for_journal(pop)
            self.assertEqual(len(idx),19)
            self.assertEqual(len(opportunities_for_journal(peer)),0)
            original_ids={x['original_id'] for x in idx.values()}
            self.assertIn('A_P0_redox_electrocapillary_two_pole_hypothesis_018',original_ids)
            self.assertIn('A_P0_two_pole_adversarial_null_test_019',original_ids)
            self.assertFalse(any(x['science_certification'] for x in idx.values()))
            self.assertFalse(pop.verify().assets)
            self.assertTrue((exp/PIN_NAME).is_file())
            with self.assertRaises(FileExistsError):pin_archive(exp,path)


if __name__=='__main__':unittest.main()
