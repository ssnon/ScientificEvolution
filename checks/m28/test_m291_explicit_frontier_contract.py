"""M29.1: scientific HOLD requires an explicit frontier judgement, never new science."""
import json
import unittest
from e2core.core import EvolutionJournal, EvidenceError, canon, sha
from e2core.engine import controller_plan
from e2core.m28_successor import build_successor
from e2core.m291_frontier_contract import active, MARKER, CONTROLLER_PRELUDE
import test_m28_terminal_projection_chain as previous
import test_m29_frontier_handoff as m29_previous


class TestM291ExplicitFrontierContract(unittest.TestCase):
    def setUp(self):
        self.h=previous.TestTerminalProjectionChain(
            'test_zero_child_hold_projection_preserves_model_authorship')
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self._old,self.parent,self.pj=self.h._first_successor_with_new_rejections()
        self.exp=self.h.base/'M28_DAC_NO3RR_20261111_06'
        build_successor(self.parent,self.exp,m291_explicit_frontier_contract=True)
        self.j=EvolutionJournal(self.exp/'ROOTS'/'PRIMARY')
        self.h.saved(self.j,'CTRL_D00004')

    def proposal(self):
        return {
            'rationale':'P0 remains unresolved; previous experiments are not a matched causal contrast.',
            'new_problems':[],'reviews':[],'actions':[],'portfolio_decisions':[],
            'organization_requests':[],'collaboration_requests':[],
            'disposition':'HOLD_WITH_RATIONALE',
            'unresolved_opportunities':['Matched adjacency contrast is not yet available'],
            'objective_assessment':{
                'objective_status':'UNRESOLVED','research_status':'PAUSED_LOW_INFORMATION',
                'resolved_scope':'Conditional identifiability only',
                'objective_coverage':'SUBPROBLEM_ONLY','supporting_asset_ids':[],
                'remaining_questions':['Does adjacency cause a corrected rate residual?'],
                'untried_approaches_considered':['Conditional targeted experiment remains'],
                'reason':'Evidence insufficient for a causal claim',
            },
            'program_portfolio_review':None,
        }

    def test_source_pinned_activation_recorded_and_recoverable(self):
        self.assertTrue(active(self.j))
        self.assertTrue(any(p['reason']==MARKER for p in self.j.verify().operational_pauses))
        self.assertIn('CANNOT_YET_SPECIFY',CONTROLLER_PRELUDE)
        self.assertEqual(len(self.j.verify().controller_decisions),1)

    def test_missing_assessment_rejected_without_partial_science_commit(self):
        obj=self.proposal()
        before=sha(canon(self.j._events()[-1]))
        with self.assertRaisesRegex(EvidenceError,'M291_HOLD_FRONTIER_ASSESSMENT_REQUIRED'):
            controller_plan(self.j,obj,'CTRL_D00004','D00004')
        self.assertEqual(before,sha(canon(self.j._events()[-1])))
        self.assertEqual(self.j.verify().program_reviews[-1]['scientific_status'],'ONGOING')

    def test_explicit_no_new_value_is_valid_no_forced_problem(self):
        obj=self.proposal()
        obj['research_frontier_assessment']={
            'status':'NO_ADDITIONAL_VALUE','problem_ids':[],
            'rationale':'Existing conditional and countermodel assets already specify the relevant contrasts; without a new independent parameter restriction, another formal Problem would duplicate that work.'}
        planned=controller_plan(self.j,obj,'CTRL_D00004','D00004')
        self.assertFalse(any(k=='PROBLEM_CREATED' for k,_ in planned))
        review=next(p for k,p in planned if k=='PROGRAM_REVIEWED')
        self.assertEqual(review['m29_research_frontier_assessment']['status'],
                         'NO_ADDITIONAL_VALUE')

    def test_new_conditional_subhypothesis_survives_hold_without_worker(self):
        obj=self.proposal()
        p=m29_previous.TestM29FrontierHandoff.new_problem(None)
        obj['new_problems']=[p]
        obj['research_frontier_assessment']={
            'status':'REGISTERED_NEW','problem_ids':[p['id']],
            'rationale':'The controlled adjacency variation would distinguish specified conditional models.'}
        planned=controller_plan(self.j,obj,'CTRL_D00004','D00004')
        self.assertTrue(any(k=='PROBLEM_CREATED' for k,_ in planned))
        self.assertFalse(any(k=='WORK_CREATED' for k,_ in planned))
        blob=self.j.blob(canon(obj))
        self.j.append('CONTROLLER_DECISION',{
            'id':'D00004','call_id':'CTRL_D00004',
            'parsed_blob':blob,'rationale':obj['rationale']})
        for kind,payload in planned:self.j.append(kind,payload)
        s=self.j.verify()
        self.assertEqual(s.program_reviews[-1]['scientific_status'],'HOLD_WITH_RATIONALE')
        self.assertIn(p['id'],s.problems)
        self.assertEqual(s.problems[p['id']]['research_frontier']['scientific_status'],
                         'PROPOSED_NOT_EXECUTED')
        self.assertEqual(len(s.work),0)

    def test_invalid_assessment_ids_are_not_auto_repaired(self):
        obj=self.proposal()
        obj['research_frontier_assessment']={
            'status':'REGISTERED_NEW','problem_ids':['P_NOT_REAL'],
            'rationale':'An experiment should distinguish the alternatives'}
        with self.assertRaisesRegex(EvidenceError,'M29_FRONTIER_UNKNOWN_PROBLEM'):
            controller_plan(self.j,obj,'CTRL_D00004','D00004')

if __name__=='__main__':unittest.main()
