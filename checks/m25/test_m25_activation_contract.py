"""No-paid regression tests for declared new-root runtime activation."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from e2core.activation_contract import (
    PROTOCOL, DEFAULTS, digest, read_profile, check_activation
)


def example(model='openai/gpt-5.6-luna', **kwargs):
    return {
        'protocol': PROTOCOL,
        'model': model,
        'purpose': 'Explicit operator-selected synthetic test, not science',
        'features': {**DEFAULTS, **kwargs},
    }


class TestM25ActivationContract(unittest.TestCase):
    def test_full_requires_explicit_record_but_accepts_unset_defaults(self):
        p = example()
        with patch.dict(os.environ, {}, clear=True):
            result = check_activation({'activation_profile': p,
                                       'activation_profile_sha256': digest(p)},
                                      model=p['model'])
        self.assertEqual(result['status'], 'ACTIVATION_PROFILE_VERIFIED_NO_PAID')
        self.assertEqual(result['features']['M232_CONTROLLER_DETAIL_MODE'], 'FULL')

    def test_unset_optimized_env_fails_before_paid_call(self):
        p = example(M232_CONTROLLER_DETAIL_MODE='ON_DEMAND',
                    M232_NAMESPACE_MODE='COMPACT',
                    M233_MODEL_METADATA_MODE='SEPARATE',
                    M232_BUDGET_REQUIRED='YES')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'ENVIRONMENT_DRIFT'):
                check_activation(p)

    def test_optimized_existing_budget_parser_used(self):
        p = example(M232_CONTROLLER_DETAIL_MODE='ON_DEMAND',
                    M232_NAMESPACE_MODE='COMPACT',
                    M233_MODEL_METADATA_MODE='SEPARATE',
                    M232_CACHE_POLICY='SELECTIVE_NO_WRITE',
                    M232_SYN_PMI_MODE='SCOPED',
                    M232_BUDGET_REQUIRED='YES')
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            with patch.dict(os.environ, p['features'], clear=True):
                with self.assertRaises(Exception):
                    check_activation(p, model=p['model'], experiment=d, require_budget=True)
                (d / 'M232_DEV_BUDGET.json').write_text(json.dumps({
                    'protocol': 'M232_DEVELOPMENT_BUDGET_V1',
                    'limit_usd': 4.0,
                    'model_rates_per_million_usd': {p['model']: {
                        'input': 0.1, 'output': 0.2}},
                }))
                out = check_activation(p, model=p['model'], experiment=d,
                                       require_budget=True)
        self.assertTrue(out['budget_config_required'])

    def test_incompatible_mode_is_rejected(self):
        p = example(M232_NAMESPACE_MODE='COMPACT')
        with self.assertRaisesRegex(RuntimeError, 'REQUIRES_ON_DEMAND'):
            check_activation(p)

    def test_model_mismatch_is_rejected(self):
        p = example()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'MODEL_CHANGED'):
                check_activation(p, model='another/model')

    def test_profile_loading_requires_exact_schema(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'activation.json'
            path.write_text(json.dumps(example()))
            self.assertEqual(read_profile(path)['protocol'], PROTOCOL)
            corrupt = example(); corrupt['features'].pop('M232_SYN_PMI_MODE')
            path.write_text(json.dumps(corrupt))
            with self.assertRaisesRegex(RuntimeError, 'FEATURE_KEYS_INCOMPLETE'):
                read_profile(path)

    def test_manifest_hash_mismatch_rejected(self):
        p = example()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'DIGEST_MISMATCH'):
                check_activation({'activation_profile': p,
                                  'activation_profile_sha256': '0' * 64})

if __name__ == '__main__':
    unittest.main()
