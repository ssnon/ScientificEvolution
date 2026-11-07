"""No-paid contract regression: inherited actual arithmetic != failed attempt.

Synthetic tool blobs test only the existing transport classifier. They do not
certify a formula, perform a calculation, or call a model/provider.
"""
from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import population_run as pop


class _Donor:
    root = Path('/synthetic/immutable_donor')
    def __init__(self, blobs):
        self.blobs = blobs
    def raw(self, blob_id):
        return self.blobs[blob_id]


class _Dest:
    def __init__(self):
        self.sources = {}
    def add_source(self, source_id, source_kind, payload, description):
        if source_id in self.sources:
            raise AssertionError('DUPLICATE_SOURCE')
        self.sources[source_id] = (source_kind, payload, description)


class TestInheritedScienceToolStatus(unittest.TestCase):
    def test_verification_success_is_not_a_failed_attempt(self):
        statuses = [
            ('PY', 'python_science', 'EXECUTED',
             'EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED'),
            ('BAD', 'verified_calculation', 'REJECTED',
             'FAILED_CALCULATION_ATTEMPT_NOT_SCIENTIFIC_NEGATIVE'),
            ('OK', 'verified_calculation', 'VERIFIED_NUMERIC_ARITHMETIC',
             'EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED'),
        ]
        blobs = {}
        tool_results = {}
        for tid, kind, status, expected_class in statuses:
            blobs['REQ_'+tid] = json.dumps({'kind':kind,'arguments':{'marker':tid}})
            blobs['OUT_'+tid] = json.dumps({'status':status,'marker':tid})
            tool_results[tid] = {'work_id':'W_SYN',
                                 'request_blob':'REQ_'+tid,
                                 'result_blob':'OUT_'+tid}
        donor = _Donor(blobs)
        state = SimpleNamespace(tool_results=tool_results,work={'W_SYN':{'status':'DONE'}})
        dest = _Dest()
        canon = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        mods = SimpleNamespace(canon=canon,sha=lambda b:hashlib.sha256(b).hexdigest())
        with patch.object(pop,'uninterpreted_last_tool_feedback',return_value=[]):
            receipt = pop.record_science_tool_results(mods,dest,donor,state,'PRIOR_POPULATION')
        self.assertEqual(receipt['registered_science_tools'],3)
        self.assertEqual(len(dest.sources),3)
        carried = {record[1]['original_tool_id']:record[1] for record in dest.sources.values()}
        for tid, kind, status, expected_class in statuses:
            with self.subTest(tool=tid):
                obj = carried[tid]
                self.assertEqual(obj['evidence_class'],expected_class)
                self.assertEqual(obj['original_returned_data']['evidence_class'],expected_class)
                self.assertEqual(obj['original_returned_data']['result']['status'],status)
                self.assertEqual(obj['original_returned_data']['request']['kind'],kind)
                self.assertEqual(obj['original_result_blob_sha256'],'OUT_'+tid)
                self.assertFalse(obj['is_a_new_tool_execution'])
                self.assertTrue(obj['not_independently_certified'])

if __name__ == '__main__':
    unittest.main()
