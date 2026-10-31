#!/usr/bin/env python3
import unittest,math,sys,pathlib,json,hashlib
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
if __name__=='__main__':unittest.main(verbosity=2)
