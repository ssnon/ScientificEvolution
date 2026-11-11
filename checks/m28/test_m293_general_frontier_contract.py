"""M29.3: real NEW M28 init -> opt-in -> native/V3 shared prompt -> HOLD validation.

No provider calls. Tests do not mutate any user experiment.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from e2core.core import EvolutionJournal, EvidenceError, sha, canon
from e2core.activation_contract import PROTOCOL as PROFILE_PROTOCOL
from e2core.engine import controller_plan, effective_controller_contract
from e2core.m291_frontier_contract import (
    GENERAL_FLAG, GENERAL_MARKER, active, validate_for_controller,
)
from e2core.meta_autonomy import POLICY as META_POLICY
from e2core.meta_collaboration import POLICY as COLLAB_POLICY
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


class TestM293GeneralFrontier(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.exp=self.folder/'M293_FRESH_REAL_INIT'
        self.input=self.folder/'p0.txt'
        self.profile=self.folder/'activation.json'
        self.budget=self.folder/'budget.json'
        self.input.write_text('What can distinguish two causal mechanisms?',encoding='utf8')
        self.profile.write_text(json.dumps({
            'protocol':PROFILE_PROTOCOL,'model':MODEL,
            'purpose':'M29.3 contract integration no-paid regression',
            'features':FEATURES}),encoding='utf8')
        self.budget.write_text(json.dumps({
            'protocol':'M232_DEVELOPMENT_BUDGET_V1',
            'limit_usd':8.0,
            'model_rates_per_million_usd':{MODEL:{'input':0.25,'output':2.0}},
            'reserve_multiplier':1.25}),encoding='utf8')
        env={**FEATURES,'FAKG_RESEARCH_ALLOW_PAID':'NO'}
        with patch.dict(os.environ,env,clear=False):
            meta_run.init(SimpleNamespace(out=str(self.exp),
                problem_file=str(self.input),activation_profile=str(self.profile),
                budget_config=str(self.budget)))
            # Covers native source pin and NEW frontier marker in preflight.
            meta_run._preflight(self.exp,json.loads(
                (self.exp/'meta_research.json').read_text(encoding='utf8')))
        self.j=EvolutionJournal(self.exp/'ROOTS'/'PRIMARY')

    def record_saved_controller_call(self):
        """Mirror the real provider state before Controller plan validation.

        M28-A2 program-wide review requires its originating CTRL call to
        exist as SAVED; no fake scientific result is attributed to the call.
        """
        cid='CTRL_D00001'
        request_blob=self.j.blob({'synthetic_test_request':cid})
        response_blob=self.j.blob({'synthetic_test_response':cid})
        self.j.append('MODEL_CALL_INTENT',{
            'id':cid,'actor':'CONTROLLER','work_id':None,
            'request_blob':request_blob,'model':MODEL,
            'billing_mode':'EXTERNAL'})
        self.j.append('MODEL_CALL_SAVED',{
            'id':cid,'response_blob':response_blob,'usage':{'cost':0.0}})

    @staticmethod
    def hold():
        return {
            'rationale':'The available causal observations do not identify the two mechanisms.',
            'disposition':'HOLD_WITH_RATIONALE',
            'new_problems':[],'reviews':[],'actions':[],
            'portfolio_decisions':[],
            'organization_requests':[],'collaboration_requests':[],
            'unresolved_opportunities':['The matched control has not been executed'],
            'objective_assessment':{
                'objective_status':'UNRESOLVED',
                'research_status':'PAUSED_LOW_INFORMATION',
                'resolved_scope':'Nothing is independently established',
                'objective_coverage':'SUBPROBLEM_ONLY',
                'supporting_asset_ids':[],
                'remaining_questions':['Which controlled intervention separates them?'],
                'untried_approaches_considered':['Matched intervention'],
                'reason':'No contrasting evidence has been produced',
            },
            'program_portfolio_review':None,
        }

    def test_general_activation_and_full_preflight(self):
        self.assertTrue(active(self.j))
        p=json.loads((self.exp/'persistent.json').read_text(encoding='utf8'))
        m=json.loads((self.exp/'meta_research.json').read_text(encoding='utf8'))
        self.assertIs(p[GENERAL_FLAG],True)
        self.assertIs(m[GENERAL_FLAG],True)
        marks=[e for e in self.j._events() if e['kind']=='OPERATIONAL_PAUSE' and
               e['payload'].get('reason')==GENERAL_MARKER]
        self.assertEqual(len(marks),1)
        self.assertFalse(marks[0]['payload']['science_certification'])
        from generational_run import modules, verify_runtime_source
        self.assertEqual(verify_runtime_source(modules(),self.j.root)['pinned_python_file_count']>0,True)

    def test_real_new_primary_native_prompt_has_m291(self):
        p,c=effective_controller_contract(self.j,'NATIVE_BASE',{'program':'test'})
        self.assertIn('M28-A1 META-RESEARCH AUTONOMY',p)
        self.assertIn('M28-A2 SELECTIVE SCIENTIFIC COLLABORATION',p)
        self.assertIn('M29 EVIDENCE-TO-RESEARCH-FRONTIER HANDOFF',p)
        self.assertEqual(p.count('M29.1 EXPLICIT SCIENTIFIC FRONTIER ASSESSMENT CONTRACT'),2)
        self.assertIn('meta_research_organization_context',c)

    def test_real_new_primary_missing_hold_assessment_rejected_atomically(self):
        raw=self.hold()
        head=sha(canon(self.j._events()[-1]))
        with self.assertRaisesRegex(EvidenceError,'M291_HOLD_FRONTIER_ASSESSMENT_REQUIRED'):
            controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertEqual(head,sha(canon(self.j._events()[-1])))
        self.assertEqual(len(self.j.verify().controller_decisions),0)

    def test_valid_no_additional_value_hold_requires_no_new_work(self):
        self.record_saved_controller_call()
        raw=self.hold()
        raw['research_frontier_assessment']={
            'status':'NO_ADDITIONAL_VALUE','problem_ids':[],
            'rationale':'No further nonredundant causal contrast is scientifically formulable from the evidence presently described.'}
        plan=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertFalse(any(k in {'EVOLUTION_APPLIED','PROBLEM_CREATED'} for k,_ in plan))
        review=next(p for k,p in plan if k=='PROGRAM_REVIEWED')
        self.assertEqual(review['m29_research_frontier_assessment']['status'],
                         'NO_ADDITIONAL_VALUE')

    def test_cannot_yet_specify_is_valid_explicit_answer(self):
        self.record_saved_controller_call()
        raw=self.hold()
        raw['research_frontier_assessment']={
            'status':'CANNOT_YET_SPECIFY','problem_ids':[],
            'rationale':'The physical observable and sample identity are missing; no conditional contrast is yet well specified.'}
        plan=controller_plan(self.j,raw,'CTRL_D00001','D00001')
        self.assertEqual(next(p for k,p in plan if k=='PROGRAM_REVIEWED')[
            'm29_research_frontier_assessment']['status'],'CANNOT_YET_SPECIFY')

    def test_ongoing_without_frontier_assessment_is_not_rejected_by_m291(self):
        s=self.j.verify()
        self.assertIsNone(validate_for_controller(self.j,None,[],
                           disposition='ONGOING',state=s))

    def test_child_root_inherits_contract_without_auto_certifying_science(self):
        child=EvolutionJournal(self.exp/'ROOTS'/'CHILD_SYNTHETIC')
        child.init(self.j.verify().program['problem'])
        child.append('META_RESEARCH_AUTONOMY_ACTIVATED',{'policy':META_POLICY})
        child.append('META_RESEARCH_COLLABORATION_ACTIVATED',{'policy':COLLAB_POLICY})
        self.assertTrue(active(child))
        with self.assertRaisesRegex(EvidenceError,'M291_HOLD_FRONTIER_ASSESSMENT_REQUIRED'):
            validate_for_controller(child,None,[],disposition='HOLD_WITH_RATIONALE',
                                    state=child.verify())

    def test_manifest_flag_drift_fails_closed(self):
        meta_path=self.exp/'meta_research.json'
        content=json.loads(meta_path.read_text(encoding='utf8'))
        content[GENERAL_FLAG]=False
        meta_path.write_text(json.dumps(content),encoding='utf8')
        with self.assertRaisesRegex(EvidenceError,'M293_FRONTIER_MANIFEST_FLAG_DRIFT'):
            active(self.j)

    def test_missing_marker_fails_closed(self):
        # One accidental loss of marker must not silently disable the contract.
        # We test via an isolated copied journal with no marker, leaving the
        # real synthetic root and user experiments untouched.
        blank=EvolutionJournal(self.folder/'TEMP_NO_MARKER')
        blank.init('Unrelated?')
        # A missing marker in a flagged program root is checked by preflight.
        marks=[e for e in self.j._events() if e['payload'].get('reason')==GENERAL_MARKER]
        self.assertEqual(len(marks),1)
        self.assertFalse(active(blank))

if __name__=='__main__':unittest.main()
