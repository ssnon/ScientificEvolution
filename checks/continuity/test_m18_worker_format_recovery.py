"""M18 no-paid E2 tests: model-authored correction with no tool cherry-picking."""
from __future__ import annotations
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'runtime'))
from e2core.core import EvolutionJournal
from e2core.engine import Engine


class MockWorker:
    def __init__(self, journal, responses):
        self.j = journal
        self.responses = list(responses)
        self.prompts = []
        self.payloads = []

    def call(self, ident, actor, work_id, system, payload):
        assert actor == 'WORKER'
        self.prompts.append(system)
        self.payloads.append(payload)
        if not self.responses:
            raise AssertionError('Unexpected extra model call')
        rendered = self.responses.pop(0)
        self.j.append('MODEL_CALL_INTENT', {
            'id':ident, 'actor':actor, 'work_id':work_id,
            'request_blob':self.j.blob({'synthetic':True, 'id':ident}),
            'model':'MOCK', 'billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED', {
            'id':ident,
            'response_blob':self.j.blob({'choices':[{'message':{'content':rendered},
                                                    'finish_reason':'stop'}]}),
            'usage':{}})
        return rendered


class MockTool:
    def __init__(self):
        self.calls = []
    def __call__(self, request, context):
        self.calls.append(request)
        return {'status':'DELIVERED', 'evidence_class':'BIBLIOGRAPHIC_METADATA',
                'synthetic_only':True}


def science(action='CONTINUE', query='one confirmed request'):
    return {'scientific_text':'Synthetic hypothesis audit, no empirical claim.',
            'next_action':action,'assets':[],'new_problems':[],
            'tool_request':{'kind':'literature_research','arguments':{
                'action':'search','query':query,'provider':'openalex','page':1}}}


def bad_three_objects():
    a = {'kind':'literature_research',
         'arguments':{'action':'search','query':'first tool','provider':'openalex','page':1}}
    b = {'kind':'literature_research',
         'arguments':{'action':'search','query':'second tool','provider':'europepmc','page':1}}
    return '\n\n'.join(json.dumps(x) for x in (a,b,science(query='third tool')))


class FormatRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='m18_native_repair_')
        self.addCleanup(self.tmp.cleanup)
        self.j = EvolutionJournal(Path(self.tmp.name)/'root')
        self.j.init('Synthetic problem; no real sources.')
        self.j.evolve('EV_FRESH','FRESH',[],{
            'id':'W_TEST','mode':'FRESH','problem_id':'P0',
            'question':'Synthetic test only','research_rationale':'Test parser recovery',
            'source_ids':[]}, 'Mock only')
        self.tool = MockTool()

    def run_engine(self, mock):
        return Engine(self.j, mock, tool_backend=self.tool, serial_fair=True)

    def test_structured_multi_json_requires_model_authored_repair(self):
        corrected = json.dumps(science(query='model selected follow-up'))
        worker = MockWorker(self.j, [bad_three_objects(), corrected])
        engine = self.run_engine(worker)
        first = engine.worker_step('W_TEST')
        self.assertEqual(first['status'], 'FORMAT_REPAIR_PENDING')
        self.assertEqual(self.tool.calls, [])
        interim = self.j.verify()
        self.assertEqual(interim.work['W_TEST']['status'], 'ACTIVE')
        self.assertEqual(len(interim.model_calls),1)
        self.assertFalse(interim.assets)
        saved = json.loads(self.j.raw(interim.work['W_TEST']['steps'][0]['raw_blob']))
        self.assertEqual(saved['format_audit']['status'], 'DISTINCT_MULTIPLE_JSON_REJECTED')
        self.assertEqual(saved['text'], bad_three_objects())
        second = engine.worker_step('W_TEST')
        self.assertEqual(second['status'], 'TOOL_FEEDBACK_PENDING')
        self.assertEqual(len(self.tool.calls),1)
        self.assertEqual(self.tool.calls[0]['arguments']['query'],'model selected follow-up')
        self.assertIn('OPERATIONAL FORMAT CORRECTION', worker.prompts[1])
        self.assertNotIn('OPERATIONAL FORMAT CORRECTION', worker.prompts[0])
        self.assertTrue(any(x['kind']=='MODEL_RESPONSE' for x in interim.work['W_TEST']['steps']))
        after = self.j.verify()
        self.assertEqual(len(after.model_calls),2)
        self.assertTrue(all(c['state']=='SAVED' for c in after.model_calls.values()))
        self.assertEqual(len(after.tool_results),1)
        self.assertEqual(after.work['W_TEST']['status'], 'ACTIVE')

    def test_second_malformed_response_blocks_without_tool_execution(self):
        worker = MockWorker(self.j, [bad_three_objects(), bad_three_objects()])
        engine = self.run_engine(worker)
        self.assertEqual(engine.worker_step('W_TEST')['status'],'FORMAT_REPAIR_PENDING')
        self.assertEqual(engine.worker_step('W_TEST')['status'],'BLOCKED_FORMAT')
        state = self.j.verify()
        self.assertEqual(state.work['W_TEST']['outcome'],'BLOCKED')
        self.assertEqual(len(state.model_calls),2)
        self.assertEqual(len(state.tool_results),0)
        self.assertEqual(len(self.tool.calls),0)
        self.assertFalse(state.assets)

    def test_recovery_survives_engine_restart_without_rebilling(self):
        first_model = MockWorker(self.j, [bad_three_objects()])
        self.assertEqual(self.run_engine(first_model).worker_step('W_TEST')['status'],
                         'FORMAT_REPAIR_PENDING')
        next_model = MockWorker(self.j, [json.dumps(science(query='after restart'))])
        self.assertEqual(self.run_engine(next_model).worker_step('W_TEST')['status'],
                         'TOOL_FEEDBACK_PENDING')
        state = self.j.verify()
        self.assertEqual(len(state.model_calls),2)
        self.assertEqual(len(self.tool.calls),1)
        self.assertEqual(self.tool.calls[0]['arguments']['query'],'after restart')

    def test_schema_invalid_complete_json_gets_one_recovery(self):
        wrong = science()
        wrong['scientific_text'] = 123  # syntactically valid, semantically invalid
        worker = MockWorker(self.j, [json.dumps(wrong), json.dumps(science(query='corrected schema'))])
        engine = self.run_engine(worker)
        self.assertEqual(engine.worker_step('W_TEST')['status'],'FORMAT_REPAIR_PENDING')
        self.assertEqual(engine.worker_step('W_TEST')['status'],'TOOL_FEEDBACK_PENDING')
        self.assertEqual(len(self.tool.calls),1)
        self.assertIn('OPERATIONAL FORMAT CORRECTION',worker.prompts[1])

    def test_normal_one_json_response_unchanged(self):
        worker = MockWorker(self.j, [json.dumps(science())])
        self.assertEqual(self.run_engine(worker).worker_step('W_TEST')['status'],
                         'TOOL_FEEDBACK_PENDING')
        self.assertEqual(len(self.tool.calls),1)
        self.assertNotIn('OPERATIONAL FORMAT CORRECTION', worker.prompts[0])
        self.assertEqual(self.j.verify().work['W_TEST']['status'],'ACTIVE')


if __name__ == '__main__':
    unittest.main()
