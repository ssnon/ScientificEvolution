import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from e2core.m232_budget import reserve_call, settle_call, budget_report
from e2core.core import EvidenceError


class M232BudgetTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root=Path(self.t.name)
        self.exp=self.root/'exp';self.exp.mkdir()
        (self.exp/'autonomous.json').write_text('{}')
        self.work=self.exp/'CYCLE_000/SYN_01';self.work.mkdir(parents=True)
        (self.exp/'M232_DEV_BUDGET.json').write_text(json.dumps({
           'protocol':'M232_DEVELOPMENT_BUDGET_V1','limit_usd':0.10,
           'model_rates_per_million_usd':{'test-model':{'input':1.0,'output':2.0}},
           'reserve_multiplier':1.25}))

    def tearDown(self):self.t.cleanup()

    def test_reserve_settle_and_limited_next(self):
        with patch.dict(os.environ,{'M232_BUDGET_REQUIRED':'YES'}):
            ticket=reserve_call(self.work,'A',b'{'*60000,'test-model',10000,'EXTERNAL')
            self.assertTrue(ticket)
            self.assertEqual(budget_report(self.exp)['states']['RESERVED']['count'],1)
            settle_call(ticket,{'cost':0.06})
            self.assertEqual(budget_report(self.exp)['states']['SAVED']['count'],1)
            with self.assertRaisesRegex(EvidenceError, 'OPERATIONAL_DEVELOPMENT_BUDGET_REACHED'):
                reserve_call(self.work,'B',b'{'*60000,'test-model',10000,'EXTERNAL')

    def test_no_paid_mock_does_not_reserve(self):
        self.assertIsNone(reserve_call(self.work,'M',b'{}','test-model',10000,'MOCK'))
        self.assertFalse((self.exp/'.M232_DEV_BUDGET.sqlite3').exists())

    def test_duplicate_is_fail_closed(self):
        reserve_call(self.work,'A',b'{}','test-model',1000,'EXTERNAL')
        with self.assertRaisesRegex(EvidenceError,'EXISTING_BUDGET_RESERVATION'):
            reserve_call(self.work,'A',b'{}','test-model',1000,'EXTERNAL')

    def test_no_budget_required_failure(self):
        (self.exp/'M232_DEV_BUDGET.json').unlink()
        with patch.dict(os.environ,{'M232_BUDGET_REQUIRED':'YES'}):
            with self.assertRaisesRegex(EvidenceError,'NOT_CONFIGURED'):
                reserve_call(self.work,'A',b'{}','test-model',1000,'EXTERNAL')
        self.assertFalse((self.exp/'.M232_DEV_BUDGET.sqlite3').exists())

if __name__=='__main__':unittest.main()
