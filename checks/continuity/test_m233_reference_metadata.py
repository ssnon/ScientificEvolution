"""M23.3 opt-in scientific-context-safe presentation and Work-ref diagnostics.

All tests are no-network; no paid provider or scientific journal is modified.
"""
from __future__ import annotations
import copy
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from e2core.core import EvidenceError
from e2core.m233_model_metadata import (
    FULL, SEPARATE, MODE_KEY, VIEW_KEY, CONTRACT_KEY,
    compact_presentation_metadata, restore_from_unmodified_view,
    verify_metadata_mode,
)
from e2core.m233_reference_diagnostics import (
    reference_failure_diagnostic, WORK_REFERENCE_ADDENDUM,
)
from e2core.m232_live import assessor_call, ON_DEMAND


class StubJournal:
    def __init__(self, calls=None, assets=None, problems=None):
        self.calls = calls or {}
        self.assets = assets or {'A_CARRY_c0c1e0fd8131939f7a6da5d': {}}
        self.problems = problems or {'P0': {}}
    def verify(self):
        return SimpleNamespace(
            model_calls=self.calls,
            sources={'SRC_RECEIPT': {'kind': 'HISTORICAL_AI'}},
            problems=self.problems,
            assets=self.assets,
        )
    def raw(self, blob):
        return blob.encode('utf8')


class MockModel:
    mode = 'MOCK'
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []
    def call(self, ident, actor, work_id, prompt, payload):
        self.calls.append({'ident': ident, 'prompt': prompt,
                           'payload': copy.deepcopy(payload)})
        assert self.answers, 'UNEXPECTED_EXTRA_MODEL_CALL'
        return json.dumps(self.answers.pop(0))


def fixture():
    return {
        'program': {'problem_id': 'P0', 'criteria': 'New discriminating mechanism'},
        'assets': [
            {'id': 'A_CARRY_1', 'kind': 'HYPOTHESIS',
             'origin': 'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK',
             'claim': 'A charge-transfer mechanism', 'scope': 'single molecule',
             'assumptions': 'requires fixed occupancy', 'parent_ids': [],
             'source_ids': ['SRC_RECEIPT'], 'source_evidence_classes': [],
             'limitations': 'unknown hotspot stability'},
            {'id': 'A_LIVE_2', 'kind': 'NULL_MODEL', 'claim': 'orientation alternative',
             'origin': 'LIVE_WORK', 'parent_ids': [], 'source_ids': [],
             'limitations': 'may be observationally equivalent'}
        ],
        'problems': [
            {'id': 'P0', 'question': 'Can an AI discover a falsifiable SERS mechanism?',
             'parents': [], 'status': 'OPEN'},
            {'id': 'P_HISTORY', 'question': 'Does bounded null mimic charge switching?',
             'parents': ['P0'], 'status': 'OPEN'},
        ],
        'm23_root_scoped_asset_namespace': {
            'scope': 'CURRENT_ROOT_ONLY',
            'canonical_asset_ids': ['A_CARRY_1', 'A_LIVE_2'],
            'verified_original_to_canonical': {
                'A_OLD_1': {'canonical_id': 'A_CARRY_1',
                            'receipt_source_id': 'SRC_RECEIPT',
                            'supporting_receipt_source_ids': ['SRC_RECEIPT']}
            },
            'instructions': 'Use current-root IDs',
        }
    }


