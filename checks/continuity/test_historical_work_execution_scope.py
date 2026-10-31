"""Free regression: prior-generation Work is historical, not executable in a new Journal.

All science and decisions are synthetic. No model, literature or tool calls.
"""
from __future__ import annotations
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'runtime'))
sys.path.insert(0, str(REPO / 'AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029'))

from e2core.core import EvolutionJournal, EvidenceError
from e2core.engine import controller_plan, E3R1_CONTROLLER_ADDENDUM
import persistent_population as pp


class TestHistoricalWorkExecutionScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.j = EvolutionJournal(Path(self.tmp.name) / 'new-cycle' / 'SYN_01')
        self.j.init('Synthetic P0 for work-scope regression only')
        self.j.append('R5_POLICY_ACTIVATED', {'policy': 'OBJECTIVE_AND_DISPOSITION_V1'})
        self.j.append('E3R1_POLICY_ACTIVATED', {'policy': 'PORTFOLIO_DECISIONS_V1'})
        self.j.add_source('SRC_PREVIOUS_POPULATION_STATUS','HISTORICAL_AI',{
            'source_root':'/fictional/old-cycle/POPULATION',
            'source_head':{'events':10,'head_sha256':'f'*64},
            'work_statuses':{
                'W_OLD_ACTIVE': {'status':'ACTIVE','operation':'DEVELOP','mode':'INFORMED',
                                 'question':'Old high-value scientific frontier','published':[],
                                 'unfinished_at_checkpoint':True},
                'W_OLD_QUEUED': {'status':'QUEUED','operation':'FRESH','mode':'FRESH',
                                 'question':'Old high-value literature frontier','published':[],
                                 'unfinished_at_checkpoint':True},
            },
            'previous_review':None,
            'recent_controller_decisions':[],
        },'Historical work status only, not new execution')

    def draft(self):
        return {
            'rationale':'Synthetic decision; no empirical result',
            'new_problems':[], 'reviews':[],
            'actions':[], 'portfolio_decisions':[],
            'disposition':'ONGOING', 'unresolved_opportunities':[],
            'objective_assessment':{
                'objective_status':'UNRESOLVED','research_status':'CONTINUING',
                'resolved_scope':'No solved scope','objective_coverage':'NO_OBJECTIVE_RESULT',
                'supporting_asset_ids':[], 'remaining_questions':['Need actual synthetic test'],
                'untried_approaches_considered':['Avoid duplicate synthetic work'],
                'reason':'Synthetic test of contractual Work scope',
            },
        }

    def test_old_status_is_visible_but_never_currently_executable(self):
        original_context=lambda j,*a,**kw: {'portfolio_context': {'open_work_items': []}}
        mods=SimpleNamespace(v3=SimpleNamespace(_external_context=original_context))
        before=len(self.j._events())
        with pp.previous_population_bridge(mods):
            ctx=mods.v3._external_context(self.j)
        self.assertIs(mods.v3._external_context, original_context)
        old=ctx['previous_generation_scientific_portfolio']
        execution=ctx['current_journal_work_execution_scope']
        self.assertEqual(old['work_statuses']['W_OLD_ACTIVE']['status'],'ACTIVE')
        self.assertTrue(old['historical_active_does_not_mean_current_active'])
        self.assertEqual(execution['current_root_work_ids'],[])
        self.assertEqual(execution['eligible_portfolio_decisions_work_ids'],[])
        self.assertEqual(execution['currently_runnable_work_ids'],[])
        self.assertEqual(set(execution['historical_work_ids_not_executable_here']),
                         {'W_OLD_ACTIVE','W_OLD_QUEUED'})
        self.assertEqual(len(self.j._events()), before)
        self.assertEqual(self.j.verify().work,{})
        self.assertIn('historical',E3R1_CONTROLLER_ADDENDUM.lower())
        self.assertIn('NEW explicit actions',E3R1_CONTROLLER_ADDENDUM)

    def test_model_cannot_keep_historical_work_by_id(self):
        plan=self.draft()
        plan['portfolio_decisions']=[{
            'work_ids':['W_OLD_ACTIVE'], 'action':'KEEP',
            'assessment':'VALUABLE', 'rationale':'Scientific value in old frontier',
            'evidence_asset_ids':[],
        }]
        before=len(self.j._events())
        with self.assertRaisesRegex(EvidenceError,'E3R1_NONLOCAL_WORK_NOT_EXECUTABLE:W_OLD_ACTIVE'):
            controller_plan(self.j,plan,'CTRL_D1','D1')
        self.assertEqual(len(self.j._events()),before)
        self.assertEqual(self.j.verify().work,{})

    def test_ongoing_without_new_work_remains_invalid(self):
        before=len(self.j._events())
        with self.assertRaisesRegex(EvidenceError,'E3R1_ONGOING_NO_RUNNABLE_OR_NEW_WORK'):
            controller_plan(self.j,self.draft(),'CTRL_D1','D1')
        self.assertEqual(len(self.j._events()),before)

    def test_explicit_new_work_is_authorized_without_rewriting_history(self):
        plan=self.draft()
        plan['rationale']='The historical frontier is worth an independent fresh study, not silent activation.'
        plan['actions']=[{
            'id':'EV_NEW_REVIEW_01','operation':'FRESH','asset_ids':[],
            'reason':'Independent source-based reinspection chosen by the model',
            'work':{
                'id':'W_NEW_REVIEW_01','mode':'FRESH','problem_id':'P0',
                'question':'Test whether synthetic precedent exists, without inherited AI conclusions',
                'research_rationale':'Independent review of a remaining scientific question',
                'source_ids':[],
            },
        }]
        before=len(self.j._events())
        events=controller_plan(self.j,plan,'CTRL_D1','D1')
        self.assertTrue(any(k=='EVOLUTION_APPLIED' and
                            p['work']['id']=='W_NEW_REVIEW_01' for k,p in events))
        self.assertFalse(any(k=='WORK_PORTFOLIO_ASSESSED' for k,p in events))
        self.assertEqual(len(self.j._events()),before)
        for kind,payload in events:
            self.j.append(kind,payload)
        s=self.j.verify()
        self.assertEqual(s.work['W_NEW_REVIEW_01']['status'],'QUEUED')
        self.assertNotIn('W_OLD_ACTIVE',s.work)
        self.assertNotIn('W_OLD_QUEUED',s.work)
        self.assertEqual(s.sources['SRC_PREVIOUS_POPULATION_STATUS']['kind'],'HISTORICAL_AI')

    def test_existing_current_work_can_still_be_kept(self):
        self.j.evolve('EV_PRE_EXISTING','FRESH',[],{
            'id':'W_CURRENT','mode':'FRESH','problem_id':'P0',
            'question':'A newly authorized synthetic study',
            'research_rationale':'Synthetic study under new Journal',
            'source_ids':[],
        },'Synthetic initial assignment')
        plan=self.draft()
        plan['portfolio_decisions']=[{
            'work_ids':['W_CURRENT'], 'action':'KEEP',
            'assessment':'VALUABLE','rationale':'Keep current authorized work',
            'evidence_asset_ids':[],
        }]
        events=controller_plan(self.j,plan,'CTRL_D2','D2')
        self.assertTrue(any(k=='WORK_PORTFOLIO_ASSESSED' and p['id']=='W_CURRENT'
                            for k,p in events))


if __name__=='__main__':
    unittest.main()
