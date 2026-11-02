import copy
import unittest
from e2core.m232_partb import (project_context, expand_context, audit_shadow,
                              ShadowProjectionError, TAG)

class M232PartBShadowTests(unittest.TestCase):
    def context(self):
        return {
            'program':{'problem':'P0 original and immutable'},
            'assets':[
                {'id':'A_OLD','kind':'COUNTEREXAMPLE','claim':'adversarial null',
                 'scope':'finite exposure', 'origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK',
                 'parent_ids':[],'source_ids':['SRC_01'],'source_evidence_classes':{'SRC_01':'OA_FULLTEXT_TEXT'},
                 'status':'PROPOSED','predictions':['negative evidence'],
                 'limitations':['a serious limitation'], 'assumptions':'A', 'delta_from_parents':'D'},
                {'id':'A_LIVE','kind':'HYPOTHESIS','claim':'new hypothesis',
                 'scope':'live', 'origin':'LIVE_WORK','parent_ids':['A_OLD'],
                 'source_ids':[],'status':'PROPOSED', 'predictions':['P']},
                {'id':'A_OTHER','kind':'NULL_MODEL','claim':'other null',
                 'scope':'alternate mechanism','origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK',
                 'parent_ids':[],'source_ids':[],'limitations':['missing nuisance']},
            ],
            'problems':[
                {'id':'P0','question':'original','parents':[],'status':'OPEN'},
                {'id':'P_OLD','question':'old unresolved','parents':['P0'],'scope':'far',
                 'decomposition_rationale':'detailed explanation'}],
            'm23_root_scoped_asset_namespace':{'canonical_asset_ids':['A_OLD','A_LIVE','A_OTHER'],
                'verified_original_to_canonical':{'old':{'canonical_id':'A_OLD','receipt_source_id':'SRC_REC'}}},
            'm231_current_root_work_source_contract':{'registered_source_count':2},
            'objective_assessments':[{'supporting_asset_ids':[]}],
        }
    def test_roundtrip_complete_and_immutable(self):
        ctx=self.context();original=copy.deepcopy(ctx)
        p=project_context(ctx);report=audit_shadow(ctx,p)
        self.assertEqual(original,ctx)
        self.assertTrue(report['full_roundtrip_exact'])
        self.assertTrue(report['asset_ids_preserved'])
        self.assertEqual(report['index_assets'],2)
        self.assertEqual(report['full_assets'],1)
        self.assertEqual(p['program'],ctx['program'])
        self.assertEqual(p['problems'][0],ctx['problems'][0])
        self.assertEqual(p['m23_root_scoped_asset_namespace'],ctx['m23_root_scoped_asset_namespace'])
    def test_direct_request_can_expand_any_old_asset(self):
        ctx=self.context();p=project_context(ctx)
        q=expand_context(ctx,p,asset_ids=['A_OTHER'],problem_ids=['P_OLD'])
        self.assertEqual(q['assets'][2],ctx['assets'][2])
        self.assertEqual(q['problems'][1],ctx['problems'][1])
        self.assertEqual(q['assets'][0][TAG],'INDEX_ONLY_NOT_FULL_SCIENTIFIC_EVIDENCE')
    def test_all_records_can_be_requested_without_quota(self):
        ctx=self.context();p=project_context(ctx)
        q=expand_context(ctx,p,asset_ids=[x['id'] for x in ctx['assets']],
                         problem_ids=[x['id'] for x in ctx['problems']])
        for field in ('assets','problems'):
            self.assertEqual(q[field],ctx[field])
    def test_unknown_ids_fail_closed(self):
        ctx=self.context()
        with self.assertRaisesRegex(ShadowProjectionError,'UNKNOWN_ASSET'):
            project_context(ctx,expanded_asset_ids=['A_FORGED'])
        with self.assertRaisesRegex(ShadowProjectionError,'UNKNOWN_PROBLEM'):
            project_context(ctx,expanded_problem_ids=['P_FORGED'])
    def test_mutated_index_does_not_reexpand(self):
        ctx=self.context();p=project_context(ctx)
        p['assets'][0]['claim']='unsupported new claim'
        with self.assertRaisesRegex(ShadowProjectionError,'TAMPER'):
            expand_context(ctx,p,asset_ids=['A_OLD'])
    def test_peer_aliases_stay_untouched(self):
        ctx=self.context();p=project_context(ctx)
        assert p['m23_root_scoped_asset_namespace']==ctx['m23_root_scoped_asset_namespace']
        assert p['m231_current_root_work_source_contract']==ctx['m231_current_root_work_source_contract']
    def test_p0_never_indexed(self):
        p=project_context(self.context())
        self.assertNotIn(TAG,p['problems'][0])
    def test_complete_history_is_not_full_by_default(self):
        p=project_context(self.context())
        self.assertEqual(p['assets'][0]['claim'],'adversarial null')
        self.assertEqual(p['assets'][0]['source_ids'],['SRC_01'])
        self.assertNotIn('limitations',p['assets'][0])
        self.assertTrue(p['m232_shadow_projection']['indexed_assets_have_omitted_assumptions_predictions_limitations_delta'])

if __name__=='__main__':unittest.main()
