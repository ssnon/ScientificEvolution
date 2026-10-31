"""Free regression tests for the integrated worker JSON execution boundary."""
from __future__ import annotations
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'runtime'))

from e2core.worker_json import parse_worker_response
from e2core.provider import strict_envelope


class TestWorkerSerialization(unittest.TestCase):
    def setUp(self):
        self.base = {'scientific_text':'Fixture: ask for a mock literature search.',
                     'next_action':'CONTINUE', 'assets':[], 'new_problems':[],
                     'tool_request':{'kind':'literature_research',
                         'arguments':{'action':'search','query':'fixture only',
                                      'provider':'openalex','page':1}}}
        self.raw = json.dumps(self.base, ensure_ascii=False, sort_keys=True)

    def test_identical_json_repetition(self):
        obj, meta = parse_worker_response(self.raw+'\n\n'+self.raw, strict_envelope)
        self.assertEqual(obj,self.base)
        self.assertEqual(meta['status'],'IDENTICAL_DUPLICATE_COLLAPSED')
        self.assertEqual(meta['document_count'],2)

    def test_distinct_research_or_tool_rejected(self):
        other = {**self.base,'scientific_text':'Different research conclusion.'}
        obj, meta = parse_worker_response(self.raw+'\n'+json.dumps(other),strict_envelope)
        self.assertIsNone(obj)
        self.assertEqual(meta['status'],'DISTINCT_MULTIPLE_JSON_REJECTED')
        other = {**self.base,'tool_request':None}
        obj, meta = parse_worker_response(self.raw+'\n'+json.dumps(other),strict_envelope)
        self.assertIsNone(obj)
        self.assertEqual(meta['status'],'DISTINCT_MULTIPLE_JSON_REJECTED')

    def test_invalid_and_duplicate_keys(self):
        s='{"scientific_text":"a","scientific_text":"b"}'
        obj, _ = parse_worker_response(s,strict_envelope)
        self.assertIsNone(obj)
        obj, _ = parse_worker_response(self.raw+'\n'+s,strict_envelope)
        self.assertIsNone(obj)
        obj, _ = parse_worker_response('{"x": NaN}',strict_envelope)
        self.assertIsNone(obj)
        obj, _ = parse_worker_response(self.raw+'\n'+self.raw+'\n{}',strict_envelope)
        self.assertIsNone(obj)

    def test_legacy_single_preamble_and_controller_unchanged(self):
        body='Preamble\n'+self.raw
        obj,meta=parse_worker_response(body,strict_envelope)
        self.assertEqual(obj,self.base)
        self.assertEqual(meta['status'],'LEGACY_SINGLE_ENVELOPE')
        self.assertEqual(strict_envelope(self.raw),self.base)


class MockSavedWorker:
    def __init__(self,j,rendered):
        self.j=j
        self.rendered=rendered

    def call(self,ident,actor,work_id,system,payload):
        assert actor=='WORKER'
        self.j.append('MODEL_CALL_INTENT',{
            'id':ident,'actor':actor,'work_id':work_id,
            'request_blob':self.j.blob({'synthetic':True,'call_id':ident}),
            'model':'LOCAL_MOCK','billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED',{
            'id':ident,'response_blob':self.j.blob({'choices':[
                {'message':{'content':self.rendered},'finish_reason':'stop'}]}),
            'usage':{}})
        return self.rendered

class MockTool:
    def __init__(self):
        self.requests=[]
    def __call__(self,req,ctx):
        self.requests.append(req)
        return {'status':'DELIVERED','evidence_class':'BIBLIOGRAPHIC_METADATA',
                'synthetic_only':True}


class TestRealE2WorkerIntegration(unittest.TestCase):
    def run_mock_work(self,rendered,expected_status):
        from e2core.core import EvolutionJournal
        from e2core.engine import Engine
        with tempfile.TemporaryDirectory(prefix='scientific_core_worker_') as folder:
            j=EvolutionJournal(Path(folder)/'root')
            j.init('Synthetic test: no real science.')
            j.evolve('EV_TEST','FRESH',[],{'id':'W_TEST','mode':'FRESH',
                'problem_id':'P0','question':'Synthetic fixture only',
                'research_rationale':'No real research','source_ids':[]},
                'Synthetic fixture only')
            tool=MockTool()
            e=Engine(j,MockSavedWorker(j,rendered),tool_backend=tool)
            result=e.worker_step('W_TEST')
            self.assertEqual(result['status'],expected_status)
            s=j.verify()
            self.assertEqual(s.model_calls['WK_W_TEST_00001']['state'],'SAVED')
            self.assertEqual(s.model_calls['WK_W_TEST_00001']['billing_mode'],'MOCK')
            saved=json.loads(j.raw(s.work['W_TEST']['steps'][0]['raw_blob']))
            self.assertEqual(saved['text'],rendered)
            self.assertEqual(saved['format_audit']['status'],
                'IDENTICAL_DUPLICATE_COLLAPSED' if expected_status=='TOOL_FEEDBACK_PENDING'
                else 'DISTINCT_MULTIPLE_JSON_REJECTED')
            if expected_status=='TOOL_FEEDBACK_PENDING':
                self.assertEqual(len(tool.requests),1)
                self.assertTrue(any(x['kind']=='TOOL_RECORDED' for x in j._events()))
            else:
                self.assertEqual(len(tool.requests),0)
                self.assertEqual(s.work['W_TEST']['outcome'],'BLOCKED')
            self.assertFalse(os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES')

    def test_identical_repeat_executes_one_tool(self):
        base={'scientific_text':'Synthetic only','next_action':'CONTINUE',
              'assets':[], 'new_problems':[],
              'tool_request':{'kind':'literature_research',
                              'arguments':{'action':'search','query':'fixture only',
                                           'provider':'openalex','page':1}}}
        raw=json.dumps(base)
        self.run_mock_work(raw+'\n'+raw,'TOOL_FEEDBACK_PENDING')

    def test_distinct_repeat_never_executes_tool(self):
        base={'scientific_text':'Synthetic only','next_action':'CONTINUE',
              'assets':[], 'new_problems':[],
              'tool_request':{'kind':'literature_research',
                              'arguments':{'action':'search','query':'fixture only',
                                           'provider':'openalex','page':1}}}
        raw=json.dumps(base)
        self.run_mock_work(raw+'\n'+json.dumps({**base,'next_action':'HOLD'}),
                           'BLOCKED_FORMAT')


if __name__=='__main__':
    unittest.main()
