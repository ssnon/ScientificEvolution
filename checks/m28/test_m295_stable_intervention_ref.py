"""M29.5: a registered intervention is ID+kind; model echo is not its identity.

Every case uses a freshly initialized source-pinned TEMP root and no paid model.
No test certifies scientific equivalence, novelty, or correctness of the model.
"""
from __future__ import annotations
import copy
import unittest

from e2core.core import EvidenceError
from e2core.engine import controller_plan
from test_m295_prior_art_choices import M295ContractTests, prob, hold


class TestM295StableInterventionReferences(unittest.TestCase):
    def setUp(self):
        M295ContractTests.setUp(self)

    def scenario(self):
        p=prob()
        p['m295_interventions']=[
            {'id':'T_EVAL_MATH','kind':'CALCULATION',
             'method_or_observation':'Joint reachable-set profiling',
             'distinguishing_claim':'Whether simultaneous and sequential-spatial response sets can be separated'},
            {'id':'T_EVAL_PULSE','kind':'EXPERIMENT',
             'method_or_observation':'Resolved A/B-selective pulse and intermediate readout',
             'distinguishing_claim':'Whether a resolved ordered intermediate can reject a restricted instant comparator'},
        ]
        self.j.append('PROBLEM_CREATED',p)
        raw=hold(linked=True)
        raw['prior_art_assessments'][0]['intervention_reviews']=[
            {'id':d['id'],'kind':d['kind'],
             'method_or_observation':d['method_or_observation'],
             'distinguishing_claim':d['distinguishing_claim'],
             'status':'NOT_REVIEWED','contribution_class':'UNCERTAIN',
             'compared_sources':[],'attempted_tool_ids':[],
             'search_limitations':'No verified outside literature available',
             'scientific_value':'Candidate contrast; novelty has not been assessed'}
            for d in p['m295_interventions']
        ]
        return raw

    def plan(self,raw):
        # Native Controller의 SAVED 호출 선행조건 재현
        M295ContractTests.saved_controller(self)
        planned=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        return next(p['m295_model_authored_decision_audit'] for k,p in planned if k=='PROGRAM_REVIEWED')

    def test_real_reported_two_claim_paraphrases_do_not_invent_novelty(self):
        raw=self.scenario()
        reviews=raw['prior_art_assessments'][0]['intervention_reviews']
        reviews[0]['distinguishing_claim'] += ' under common observables and explicit bounds'
        reviews[1]['distinguishing_claim'] = ('Whether a resolved ordered intermediate '
            'can reject a restricted instantaneous comparator')
        audit=self.plan(raw)
        binding=audit['intervention_review_scope_binding']['P_M295_TOY']
        self.assertEqual(set(binding),{'T_EVAL_MATH','T_EVAL_PULSE'})
        for ident in binding:
            item=binding[ident]
            self.assertEqual(item['echo_status'],'LEGACY_ECHO_DIFFERS_UNVERIFIED')
            self.assertEqual(item['echo_disagreement_fields'],['distinguishing_claim'])
            self.assertEqual(item['binding'],'REGISTERED_ID_AND_KIND')
            self.assertNotEqual(reviews[0]['distinguishing_claim'],
                binding['T_EVAL_MATH']['authoritative_registered_intervention']['distinguishing_claim'])
        self.assertTrue(audit['novelty_not_guaranteed'])
        self.assertEqual(audit['intervention_registration_status']['P_M295_TOY']['T_EVAL_MATH'],
                         'PROVISIONAL_NOVELTY_UNVERIFIED')

    def test_compact_reference_to_registered_intervention_is_accepted(self):
        raw=self.scenario()
        for item in raw['prior_art_assessments'][0]['intervention_reviews']:
            del item['method_or_observation']; del item['distinguishing_claim']
        audit=self.plan(raw)
        binding=audit['intervention_review_scope_binding']['P_M295_TOY']
        self.assertTrue(all(x['echo_status']=='CANONICAL_ID_REFERENCE_NO_ECHO' for x in binding.values()))
        self.assertTrue(all(x['authoritative_registered_intervention'] for x in binding.values()))

    def test_exact_old_format_retains_validity(self):
        audit=self.plan(self.scenario())
        self.assertTrue(all(v['echo_status']=='LEGACY_ECHO_EXACT' for v in
            audit['intervention_review_scope_binding']['P_M295_TOY'].values()))

    def test_kind_change_is_always_rejected(self):
        raw=self.scenario()
        raw['prior_art_assessments'][0]['intervention_reviews'][0]['kind']='EXPERIMENT'
        with self.assertRaisesRegex(EvidenceError,'M295_INTERVENTION_REVIEW_KIND_CHANGED'):
            self.plan(raw)

    def test_ref_to_unknown_test_is_rejected(self):
        raw=self.scenario()
        raw['prior_art_assessments'][0]['intervention_reviews'][0]['id']='T_UNKNOWN'
        with self.assertRaisesRegex(EvidenceError,'M295_INTERVENTION_PRIOR_ART_COVERAGE_MISMATCH'):
            self.plan(raw)

    def test_non_uncertain_contribution_with_scope_drift_rejected(self):
        raw=self.scenario()
        rev=raw['prior_art_assessments'][0]['intervention_reviews'][0]
        rev['distinguishing_claim']='A completely different scientific claim'
        rev['contribution_class']='POTENTIALLY_DISTINCT'
        rev['status']='REVIEWED'
        with self.assertRaisesRegex(EvidenceError,'M295_SCOPE_DRIFT_CANNOT_SUPPORT_NOVELTY_CLASS'):
            self.plan(raw)

    def test_partial_legacy_echo_is_not_silently_repaired(self):
        raw=self.scenario()
        del raw['prior_art_assessments'][0]['intervention_reviews'][0]['distinguishing_claim']
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_ITEM_FIELDS_INVALID'):
            self.plan(raw)

    def test_new_frontier_compact_review_preserves_registration(self):
        raw=hold(new=True)
        for item in raw['prior_art_assessments'][0]['intervention_reviews']:
            del item['method_or_observation'];del item['distinguishing_claim']
        audit=self.plan(raw)
        self.assertEqual(set(audit['intervention_registration_status']['P_M295_TOY']),
                         {'T_EXPERIMENT','T_CALC'})

    def test_compact_review_of_legacy_uninventoried_frontier_rejected(self):
        p=prob(); del p['m295_interventions'];self.j.append('PROBLEM_CREATED',p)
        raw=hold(linked=True)
        item=raw['prior_art_assessments'][0]['intervention_reviews'][0]
        del item['method_or_observation'];del item['distinguishing_claim']
        with self.assertRaisesRegex(EvidenceError,'M295_LEGACY_WITHOUT_INVENTORY_NEEDS_SCOPE'):
            self.plan(raw)


if __name__=='__main__':
    unittest.main()
