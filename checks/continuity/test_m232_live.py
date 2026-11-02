"""M23.2 no-network tests for experimental Option/Controller gateway."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from e2core.core import EvidenceError, EvolutionJournal
from e2core.provider import DurableModel
from e2core.m232_live import FULL, ON_DEMAND, assessor_call, selected_mode
from e2core.m232_partb import TAG


class FakeModel:
    mode = 'MOCK'

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def call(self, ident, actor, work_id, prompt, payload):
        self.calls.append((ident, actor, work_id, prompt, payload))
        if not self.answers:
            raise AssertionError('UNEXPECTED_MODEL_CALL')
        return json.dumps(self.answers.pop(0))


def context():
    return {
        'program': {'problem':'P0 original problem'},
        'assets': [
            {'id':'A1','kind':'NULL_MODEL','origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK',
             'claim':'Historical null', 'scope':'whole', 'predictions':['negative control'],
             'limitations':['strongest confound'], 'source_ids':[], 'parent_ids':[]},
            {'id':'A2','kind':'HYPOTHESIS','origin':'LIVE_WORK','claim':'Current hypothesis',
             'scope':'whole','predictions':['positive signal'],'limitations':[], 'source_ids':[],
             'parent_ids':[]},
        ],
        'problems': [
            {'id':'P0','question':'Original?','parents':[],'scope':'whole'},
            {'id':'P1','question':'Historical?','parents':['P0'],'scope':'narrow',
             'decomposition_rationale':'Old derivation'},
        ],
        'm23_root_scoped_asset_namespace': {'canonical_asset_ids':['A1','A2']},
    }


class LiveGatewayTests(unittest.TestCase):
    def test_full_mode_preserves_exact_call(self):
        old = context()
        m = FakeModel([{'opportunities':[]}])
        text, ident, trace=assessor_call(m,None,'OPP_D00001','PROMPT',old,
                                         'OPPORTUNITY',mode=FULL)
        self.assertEqual(ident,'OPP_D00001')
        self.assertIsNone(trace)
        self.assertEqual(m.calls[0][:4],('OPP_D00001','CONTROLLER',None,'PROMPT'))
        self.assertEqual(m.calls[0][4],old)
        self.assertNotIn('m232_live_detail_mode',m.calls[0][4])

    def test_one_call_direct_native_answer(self):
        m=FakeModel([{'opportunities':[]}])
        _text,ident,trace=assessor_call(m,None,'OPP_D00001','PROMPT',context(),
                                        'OPPORTUNITY',mode=ON_DEMAND)
        self.assertEqual(len(m.calls),1)
        self.assertEqual(ident,'OPP_D00001')
        self.assertEqual(trace['indexed_asset_count'],1)
        self.assertTrue(trace['finished'])
        self.assertIn(TAG,m.calls[0][4]['assets'][0])
        self.assertEqual(m.calls[0][4]['m232_live_detail_mode'],'ON_DEMAND')

    def test_request_old_null_then_native_answer(self):
        m=FakeModel([
            {'m232_action':'REQUEST_DETAILS','asset_ids':['A1'],
             'problem_ids':['P1'],'reason':'Inspect the opposing derivation'},
            {'opportunities':[{'question':'Test the null'}]},
        ])
        _text,ident,trace=assessor_call(m,None,'OPP_D00002','PROMPT',context(),
                                        'OPPORTUNITY',mode=ON_DEMAND)
        self.assertEqual(len(m.calls),2)
        self.assertEqual(ident,'OPP_D00002_M232R0001')
        self.assertIn(TAG,m.calls[0][4]['assets'][0])
        self.assertNotIn(TAG,m.calls[1][4]['assets'][0])
        self.assertEqual(m.calls[1][4]['assets'][0]['limitations'],['strongest confound'])
        self.assertEqual(m.calls[1][4]['problems'][1]['decomposition_rationale'],'Old derivation')
        self.assertEqual(trace['indexed_asset_count'],0)
        self.assertEqual(trace['indexed_problem_count'],0)

    def test_full_request_available_without_detail_quota(self):
        m=FakeModel([
            {'m232_action':'REQUEST_FULL_CONTEXT','reason':'Need all old controls'},
            {'actions':[],'disposition':'HOLD_WITH_RATIONALE','rationale':'Insufficient'},
        ])
        _text,ident,trace=assessor_call(m,None,'CTRL_D00003','PROMPT',context(),
                                        'CONTROLLER',mode=ON_DEMAND)
        self.assertEqual(len(m.calls),2)
        self.assertEqual(ident,'CTRL_D00003_M232R0001')
        self.assertNotIn(TAG,m.calls[1][4]['assets'][0])
        self.assertEqual(trace['indexed_asset_count'],0)
        self.assertEqual(trace['indexed_problem_count'],0)

    def test_invalid_response_fails_closed_without_silent_repair(self):
        m=FakeModel([{'m232_action':'REQUEST_DETAILS','asset_ids':['MISSING'],
                      'reason':'Just curious'}])
        with self.assertRaisesRegex(EvidenceError,'INVALID_MODEL_DETAIL_RESPONSE'):
            assessor_call(m,None,'OPP_D00004','PROMPT',context(),
                          'OPPORTUNITY',mode=ON_DEMAND)
        self.assertEqual(len(m.calls),1)

    def test_invalid_native_schema_fails_closed(self):
        m=FakeModel([{'rationale':'not a controller schema'}])
        with self.assertRaisesRegex(EvidenceError,'INVALID_MODEL_DETAIL_RESPONSE'):
            assessor_call(m,None,'CTRL_D00004','PROMPT',context(),
                          'CONTROLLER',mode=ON_DEMAND)

    def test_default_full_and_external_optin_budget_guard(self):
        with tempfile.TemporaryDirectory() as td:
            j=EvolutionJournal(Path(td)/'journal')
            j.init('P0')
            self.assertEqual(selected_mode(j,FakeModel([])),FULL)
            with patch.dict(os.environ,{'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND'},clear=False):
                self.assertEqual(selected_mode(j,FakeModel([])),ON_DEMAND)
                class External:
                    mode='EXTERNAL'
                with patch.dict(os.environ,{'M232_BUDGET_REQUIRED':''},clear=False):
                    with self.assertRaisesRegex(EvidenceError,'REQUIRES_EXPLICIT_DEVELOPMENT_BUDGET'):
                        selected_mode(j,External())

    def test_preexisting_full_request_rejects_optin(self):
        with tempfile.TemporaryDirectory() as td:
            j=EvolutionJournal(Path(td)/'journal')
            j.init('P0')
            old={'messages':[{'role':'user','content':json.dumps(context())}]}
            j.append('MODEL_CALL_INTENT',{'id':'OPP_D00001','actor':'CONTROLLER',
                     'work_id':None,'request_blob':j.blob(old),'model':'mock',
                     'billing_mode':'MOCK'})
            with patch.dict(os.environ,{'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND'},clear=False):
                with self.assertRaisesRegex(EvidenceError,'MODE_DRIFT'):
                    selected_mode(j,FakeModel([]))

    def test_saved_adaptive_call_rejects_mode_switch(self):
        with tempfile.TemporaryDirectory() as td:
            j=EvolutionJournal(Path(td)/'journal')
            j.init('P0')
            oldctx={**context(),'m232_live_detail_mode':'ON_DEMAND'}
            old={'messages':[{'role':'user','content':json.dumps(oldctx)}]}
            j.append('MODEL_CALL_INTENT',{'id':'OPP_D00001','actor':'CONTROLLER',
                     'work_id':None,'request_blob':j.blob(old),'model':'mock',
                     'billing_mode':'MOCK'})
            with self.assertRaisesRegex(EvidenceError,'MODE_DRIFT'):
                selected_mode(j,FakeModel([]))

    def test_real_durable_replay_after_budget_interruption(self):
        # No actual network. A saved detail request must not bill again after
        # a process restart; the second round gets its own durable call ID.
        with tempfile.TemporaryDirectory() as td:
            j=EvolutionJournal(Path(td)/'journal')
            j.init('P0')
            requests=[]

            def first_provider(wire, timeout=180):
                requests.append(wire)
                return json.dumps({'choices':[{'message':{'content':json.dumps({
                    'm232_action':'REQUEST_DETAILS','asset_ids':['A1'],
                    'problem_ids':[],'reason':'Need old null limitations'
                })}}]}).encode()

            first=DurableModel(j,provider=first_provider,approved=True,
                               max_new_calls=1,model='mock/model',mode='MOCK')
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'},clear=False):
                with self.assertRaisesRegex(EvidenceError,'OPERATIONAL_CALL_BUDGET_REACHED'):
                    assessor_call(first,j,'OPP_D00009','PROMPT',context(),
                                  'OPPORTUNITY',mode=ON_DEMAND)
            self.assertEqual(len(requests),1)
            self.assertEqual(j.verify().model_calls['OPP_D00009']['state'],'SAVED')

            def next_provider(wire, timeout=180):
                requests.append(wire)
                return json.dumps({'choices':[{'message':{'content':json.dumps({
                    'opportunities':[]
                })}}]}).encode()

            second=DurableModel(j,provider=next_provider,approved=True,
                                max_new_calls=1,model='mock/model',mode='MOCK')
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'},clear=False):
                _text,cid,trace=assessor_call(second,j,'OPP_D00009','PROMPT',context(),
                                               'OPPORTUNITY',mode=ON_DEMAND)
            self.assertEqual(cid,'OPP_D00009_M232R0001')
            self.assertTrue(trace['finished'])
            self.assertEqual(len(requests),2)
            self.assertEqual(len(j.verify().model_calls),2)

    def test_uncertain_provider_never_reissued(self):
        with tempfile.TemporaryDirectory() as td:
            j=EvolutionJournal(Path(td)/'journal')
            j.init('P0')
            network_attempts=[]

            def unavailable(wire,timeout=180):
                network_attempts.append(wire)
                raise ConnectionError('unknown provider outcome')

            model=DurableModel(j,provider=unavailable,approved=True,
                               max_new_calls=2,model='mock/model',mode='MOCK')
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'},clear=False):
                with self.assertRaisesRegex(EvidenceError,'PROVIDER_UNKNOWN_OUTCOME'):
                    assessor_call(model,j,'OPP_D00010','PROMPT',context(),
                                  'OPPORTUNITY',mode=ON_DEMAND)
                retry=DurableModel(j,provider=unavailable,approved=True,
                                   max_new_calls=2,model='mock/model',mode='MOCK')
                with self.assertRaisesRegex(EvidenceError,'UNCERTAIN_MODEL_CALL'):
                    assessor_call(retry,j,'OPP_D00010','PROMPT',context(),
                                  'OPPORTUNITY',mode=ON_DEMAND)
            self.assertEqual(len(network_attempts),1)
            self.assertEqual(j.verify().model_calls['OPP_D00010']['state'],'UNCERTAIN')

    def test_real_syn_route_references_actual_final_call(self):
        import inspect
        import scientific_closed_loop_v3 as v3
        src=inspect.getsource(v3.controller_v3)
        self.assertIn('m232_detail_mode=selected_mode(j,self.model)',src)
        self.assertIn('assessor_call(self.model,j,opp_id',src)
        self.assertIn('assessor_call(self.model,j,\'CTRL_\'+ident',src)
        self.assertIn('controller_plan(j,control,m232_final_controller_call_id,ident)',src)
        self.assertIn("'call_id':m232_final_controller_call_id",src)

    def test_no_user_visible_science_certification(self):
        m=FakeModel([{'opportunities':[]}])
        _text,ident,trace=assessor_call(m,None,'OPP_D00001','PROMPT',context(),
                                        'OPPORTUNITY',mode=ON_DEMAND)
        self.assertFalse(trace['scientific_equivalence_certified'])
        self.assertEqual(m.calls[0][4]['m232_shadow_projection']['status'],
                         'EXPERIMENTAL_OPT_IN_LIVE_UNCERTIFIED')

if __name__=='__main__':unittest.main()
