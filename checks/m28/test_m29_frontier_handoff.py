"""M29 no-paid contract tests: persistent scientific frontier without forced Work."""
import json
import tempfile
import unittest
from pathlib import Path

from e2core.core import EvolutionJournal, EvidenceError, canon
from e2core.engine import controller_plan
from e2core.m29_frontier import (CONTROLLER_ADDENDUM,
    validate_model_frontier_assessment)


class TestM29FrontierHandoff(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.j=EvolutionJournal(Path(self.tmp.name)/'ROOTS'/'PRIMARY')
        self.j.init('Can adjacent dual-atom centers cooperate in nitrate reduction?',
                    origin='NEW_META_RESEARCH_AUTONOMY_RESEARCH')
        self.j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        self.j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        from e2core.meta_autonomy import POLICY
        from e2core.meta_collaboration import POLICY as CPOLICY
        self.j.append('META_RESEARCH_AUTONOMY_ACTIVATED',{'policy':POLICY})
        self.j.append('META_RESEARCH_COLLABORATION_ACTIVATED',{'policy':CPOLICY})
        ident='CTRL_D00001'
        req=self.j.blob(canon({'unit':'m29'}))
        resp=self.j.blob(canon({'choices':[{'message':{'content':'{}'}}]}))
        self.j.append('MODEL_CALL_INTENT',{'id':ident,'actor':'CONTROLLER',
            'work_id':None,'request_blob':req,'model':'mock',
            'billing_mode':'LOCAL'})
        self.j.append('MODEL_CALL_SAVED',{'id':ident,'response_blob':resp,'usage':{}})

    def raw(self):
        return {
            'rationale':'The current evidence does not identify a causal adjacent-center effect.',
            'new_problems':[],'reviews':[],'actions':[],'portfolio_decisions':[],
            'disposition':'HOLD_WITH_RATIONALE',
            'unresolved_opportunities':['New discriminating intervention may be required'],
            'objective_assessment':{
                'objective_status':'UNRESOLVED','research_status':'PAUSED_LOW_INFORMATION',
                'resolved_scope':'Conditional identifiability only',
                'objective_coverage':'SUBPROBLEM_ONLY','supporting_asset_ids':[],
                'remaining_questions':['Would adjacent and separated catalysts diverge?'],
                'untried_approaches_considered':[],
                'reason':'No matched measured contrast; no executable experiment now',
            },
            'program_portfolio_review':None,
            'organization_requests':[],
            'collaboration_requests':[],
        }

    def new_problem(self):
        return {
            'id':'P_DAC_ADJACENCY_FUTURE_01','parents':['P0'],
            'question':'With the same operando metal populations, does adjacency change corrected ammonia production?',
            'scope':'Conditional matched pair-fraction or spacing intervention; not an executed experiment',
            'decomposition_rationale':'Existing kinetics do not identify an adjacency-specific contribution',
            'contribution_to_parent':'Tests a mechanism-relevant causal contrast left unresolved in P0',
            'research_frontier':{
                'scientific_status':'PROPOSED_NOT_EXECUTED',
                'competing_hypotheses':[
                    'Direct or effective adjacency-dependent contribution',
                    'Independent-site or shared-intermediate contribution only'],
                'discriminating_intervention_or_observation':
                    'Change verified operating pair fraction while matching accessible active sites and local conditions',
                'predicted_outcomes':[
                    {'if':'Adjacency contributes after nuisance correction',
                     'then':'A corrected residual varies with operating pair fraction',
                     'limitation':'A residual alone does not identify a microscopic elementary step'},
                    {'if':'Only independent sites or sequential pathways matter',
                     'then':'Matched controls explain the measured rate without an adjacency term',
                     'limitation':'A null excludes only the tested regime and sensitivity'}],
                'required_evidence':[{'kind':'EXPERIMENT',
                    'purpose':'Distinguish pair-dependent and noncooperative mechanisms',
                    'acquisition_state':'REQUIRES_EXTERNAL_RESOURCE'}],
                'blocking_resources':['Matched catalyst series',
                    'Operando adjacent-pair and accessible-site measurement capability'],
                'interpretation_limits':'No result can be claimed before intervention; direct cooperation needs further mechanistic discrimination',
                'motivating_asset_ids':[],
            },
        }

    def commit(self,obj):
        planned=controller_plan(self.j,obj,'CTRL_D00001','D00001')
        blob=self.j.blob(canon(obj))
        self.j.append('CONTROLLER_DECISION',{'id':'D00001','call_id':'CTRL_D00001',
            'parsed_blob':blob,'rationale':obj['rationale']})
        for kind,payload in planned:
            self.j.append(kind,payload)
        return self.j.verify()

    def test_hold_registers_real_p0_child_problem_without_worker(self):
        obj=self.raw()
        obj['new_problems']=[self.new_problem()]
        obj['research_frontier_assessment']={
            'status':'REGISTERED_NEW','problem_ids':['P_DAC_ADJACENCY_FUTURE_01'],
            'rationale':'A new conditional intervention can discriminate the existing alternatives.'}
        s=self.commit(obj)
        self.assertEqual(s.program_reviews[-1]['scientific_status'],'HOLD_WITH_RATIONALE')
        self.assertEqual(s.program_portfolio_reviews[-1]['disposition'],'PAUSE_WITH_RATIONALE')
        self.assertEqual(len(s.work),0)
        self.assertIn('P_DAC_ADJACENCY_FUTURE_01',s.problems)
        self.assertEqual(s.problems['P_DAC_ADJACENCY_FUTURE_01']['research_frontier']
            ['scientific_status'],'PROPOSED_NOT_EXECUTED')
        self.assertEqual(s.program_reviews[-1]['m29_research_frontier_assessment']
            ['status'],'REGISTERED_NEW')
        saved=json.loads(self.j.raw(s.controller_decisions[-1]['parsed_blob']))
        self.assertEqual(saved['new_problems'],obj['new_problems'])

    def test_no_extra_frontier_is_valid_scientific_hold(self):
        obj=self.raw()
        obj['research_frontier_assessment']={
            'status':'NO_ADDITIONAL_VALUE','problem_ids':[],
            'rationale':'Already registered experiments and all untried contrasts have low expected value.'}
        s=self.commit(obj)
        self.assertEqual(len(s.problems),1)
        self.assertEqual(s.program_reviews[-1]['m29_research_frontier_assessment']
            ['status'],'NO_ADDITIONAL_VALUE')

    def test_missing_frontier_is_not_invented_or_forced(self):
        s=self.commit(self.raw())
        self.assertNotIn('m29_research_frontier_assessment',s.program_reviews[-1])
        self.assertEqual(len(s.problems),1)

    def test_bad_outcomes_fail_closed_no_journal_changes(self):
        obj=self.raw();p=self.new_problem()
        p['research_frontier']['predicted_outcomes']=[]
        obj['new_problems']=[p]
        obj['research_frontier_assessment']={
            'status':'REGISTERED_NEW','problem_ids':[p['id']],
            'rationale':'A discriminating experiment is needed.'}
        before=len(self.j._events())
        with self.assertRaisesRegex(EvidenceError,'M29_FRONTIER_CONDITIONAL_OUTCOMES_REQUIRED'):
            controller_plan(self.j,obj,'CTRL_D00001','D00001')
        self.assertEqual(len(self.j._events()),before)

    def test_unknown_asset_rejected(self):
        obj=self.raw();p=self.new_problem()
        p['research_frontier']['motivating_asset_ids']=['A_MADE_UP']
        obj['new_problems']=[p]
        obj['research_frontier_assessment']={
            'status':'REGISTERED_NEW','problem_ids':[p['id']],
            'rationale':'Distinguishing intervention.'}
        with self.assertRaisesRegex(EvidenceError,'M29_FRONTIER_UNKNOWN_ASSET'):
            controller_plan(self.j,obj,'CTRL_D00001','D00001')

    def test_prompt_never_forces_executable_or_scientific_claim(self):
        self.assertIn('actions=[]',CONTROLLER_ADDENDUM)
        self.assertIn('not',CONTROLLER_ADDENDUM.lower())
        self.assertIn('NO_ADDITIONAL_VALUE',CONTROLLER_ADDENDUM)

if __name__=='__main__':unittest.main()
