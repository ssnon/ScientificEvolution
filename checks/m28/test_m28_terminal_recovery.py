"""M28 no-paid regression: termination contract, audited successor, lineage, cost.

All fixtures are locally constructed and do not contact any paid provider.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from e2core.core import EvolutionJournal, EvidenceError, canon, sha
from e2core.engine import controller_plan
from e2core.m28_successor import build_successor, verify_successor_prefix
from e2core.meta_scheduler import controller_recovery_pending, root_ready
from e2core.m232_budget import _connection
from e2core.meta_collaboration import CONTROLLER_ADDENDUM


FEATURES={
    'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND',
    'M232_NAMESPACE_MODE':'COMPACT',
    'M233_MODEL_METADATA_MODE':'SEPARATE',
    'M232_CACHE_POLICY':'SELECTIVE_NO_WRITE',
    'M232_SYN_PMI_MODE':'FULL',
    'M232_BUDGET_REQUIRED':'YES',
}


class TestM28TerminalRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.env=patch.dict(os.environ,FEATURES,clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)

    def _journal(self,root):
        j=EvolutionJournal(root)
        j.init('Can adjacent dual centers causally outperform independent sites?',origin='NEW_META_RESEARCH_AUTONOMY_RESEARCH')
        j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        from e2core.meta_autonomy import POLICY
        from e2core.meta_collaboration import POLICY as COLLAB_POLICY
        j.append('META_RESEARCH_AUTONOMY_ACTIVATED',{'policy':POLICY})
        j.append('META_RESEARCH_COLLABORATION_ACTIVATED',{'policy':COLLAB_POLICY})
        return j

    def _saved(self,j,cid):
        request=j.blob(canon({'id':cid,'model':'openai/gpt-5.6-luna'}))
        result=j.blob(canon({'choices':[{'message':{'content':'{}'}}]}))
        j.append('MODEL_CALL_INTENT',{'id':cid,'actor':'CONTROLLER','work_id':None,
                                    'request_blob':request,'model':'openai/gpt-5.6-luna',
                                    'billing_mode':'EXTERNAL'})
        j.append('MODEL_CALL_SAVED',{'id':cid,'response_blob':result,'usage':{'cost':0.05}})

    def _old_experiment(self):
        repo=Path(__file__).resolve().parents[2]
        exp=self.base/'M28_DAC_NO3RR_20261111_02'
        exp.mkdir()
        (exp/'ROOTS').mkdir()
        root=exp/'ROOTS'/'PRIMARY'
        j=self._journal(root)
        self._saved(j,'CTRL_D00001')
        parsed=j.blob(canon({'rationale':'Still open','actions':[]}))
        j.append('CONTROLLER_DECISION',{'id':'D00001','call_id':'CTRL_D00001','parsed_blob':parsed,
                                        'rationale':'First scientific judgment'})
        j.append('PROGRAM_REVIEWED',{'reviewer_id':'D00001','scientific_status':'ONGOING',
                                     'rationale':'Need more evidence','considered_asset_ids':[],
                                     'unresolved_opportunities':['Decisive causal control']})
        j.append('PROGRAM_OBJECTIVE_ASSESSED',{'reviewer_id':'D00001',
               'objective_status':'UNRESOLVED','research_status':'CONTINUING',
               'resolved_scope':'none','objective_coverage':'NO_OBJECTIVE_RESULT',
               'supporting_asset_ids':[], 'remaining_questions':['Causal contrast'],
               'untried_approaches_considered':[],'reason':'Still open'})
        self._saved(j,'CTRL_D00002')
        j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_PLAN_REJECTED:META_A2_PRIMARY_TERMINAL_REQUIRES_PROGRAM_REVIEW',
                                       'call_id':'CTRL_D00002'})
        profile={'protocol':'M25_NATIVE_ACTIVATION_PROFILE_V1',
                 'model':'openai/gpt-5.6-luna','purpose':'Test continuity','features':FEATURES}
        from e2core.activation_contract import digest
        budget={'protocol':'M232_DEVELOPMENT_BUDGET_V1','limit_usd':10.0,
                'model_rates_per_million_usd':{'openai/gpt-5.6-luna':{'input':0.4,'output':1.8}},
                'reserve_multiplier':1.5}
        budget_blob=canon(budget)
        (exp/'M232_DEV_BUDGET.json').write_bytes(budget_blob)
        persistent={'protocol':'SCIENTIFIC_META_RESEARCH_AUTONOMY_A1',
                    'science_certification':False,'meta_autonomy_enabled':True,
                    'activation_profile':profile,'activation_profile_sha256':digest(profile),
                    'budget_config_sha256':sha(budget_blob)}
        (exp/'persistent.json').write_bytes(canon(persistent))
        meta={'protocol':'SCIENTIFIC_META_RESEARCH_AUTONOMY_A1','root':str(exp),
              'original_P0_sha256':sha(j.verify().program['problem'].encode()),
              'initial_root':str(root),'science_certification':False,
              'researcher_count_not_preselected':True,'mandatory_generations':False,
              'mandatory_synthesis':False,
              'activation_profile_sha256':digest(profile),'budget_config_sha256':sha(budget_blob)}
        (exp/'meta_research.json').write_bytes(canon(meta))
        rel='runtime/e2core/core.py'
        raw=subprocess.check_output(['git','show','9487b96:'+rel],cwd=repo)
        import hashlib
        oldpin={'protocol':'M16_NATIVE_EXECUTION_SOURCE_V1',
                'repository':str(repo), 'files':{rel:hashlib.sha256(raw).hexdigest()},
                'source_verification':'EXACT_PYTHON_BYTES_SHA256',
                'not_historical_v3_replay':True,'not_scientific_certification':True}
        (exp/'NATIVE_RUNTIME_SOURCE_PIN.json').write_bytes(canon(oldpin))
        conn=_connection(exp)
        try:
            for cid in ('CTRL_D00001','CTRL_D00002'):
                conn.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                             ('key-'+cid,str(root),cid,'a'*64,'openai/gpt-5.6-luna',
                              'SAVED',0.4,0.05,1.0))
        finally:
            conn.close()
        return exp,j

    def test_model_prompt_explains_mandatory_terminal_review(self):
        self.assertIn('REQUIRED whenever top-level disposition',CONTROLLER_ADDENDUM)
        self.assertIn('BOTH considered_organization_request_ids and considered_report_ids MUST be []',
                      CONTROLLER_ADDENDUM)
        self.assertIn('SUBPROBLEM_ONLY',CONTROLLER_ADDENDUM)

    def test_scoped_candidate_does_not_need_false_p0_completion(self):
        j=self._journal(self.base/'PRIMARY')
        obj={'rationale':'Conditional testable framework', 'new_problems':[], 'reviews':[],
             'actions':[], 'portfolio_decisions':[], 'disposition':'REVIEW_WORTHY_CANDIDATE',
             'unresolved_opportunities':[],
             'objective_assessment':{'objective_status':'REVIEW_WORTHY_CANDIDATE',
              'research_status':'PAUSED_EVIDENCE','objective_coverage':'SUBPROBLEM_ONLY',
              'resolved_scope':'conditional test','supporting_asset_ids':['A_missing'],
              'remaining_questions':[], 'untried_approaches_considered':[],
              'reason':'Needs an experiment'},
             'program_portfolio_review':{'disposition':'REVIEW_WORTHY_CANDIDATE',
              'rationale':'No actual causal demonstration','considered_organization_request_ids':[],
              'considered_report_ids':[],'unresolved_frontiers':['causal test']}}
        with self.assertRaises(EvidenceError) as ex:
            controller_plan(j,obj,'CTRL_D00001','D00001')
        self.assertNotIn('R5_CANDIDATE_DISPOSITION_MISMATCH',str(ex.exception))
        self.assertIn('INVALID_OBJECTIVE_COVERAGE_OR_SUPPORT',str(ex.exception))

    def test_legacy_r5_candidate_semantics_unchanged(self):
        root=self.base/'PRIMARY'
        j=EvolutionJournal(root)
        j.init('Test')
        j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        obj={'rationale':'Claim','actions':[], 'new_problems':[], 'reviews':[],
             'disposition':'REVIEW_WORTHY_CANDIDATE',
             'objective_assessment':{'objective_status':'REVIEW_WORTHY_CANDIDATE',
               'research_status':'PAUSED_EVIDENCE','objective_coverage':'SUBPROBLEM_ONLY',
               'supporting_asset_ids':['A_missing']}}
        with self.assertRaises(EvidenceError) as ex:
            controller_plan(j,obj,'CTRL_D00001','D00001')
        self.assertIn('R5_CANDIDATE_DISPOSITION_MISMATCH',str(ex.exception))

    def test_audited_successor_preserves_events_and_reopens_recovery(self):
        old,j=self._old_experiment()
        parent_head=sha(canon(j._events()[-1]))
        new=self.base/'M28_DAC_NO3RR_20261111_03'
        build_successor(old,new)
        self.assertTrue(controller_recovery_pending(EvolutionJournal(new/'ROOTS'/'PRIMARY')))
        self.assertTrue(root_ready(new/'ROOTS'/'PRIMARY'))
        data=verify_successor_prefix(new)
        self.assertEqual(data['parent_head_sha256'],parent_head)
        self.assertEqual(data['parent_calls_saved'],2)
        self.assertAlmostEqual(data['successor_budget_limit_usd'],9.90)
        self.assertEqual(sha(canon(j._events()[-1])),parent_head)
        self.assertFalse((old/'M28_NATIVE_RESEARCH_SUCCESSOR.json').exists())
        newj=EvolutionJournal(new/'ROOTS'/'PRIMARY')
        newj.append('OPERATIONAL_PAUSE',{'reason':'EXTERNAL_RUNTIME_BOUNDARY_NOT_SCIENTIFIC_HOLD'})
        self.assertTrue(controller_recovery_pending(newj))
        self.assertEqual(verify_successor_prefix(new)['parent_head_sha256'],parent_head)

    def test_resume_rejects_unresolved_provider_call_without_mutation(self):
        old,j=self._old_experiment()
        req=j.blob(canon({'x':1}))
        j.append('MODEL_CALL_INTENT',{'id':'CTRL_D00003','actor':'CONTROLLER','work_id':None,
                                      'request_blob':req,'model':'openai/gpt-5.6-luna',
                                      'billing_mode':'EXTERNAL'})
        new=self.base/'M28_DAC_NO3RR_20261111_03'
        with self.assertRaises(EvidenceError):build_successor(old,new)
        self.assertFalse(new.exists())

if __name__=='__main__':unittest.main()
