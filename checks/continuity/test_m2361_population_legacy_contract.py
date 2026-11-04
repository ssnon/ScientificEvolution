"""No-paid native compatibility integration. All Journals are temporary fixtures."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import population_resume as compat
import scientific_problem_evolution as spe
from e2core.core import EvolutionJournal, EvidenceError, sha, canon

class M2361PopulationLegacyContract(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix='m2361_legacy_nopaid_')
        self.addCleanup(t.cleanup)
        self.j=EvolutionJournal(Path(t.name)/'POPULATION')
        self.j.init('Synthetic P0 for lineage and source permission checks only')
        self.j.evolve('EV_SEED','FRESH',[],{
            'id':'W_SEED','mode':'FRESH','problem_id':'P0',
            'question':'Synthetic seed','research_rationale':'Synthetic isolation fixture',
            'source_ids':[]},'Synthetic seed')
        self.j.start('W_SEED')
        self.j.step('W_SEED','MODEL_RESPONSE',{'text':'Synthetic model result'})
        self.j.asset('A_SEED','W_SEED','HYPOTHESIS','P0',
                     'Synthetic seed claim','Synthetic assumption','Synthetic scope')
        self.j.finish('W_SEED','RETURN','Synthetic completion')
        source='SRC_PEER_ASSET_FIXTURE'
        a={'id':'A_FAKE_UPSTREAM','claim':'Synthetic peer finding','kind':'HYPOTHESIS'}
        self.j.add_source(source,'HISTORICAL_AI',{
            'kind':'PEER_RESEARCH_RESULT_HISTORICAL_AI_NOT_NEW_EXECUTION',
            'verification':'SAVED_WORKER_MODEL_CALL_AND_ORIGIN_STEP_MATCHED',
            'not_primary_literature':True,'original_asset':a,
            'original_asset_sha256':sha(canon(a)),
            'original_root':'/synthetic/upstream',
            'original_asset_id':a['id'],
        },'Synthetic peer asset, NOT empirical evidence')
        self.j.add_source('SRC_OTHER_AUDIT','EXTERNAL_AUDIT',
                          {'scope':'Different work; no citation permission'},
                          'Not authorized for synthetic worker')
        self.j.evolve('EV_DEV','DEVELOP',['A_SEED'],{
            'id':'W_DEV','mode':'INFORMED','problem_id':'P0',
            'question':'Synthetic informed followup','research_rationale':'Synthetic test',
            'source_ids':[source]},'Synthetic followup')
        self.j.start('W_DEV')
        # One actual rejected authored proposal in a synthetic Journal;
        # restoration must reveal this only in the owning Work.
        proposal={
            'scientific_text':'Synthetic','next_action':'CONTINUE',
            'assets':[{'id':'A_REJECTED','kind':'HYPOTHESIS','problem_id':'P0',
                       'claim':'Synthetic invalid reference','assumptions':'toy',
                       'scope':'toy','predictions':[],'limitations':[],
                       'source_ids':['SRC_OTHER_AUDIT'],'parent_ids':['A_SEED'],
                       'delta_from_parents':'Synthetic delta'}],
            'new_problems':[],'tool_request':None,
        }
        self.j.step('W_DEV','MODEL_RESPONSE',{'text':json.dumps(proposal)})
        self.j.step('W_DEV','OUTPUT_VALIDATION',{
            'status':'REJECTED','rejected':[{
                'kind':'ASSET','index':0,'error':'ASSET_UNAUTHORIZED_SOURCE'}]})
        self.mods=SimpleNamespace(spe=spe,sha=sha,canon=canon)

    def test_legacy_bridge_delivers_all_four_native_contracts(self):
        before=self.j._events()
        original=spe._ORIGINAL_WORKER_INPUT
        with compat.historical_input_compat(self.mods,self.j.root):
            payload=spe._ORIGINAL_WORKER_INPUT(self.j,'W_DEV','NATIVE_RESEARCH_TOOLS')
        self.assertIs(spe._ORIGINAL_WORKER_INPUT,original)
        self.assertEqual(before,self.j._events())
        hist=payload['pinned_input']['authorized_historical_records']
        self.assertEqual(len(hist),1)
        self.assertEqual(hist[0]['id'],'SRC_PEER_ASSET_FIXTURE')
        self.assertEqual(payload['m23_asset_publication_source_contract']['scope'],'CURRENT_WORK_ASSET_PUBLICATION')
        citable=payload['m23_asset_publication_source_contract']['citable_source_ids']
        self.assertIn('SRC_PEER_ASSET_FIXTURE',citable)
        self.assertNotIn('SRC_OTHER_AUDIT',citable)
        parents=payload['m236_parent_reference_contract']['allowed_registered_parent_ids']
        self.assertEqual(parents,['A_SEED'])
        self.assertEqual(payload['m236_metadata_repair_context']['repair_notice_count'],0)
        rejected=payload['m235_own_lineage_feedback']['rejected_asset_events']
        self.assertEqual(len(rejected),1)
        self.assertEqual(rejected[0]['model_asset_id'],'A_REJECTED')
        self.assertEqual(rejected[0]['error'],'ASSET_UNAUTHORIZED_SOURCE')

    def test_source_validator_still_rejects_unpinned_external_audit(self):
        self.j.step('W_DEV','MODEL_RESPONSE',{'text':'Synthetic invalid citation attempt'})
        before=len(self.j._events())
        with self.assertRaisesRegex(EvidenceError,'ASSET_UNAUTHORIZED_SOURCE'):
            self.j.asset('A_UNAUTHORIZED','W_DEV','HYPOTHESIS','P0',
                'Claim that must not be registered','Synthetic','Synthetic',
                parent_ids=['A_SEED'],delta_from_parents='Toy delta',
                source_ids=['SRC_OTHER_AUDIT'])
        self.assertEqual(len(self.j._events()),before)
        self.assertNotIn('A_UNAUTHORIZED',self.j.verify().assets)

    def test_fresh_remains_uninformed_and_compat_does_not_leak(self):
        self.j.evolve('EV_BLIND','FRESH',[],{
            'id':'W_BLIND','mode':'FRESH','problem_id':'P0',
            'question':'Fresh synthetic','research_rationale':'Fresh isolated',
            'source_ids':[]},'Synthetic independent')
        self.j.start('W_BLIND')
        original=spe._ORIGINAL_WORKER_INPUT
        with compat.historical_input_compat(self.mods,self.j.root):
            payload=spe._ORIGINAL_WORKER_INPUT(self.j,'W_BLIND','NATIVE_RESEARCH_TOOLS')
        self.assertIs(spe._ORIGINAL_WORKER_INPUT,original)
        self.assertNotIn('authorized_historical_records',payload['pinned_input'])
        self.assertEqual(payload['m236_parent_reference_contract']['allowed_registered_parent_ids'],[])
        self.assertNotIn('SRC_PEER_ASSET_FIXTURE',json.dumps(payload))
        self.assertNotIn('A_SEED',json.dumps(payload))

if __name__=='__main__':unittest.main()
