"""No-paid Persistent Population activation lifecycle integration tests.

Uses only disposable EvolutionJournals.  No provider calls, network requests,
or modifications to actual research roots.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import persistent_population as pp
from e2core.activation_contract import DEFAULTS, PROTOCOL
from e2core.core import EvolutionJournal
from e2core.provider import DurableModel

MODEL = 'openai/gpt-5.6-luna'


class TestM25ActivationLifecycle(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='m25_activation_lifecycle_')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.source = self.folder / 'source'
        self.donor = EvolutionJournal(self.source)
        self.donor.init('Synthetic P0: test operational activation, not scientific truth')
        self.original_events = self.donor._events()
        # Any accidental model execution is an immediate test failure.
        no_provider = patch.object(
            DurableModel, 'call',
            side_effect=AssertionError('PROVIDER_CALL_FORBIDDEN_IN_NO_PAID_TEST')
        )
        no_provider.start()
        self.addCleanup(no_provider.stop)

    def _prepare(self, label, features):
        root = self.folder / label
        profile_file = self.folder / (label + '_activation.json')
        profile = {
            'protocol': PROTOCOL,
            'model': MODEL,
            'purpose': 'No-paid synthetic integration fixture',
            'features': features,
        }
        profile_file.write_text(json.dumps(profile), encoding='utf8')
        args = SimpleNamespace(
            source_root=str(self.source), out=str(root),
            math_verification=False, activation_profile=str(profile_file),
        )
        with patch.dict(os.environ, features, clear=False):
            with contextlib.redirect_stdout(io.StringIO()):
                pp.init(args)
        self.assertEqual(self.original_events, self.donor._events())
        self.assertEqual(pp.plan_at(root)['activation_profile'], profile)
        self.assertEqual(len(pp.verify(pp.pop.gen.modules(), root / 'BASE_000')[1].model_calls), 0)
        return root

    def _preflight(self, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            pp.preflight(SimpleNamespace(experiment=str(root)))
        self.assertIn('PERSISTENT_PREFLIGHT_OK_NO_PAID', output.getvalue())
        self.assertIn('ACTIVATION_PROFILE_VERIFIED_NO_PAID', output.getvalue())

    def test_full_profile_preflight_passes_but_drift_fails_before_journal(self):
        f = dict(DEFAULTS)
        root = self._prepare('FULL', f)
        with patch.dict(os.environ, f, clear=False):
            self._preflight(root)
            with patch.dict(os.environ, {'M232_NAMESPACE_MODE': 'COMPACT'}):
                with patch.object(pp, 'verify', side_effect=AssertionError('JOURNAL_CHECK_REACHED')):
                    with self.assertRaisesRegex(RuntimeError, 'ACTIVATION_PROFILE_ENVIRONMENT_DRIFT'):
                        pp.preflight(SimpleNamespace(experiment=str(root)))
        self.assertEqual(self.original_events, self.donor._events())

    def test_optimized_profile_requires_budget_before_preflight(self):
        f = dict(DEFAULTS)
        f.update({
            'M232_CONTROLLER_DETAIL_MODE': 'ON_DEMAND',
            'M232_NAMESPACE_MODE': 'COMPACT',
            'M233_MODEL_METADATA_MODE': 'SEPARATE',
            'M232_CACHE_POLICY': 'SELECTIVE_NO_WRITE',
            'M232_BUDGET_REQUIRED': 'YES',
        })
        root = self._prepare('OPTIMIZED', f)
        with patch.dict(os.environ, f, clear=False):
            with self.assertRaisesRegex(Exception, 'M232_DEVELOPMENT_BUDGET_NOT_CONFIGURED'):
                pp.preflight(SimpleNamespace(experiment=str(root)))
            (root / 'M232_DEV_BUDGET.json').write_text(json.dumps({
                'protocol': 'M232_DEVELOPMENT_BUDGET_V1',
                'limit_usd': 1.0,  # synthetic; no calls will be made
                'model_rates_per_million_usd': {MODEL: {'input': 0.1, 'output': 0.2}},
            }), encoding='utf8')
            self._preflight(root)
            with patch.dict(os.environ, {'M233_MODEL_METADATA_MODE': 'FULL'}):
                with self.assertRaisesRegex(RuntimeError, 'ACTIVATION_PROFILE_ENVIRONMENT_DRIFT'):
                    pp.preflight(SimpleNamespace(experiment=str(root)))
        self.assertEqual(self.original_events, self.donor._events())

    def test_paid_segment_boundary_checks_profile_before_journal_or_driver(self):
        f = dict(DEFAULTS)
        root = self._prepare('SEGMENT', f)
        args = SimpleNamespace(experiment=str(root), model=MODEL)
        with patch.dict(os.environ, f, clear=False):
            with patch.dict(os.environ, {'M232_CONTROLLER_DETAIL_MODE': 'ON_DEMAND'}):
                with patch.object(pp, 'verify', side_effect=AssertionError('JOURNAL_CHECK_REACHED')):
                    with patch.object(pp.pop.gen, 'drive', side_effect=AssertionError('MODEL_DRIVE_REACHED')):
                        with self.assertRaisesRegex(RuntimeError, 'ACTIVATION_PROFILE_ENVIRONMENT_DRIFT'):
                            pp.budgeted_drive(pp.pop.gen.modules(), root / 'NO_ROOT', args, 0, 'peer')
        self.assertEqual(self.original_events, self.donor._events())


if __name__ == '__main__':
    unittest.main()
