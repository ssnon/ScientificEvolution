#!/usr/bin/env python3
"""Offline regression for long-horizon nested V4 advisory accumulation.

No file system writes to research journals and no provider/network calls.
"""
from __future__ import annotations
import copy
import unittest
import memory_bridge as m
import science_frontier as sf


class LongRunningAttentionRegression(unittest.TestCase):
    def test_nested_handoff_preserves_all_science_refs_and_runnable_work(self):
        records=[]
        for n in range(17):
            records.append({'asset_id':f'A_PAST_{n}', 'relation':'NOT_FOUND_IN_INSPECTED_SCOPE',
                'evidence_ids':[f'SRC_STUDY_{n}_{k}' for k in range(3)],
                'residual_hypothesis':'This mechanism remains conditional and undecided. '*20,
                'specific_differentiating_prediction':'Independent occupancy and polarization test. '*20,
                'decisive_test':'Pre-calibrated reporter intervention. '*20})
        impacts=[{'asset_id':r['asset_id'],'relation_to_p0':'CONDITIONAL',
                  'evidence_ids':r['evidence_ids'],
                  'impact_on_solution':'Provisional only; no certificate. '*20} for r in records]
        active=[{'work_id':'W_ACTIVE_1','mode':'INFORMED','status':'ACTIVE',
                 'question':'Test one specific nonredundant physics mechanism',
                 'published_count':2,'steps':7}]
        handoff={'status':'LAST_COMMITTED_MODEL_ADVISORY_NOT_VERIFIED_SCIENCE',
            'controller_decision':'D00003','model_assessment_only':True,
            'original_problem_immutable':True,
            'relevant_parent_asset_ids':['A_PARENT_1','A_PARENT_2'],
            'working_problem_interpretation':{'state':'OPEN','original_problem_still_open':True},
            'novelty_claim_rows':records,'claim_to_original_problem':impacts,
            'recent_prior_art_assessment_changes':[{'asset_id':'A_PAST_1','change':'NEW_EVIDENCE'}],
            'research_instruction':'Challenge the strongest null scientifically.'}
        payload={
            'program':{'problem':'SERS blinking question P0'},
            'problems':[{'id':'P0','question':'SERS blinking question P0','parents':[]}]+[
                {'id':f'P{i}','parents':['P0'],'question':'Conditional competing mechanism '*35}
                for i in range(1,118)],
            'assets':[{'id':f'A_{n}','kind':'HYPOTHESIS','claim':'Long science text '*70,
                       'origin':'LIVE_WORK','parent_ids':['A_PARENT_1']}
                      for n in range(50)],
            'v3_science_work_options':{
                'active_scientific_work':active,
                'concurrent_informed_work_is_permitted':True,
                'no_requirement_to_create_work':True,
                'v4_scientific_delta_handoff':handoff},
            'independent_peer_syn_portfolio':[{'peer':'SYN_01','decisions':[]}],
            'claim_prior_art_assessment':{'claim_assessments':[]},
            'problem_level_impact':{'problem_impact':{'state':'UNCHANGED'}}}
        original=copy.deepcopy(payload);hash_before=sf.sha(payload)
        bounded=m.bound_advisor_payload(payload,'OPP_D00004')
        self.assertLessEqual(m.jsize(bounded),86000)
        self.assertEqual(sf.sha(payload),hash_before)
        self.assertEqual(payload,original)
        self.assertEqual([r['id'] for r in bounded['problems']],
                         [r['id'] for r in payload['problems']])
        work=bounded['v3_science_work_options']
        self.assertEqual(work['active_scientific_work'],active)
        h=work['v4_scientific_delta_handoff']
        for name in ('novelty_claim_rows','claim_to_original_problem'):
            self.assertEqual([r['asset_id'] for r in h[name]],
                             [r['asset_id'] for r in handoff[name]])
            self.assertEqual([r['evidence_ids'] for r in h[name]],
                             [r['evidence_ids'] for r in handoff[name]])
        self.assertEqual(h['original_handoff_sha256'],sf.sha(handoff))
        self.assertTrue(h['full_prose_in_original_controller_journal'])
        self.assertEqual(bounded['science_memory_request_receipt']['original_payload_sha256'],hash_before)


if __name__=='__main__':unittest.main(verbosity=2)
