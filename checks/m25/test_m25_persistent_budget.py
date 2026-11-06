"""M25.2 Native persistent budget routing tests. No paid/network calls."""
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from e2core.m232_budget import _experiment_path, reserve_call, budget_report
from e2core.core import EvidenceError


class M25PersistentBudgetTests(unittest.TestCase):
    def test_persistent_root_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'M25_EXPERIMENT'
            worker=root/'CYCLE_000'/'SYN_01'
            worker.mkdir(parents=True)
            (root/'persistent.json').write_text('{}',encoding='utf8')
            self.assertEqual(_experiment_path(worker), root)

    def test_legacy_autonomous_root_discovery_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'OLDER_AUTONOMOUS'
            worker=root/'CYCLE_001'/'POPULATION'
            worker.mkdir(parents=True)
            (root/'autonomous.json').write_text('{}',encoding='utf8')
            self.assertEqual(_experiment_path(worker), root)

    def test_budget_requirement_fails_closed_for_missing_config(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'M25_EXPERIMENT'
            worker=root/'CYCLE_000'/'POPULATION'
            worker.mkdir(parents=True)
            (root/'persistent.json').write_text('{}',encoding='utf8')
            with patch.dict(os.environ,{'M232_BUDGET_REQUIRED':'YES'}):
                with self.assertRaisesRegex(EvidenceError,'M232_DEVELOPMENT_BUDGET_NOT_CONFIGURED'):
                    reserve_call(worker,'CTRL_D00001',b'{}','test/model',100,'EXTERNAL')

    def test_budget_reservation_on_persistent_root(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'M25_EXPERIMENT'
            worker=root/'CYCLE_000'/'SYN_01'
            worker.mkdir(parents=True)
            (root/'persistent.json').write_text('{}',encoding='utf8')
            config={'protocol':'M232_DEVELOPMENT_BUDGET_V1',
                    'limit_usd':1.0,
                    'model_rates_per_million_usd':{'test/model':{'input':3.0,'output':12.0}},
                    'reserve_multiplier':1.25}
            (root/'M232_DEV_BUDGET.json').write_text(json.dumps(config),encoding='utf8')
            with patch.dict(os.environ,{'M232_BUDGET_REQUIRED':'YES'}):
                receipt=reserve_call(worker,'CTRL_D00001',b'{"test":123}','test/model',200,'EXTERNAL')
                self.assertEqual(Path(receipt[0]),root)
                self.assertEqual(budget_report(root)['status'],'M232_OPERATIONAL_COST_LEDGER')
                # A second reservation for the same request is never silently billed.
                with self.assertRaisesRegex(EvidenceError,'M232_EXISTING_BUDGET_RESERVATION'):
                    reserve_call(worker,'CTRL_D00001',b'{"test":123}','test/model',200,'EXTERNAL')

    def test_cap_rejects_pre_provider_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'M25_EXPERIMENT'
            worker=root/'CYCLE_000'/'SYN_01'
            worker.mkdir(parents=True)
            (root/'persistent.json').write_text('{}',encoding='utf8')
            config={'protocol':'M232_DEVELOPMENT_BUDGET_V1',
                    'limit_usd':0.000001,
                    'model_rates_per_million_usd':{'test/model':{'input':3.0,'output':12.0}}}
            (root/'M232_DEV_BUDGET.json').write_text(json.dumps(config),encoding='utf8')
            with patch.dict(os.environ,{'M232_BUDGET_REQUIRED':'YES'}):
                with self.assertRaisesRegex(EvidenceError,'OPERATIONAL_DEVELOPMENT_BUDGET_REACHED'):
                    reserve_call(worker,'CTRL_D00001',b'{}','test/model',200,'EXTERNAL')

if __name__=='__main__':unittest.main()
