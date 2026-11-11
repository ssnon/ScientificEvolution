"""M29 same-snapshot baseline cost is independently debited from full $10."""
import json
import unittest
from e2core.core import EvolutionJournal, canon
from e2core.m28_successor import build_successor, verify_successor_prefix
from e2core.m232_budget import _connection
import test_m28_terminal_projection_chain as previous

class TestM29ComparatorBudget(unittest.TestCase):
    def setUp(self):
        self.h=previous.TestTerminalProjectionChain('test_zero_child_hold_projection_preserves_model_authorship')
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def test_same_snapshot_comparator_cost_subtracted_without_science_contamination(self):
        _old,parent,_j=self.h._first_successor_with_new_rejections()
        baseline=self.h.base/'M28_DAC_NO3RR_20261111_04'
        build_successor(parent,baseline)
        bj=EvolutionJournal(baseline/'ROOTS'/'PRIMARY')
        self.h.saved(bj,'CTRL_D00004',usage=0.03)
        obj={'rationale':'P0 still unresolved; pause.', 'actions':[],
             'disposition':'HOLD_WITH_RATIONALE'}
        blob=bj.blob(canon(obj))
        bj.append('CONTROLLER_DECISION',{'id':'D00004','call_id':'CTRL_D00004',
                   'parsed_blob':blob,'rationale':obj['rationale']})
        bj.append('PROGRAM_REVIEWED',{'reviewer_id':'D00004',
                   'scientific_status':'HOLD_WITH_RATIONALE',
                   'rationale':obj['rationale'],'considered_asset_ids':[],
                   'unresolved_opportunities':['Matched intervention needed']})
        bj.append('PROGRAM_OBJECTIVE_ASSESSED',{'reviewer_id':'D00004',
                  'objective_status':'UNRESOLVED','research_status':'PAUSED_LOW_INFORMATION',
                  'resolved_scope':'conditional','objective_coverage':'SUBPROBLEM_ONLY',
                  'supporting_asset_ids':[],'remaining_questions':['Adjacency contrast'],
                  'untried_approaches_considered':[], 'reason':'No causal contrast'})
        bj.append('PROGRAM_PORTFOLIO_REVIEWED',{'decision_id':'D00004',
                  'call_id':'CTRL_D00004','disposition':'PAUSE_WITH_RATIONALE',
                  'rationale':obj['rationale'],
                  'considered_organization_request_ids':[],
                  'considered_report_ids':[],
                  'unresolved_frontiers':['Adjacency contrast'],
                  'science_certification':False,
                  'program_level_model_judgment_only':True})
        c=_connection(baseline)
        try:
            c.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                ('key-CTRL_D00004',str(bj.root),'CTRL_D00004','c'*64,
                 'openai/gpt-5.6-luna','SAVED',0.4,0.03,1.0))
        finally:c.close()
        self.assertEqual(verify_successor_prefix(baseline)['parent_calls_saved'],3)
        exp=self.h.base/'M28_DAC_NO3RR_20261111_05'
        preview=build_successor(parent,exp,dry_run=True,comparison_baseline=baseline)
        self.assertAlmostEqual(preview['successor_budget_limit_usd'],9.85)
        self.assertFalse(exp.exists())
        built=build_successor(parent,exp,comparison_baseline=baseline)
        self.assertAlmostEqual(built['successor_budget_limit_usd'],9.85)
        self.assertEqual(verify_successor_prefix(exp)['parent_calls_saved'],3)
        es=EvolutionJournal(exp/'ROOTS'/'PRIMARY').verify()
        self.assertEqual(len(es.model_calls),3)  # comparator's CTRL_D00004 NEVER copied
        self.assertEqual(es.program_reviews[-1]['scientific_status'],'ONGOING')
        comparison=json.loads((exp/'M28_NATIVE_RESEARCH_SUCCESSOR.json').read_bytes())
        self.assertAlmostEqual(comparison['comparison_baseline']['actual_usd'],0.03)
        self.assertAlmostEqual(comparison['direct_parent_spent_usd'],0.02)
        self.assertAlmostEqual(comparison['cumulative_upstream_accounted_usd'],0.15)

if __name__=='__main__':unittest.main()
