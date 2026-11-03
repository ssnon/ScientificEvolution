"""M23.4 offline regression: recorded exec is not proof of science.

Uses the exact model-submitted not_executed code and result shape from the
operator's real M23.3 audit; does not execute model-authored Python or access
network/model providers. No research Journal is written.
"""
from __future__ import annotations
import json
import unittest
from types import SimpleNamespace
from e2core.m234_execution_observation import inspect_python_execution
from e2core.research_context import _attempts, research_capability_state, research_worker_context
from unittest.mock import patch

ORIGINAL_CODE = (
    'result={"status":"not_executed","purpose":"Future design study should simulate '
    'matched polarity waveforms with finite exposure, charge and orientation '
    'kinetics, occupancy and elastic-reference channels, and held-out waveform '
    'validation."}'
)
REAL_REQUEST = {'kind':'python_science','arguments':{'code':ORIGINAL_CODE}}
REAL_RESPONSE = {
    'status':'EXECUTED','exit_code':0,'sandbox_backend':'bubblewrap',
    'result':{
        'status':'not_executed',
        'purpose': 'Future design study should simulate matched polarity waveforms '
                   'with finite exposure, charge and orientation kinetics, occupancy '
                   'and elastic-reference channels, and held-out waveform validation.',
    },
}


class FakeJournal:
    def __init__(self):
        self.requests={
            'R1':REAL_REQUEST,
            'R2':{'kind':'literature_research','arguments':{'action':'search'}},
            'R3':{'kind':'python_science','arguments':{'code':'result={"value": 2+2}'}},
        }
        self.responses={
            'S1':REAL_RESPONSE,
            'S2':{'status':'DELIVERED','evidence_class':'BIBLIOGRAPHIC_METADATA'},
            'S3':{'status':'EXECUTED','result':{'value':4}},
        }
        self.tool_results={
            'T1':{'work_id':'W_INFORMED','request_blob':'R1','result_blob':'S1'},
            'T2':{'work_id':'W_FRESH','request_blob':'R2','result_blob':'S2'},
            'T3':{'work_id':'W_FRESH','request_blob':'R3','result_blob':'S3'},
        }
    def verify(self):
        return SimpleNamespace(tool_results=self.tool_results, sources={},
                               work={"W_INFORMED":{"mode":"INFORMED"},
                                     "W_FRESH":{"mode":"FRESH"}}, r5_policy=True)
    def raw(self,key):
        item = self.requests.get(key, self.responses.get(key))
        return json.dumps(item).encode('utf-8')


class M234ExecutionFeedbackTests(unittest.TestCase):
    def test_exact_logged_not_executed_case_is_not_numerical_validation(self):
        observation=inspect_python_execution(REAL_REQUEST,REAL_RESPONSE)
        self.assertEqual(observation['observation'],
            'SANDBOX_EXECUTED_MODEL_DECLARED_NO_COMPUTATION')
        self.assertTrue(observation['model_declared_noncomputation'])
        self.assertFalse(observation['scientific_computation_validated'])
        self.assertEqual(observation['sandbox_execution_status'],'EXECUTED')

    def test_real_computation_not_automatically_certified(self):
        obs=inspect_python_execution(
            {'kind':'python_science','arguments':{'code':'result={"mean":sum([1,2,3])/3}'}},
            {'status':'EXECUTED','result':{'mean':2.0}})
        self.assertEqual(obs['observation'],
            'SANDBOX_EXECUTED_SCIENTIFIC_CONTENT_UNVERIFIED')
        self.assertFalse(obs['scientific_computation_validated'])

    def test_failed_tool_not_marked_scientific_failure(self):
        obs=inspect_python_execution(REAL_REQUEST,
            {'status':'EXECUTION_FAILED','error_code':'SyntaxError'})
        self.assertEqual(obs['observation'],'NO_SUCCESSFUL_SANDBOX_EXECUTION_RECORDED')
        self.assertFalse(obs['scientific_computation_validated'])

    def test_nonpython_tool_has_no_derived_assessment(self):
        self.assertIsNone(inspect_python_execution(
            {'kind':'literature_research'}, {'status':'DELIVERED'}))

    def test_model_claim_of_validation_cannot_certify_itself(self):
        obs=inspect_python_execution(REAL_REQUEST,
            {'status':'EXECUTED','result':{'status':'VALIDATED','validated':True}})
        self.assertFalse(obs['scientific_computation_validated'])

    def test_feedback_reaches_worker_and_controller_without_forced_action(self):
        j=FakeJournal()
        with patch('e2core.research_context.inherited_inventory', return_value={}), \
             patch('e2core.research_context.inherited_planning_brief', return_value={}), \
             patch('e2core.research_context.uninterpreted_last_tool_feedback', return_value={}):
            portfolio=research_capability_state(j, 'NATIVE_RESEARCH_TOOLS')
            informed=research_worker_context(j,'W_INFORMED','NATIVE_RESEARCH_TOOLS')
            fresh=research_worker_context(j,'W_FRESH','NATIVE_RESEARCH_TOOLS')
        pobs=portfolio['attempt_inventory']['recent_python_execution_observations']
        self.assertEqual(len(pobs),2)
        self.assertTrue(any(x['execution_observation']['model_declared_noncomputation']
                            for x in pobs))
        self.assertEqual(len(informed['own_recent_tool_attempts']),1)
        self.assertTrue(informed['own_recent_tool_attempts'][0][
                         'execution_observation']['model_declared_noncomputation'])
        self.assertNotIn('not_executed', json.dumps(fresh))
        self.assertIn('no mandatory computation',informed['guidance'])

    def test_attempt_filter_preserves_fresh_isolation(self):
        j=FakeJournal()
        before=(dict(j.requests),dict(j.responses),dict(j.tool_results))
        informed=_attempts(j,'W_INFORMED')
        fresh=_attempts(j,'W_FRESH')
        self.assertEqual(len(informed),1)
        self.assertEqual(len(fresh),2)
        self.assertEqual(informed[0]['execution_observation']['model_result_status'],
                         'not_executed')
        self.assertNotIn('not_executed', json.dumps(fresh))
        self.assertNotIn('execution_observation',fresh[0])
        self.assertEqual(before,(j.requests,j.responses,j.tool_results))


if __name__=='__main__':unittest.main()
