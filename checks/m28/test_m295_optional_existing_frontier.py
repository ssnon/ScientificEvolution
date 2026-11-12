"""M29.5 ONGOING optional existing-frontier prior-art coverage regression.

All cases use isolated temporary, source-pinned roots; zero external calls.
Real papers/novelty are NOT certified by these tests.
"""
from __future__ import annotations
import copy
import unittest
from unittest.mock import patch

from e2core.core import EvidenceError
from e2core.engine import controller_plan
import e2core.m295_decision_contract as m295
from test_m295_prior_art_choices import (
    M295ContractTests, prob, prior_not_reviewed, hold,
)


def ongoing(*,extra=True):
    raw=hold()
    raw['disposition']='ONGOING'
    raw['research_frontier_assessment']=None
    raw['objective_assessment']['research_status']='CONTINUING'
    raw['remaining_calculation_assessments']=[]
    raw['prior_art_assessments']=[prior_not_reviewed()] if extra else []
    raw['actions']=[{'id':'EV_M295_ONGOING_001','operation':'DECOMPOSE',
      'asset_ids':[], 'reason':'Check conditional reachable-set computation',
      'work':{'id':'W_M295_ONGOING_001','mode':'INFORMED',
        'problem_id':'P_M295_TOY',
        'question':'Compute bounded input-output reachable sets',
        'research_rationale':'A countermodel can falsify a universal claim',
        'source_ids':[]}}]
    return raw


class TestM295OptionalExistingFrontier(unittest.TestCase):
    def setUp(self):
        M295ContractTests.setUp(self)

    def _register(self, *,legacy=False):
        p=prob()
        if legacy:
            p.pop('m295_interventions')
        self.j.append('PROBLEM_CREATED',p)

    def test_ongoing_existing_frontier_proactive_review_is_accepted(self):
        self._register()
        raw=ongoing(extra=True)
        # FULL Native Controller plan validation, not only M29.5 function.
        plan=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        record=next(p for kind,p in plan if kind=='PROGRAM_REVIEWED')
        audit=record['m295_model_authored_decision_audit']
        self.assertEqual([x['problem_id'] for x in audit['prior_art_assessments']],
                         ['P_M295_TOY'])
        self.assertEqual(set(audit['intervention_registration_status']['P_M295_TOY']),
                         {'T_EXPERIMENT','T_CALC'})

    def test_ongoing_existing_frontier_review_may_be_omitted(self):
        self._register()
        plan=controller_plan(self.j,ongoing(extra=False),'CTRL_D00001','D00001')
        audit=next(p for kind,p in plan if kind=='PROGRAM_REVIEWED')[
            'm295_model_authored_decision_audit']
        self.assertEqual(audit['prior_art_assessments'],[])

    def test_ongoing_unknown_problem_cannot_be_smuggled_in(self):
        self._register()
        raw=ongoing()
        raw['prior_art_assessments'][0]['problem_id']='P_INVENTED'
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_COVERAGE_MISMATCH'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_ongoing_nonfrontier_problem_rejected(self):
        self._register()
        raw=ongoing()
        state=copy.deepcopy(self.j.verify())
        state.problems['P_M295_TOY'].pop('research_frontier')
        with patch.object(m295,'active',return_value=True):
            with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_COVERAGE_MISMATCH'):
                m295.validate_decision(self.j,state,raw,[])

    def test_ongoing_closed_frontier_rejected(self):
        self._register()
        raw=ongoing()
        state=copy.deepcopy(self.j.verify())
        state.problems['P_M295_TOY']['status']='CLOSED'
        with patch.object(m295,'active',return_value=True):
            with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_COVERAGE_MISMATCH'):
                m295.validate_decision(self.j,state,raw,[])

    def test_ongoing_legacy_frontier_without_inventory_is_not_artificially_blocked(self):
        self._register(legacy=True)
        plan=controller_plan(self.j,ongoing(),'CTRL_D00001','D00001')
        audit=next(p for kind,p in plan if kind=='PROGRAM_REVIEWED')[
            'm295_model_authored_decision_audit']
        self.assertEqual(audit['prior_art_assessments'][0]['problem_id'],'P_M295_TOY')
        # No source has been read; provenance remains explicitly unverified.
        self.assertTrue(audit['novelty_not_guaranteed'])

    def test_hold_still_requires_all_open_frontier_reviews(self):
        self._register()
        raw=hold()
        raw['prior_art_assessments']=[]
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_COVERAGE_MISMATCH'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_duplicate_review_rejected(self):
        self._register()
        raw=ongoing()
        raw['prior_art_assessments'].append(copy.deepcopy(raw['prior_art_assessments'][0]))
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_COVERAGE_MISMATCH'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_optional_review_keeps_source_provenance_rules(self):
        self._register()
        raw=ongoing()
        item=raw['prior_art_assessments'][0]['intervention_reviews'][0]
        item['status']='REVIEWED'
        item['contribution_class']='POTENTIALLY_DISTINCT'
        item['compared_sources']=[{'source_id':'SRC_INVENTED','evidence_level':'FULL_TEXT',
          'what_prior_work_tested':'Invented result',
          'remaining_delta':'A comparison without a registered source'}]
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_SOURCE_NOT_REGISTERED'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_ongoing_new_frontier_plus_existing_review_both_allowed(self):
        self._register()
        raw=ongoing(extra=True)
        new=prob();new['id']='P_M295_OTHER'
        raw['new_problems']=[new]
        another=copy.deepcopy(prior_not_reviewed())
        another['problem_id']='P_M295_OTHER'
        raw['prior_art_assessments'].append(another)
        plan=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        audit=next(p for kind,p in plan if kind=='PROGRAM_REVIEWED')[
            'm295_model_authored_decision_audit']
        self.assertEqual({x['problem_id'] for x in audit['prior_art_assessments']},
                         {'P_M295_TOY','P_M295_OTHER'})

    def test_new_frontier_still_requires_its_own_review(self):
        self._register()
        raw=ongoing(extra=True)
        new=prob();new['id']='P_M295_OTHER'
        raw['new_problems']=[new]
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_COVERAGE_MISMATCH'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')


if __name__=='__main__':
    unittest.main()
