#!/usr/bin/env python3
import unittest,math,sys,pathlib,json,hashlib,tempfile
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import verify_mc as v
import audit_bridge as bridge

class IndependentFeedbackTests(unittest.TestCase):
    def test_telegraph_exact_transition(self):
        dt=.005;tau=.1
        p=(1-math.exp(-dt/tau))/2
        self.assertAlmostEqual(p,.024385287749643,12)
        wrong=1-math.exp(-2*dt/tau)
        self.assertGreater(wrong,p*3.5)
    def test_variance_theory(self):
        self.assertAlmostEqual(v.integrated_variance(1000,.3,.1,.1),662.1829941085964,8)
    def test_bounded_continuous_null(self):
        null=v.jacobi_null_moments(.2,.6)
        self.assertGreater(null['support_min_relative_intensity'],0)
        self.assertAlmostEqual(null['fourth_cumulant'],-6/3.4,10)
    def test_packet_has_original_code_receipt(self):
        p,h=bridge.packet_load()
        self.assertEqual(p['original_calculation']['code_sha256'],'6bea5c9004b6d7f727c1a01c1186ce6d4bcdbfca1edd168b37f9a3ec93a8deaa')
        self.assertEqual(p['redox_unregistered_candidate_notice']['not_promoted_to_asset'],True)
        self.assertTrue(bridge.source_id(h).startswith('SRC_AUDIT_G13_MC_'))
    def test_injected_payload_is_labeled_and_original_untouched(self):
        p,h=bridge.packet_load()
        old={'pinned_input':{'work':{'id':'W'}},'own_prior_steps':[]}
        newer=bridge.inject_into_payload(old,p,bridge.source_id(h))
        self.assertNotIn('independent_external_science_audit',old)
        self.assertEqual(newer['own_prior_steps'],old['own_prior_steps'])
        self.assertFalse(newer['independent_external_science_audit']['origin'].startswith('ACTUAL'))
    def _fixture(self, corrupt=None):
        code='x=1\nresult={"number": x}'
        digest=hashlib.sha256(code.encode()).hexdigest()
        pkt={'original_calculation':{'code_sha256':digest}}
        req={'kind':'python_science','arguments':{'code':code}}
        got={'code_sha256':digest,'status':'EXECUTED','exit_code':0,'result':{'number':1},'sandbox_backend':'bubblewrap'}
        if corrupt=='wrong_hash':got['code_sha256']='0'*64
        if corrupt=='not_executed':got['status']='REJECTED'
        if corrupt=='failed_exit':got['exit_code']=1
        # WORK_STEP 'result' is the backend receipt, not the nested scientific values.
        step2={'text':json.dumps({'tool_request':req})}
        step3={'tool_id':bridge.EXPECTED_TOOL,'result':got,'is_empirical_evidence':False}
        wire={ 'step2':json.dumps(step2).encode(), 'step3':json.dumps(step3).encode(),
               'toolreq':json.dumps(req).encode(), 'toolres':json.dumps(got).encode() }
        class Journal:
            def raw(self,k):return wire[k]
            root=pathlib.Path('/synthetic')
            def _events(self):return [{'a':1}]
        w={'mode':'INFORMED','status':'ACTIVE','steps':[{'kind':'MODEL_RESPONSE','raw_blob':'step1'},
          {'kind':'MODEL_RESPONSE','raw_blob':'step2'},
          {'kind':'TOOL_RESULT','raw_blob':'step3'}]}
        tr={'work_id':bridge.WORK,'request_blob':'toolreq','result_blob':'toolres'}
        if corrupt=='different_recorded_result':wire['toolres']=json.dumps({'other':1}).encode()
        if corrupt=='missing_record':tr=None
        s=SimpleNamespace(work={bridge.WORK:w},model_calls={},sources={},tool_results=({bridge.EXPECTED_TOOL:tr} if tr else {}))
        mods=SimpleNamespace(sha=lambda _: 'head_sha',canon=lambda x:json.dumps(x).encode())
        return pkt,Journal(),s,mods
    def test_e2_executed_receipt_shape_and_journal_consistency(self):
        packet,j,s,mods=self._fixture()
        self.assertEqual(bridge.verify_executed_receipt(j,s,packet),packet['original_calculation']['code_sha256'])
    def test_real_receipt_shape_does_not_have_nested_code_sha(self):
        packet,j,s,mods=self._fixture()
        last=json.loads(j.raw('step3'))
        self.assertNotIn('code_sha256',last['result']['result'])
        self.assertEqual(last['result']['code_sha256'],packet['original_calculation']['code_sha256'])
        self.assertEqual(bridge.verify_executed_receipt(j,s,packet),packet['original_calculation']['code_sha256'])
    def test_bad_receipts_fail_closed(self):
        for bad in ('wrong_hash','not_executed','failed_exit','different_recorded_result','missing_record'):
            with self.subTest(bad=bad):
                pkt,j,s,_=self._fixture(corrupt=bad)
                with self.assertRaises(RuntimeError):bridge.verify_executed_receipt(j,s,pkt)

if __name__=='__main__':unittest.main(verbosity=2)
