"""Declared execution activation for NEW Persistent Population experiments.

An operational reproducibility contract, not a science policy. It never changes
Journal, source content, model science, or environment variables.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

PROTOCOL = 'M25_NATIVE_ACTIVATION_PROFILE_V1'
DEFAULTS = {
    'M232_CONTROLLER_DETAIL_MODE': 'FULL',
    'M232_NAMESPACE_MODE': 'FULL',
    'M233_MODEL_METADATA_MODE': 'FULL',
    'M232_CACHE_POLICY': 'AUTO',
    'M232_SYN_PMI_MODE': 'FULL',
    'M232_BUDGET_REQUIRED': 'NO',
}
ALLOWED = {
    'M232_CONTROLLER_DETAIL_MODE': {'FULL', 'ON_DEMAND'},
    'M232_NAMESPACE_MODE': {'FULL', 'COMPACT'},
    'M233_MODEL_METADATA_MODE': {'FULL', 'SEPARATE'},
    'M232_CACHE_POLICY': {'AUTO', 'SELECTIVE_NO_WRITE'},
    'M232_SYN_PMI_MODE': {'FULL', 'SCOPED'},
    'M232_BUDGET_REQUIRED': {'NO', 'YES'},
}
SELECTIVE_CACHE_MODEL = 'openai/gpt-5.6-luna'


def _reject(reason):
    raise RuntimeError('ACTIVATION_PROFILE_' + reason)


def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')


def digest(profile):
    return hashlib.sha256(_canon(profile)).hexdigest()


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {'protocol', 'model', 'purpose', 'features'}:
        _reject('SCHEMA_INVALID')
    if profile['protocol'] != PROTOCOL:
        _reject('PROTOCOL_INVALID')
    if not isinstance(profile['model'], str) or not profile['model'].strip():
        _reject('MODEL_REQUIRED')
    if not isinstance(profile['purpose'], str) or not profile['purpose'].strip():
        _reject('OPERATOR_PURPOSE_REQUIRED')
    f = profile['features']
    if not isinstance(f, dict) or set(f) != set(DEFAULTS):
        _reject('FEATURE_KEYS_INCOMPLETE_OR_UNKNOWN')
    for key, permitted in ALLOWED.items():
        if type(f[key]) is not str or f[key] not in permitted:
            _reject('UNSUPPORTED_VALUE_' + key)
    detail = f['M232_CONTROLLER_DETAIL_MODE']
    if detail == 'FULL' and (f['M232_NAMESPACE_MODE'] != 'FULL' or
                             f['M233_MODEL_METADATA_MODE'] != 'FULL'):
        _reject('COMPACT_OR_SEPARATE_REQUIRES_ON_DEMAND')
    if detail == 'ON_DEMAND' and f['M232_BUDGET_REQUIRED'] != 'YES':
        _reject('ON_DEMAND_REQUIRES_BUDGET_GUARD')
    if f['M232_CACHE_POLICY'] == 'SELECTIVE_NO_WRITE' and profile['model'] != SELECTIVE_CACHE_MODEL:
        _reject('SELECTIVE_CACHE_UNSUPPORTED_MODEL')
    return profile


def read_profile(path):
    if not path:
        _reject('EXPLICIT_OPERATOR_PROFILE_REQUIRED_AT_INIT')
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        _reject('FILE_MISSING')
    try:
        value = json.loads(p.read_text(encoding='utf8'))
    except (OSError, ValueError) as e:
        _reject('FILE_UNREADABLE:' + type(e).__name__)
    return validate_profile(value)


def observed_features():
    # Preserve absence -> documented runtime defaults. Empty explicit values
    # are not treated as absent: downstream contracts already reject them.
    return {key: os.environ.get(key, default) for key, default in DEFAULTS.items()}


def check_activation(manifest_or_profile, *, model=None, experiment=None, require_budget=False):
    """Reject drift before an external model call, including across generations."""
    if 'activation_profile' in manifest_or_profile:
        profile = manifest_or_profile['activation_profile']
        if manifest_or_profile.get('activation_profile_sha256') != digest(profile):
            _reject('MANIFEST_DIGEST_MISMATCH')
    else:
        profile = manifest_or_profile
    validate_profile(profile)
    if model is not None and model != profile['model']:
        _reject('MODEL_CHANGED')
    expected = profile['features']
    actual = observed_features()
    drift = {k: {'expected': expected[k], 'observed': actual[k]}
             for k in expected if expected[k] != actual[k]}
    if drift:
        _reject('ENVIRONMENT_DRIFT:' + json.dumps(drift, sort_keys=True))
    if require_budget and expected['M232_BUDGET_REQUIRED'] == 'YES':
        if experiment is None:
            _reject('BUDGET_EXPERIMENT_ROOT_REQUIRED')
        # Reuse the existing M23.2 budget parser/validator, do not create
        # a second budget policy or open its SQLite database in preflight.
        from .m232_budget import _config
        cfg = _config(Path(experiment).expanduser().resolve())
        if cfg is None or profile['model'] not in cfg['model_rates_per_million_usd']:
            _reject('BUDGET_FILE_OR_MODEL_RATE_MISSING')
    return {'status': 'ACTIVATION_PROFILE_VERIFIED_NO_PAID',
            'profile_sha256': digest(profile),
            'model': profile['model'],
            'features': dict(expected),
            'budget_config_required': expected['M232_BUDGET_REQUIRED'] == 'YES',
            'no_scientific_certification': True}
