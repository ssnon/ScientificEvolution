"""No-paid contract test: carry actual tool status without upgrading PLAN_ONLY to computation."""
from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
import population_run as pop


class FakeDonor:
    root = Path('/deterministic/offline/source')
    def __init__(self, blobs):
        self.blobs = blobs
    def raw(self, key):
        return json.dumps(self.blobs[key], ensure_ascii=False).encode('utf-8')


class FakeDestination:
    def __init__(self):
        self.records = {}
    def add_source(self, sid, kind, data, description):
        if sid in self.records:
            raise AssertionError('duplicate source ID')
        self.records[sid] = (kind, data, description)


class HistoricalScienceClassificationTests(unittest.TestCase):
    def test_model_declared_plan_is_distinct_from_executed_unvalidated_and_failed(self):
        cases = [
            ('TOOL_PLAN', 'python_science', {'status':'EXECUTED','result':{'status':'PLAN_ONLY'}},
             'SANDBOX_EXECUTED_MODEL_DECLARED_NO_COMPUTATION'),
            ('TOOL_PLAN_FLAG', 'python_science',
             {'status':'EXECUTED','result':{'status':'EXECUTED_CONTROL_CALCULATION','not_executed':True}},
             'SANDBOX_EXECUTED_MODEL_DECLARED_NO_COMPUTATION'),
            ('TOOL_NUMERIC', 'python_science',
             {'status':'EXECUTED','result':{'status':'EXECUTED_CORRECTED_COUNT_LAW_INVARIANT_AUDIT','mean':4.2}},
             'EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED'),
            ('TOOL_VERIFIED', 'verified_calculation',
             {'status':'VERIFIED_NUMERIC_ARITHMETIC','result':{'value':4}},
             'EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED'),
            ('TOOL_FAILED', 'python_science', {'status':'EXECUTION_FAILED','error_code':'ValueError'},
             'FAILED_CALCULATION_ATTEMPT_NOT_SCIENTIFIC_NEGATIVE'),
        ]
        blobs = {'LAST_STEP': {'tool_id':'TOOL_FAILED'}}
        tools = {}
        for tid,kind,result,_ in cases:
            req_blob, res_blob = tid + '_REQUEST', tid + '_RESULT'
            blobs[req_blob] = {'kind':kind,'arguments':{'code':'result={"status":"PLAN_ONLY"}'}}
            blobs[res_blob] = result
            tools[tid] = {'work_id':'W','request_blob':req_blob,'result_blob':res_blob}
        donor = FakeDonor(blobs)
        state = SimpleNamespace(
            tool_results=tools,
            work={'W':{'status':'ACTIVE','steps':[{'kind':'TOOL_RESULT','raw_blob':'LAST_STEP'}]}},
        )
        mods = SimpleNamespace(
            sha=lambda b: hashlib.sha256(b).hexdigest(),
            canon=lambda obj: json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8'),
        )
        dest = FakeDestination()
        receipt = pop.record_science_tool_results(mods, dest, donor, state, 'PRIOR_POPULATION')
        self.assertEqual(receipt['registered_science_tools'],len(cases))
        self.assertEqual(len(dest.records),len(cases))
        by_id = {entry['original_tool_id']:entry for kind,entry,_ in dest.records.values()}
        for tid,kind,result,want_class in cases:
            entry = by_id[tid]
            self.assertEqual(entry['evidence_class'], want_class)
            self.assertEqual(entry['original_returned_data']['result'], result)
            self.assertEqual(entry['original_returned_data']['request'], blobs[tid+'_REQUEST'])
            self.assertEqual(entry['original_request_blob_sha256'], tid+'_REQUEST')
            self.assertEqual(entry['original_result_blob_sha256'], tid+'_RESULT')
            self.assertEqual(entry['pending_worker_interpretation'],tid=='TOOL_FAILED')
            self.assertFalse(entry['not_independently_certified'] is False)
            self.assertFalse(entry['is_a_new_tool_execution'])
        self.assertEqual(len(receipt['ids']),len(cases))


if __name__ == '__main__':
    unittest.main()
