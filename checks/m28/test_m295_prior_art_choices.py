"""M29.5 explicit opt-in source-pinned science decision contract, NO PAID CALLS.

The tests intentionally validate provenance/schema, not scientific truth.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from e2core.core import EvolutionJournal, EvidenceError, canon, sha
from e2core.activation_contract import PROTOCOL as PROFILE_PROTOCOL
from e2core.engine import controller_plan, effective_controller_contract
from e2core.m295_decision_contract import active, literature_source_index, FLAG
import meta_research_autonomy as meta_run

FEATURES={
  'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND',
  'M232_NAMESPACE_MODE':'COMPACT',
  'M233_MODEL_METADATA_MODE':'SEPARATE',
  'M232_CACHE_POLICY':'SELECTIVE_NO_WRITE',
  'M232_SYN_PMI_MODE':'FULL',
  'M232_BUDGET_REQUIRED':'YES',
}
MODEL='openai/gpt-5.6-luna'


def frontier():
    return {
      'scientific_status':'PROPOSED_NOT_EXECUTED',
      'competing_hypotheses':['H1: alternative states differ','H0: one nuisance model explains both'],
      'discriminating_intervention_or_observation':'A controlled input-output contrast',
      'predicted_outcomes':[
         {'if':'H1','then':'A bounded residual occurs','limitation':'No unique mechanism'},
         {'if':'H0','then':'Both inputs lie in null set','limitation':'Not absence of H1'},
      ],
      'required_evidence':[
         {'kind':'CALCULATION','purpose':'Fit one common correlated null',
          'acquisition_state':'NOT_ATTEMPTED'},
         {'kind':'EXPERIMENT','purpose':'Measure input-output contrasts',
          'acquisition_state':'REQUIRES_EXTERNAL_RESOURCE'},
      ],
      'blocking_resources':['Missing catalyst-specific observations'],
      'interpretation_limits':'Conditional only, no unique mechanism',
      'motivating_asset_ids':[],
    }


def prob():
    return {
      'id':'P_M295_TOY','parents':['P0'],
      'question':'Which intervention discriminates two candidate mechanisms?',
      'decomposition_rationale':'Both mechanisms fit existing observations',
      'contribution_to_parent':'Identifiability subproblem',
      'scope':'Toy model, not a real catalyst',
      'research_frontier':frontier(),
      'm295_interventions':[
         {'id':'T_EXPERIMENT','kind':'EXPERIMENT',
          'method_or_observation':'Matched time-resolved measurement',
          'distinguishing_claim':'Separate sequential and simultaneous input effects'},
         {'id':'T_CALC','kind':'CALCULATION',
          'method_or_observation':'Joint null reachable-set profiling',
          'distinguishing_claim':'Whether one null fits all correlated modalities'},
      ],
    }


def prior_not_reviewed():
    def entry(ident,kind,method,claim):
        return {'id':ident,'kind':kind,'method_or_observation':method,
            'distinguishing_claim':claim,
            'status':'NOT_REVIEWED','contribution_class':'UNCERTAIN',
            'compared_sources':[],'attempted_tool_ids':[],
            'search_limitations':'No literature inquiry has been completed',
            'scientific_value':'Provisional conditional contrast, unverified novelty'}
    return {'problem_id':'P_M295_TOY',
        'coverage_explanation':'Separated experimental observations from computation',
        'intervention_reviews':[
         entry('T_EXPERIMENT','EXPERIMENT','Matched time-resolved measurement',
               'Separate sequential and simultaneous input effects'),
         entry('T_CALC','CALCULATION','Joint null reachable-set profiling',
               'Whether one null fits all correlated modalities'),
        ]}


def calc():
    return {'problem_id':'P_M295_TOY','decision':'DEFER',
            'information_value':'Could quantify whether a bounded common null fits two channels',
            'reason':'No empirically justified physical bounds are currently available',
            'missing_inputs':'Catalyst-specific bounded nuisance values'}


def org(choice='LOCAL_WORK'):
    return {'choice':choice,
            'independence_value':'A genuinely blind reviewer might reveal missing alternatives',
            'overlap_or_cost':'Additional root could repeat prior symbolic work',
            'rationale':'No new autonomous root is presently requested for this toy checkpoint'}


def hold(*,new=False,linked=False):
    raw={
     'rationale':'An empirical test and bounded model remain unperformed; science is unresolved',
     'new_problems':[prob()] if new else [],'reviews':[],'actions':[],
     'portfolio_decisions':[], 'organization_requests':[],
     'collaboration_requests':[],
     'disposition':'HOLD_WITH_RATIONALE',
     'unresolved_opportunities':['Quantified nuisance bounds and matched observations'],
     'objective_assessment':{
        'objective_status':'UNRESOLVED','research_status':'PAUSED_EVIDENCE',
        'resolved_scope':'Conditional theory only','objective_coverage':'SUBPROBLEM_ONLY',
        'supporting_asset_ids':[],
        'remaining_questions':['Will a matched intervention discriminate?'],
        'untried_approaches_considered':['Bounded correlated calculation'],
        'reason':'Proposed testing is incomplete',
     },
     'research_frontier_assessment':{
         'status':'REGISTERED_NEW' if new else ('LINKED_EXISTING' if linked else 'NO_ADDITIONAL_VALUE'),
         'problem_ids':['P_M295_TOY'] if new or linked else [],
         'rationale':'Preserve an existing or candidate discriminating research test',
     },
     'prior_art_assessments':[prior_not_reviewed()] if new or linked else [],
     'remaining_calculation_assessments':[calc()] if new or linked else [],
     'organization_choice_assessment':org(),
    }
    return raw


class M295ContractTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder=Path(temp.name)
        self.exp=folder/'M295_NEW_OPT_IN'
        problem=folder/'P0.txt'; problem.write_text('Can two hypothetical mechanisms be distinguished?',encoding='utf8')
        profile=folder/'activation.json'; profile.write_text(json.dumps({
            'protocol':PROFILE_PROTOCOL,'model':MODEL,
            'purpose':'M29.5 source-pinned offline integration',
            'features':FEATURES}),encoding='utf8')
        budget=folder/'budget.json'; budget.write_text(json.dumps({
            'protocol':'M232_DEVELOPMENT_BUDGET_V1','limit_usd':8.0,
            'model_rates_per_million_usd':{MODEL:{'input':0.25,'output':2.0}},
            'reserve_multiplier':1.25}),encoding='utf8')
        with patch.dict(os.environ, {**FEATURES,
                         'FAKG_RESEARCH_ALLOW_PAID':'NO',
                         'M295_SCIENCE_CHOICE_GATE':'YES'}, clear=False):
            meta_run.init(SimpleNamespace(out=str(self.exp),problem_file=str(problem),
                activation_profile=str(profile),budget_config=str(budget)))
            meta_run._preflight(self.exp,json.loads((self.exp/'meta_research.json').read_text()))
        self.j=EvolutionJournal(self.exp/'ROOTS'/'PRIMARY')
        self.assertTrue(active(self.j))

    def saved_controller(self):
        cid='CTRL_D00001'
        self.j.append('MODEL_CALL_INTENT',{'id':cid,'actor':'CONTROLLER',
          'work_id':None,'request_blob':self.j.blob({'synthetic':True}),
          'model':MODEL,'billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED',{'id':cid,
          'response_blob':self.j.blob({'synthetic':True}),
          'usage':{'cost':0}})

    def test_active_contract_is_in_both_manifests_and_prompt(self):
        for name in ('meta_research.json','persistent.json'):
            self.assertIs(json.loads((self.exp/name).read_text())[FLAG],True)
        prompt,context=effective_controller_contract(self.j,'OLD_PROMPT',{'ctx':'base'})
        self.assertIn('M29.5 PRIOR-ART',prompt)
        self.assertEqual(context['m295_prior_art_source_index'],[])

    def test_new_frontier_without_prior_art_assessment_rejected(self):
        raw=hold(new=True); del raw['prior_art_assessments']
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_ASSESSMENTS_REQUIRED'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertFalse(self.j.verify().problems.get('P_M295_TOY'))

    def test_new_frontier_provisional_unverified_is_allowed_not_certified(self):
        self.saved_controller()
        plan=controller_plan(self.j,hold(new=True),'CTRL_D00001','D00001')
        review=next(p for k,p in plan if k=='PROGRAM_REVIEWED')
        self.assertIs(review['m295_model_authored_decision_audit']['novelty_not_guaranteed'],True)
        self.assertEqual(review['m295_model_authored_decision_audit']['prior_art_assessments'][0]
                         ['intervention_reviews'][0]['contribution_class'],'UNCERTAIN')
        self.assertIn('PROBLEM_CREATED',[k for k,p in plan])

    def test_cannot_claim_potential_novelty_without_literature_comparison(self):
        raw=hold(new=True)
        raw['prior_art_assessments'][0]['intervention_reviews'][0]['contribution_class']='POTENTIALLY_DISTINCT'
        with self.assertRaisesRegex(EvidenceError,'M295_NOT_REVIEWED_CANNOT_ASSERT_NOVELTY'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_false_source_id_cannot_support_reviewed(self):
        raw=hold(new=True)
        entry=raw['prior_art_assessments'][0]['intervention_reviews'][0]
        entry['status']='REVIEWED'; entry['contribution_class']='POTENTIALLY_DISTINCT'
        entry['compared_sources']=[{'source_id':'SRC_INVENTED','evidence_level':'FULL_TEXT',
          'what_prior_work_tested':'Prior paper tested method','remaining_delta':'New conditional contrast'}]
        with self.assertRaisesRegex(EvidenceError,'M295_PRIOR_ART_SOURCE_NOT_REGISTERED'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_reviewed_literature_metadata_is_not_full_text(self):
        sid='SRC_M295_TOY_META'
        self.j.append('SOURCE_REGISTERED',{'id':sid,'kind':'TOOL_RESULT',
          'blob':self.j.blob({'request':{'kind':'literature_research',
            'arguments':{'action':'search'}},'result':{'status':'DELIVERED'},
            'evidence_class':'BIBLIOGRAPHIC_METADATA'}),
          'description':'Synthetic metadata fixture; not real citation', 'work_id':'W_fixture'})
        raw=hold(new=True)
        p=raw['prior_art_assessments'][0]['intervention_reviews'][0]
        p['status']='REVIEWED';p['contribution_class']='POTENTIALLY_DISTINCT'
        p['compared_sources']=[{'source_id':sid,'evidence_level':'FULL_TEXT',
             'what_prior_work_tested':'The title mentions the method',
             'remaining_delta':'Cannot verify result from abstract'}]
        with self.assertRaisesRegex(EvidenceError,'M295_FULLTEXT_NOT_ACTUALLY_READ'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')
        p['compared_sources'][0]['evidence_level']='METADATA'
        with self.assertRaisesRegex(EvidenceError,'M295_NONUNCERTAIN_REQUIRES_FULLTEXT_COMPARISON'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')
        p['contribution_class']='UNCERTAIN'
        self.saved_controller()
        plan=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertEqual(len([k for k,p in plan if k=='PROBLEM_CREATED']),1)
        self.assertEqual(len(literature_source_index(self.j)),1)

    def test_prior_art_must_cover_every_intervention_not_just_problem(self):
        raw=hold(new=True)
        raw['prior_art_assessments'][0]['intervention_reviews'].pop()
        with self.assertRaisesRegex(EvidenceError,'M295_INTERVENTION_PRIOR_ART_COVERAGE_MISMATCH'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_actual_fulltext_source_supports_tentative_distinction_only(self):
        sid='SRC_M295_TOY_FULLTEXT'
        self.j.append('SOURCE_REGISTERED',{'id':sid,'kind':'TOOL_RESULT',
          'blob':self.j.blob({'request':{'kind':'literature_research',
            'arguments':{'action':'read_fulltext'}},'result':{'status':'DELIVERED'},
            'evidence_class':'OA_FULLTEXT_TEXT'}),
          'description':'Synthetic fulltext fixture, not a scientific citation',
          'work_id':'W_fixture'})
        raw=hold(new=True)
        p=raw['prior_art_assessments'][0]['intervention_reviews'][0]
        p['status']='REVIEWED';p['contribution_class']='POTENTIALLY_DISTINCT'
        p['compared_sources']=[{'source_id':sid,'evidence_level':'FULL_TEXT',
          'what_prior_work_tested':'The synthetic text tests an earlier endpoint',
          'remaining_delta':'The intervention asks a different conditional contrast'}]
        self.saved_controller()
        plan=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        review=next(v for k,v in plan if k=='PROGRAM_REVIEWED')
        item=review['m295_model_authored_decision_audit']['intervention_registration_status']
        self.assertEqual(item['P_M295_TOY']['T_EXPERIMENT'],
                         'CANDIDATE_PRIOR_ART_COMPARED_UNCERTIFIED')
        self.assertEqual(item['P_M295_TOY']['T_CALC'],
                         'PROVISIONAL_NOVELTY_UNVERIFIED')

    def test_hold_audits_pending_calcs_even_if_unlinked(self):
        self.j.append('PROBLEM_CREATED',prob())
        raw=hold()
        # No research_frontier_assessment link, but the existing open Problem
        # still has an unattempted calculation and must be assessed.
        raw['prior_art_assessments']=[prior_not_reviewed()]
        with self.assertRaisesRegex(EvidenceError,'M295_PENDING_CALC_COVERAGE_MISMATCH'):
            controller_plan(self.j,{**raw,'remaining_calculation_assessments':[]},
                            'CTRL_D00001','D00001')
        self.saved_controller()
        plan=controller_plan(self.j,{**raw,'remaining_calculation_assessments':[calc()]},
                             'CTRL_D00001','D00001')
        self.assertTrue(plan)

    def test_hold_calculation_omission_rejected_but_defer_allowed(self):
        self.j.append('PROBLEM_CREATED',prob())
        raw=hold(linked=True)
        del raw['remaining_calculation_assessments']
        with self.assertRaisesRegex(EvidenceError,'M295_HOLD_CALC_ASSESSMENT_REQUIRED'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.saved_controller()
        plan=controller_plan(self.j,hold(linked=True),'CTRL_D00001','D00001')
        review=next(p for k,p in plan if k=='PROGRAM_REVIEWED')
        self.assertEqual(len(review['m295_model_authored_decision_audit']
                             ['remaining_calculation_assessments']),1)

    def test_organization_choice_is_required_on_hold(self):
        raw=hold(new=True);del raw['organization_choice_assessment']
        with self.assertRaisesRegex(EvidenceError,'M295_ORG_CHOICE_REQUIRED'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_organization_choice_must_match_real_request(self):
        raw=hold(new=True)
        raw['organization_choice_assessment']=org('SPAWN_NEW_ROOT')
        with self.assertRaisesRegex(EvidenceError,'M295_ORG_CHOICE_REQUEST_CONTRADICTION'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')

    def test_m295_does_not_block_voluntary_independent_root(self):
        from e2core.meta_autonomy import materialize_requests, verify_receipts
        raw={
          'rationale':'Independent falsification could find an alternative null',
          'new_problems':[],'reviews':[],'actions':[],
          'portfolio_decisions':[],
          'organization_requests':[{
              'id':'ORG_m295_peer_001','mode':'ORIGINAL_P0_BLIND_INDEPENDENT',
              'purpose':'Independent, blinded challenge to the original P0',
              'evidence_asset_ids':[],'target_asset_ids':[]}],
          'disposition':'ONGOING',
          'unresolved_opportunities':[],
          'objective_assessment':{
              'objective_status':'UNRESOLVED','research_status':'CONTINUING',
              'resolved_scope':'none','objective_coverage':'NO_OBJECTIVE_RESULT',
              'supporting_asset_ids':[],
              'remaining_questions':['Could independent review contradict theory?'],
              'untried_approaches_considered':[],
              'reason':'Scientific independence is valuable for this scenario'},
          'organization_choice_assessment':{
              'choice':'SPAWN_NEW_ROOT',
              'independence_value':'Blind analysis can generate an independent explanation',
              'overlap_or_cost':'Resource use requires an operator budget',
              'rationale':'Original-P0-blind evaluation has different informational value'},
        }
        self.saved_controller()
        planned=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertEqual(sum(k=='ORGANIZATION_REQUESTED' for k,p in planned),1)
        self.j.append('CONTROLLER_DECISION',{
            'id':'D00001','call_id':'CTRL_D00001',
            'parsed_blob':self.j.blob(raw),'rationale':raw['rationale']})
        for kind,p in planned:self.j.append(kind,p)
        created=materialize_requests(self.exp,self.exp/'ROOTS'/'PRIMARY',4)
        self.assertEqual(len(created),1)
        self.assertEqual(verify_receipts(self.exp,self.exp/'ROOTS'/'PRIMARY'),1)
        self.assertTrue(active(EvolutionJournal(Path(created[0]['root']))))

    def test_rejected_model_response_does_not_append_journal_events(self):
        # Validation occurs before any proposed scientific events commit.
        head=sha(canon(self.j._events()[-1]))
        raw=hold(new=True);del raw['prior_art_assessments']
        with self.assertRaises(EvidenceError):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertEqual(head,sha(canon(self.j._events()[-1])))


if __name__=='__main__':unittest.main()
