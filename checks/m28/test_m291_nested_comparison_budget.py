"""M29.1: unchanged _03 science + BOTH _04/_05 sibling bills, never duplicate calls."""
import json
import unittest
from e2core.core import EvolutionJournal, canon, sha
from e2core.m28_successor import build_successor, verify_successor_prefix
from e2core.m232_budget import _connection
from e2core.m291_frontier_contract import active
import test_m28_terminal_projection_chain as previous


class TestM291SiblingBudget(unittest.TestCase):
    def setUp(self):
        self.h=previous.TestTerminalProjectionChain(
            'test_zero_child_hold_projection_preserves_model_authorship')
        self.h.setUp();self.addCleanup(self.h.doCleanups)
        _,self.parent,_=self.h._first_successor_with_new_rejections()

    def terminal(self,exp,decision_num,cost):
        j=EvolutionJournal(exp/'ROOTS'/'PRIMARY')
        cid=f'CTRL_D{decision_num:05d}';did=f'D{decision_num:05d}'
        self.h.saved(j,cid,usage=cost)
        rationale='P0 remains unresolved and requires independent causal contrast.'
        obj={'rationale':rationale,'actions':[],'disposition':'HOLD_WITH_RATIONALE'}
        blob=j.blob(canon(obj))
        j.append('CONTROLLER_DECISION',{'id':did,'call_id':cid,'parsed_blob':blob,
                                        'rationale':rationale})
        j.append('PROGRAM_REVIEWED',{'reviewer_id':did,
            'scientific_status':'HOLD_WITH_RATIONALE','rationale':rationale,
            'considered_asset_ids':[],'unresolved_opportunities':['New matched experiment']})
        j.append('PROGRAM_OBJECTIVE_ASSESSED',{'reviewer_id':did,
            'objective_status':'UNRESOLVED','research_status':'PAUSED_LOW_INFORMATION',
            'resolved_scope':'conditional','objective_coverage':'SUBPROBLEM_ONLY',
            'supporting_asset_ids':[],'remaining_questions':['Adjacency'],
            'untried_approaches_considered':[],'reason':'No causal matched control'})
        j.append('PROGRAM_PORTFOLIO_REVIEWED',{'decision_id':did,'call_id':cid,
            'disposition':'PAUSE_WITH_RATIONALE','rationale':rationale,
            'considered_organization_request_ids':[],'considered_report_ids':[],
            'unresolved_frontiers':['Causal adjacency test'],
            'science_certification':False,'program_level_model_judgment_only':True})
        c=_connection(exp)
        try:
            c.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                ('key-'+cid,str(j.root),cid,'c'*64,'openai/gpt-5.6-luna',
                 'SAVED',0.4,cost,1.0))
        finally:c.close()

    def test_nested_sibling_costs_and_new_contract_are_pinned(self):
        original_head=sha(canon(EvolutionJournal(self.parent/'ROOTS'/'PRIMARY')._events()[-1]))
        base04=self.h.base/'M28_DAC_NO3RR_20261111_04'
        build_successor(self.parent,base04)
        self.terminal(base04,4,0.03)
        base05=self.h.base/'M28_DAC_NO3RR_20261111_05'
        build_successor(self.parent,base05,comparison_baseline=base04)
        self.terminal(base05,4,0.04)
        exp=self.h.base/'M28_DAC_NO3RR_20261111_06'
        preview=build_successor(self.parent,exp,dry_run=True,
                                comparison_baseline=base05,
                                m291_explicit_frontier_contract=True)
        self.assertFalse(exp.exists())
        self.assertAlmostEqual(preview['successor_budget_limit_usd'],9.81)
        build_successor(self.parent,exp,comparison_baseline=base05,
                        m291_explicit_frontier_contract=True)
        self.assertAlmostEqual(verify_successor_prefix(exp)['successor_budget_limit_usd'],9.81)
        self.assertTrue(active(EvolutionJournal(exp/'ROOTS'/'PRIMARY')))
        record=json.loads((exp/'M28_NATIVE_RESEARCH_SUCCESSOR.json').read_bytes())
        self.assertAlmostEqual(record['comparison_baseline']['direct_actual_usd'],0.04)
        self.assertAlmostEqual(record['comparison_baseline']['nested_comparator_actual_usd'],0.03)
        self.assertAlmostEqual(record['comparison_baseline']['actual_usd'],0.07)
        self.assertEqual(len(EvolutionJournal(exp/'ROOTS'/'PRIMARY').verify().model_calls),3)
        self.assertEqual(sha(canon(EvolutionJournal(self.parent/'ROOTS'/'PRIMARY')._events()[-1])),original_head)

if __name__=='__main__':unittest.main()
