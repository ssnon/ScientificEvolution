"""M23.2 read-only select-or-act protocol. No provider or existing Journal IO."""
import unittest
from copy import deepcopy
from e2core.m232_ondemand import (
    DetailSession, DetailProtocolError, PROTOCOL, single_or_multi_turn_input_bytes,
)


def fixture():
    assets=[]
    for i in range(9):
        assets.append({
            'id': f'A{i}', 'origin':'LIVE_WORK' if i==8 else 'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK',
            'kind':'HYPOTHESIS' if i%2 else 'COUNTEREXAMPLE', 'claim':f'mechanism {i}',
            'scope': 'limited', 'status':'PROPOSED','source_ids':['SRC_EXACT'],
            'parent_ids':[f'A{i-1}'] if i else [],
            'source_evidence_classes':{'SRC_EXACT':'BIBLIOGRAPHIC_METADATA'},
            'predictions':[f'prediction {i}'], 'limitations':[f'limitation {i}'],
            'assumptions': f'assumption {i}', 'delta_from_parents':f'delta {i}',
        })
    return {
        'program':{'problem':'P0 immutable','criteria':'Scientific objective'},
        'assets':assets,
        'problems':[{'id':'P0','question':'P0 immutable','parents':[], 'status':'OPEN'},
                    {'id':'P1','question':'counterexample','parents':['P0'], 'status':'OPEN',
                     'decomposition_rationale':'rationale'}],
        'm23_root_scoped_asset_namespace':{
            'verified_original_to_canonical':{'PRIOR_A1':{'canonical_id':'A1','receipt_source_id':'S1'}}},
    }


class M232OnDemandTests(unittest.TestCase):
    def test_first_call_can_be_native_opportunity_without_extra_triage(self):
        s=DetailSession(fixture(),'OPPORTUNITY')
        reply={'opportunities':[],'global_uncertainties':[],'limitations':'No action justified'}
        out=s.process(reply)
        self.assertEqual(out['status'],'NATIVE_ASSESSMENT_NEEDS_ORIGINAL_VALIDATOR')
        self.assertTrue(out['advisory_coverage']['finished'])
        with self.assertRaisesRegex(DetailProtocolError,'SESSION_ALREADY_FINISHED'):
            s.model_input()

    def test_controller_native_reply_stays_unmodified(self):
        s=DetailSession(fixture(),'CONTROLLER')
        ans={'rationale':'uncertain', 'actions':[], 'disposition':'UNRESOLVED'}
        self.assertEqual(s.process(ans)['model_authored_answer'],ans)

    def test_two_model_authored_requests_retrieve_exact_arbitrary_assets(self):
        f=fixture()
        s=DetailSession(f,'OPPORTUNITY')
        before=s.model_input()
        self.assertTrue(s.verify_all_reconstructable())
        response={'m232_action':'REQUEST_DETAILS','asset_ids':['A0','A1'],
                  'problem_ids':['P1'], 'reason':'Need counterexample and parent'}
        s.process(response)
        s.process({'m232_action':'REQUEST_DETAILS','asset_ids':['A2','A3','A4','A5','A6','A7'],
                   'reason':'Independent competing mechanisms'})
        after=s.model_input()
        self.assertEqual(after['assets'],f['assets'])
        self.assertEqual(after['problems'],f['problems'])
        self.assertTrue(s.verify_all_reconstructable())
        self.assertEqual(before['m23_root_scoped_asset_namespace'],after['m23_root_scoped_asset_namespace'])
        self.assertEqual([r['event'] for r in s.status()['request_events']],
                         ['MODEL_REQUESTED_DETAIL_EXPANSION']*2)

    def test_full_expansion_has_no_artificial_quota(self):
        s=DetailSession(fixture(),'CONTROLLER')
        out=s.process({'m232_action':'REQUEST_FULL_CONTEXT','reason':'Inspect all nulls'})
        self.assertEqual(out['retrieval_trace']['indexed_asset_count'],0)
        self.assertEqual(out['retrieval_trace']['indexed_problem_count'],0)
        self.assertTrue(s.verify_all_reconstructable())

    def test_unknown_and_duplicate_rejected_without_view_change(self):
        s=DetailSession(fixture(),'OPPORTUNITY')
        h=s.status()['current_projection_sha256']
        for bad in (
            {'m232_action':'REQUEST_DETAILS','asset_ids':['UNKNOWN'], 'reason':'x'},
            {'m232_action':'REQUEST_DETAILS','asset_ids':['A1','A1'], 'reason':'x'},
            {'m232_action':'REQUEST_DETAILS','asset_ids':[], 'reason':'x'},
            {'m232_action':'REQUEST_DETAILS','asset_ids':['A2'], 'reason':''},
            {'m232_action':'SILENT_DROP','asset_ids':['A1'], 'reason':'x'},
        ):
            with self.assertRaises(DetailProtocolError): s.process(bad)
        self.assertEqual(h,s.status()['current_projection_sha256'])

    def test_requesting_already_expanded_rejected(self):
        s=DetailSession(fixture(),'OPPORTUNITY')
        with self.assertRaisesRegex(DetailProtocolError,'NO_NEW_DETAIL_REQUESTED'):
            s.process({'m232_action':'REQUEST_DETAILS', 'asset_ids':['A8'], 'reason':'Already live'})

    def test_wrong_stage_and_final_bad_schema_rejected(self):
        with self.assertRaises(DetailProtocolError):DetailSession(fixture(),'WORKER')
        s=DetailSession(fixture(),'OPPORTUNITY')
        with self.assertRaises(DetailProtocolError):s.process({'actions':[], 'disposition':'ONGOING'})

    def test_full_context_preserved_and_immutable(self):
        f=fixture()
        snapshot=deepcopy(f)
        s=DetailSession(f,'CONTROLLER')
        f['assets'][0]['claim']='externally-mutated'
        self.assertTrue(s.verify_all_reconstructable())
        self.assertEqual(snapshot['assets'][0]['claim'],s.process({
            'm232_action':'REQUEST_DETAILS','asset_ids':['A0'],
            'reason':'Retrieve original'} )['view']['assets'][0]['claim'])

    def test_read_projections_cannot_silent_rewrite_original_p0(self):
        s=DetailSession(fixture(),'CONTROLLER')
        v=s.model_input()
        v['program']['problem']='altered'
        self.assertEqual('P0 immutable',s.model_input()['program']['problem'])

    def test_adaptive_request_has_cost_before_final(self):
        f=fixture()
        one=single_or_multi_turn_input_bytes(f)
        with_more=single_or_multi_turn_input_bytes(f,requests=[
            {'m232_action':'REQUEST_DETAILS','asset_ids':['A1'], 'reason':'compare'}])
        self.assertEqual(len(one['adaptive_input_bytes_by_turn']),1)
        self.assertEqual(len(with_more['adaptive_input_bytes_by_turn']),2)
        self.assertGreater(with_more['adaptive_input_bytes_total'],one['adaptive_input_bytes_total'])
        self.assertTrue(one['not_token_or_actual_cost_estimate'])

    def test_contract_declares_shadow_only_and_native_validation(self):
        s=DetailSession(fixture(),'OPPORTUNITY')
        view=s.model_input()
        self.assertEqual(view['m232_model_detail_request_contract']['protocol'],PROTOCOL)
        self.assertIn('NOT_ENABLED_FOR_PAID',view['m232_model_detail_request_contract']['status'])
        self.assertTrue(view['m232_model_detail_request_contract']['final_scientific_answer_remains_subject_to_existing_native_validator'])

if __name__=='__main__':unittest.main()
