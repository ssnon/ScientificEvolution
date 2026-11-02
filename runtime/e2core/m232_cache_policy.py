"""Opt-in M23.2 selective *provider prompt cache-write* policy.

No scientific prompt or payload edits. Keep default AUTO request bytes unchanged.
Do not enable within any research Journal containing calls made under AUTO.
Only OpenRouter/OpenAI GPT-5.6 Luna CONTROLLER PMI/OPP/CTRL are candidates.
"""
from __future__ import annotations

import json
import os

from .core import EvidenceError

AUTO = 'AUTO'
SELECTIVE_NO_WRITE = 'SELECTIVE_NO_WRITE'
SUPPORTED = {AUTO, SELECTIVE_NO_WRITE}
STAGES = ('PMI_', 'OPP_', 'CTRL_')
MODEL = 'openai/gpt-5.6-luna'


def _state(mode):
    if mode not in SUPPORTED:
        raise EvidenceError('M232_CACHE_POLICY_INVALID')
    return mode


def selected_cache_fields(j, ident, actor, work_id, model):
    """Return additive wire fields, never a modified prompt.

    Existing PMI/OPP/CTRL requests in a Journal determine its locked policy.
    NVT and scientific workers remain under provider automatic caching.
    """
    mode = _state(os.environ.get('M232_CACHE_POLICY', AUTO) or AUTO)
    if mode == SELECTIVE_NO_WRITE and model != MODEL:
        raise EvidenceError('M232_CACHE_POLICY_MODEL_UNSUPPORTED')
    if actor != 'CONTROLLER' or work_id is not None or not ident.startswith(STAGES):
        return {}
    records = j.verify().model_calls
    for prior_id, rec in records.items():
        if not prior_id.startswith(STAGES):
            continue
        if rec.get('actor') != 'CONTROLLER':
            continue
        old = json.loads(j.raw(rec['request_blob']))
        old_no_write = old.get('prompt_cache_options') == {'mode': 'explicit'}
        if old_no_write != (mode == SELECTIVE_NO_WRITE):
            raise EvidenceError('M232_CACHE_POLICY_MIXED_WITHIN_JOURNAL')
    if mode == SELECTIVE_NO_WRITE:
        return {'prompt_cache_options': {'mode': 'explicit'}}
    return {}
