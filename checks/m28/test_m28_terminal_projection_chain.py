"""No-paid M28 regression: zero-child model judgment projection + chained recovery.

These tests use saved synthetic model calls, never a live provider.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from e2core.core import EvolutionJournal, EvidenceError, canon, sha
from e2core.engine import controller_plan
from e2core.m232_budget import _connection
from e2core.meta_scheduler import controller_recovery_pending, root_ready
from e2core.m28_successor import build_successor, verify_successor_prefix

FEATURES = {
    'M232_CONTROLLER_DETAIL_MODE': 'ON_DEMAND',
    'M232_NAMESPACE_MODE': 'COMPACT',
    'M233_MODEL_METADATA_MODE': 'SEPARATE',
    'M232_CACHE_POLICY': 'SELECTIVE_NO_WRITE',
    'M232_SYN_PMI_MODE': 'FULL',
    'M232_BUDGET_REQUIRED': 'YES',
}


class TestTerminalProjectionChain(unittest.TestCase):
    def setUp(self):
        self._tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base=Path(self._tmp.name)
        self._env=patch.dict(os.environ,FEATURES,clear=False)
        self._env.start()
        self.addCleanup(self._env.stop)
        self._prevpaid=os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)
        self.addCleanup(self._restore_paid)

    def _restore_paid(self):
        if self._prevpaid is not None:
            os.environ['FAKG_RESEARCH_ALLOW_PAID']=self._prevpaid
        else:
            os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)

    def journal(self, root):
        j=EvolutionJournal(root)
        j.init('P0: Can adjacent NO3RR dual metal centers outperform independent sites?',
               origin='NEW_META_RESEARCH_AUTONOMY_RESEARCH')
        j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        from e2core.meta_autonomy import POLICY
        from e2core.meta_collaboration import POLICY as COLLAB_POLICY
        j.append('META_RESEARCH_AUTONOMY_ACTIVATED',{'policy':POLICY})
        j.append('META_RESEARCH_COLLABORATION_ACTIVATED',{'policy':COLLAB_POLICY})
        return j

    def saved(self, j, cid, *, usage=0.05):
        request=j.blob(canon({'model':'openai/gpt-5.6-luna','test_call':cid}))
        result=j.blob(canon({'choices':[{'message':{'content':'{}'}}]}))
        j.append('MODEL_CALL_INTENT',{'id':cid,'actor':'CONTROLLER','work_id':None,
                                     'request_blob':request,'model':'openai/gpt-5.6-luna',
                                     'billing_mode':'EXTERNAL'})
        j.append('MODEL_CALL_SAVED',{'id':cid,'response_blob':result,'usage':{'cost':usage}})

    def test_zero_child_hold_projection_preserves_model_authorship(self):
        j=self.journal(self.base/'ROOTS'/'PRIMARY')
        self.saved(j,'CTRL_D00001')
        rationale='P0 remains unresolved; no causally identified adjacent-pair advantage.'
        remaining=['Matched adjacency intervention under operando conditions is missing.']
        obj={
            'rationale':rationale,'new_problems':[],'reviews':[],'actions':[],
            'portfolio_decisions':[],'organization_requests':[],
            'collaboration_requests':[],
            'disposition':'HOLD_WITH_RATIONALE','unresolved_opportunities':[],
            'objective_assessment':{
                'objective_status':'UNRESOLVED','research_status':'PAUSED_EVIDENCE',
                'resolved_scope':'conditional pre-experiment framework',
                'objective_coverage':'SUBPROBLEM_ONLY','supporting_asset_ids':[],
                'remaining_questions':remaining,'untried_approaches_considered':[],
                'reason':'No verified controlled intervention evidence',
            },
            'program_portfolio_review':None,
        }
        before=sha(canon(j._events()[-1]))
        planned=controller_plan(j,obj,'CTRL_D00001','D00001')
        self.assertEqual(before,sha(canon(j._events()[-1])))
        project=[v for k,v in planned if k=='OPERATIONAL_PAUSE' and
                 v.get('reason')=='M28_TERMINAL_PROGRAM_REVIEW_STRUCTURED_FROM_AUTHORED_JUDGMENT']
        self.assertEqual(len(project),1)
        review=[v for k,v in planned if k=='PROGRAM_PORTFOLIO_REVIEWED']
        self.assertEqual(len(review),1)
        self.assertEqual(review[0]['rationale'],rationale)
        self.assertEqual(review[0]['unresolved_frontiers'],remaining)
        self.assertEqual(review[0]['considered_report_ids'],[])
        self.assertEqual(review[0]['considered_organization_request_ids'],[])
        blob=j.blob(canon(obj))
        j.append('CONTROLLER_DECISION',{'id':'D00001','call_id':'CTRL_D00001',
                                        'parsed_blob':blob,'rationale':rationale})
        for kind,payload in planned:
            j.append(kind,payload)
        state=j.verify()
        self.assertEqual(state.program_reviews[-1]['scientific_status'],'HOLD_WITH_RATIONALE')
        self.assertEqual(state.program_portfolio_reviews[-1]['disposition'],'PAUSE_WITH_RATIONALE')
        self.assertEqual(state.objective_assessments[-1]['research_status'],'PAUSED_EVIDENCE')
        original=json.loads(j.raw(state.controller_decisions[-1]['parsed_blob']))
        self.assertIsNone(original['program_portfolio_review'])
        self.assertEqual(len([p for p in state.operational_pauses if
          p['reason']=='M28_TERMINAL_PROGRAM_REVIEW_STRUCTURED_FROM_AUTHORED_JUDGMENT']),1)

    def test_no_projection_overrides_authored_inconsistent_candidate(self):
        j=self.journal(self.base/'ROOTS'/'PRIMARY')
        obj={
            'rationale':'Only conditional nulls were established',
            'new_problems':[],'reviews':[],'actions':[],
            'portfolio_decisions':[],'disposition':'REVIEW_WORTHY_CANDIDATE',
            'unresolved_opportunities':[],
            'objective_assessment':{
                'objective_status':'UNRESOLVED','research_status':'PAUSED_EVIDENCE',
                'resolved_scope':'No cooperation established','objective_coverage':'SUBPROBLEM_ONLY',
                'supporting_asset_ids':[],'remaining_questions':['Causal contrast'],
                'untried_approaches_considered':[], 'reason':'Not proven'
            }
        }
        with self.assertRaisesRegex(EvidenceError,'R5_CANDIDATE_DISPOSITION_MISMATCH'):
            controller_plan(j,obj,'CTRL_D00001','D00001')
        self.assertEqual(len(j._events()),5)

    def _original(self):
        repo=Path(__file__).resolve().parents[2]
        exp=self.base/'M28_DAC_NO3RR_20261111_02'
        exp.mkdir()
        (exp/'ROOTS').mkdir()
        j=self.journal(exp/'ROOTS'/'PRIMARY')
        self.saved(j,'CTRL_D00001')
        raw={'rationale':'Investigate more','actions':[]}
        blob=j.blob(canon(raw))
        j.append('CONTROLLER_DECISION',{'id':'D00001','call_id':'CTRL_D00001',
                                        'parsed_blob':blob,'rationale':'Investigate more'})
        j.append('PROGRAM_REVIEWED',{'reviewer_id':'D00001','scientific_status':'ONGOING',
                                     'rationale':'Evidence is missing',
                                     'considered_asset_ids':[],
                                     'unresolved_opportunities':['Causal controls']})
        j.append('PROGRAM_OBJECTIVE_ASSESSED',{'reviewer_id':'D00001',
                  'objective_status':'UNRESOLVED','research_status':'CONTINUING',
                  'resolved_scope':'none','objective_coverage':'NO_OBJECTIVE_RESULT',
                  'supporting_asset_ids':[], 'remaining_questions':['Control'],
                  'untried_approaches_considered':[], 'reason':'Unresolved'})
        self.saved(j,'CTRL_D00002')
        j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_PLAN_REJECTED:META_A2_PRIMARY_TERMINAL_REQUIRES_PROGRAM_REVIEW',
                                       'call_id':'CTRL_D00002'})
        from e2core.activation_contract import digest
        profile={'protocol':'M25_NATIVE_ACTIVATION_PROFILE_V1',
                 'model':'openai/gpt-5.6-luna','purpose':'unit test',
                 'features':FEATURES}
        budget={'protocol':'M232_DEVELOPMENT_BUDGET_V1','limit_usd':10.0,
                'model_rates_per_million_usd':{
                   'openai/gpt-5.6-luna':{'input':0.4,'output':1.8}},
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
              'initial_root':str(exp/'ROOTS'/'PRIMARY'),'science_certification':False,
              'researcher_count_not_preselected':True,'mandatory_generations':False,
              'mandatory_synthesis':False, 'activation_profile_sha256':digest(profile),
              'budget_config_sha256':sha(budget_blob)}
        (exp/'meta_research.json').write_bytes(canon(meta))
        rel='runtime/e2core/core.py'
        raw=subprocess.check_output(['git','show','9487b96:'+rel],cwd=repo)
        pin={'protocol':'M16_NATIVE_EXECUTION_SOURCE_V1','repository':str(repo),
             'files':{rel:hashlib.sha256(raw).hexdigest()},
             'source_verification':'EXACT_PYTHON_BYTES_SHA256',
             'not_historical_v3_replay':True, 'not_scientific_certification':True}
        (exp/'NATIVE_RUNTIME_SOURCE_PIN.json').write_bytes(canon(pin))
        conn=_connection(exp)
        try:
            for cid in ('CTRL_D00001','CTRL_D00002'):
                conn.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                      ('key-'+cid,str(j.root),cid,'a'*64,'openai/gpt-5.6-luna',
                       'SAVED',0.4,0.05,1.0))
        finally:conn.close()
        return exp,j

    def _first_successor_with_new_rejections(self):
        old,j=self._original()
        first=self.base/'M28_DAC_NO3RR_20261111_03'
        build_successor(old,first)
        firstj=EvolutionJournal(first/'ROOTS'/'PRIMARY')
        self.saved(firstj,'CTRL_D00003',usage=0.02)
        firstj.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_PLAN_REJECTED:META_A2_PRIMARY_TERMINAL_REQUIRES_PROGRAM_REVIEW',
                                            'call_id':'CTRL_D00003'})
        conn=_connection(first)
        try:
            conn.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                   ('key-CTRL_D00003',str(firstj.root),'CTRL_D00003',
                    'b'*64,'openai/gpt-5.6-luna','SAVED',0.1,0.02,1.0))
        finally:conn.close()
        # Synthetic first successor's source pin is set to the exact d931063
        # commit's core.py. Real-world _03 contains the full 65-file pin.
        repo=Path(__file__).resolve().parents[2]
        rel='runtime/e2core/core.py'
        raw=subprocess.check_output(['git','show','d931063:'+rel],cwd=repo)
        pin={'protocol':'M16_NATIVE_EXECUTION_SOURCE_V1','repository':str(repo),
             'files':{rel:hashlib.sha256(raw).hexdigest()},
             'source_verification':'EXACT_PYTHON_BYTES_SHA256',
             'not_historical_v3_replay':True, 'not_scientific_certification':True}
        (first/'NATIVE_RUNTIME_SOURCE_PIN.json').write_bytes(canon(pin))
        self.assertEqual(verify_successor_prefix(first)['parent_calls_saved'],2)
        return old,first,firstj

    def test_second_successor_preserves_all_calls_and_cumulative_budget(self):
        old,first,firstj=self._first_successor_with_new_rejections()
        original_head=sha(canon(EvolutionJournal(old/'ROOTS'/'PRIMARY')._events()[-1]))
        prior_head=sha(canon(firstj._events()[-1]))
        second=self.base/'M28_DAC_NO3RR_20261111_04'
        check=build_successor(first,second,dry_run=True)
        self.assertEqual(check['parent_calls_saved'],3)
        self.assertFalse(second.exists())
        result=build_successor(first,second)
        self.assertEqual(result['parent_calls_saved'],3)
        self.assertAlmostEqual(result['successor_budget_limit_usd'],9.88)
        self.assertEqual(result['parent_head_sha256'],prior_head)
        self.assertTrue(controller_recovery_pending(EvolutionJournal(second/'ROOTS'/'PRIMARY')))
        self.assertTrue(root_ready(second/'ROOTS'/'PRIMARY'))
        self.assertEqual(sha(canon(firstj._events()[-1])),prior_head)
        self.assertEqual(sha(canon(EvolutionJournal(old/'ROOTS'/'PRIMARY')._events()[-1])),original_head)
        self.assertEqual(verify_successor_prefix(second)['parent_calls_saved'],3)
        lineage=json.loads((second/'M28_NATIVE_RESEARCH_SUCCESSOR.json').read_bytes())
        self.assertAlmostEqual(lineage['original_total_budget_usd'],10.0)
        self.assertAlmostEqual(lineage['cumulative_upstream_accounted_usd'],0.12)
        self.assertEqual(lineage['parent_native_source_commit'],'d931063')
        self.assertEqual(len(EvolutionJournal(second/'ROOTS'/'PRIMARY').verify().model_calls),3)

    def test_second_successor_rejects_missing_cost_row_without_writes(self):
        _old,first,firstj=self._first_successor_with_new_rejections()
        db=first/'.M232_DEV_BUDGET.sqlite3'
        import sqlite3
        with sqlite3.connect(db) as c:
            c.execute("DELETE FROM calls WHERE call_id='CTRL_D00003'")
        dest=self.base/'M28_DAC_NO3RR_20261111_04'
        with self.assertRaisesRegex(EvidenceError,'ORIGINAL_LEDGER_CALL_IDS_MISMATCH'):
            build_successor(first,dest,dry_run=True)
        self.assertFalse(dest.exists())


if __name__=='__main__':
    unittest.main()
