"""No-network fail-closed namespace compaction integration tests."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from e2core.core import EvidenceError, EvolutionJournal
from e2core.m232_live import assessor_call, selected_mode, ON_DEMAND, FULL
from e2core.m232_namespace import (COMPACT, MODE_KEY, VIEW_KEY,
    compact_payload, verify_mode, full_after_request)


class MockModel:
    mode = 'MOCK'
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
    def call(self, ident, actor, work_id, system, payload):
        self.calls.append({'id': ident, 'payload': copy.deepcopy(payload)})
        if not self.responses:
            raise AssertionError('NO_UNEXPECTED_MODEL_CALLS')
        return json.dumps(self.responses.pop(0))


class StubJournal:
    def verify(self):
        return SimpleNamespace(sources={'SRC_RECEIPT': {'kind': 'HISTORICAL_AI'}}, model_calls={})


def fixture():
    return {
        'program': {'problem':'P0'},
        'assets':[
            {'id':'A_CARRY_1', 'kind':'NULL_MODEL',
             'claim':'A stringent null', 'predictions':['no separation'],
             'limitations':['unidentified latent field'], 'parent_ids':[],
             'origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK', 'source_ids':['SRC_RECEIPT']},
            {'id':'A_LIVE_2', 'kind':'HYPOTHESIS',
             'claim':'An alternative', 'predictions':['spectrum change'],
             'limitations':['confound'], 'parent_ids':[], 'origin':'LIVE_WORK',
             'source_ids':[]},
        ],
        'problems': [{'id':'P0', 'question':'Unresolved original problem','parents':[]}],
        'm23_root_scoped_asset_namespace': {
            'scope':'CURRENT_ROOT_ONLY',
            'canonical_asset_ids':['A_CARRY_1','A_LIVE_2'],
            'verified_original_to_canonical':{
                'A_OLD_1': {'canonical_id':'A_CARRY_1',
                            'receipt_source_id':'SRC_RECEIPT',
                            'supporting_receipt_source_ids':['SRC_RECEIPT']}},
            'ambiguous_original_ids_must_not_be_used':[],
            'instructions':'Use canonical IDs',
        },
    }


class NamespaceLiveTests(unittest.TestCase):
    def test_compaction_preserves_every_scientific_field_and_model_mutation_is_avoided(self):
        initial = fixture(); saved = copy.deepcopy(initial)
        compact = compact_payload(initial, {'SRC_RECEIPT'})
        self.assertEqual(initial, saved)
        self.assertEqual(compact['assets'], initial['assets'])
        self.assertEqual(compact['problems'], initial['problems'])
        self.assertNotIn('verified_original_to_canonical',
                         compact['m23_root_scoped_asset_namespace'])
        self.assertNotIn('canonical_asset_ids',
                         compact['m23_root_scoped_asset_namespace'])
        self.assertEqual(compact[MODE_KEY], COMPACT)

    def test_alias_proof_is_required_and_fail_closed(self):
        with self.assertRaisesRegex(EvidenceError,'ALIAS_PROOF_INVALID'):
            compact_payload(fixture(), set())

    def test_invalid_canonical_or_alias_target_rejected(self):
        wrong = fixture()
        wrong['m23_root_scoped_asset_namespace']['canonical_asset_ids']=['A_LIVE_2']
        with self.assertRaisesRegex(EvidenceError,'CANONICAL_ID_MISMATCH'):
            compact_payload(wrong,{'SRC_RECEIPT'})
        wrong = fixture()
        wrong['m23_root_scoped_asset_namespace']['verified_original_to_canonical']['A_OLD_1']['canonical_id']='NONEXISTENT'
        with self.assertRaisesRegex(EvidenceError,'ALIAS_TARGET_NOT_CURRENT'):
            compact_payload(wrong,{'SRC_RECEIPT'})

    def test_default_full_call_unchanged_even_if_no_sources(self):
        model = MockModel([{'opportunities':[]}])
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE':'FULL'}):
            assessor_call(model, None, 'OPP_D9', 'Prompt', fixture(),
                          'OPPORTUNITY', mode=FULL)
        self.assertEqual(model.calls[0]['payload'], fixture())
        self.assertNotIn(MODE_KEY, model.calls[0]['payload'])

    def test_compact_one_call_native_answer_no_hidden_round(self):
        model = MockModel([{'opportunities':[]}])
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE':'COMPACT'}):
            text,ident,trace = assessor_call(model,StubJournal(),'OPP_D1','Prompt',
                fixture(),'OPPORTUNITY',mode=ON_DEMAND)
        self.assertEqual(len(model.calls),1)
        self.assertEqual(ident,'OPP_D1')
        self.assertTrue(trace['finished'])
        self.assertEqual(model.calls[0]['payload'][VIEW_KEY],'CANONICAL_ONLY')
        self.assertNotIn('verified_original_to_canonical',
                         model.calls[0]['payload']['m23_root_scoped_asset_namespace'])

    def test_full_retrieval_restores_alias_map_as_well_as_scientific_assets(self):
        model = MockModel([
            {'m232_action':'REQUEST_FULL_CONTEXT',
             'reason':'Need original IDs and competing hypothesis limitations'},
            {'opportunities':[]},
        ])
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE':'COMPACT'}):
            text,ident,trace = assessor_call(model,StubJournal(),'OPP_D2','Prompt',
                fixture(),'OPPORTUNITY',mode=ON_DEMAND)
        self.assertEqual(len(model.calls),2)
        self.assertEqual(ident,'OPP_D2_M232R0001')
        self.assertEqual(model.calls[1]['payload'][VIEW_KEY],'FULL_AFTER_MODEL_REQUEST')
        self.assertEqual(model.calls[1]['payload']['m23_root_scoped_asset_namespace'],
                         fixture()['m23_root_scoped_asset_namespace'])
        self.assertNotIn('m232_detail_level',
                         model.calls[1]['payload']['assets'][0])

    def test_request_details_keeps_compact_namespace(self):
        model = MockModel([
            {'m232_action':'REQUEST_DETAILS','asset_ids':['A_CARRY_1'],
             'problem_ids':[], 'reason':'Need explicit strong null limitations'},
            {'opportunities':[]},
        ])
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE':'COMPACT'}):
            _,cid,_=assessor_call(model,StubJournal(),'OPP_D3','Prompt',
                fixture(),'OPPORTUNITY',mode=ON_DEMAND)
        self.assertEqual(cid,'OPP_D3_M232R0001')
        self.assertNotIn('verified_original_to_canonical',
                         model.calls[1]['payload']['m23_root_scoped_asset_namespace'])
        self.assertEqual(model.calls[1]['payload']['assets'][0]['limitations'],
                         ['unidentified latent field'])

    def test_mode_change_rejected_in_existing_saved_or_intent_call(self):
        with tempfile.TemporaryDirectory() as td:
            j=EvolutionJournal(Path(td)/'journal');j.init('P0')
            older={'messages':[{'role':'user','content':json.dumps({
                'm232_live_detail_mode':'ON_DEMAND'})}]}
            j.append('MODEL_CALL_INTENT',{
                'id':'OPP_D00001', 'actor':'CONTROLLER', 'work_id':None,
                'request_blob':j.blob(older), 'model':'mock', 'billing_mode':'MOCK'})
            with patch.dict(os.environ,{'M232_NAMESPACE_MODE':'COMPACT',
                  'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND'}):
                with self.assertRaisesRegex(EvidenceError,'MODE_DRIFT'):
                    selected_mode(j,MockModel([]))
            with patch.dict(os.environ,{'M232_NAMESPACE_MODE':'FULL',
                  'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND'}):
                self.assertEqual(selected_mode(j,MockModel([])),ON_DEMAND)

    def test_compact_requires_on_demand(self):
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE':'COMPACT'}):
            with self.assertRaisesRegex(EvidenceError,'REQUIRES_ON_DEMAND'):
                verify_mode(None,'FULL')

    def test_invalid_namespace_mode_rejected(self):
        with patch.dict(os.environ, {'M232_NAMESPACE_MODE':'surprise'}):
            with self.assertRaisesRegex(EvidenceError,'INVALID_MODE'):
                verify_mode(None,'FULL')

    def test_full_request_keeps_all_aliases_and_is_not_altered_by_projection(self):
        p=fixture();before=copy.deepcopy(p)
        full=full_after_request(p)
        self.assertEqual(p,before)
        self.assertEqual(full['m23_root_scoped_asset_namespace'],
                         p['m23_root_scoped_asset_namespace'])
        self.assertEqual(full[MODE_KEY],COMPACT)


if __name__ == '__main__':unittest.main()