class M233Tests(unittest.TestCase):
    def test_default_mode_full_preserved(self):
        with patch.dict(os.environ, {'M233_MODEL_METADATA_MODE': 'FULL'}):
            self.assertEqual(verify_metadata_mode(StubJournal(), 'ON_DEMAND'), FULL)

    def test_invalid_mode_rejected(self):
        with patch.dict(os.environ, {'M233_MODEL_METADATA_MODE': 'UNSAFE'}):
            with self.assertRaisesRegex(EvidenceError, 'INVALID_MODE'):
                verify_metadata_mode(StubJournal(), 'ON_DEMAND')

    def test_separate_requires_on_demand_and_journal(self):
        with patch.dict(os.environ, {'M233_MODEL_METADATA_MODE': 'SEPARATE'}):
            with self.assertRaisesRegex(EvidenceError, 'REQUIRES_ON_DEMAND'):
                verify_metadata_mode(StubJournal(), 'FULL')
            with self.assertRaisesRegex(EvidenceError, 'JOURNAL_REQUIRED'):
                verify_metadata_mode(None, 'ON_DEMAND')

    def test_sticky_rejects_prior_saved_and_intent(self):
        old = {'messages': [{'role': 'user', 'content': json.dumps({})}]}
        prior = {'OPP_D00001': {'request_blob': json.dumps(old), 'state': 'SAVED'}}
        with patch.dict(os.environ, {'M233_MODEL_METADATA_MODE': 'SEPARATE'}):
            with self.assertRaisesRegex(EvidenceError, 'MODE_DRIFT'):
                verify_metadata_mode(StubJournal(calls=prior), 'ON_DEMAND')
        old['messages'][0]['content'] = json.dumps({MODE_KEY: SEPARATE})
        prior = {'CTRL_D00001': {'request_blob': json.dumps(old), 'state': 'INTENT'}}
        with patch.dict(os.environ, {'M233_MODEL_METADATA_MODE': 'FULL'}):
            with self.assertRaisesRegex(EvidenceError, 'MODE_DRIFT'):
                verify_metadata_mode(StubJournal(calls=prior), 'ON_DEMAND')

    def test_separate_projection_exact_science_and_roundtrip(self):
        from e2core.m232_ondemand import DetailSession
        full = fixture()
        before = copy.deepcopy(full)
        session = DetailSession(full, 'OPPORTUNITY')
        self.assertTrue(session.verify_all_reconstructable())
        view = session.model_input()
        projected = compact_presentation_metadata(view)
        self.assertEqual(full, before)
        self.assertEqual(restore_from_unmodified_view(view, projected), view)
        self.assertEqual(projected[MODE_KEY], SEPARATE)
        self.assertEqual(projected[CONTRACT_KEY]['indexed_asset_count'], 1)
        self.assertEqual(projected[CONTRACT_KEY]['indexed_problem_count'], 1)
        a = projected['assets'][0]
        p = projected['problems'][1]
        self.assertIs(a[VIEW_KEY], True)
        self.assertIs(p[VIEW_KEY], True)
        self.assertNotIn('m232_original_sha256', a)
        self.assertNotIn('m232_detail_level', a)
        self.assertEqual(a['claim'], 'A charge-transfer mechanism')
        self.assertEqual(p['question'], 'Does bounded null mimic charge switching?')
        self.assertEqual(projected['assets'][1], view['assets'][1])
        self.assertEqual(projected['problems'][0], view['problems'][0])
        self.assertEqual(projected['program'], view['program'])

    def test_index_tag_hash_must_remain_consistent(self):
        from e2core.m232_ondemand import DetailSession
        view = DetailSession(fixture(), 'CONTROLLER').model_input()
        view['assets'][0].pop('m232_original_sha256')
        with self.assertRaisesRegex(EvidenceError, 'INCONSISTENT_INDEX_MARKERS'):
            compact_presentation_metadata(view)

    def test_indexedness_cannot_be_silently_lost(self):
        from e2core.m232_ondemand import DetailSession
        view = DetailSession(fixture(), 'CONTROLLER').model_input()
        view['assets'][0]['m232_detail_level'] = 'UNRECOGNIZED'
        with self.assertRaisesRegex(EvidenceError, 'UNRECOGNIZED_INDEX_TAG'):
            compact_presentation_metadata(view)

    def test_real_on_demand_assessor_one_call_and_contract(self):
        model = MockModel([{'opportunities': []}])
        j = StubJournal()
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE': 'COMPACT',
                                     'M233_MODEL_METADATA_MODE': 'SEPARATE'}):
            _, ident, trace = assessor_call(model, j, 'OPP_D1', 'Prompt',
                                            fixture(), 'OPPORTUNITY', mode=ON_DEMAND)
        self.assertEqual(ident, 'OPP_D1')
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(trace['finished'])
        payload = model.calls[0]['payload']
        self.assertIs(payload['assets'][0][VIEW_KEY], True)
        self.assertNotIn('m232_original_sha256', payload['assets'][0])
        self.assertNotIn('verified_original_to_canonical',
                         payload['m23_root_scoped_asset_namespace'])
        self.assertIn('NEVER create a Problem ID', model.calls[0]['prompt'])

    def test_model_requested_full_details_restores_science(self):
        model = MockModel([
            {'m232_action': 'REQUEST_FULL_CONTEXT',
             'reason': 'Need source detail and strongest physical counterexample'},
            {'opportunities': []},
        ])
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE': 'COMPACT',
                                     'M233_MODEL_METADATA_MODE': 'SEPARATE'}):
            _, cid, trace = assessor_call(model, StubJournal(), 'OPP_D2', 'Prompt',
                                          fixture(), 'OPPORTUNITY', mode=ON_DEMAND)
        self.assertEqual(cid, 'OPP_D2_M232R0001')
        self.assertEqual(len(model.calls), 2)
        second = model.calls[1]['payload']
        self.assertEqual(second['assets'][0]['limitations'], 'unknown hotspot stability')
        self.assertNotIn(VIEW_KEY, second['assets'][0])
        self.assertNotIn(VIEW_KEY, second['problems'][1])
        self.assertIn('verified_original_to_canonical',
                      second['m23_root_scoped_asset_namespace'])
        self.assertTrue(trace['finished'])

    def test_reference_failure_is_specific_and_never_corrected(self):
        j = StubJournal()
        response = {'new_problems': [], 'actions': [
            {'operation': 'DEVELOP', 'asset_ids': ['A_CARRY_c0c1e0fd8131939f7a6da5d'],
             'work': {'id': 'W_DEVELOP_EXACT_MATCHED_SERS_BENCHMARK_001',
                      'mode': 'INFORMED',
                      'problem_id': 'P_CARRY_c0c1e0fd8131939f7a6da5d'}}]}
        before = copy.deepcopy(response)
        d = reference_failure_diagnostic(j, response, 'BAD_WORK')
        self.assertEqual(d['diagnostic_kind'], 'UNREGISTERED_WORK_PROBLEM_ID')
        self.assertTrue(d['referential_errors'][0]['same_suffix_asset_exists'])
        self.assertEqual(d['referential_errors'][0]['same_suffix_asset_id'],
                         'A_CARRY_c0c1e0fd8131939f7a6da5d')
        self.assertEqual(before, response)
        self.assertIsNone(reference_failure_diagnostic(j, response, 'OTHER_REASON'))

    def test_new_problem_in_same_response_is_not_wrong_reference(self):
        j = StubJournal()
        response = {'new_problems': [{'id': 'P_NEW', 'question': 'New subproblem'}],
                    'actions': [{'work': {'id': 'W_NEW', 'problem_id': 'P_NEW'}}]}
        d = reference_failure_diagnostic(j, response, 'BAD_WORK')
        self.assertEqual(d['diagnostic_kind'], 'OTHER_BAD_WORK_CONDITION')
        self.assertEqual(d['referential_errors'], [])

    def test_work_prompt_does_not_force_p0_or_edit_science(self):
        self.assertIn('EXACT current-root', WORK_REFERENCE_ADDENDUM)
        self.assertIn('NEVER create a Problem ID', WORK_REFERENCE_ADDENDUM)
        self.assertIn('does NOT require', WORK_REFERENCE_ADDENDUM)

if __name__ == '__main__':
    unittest.main()
