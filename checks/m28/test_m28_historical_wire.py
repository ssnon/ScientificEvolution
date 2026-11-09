"""No-paid regression for M28-A4-0 discovered M28 historical source wire mismatch.

Exercises the existing A1/A2 real-Journal fixtures and the actual Engine Worker
input path. Never treats scripted model claims as scientific discovery.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from e2core.core import EvolutionJournal, EvidenceError, canon, sha
from e2core.engine import Engine, _worker_input
from e2core.meta_collaboration import import_selected
from test_m28_a1 import TestM28A1, _decision, _request, MODE_TARGETED
from test_m28_a2 import TestM28A2, decision


def prepare_challenge(j, asset_id):
    j.evolve('EV_WIRE_GATE','CHALLENGE',[asset_id],
             {'id':'W_WIRE_GATE','mode':'INFORMED','problem_id':'P0',
              'question':'Challenge an explicitly inherited AI claim',
              'research_rationale':'Check a conditional rival explanation',
              'source_ids':[]},'Review a historical claim with its sources')
    return 'W_WIRE_GATE'


class ScriptedWorker:
    def __init__(self,j):
        self.j=j
        self.new_calls=0
    def call(self,ident,actor,work_id,system,payload):
        reply={'scientific_text':'MOCK only: a rival conditional model may exist.',
               'next_action':'RETURN','new_problems':[], 'tool_request':None,
               'assets':[{'id':'A_WIRE_CHALLENGE','kind':'COUNTEREXAMPLE',
                          'problem_id':'P0','claim':'MOCK conditional challenge',
                          'assumptions':'Toy assumptions','scope':'Mock only',
                          'predictions':[],'limitations':['Not demonstrated'],
                          'source_ids':[],
                          'parent_ids':[payload['pinned_input']['parent_assets'][0]['id']],
                          'delta_from_parents':'A conditional alternative is considered.'}]}
        self.j.append('MODEL_CALL_INTENT',{
            'id':ident,'actor':actor,'work_id':work_id,
            'request_blob':self.j.blob({'system':system,'payload':payload}),
            'model':'OFFLINE_SCRIPTED','billing_mode':'MOCK'})
        raw={'choices':[{'message':{'content':json.dumps(reply)}}]}
        self.j.append('MODEL_CALL_SAVED',{
            'id':ident,'response_blob':self.j.blob(raw),'usage':{'cost':0}})
        return json.dumps(reply)


class TestM28HistoricalWire(unittest.TestCase):
    def test_a2_selected_import_is_readable_and_executable_by_informed_worker(self):
        fixture=TestM28A2(methodName='test_child_with_no_work_is_not_auto_imported_or_scientific_report')
        fixture.setUp()
        try:
            cj=fixture.spawn_child()
            fixture.child_work(cj)
            report_id=fixture.report(cj)
            fixture.commit(2,decision(collaboration=[fixture.selection(report_id,['A_child_science'])]))
            imported=import_selected(fixture.exp,fixture.parent)
            self.assertEqual(len(imported),1)
            aid=imported[0]['local_asset_id']
            self.assertEqual(fixture.j.verify().sources[imported[0]['source_id']]['kind'],'HISTORICAL_AI')
            wid=prepare_challenge(fixture.j,aid)
            prompt=_worker_input(fixture.j,wid)
            recs=prompt['pinned_input']['authorized_historical_records']
            self.assertEqual(len(recs),1)
            rec=recs[0]
            self.assertEqual(rec['ref'],str(cj.root)+'#A_child_science')
            self.assertEqual(rec['source_schema'],'M28_A2_MODEL_SELECTED_HISTORICAL_AI')
            self.assertEqual(rec['science']['original_asset']['id'],'A_child_science')
            self.assertEqual(rec['science']['original_source_record']['selected_report_id'],report_id)
            self.assertFalse(rec['science']['scientific_certification'])
            self.assertEqual(rec['tool_status'],'HISTORICAL_AI_IMPORT_NOT_NEW_TOOL_EXECUTION')
            self.assertEqual(rec['source_blob_sha256'],fixture.j.verify().sources[imported[0]['source_id']]['blob'])
            out=Engine(fixture.j,ScriptedWorker(fixture.j)).worker_step(wid)
            self.assertIn('A_WIRE_CHALLENGE',fixture.j.verify().assets,str(out))
            self.assertEqual(fixture.j.verify().assets['A_WIRE_CHALLENGE']['parent_ids'],[aid])
            self.assertTrue(fixture.j.verify().model_calls['WK_W_WIRE_GATE_00001']['billing_mode']=='MOCK')
        finally:
            fixture.tearDown()

    def test_a1_targeted_source_keeps_not_blind_provenance_in_informed_worker(self):
        fixture=TestM28A1(methodName='test_targeted_challenge_is_not_misrepresented_as_blind')
        fixture.setUp()
        try:
            fixture._add_historical_target()
            fixture._commit(_decision([_request(MODE_TARGETED,['A_target_claim'])]))
            child=EvolutionJournal(fixture._materialize()[0]['root'])
            asset_id=next(iter(child.verify().assets))
            wid=prepare_challenge(child,asset_id)
            recs=_worker_input(child,wid)['pinned_input']['authorized_historical_records']
            self.assertEqual(len(recs),1)
            rec=recs[0]
            self.assertEqual(rec['source_schema'],'M28_A1_TARGETED_HISTORICAL_AI_NOT_BLIND')
            self.assertEqual(rec['science']['original_source_record']['not_blind_independent'],True)
            self.assertEqual(rec['science']['original_asset']['id'],'A_target_claim')
            self.assertEqual(rec['tool_status'],'HISTORICAL_AI_IMPORT_NOT_NEW_TOOL_EXECUTION')
        finally:
            fixture.tearDown()

    def test_original_legacy_historical_ai_wire_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=EvolutionJournal(Path(tmp)/'LEGACY')
            j.init('P0, no facts assumed')
            rec={'ref':'old-root#A0','science':{'scientific_work':'Historic claim'},
                 'tool_result':{'status':'HISTORICAL_ONLY_NO_NEW_TOOL_EXECUTION'},
                 'science_sha256':'a'*64}
            j.add_source('SRC_LEGACY','HISTORICAL_AI',rec,'historic AI source')
            j.append('HISTORICAL_ASSET_INDEXED',{
                'id':'A_LEGACY','kind':'HYPOTHESIS','problem_id':'P0',
                'parent_ids':[],'claim':'Historic claim','scope':'Toy',
                'assumptions':'Assumption','source_ids':['SRC_LEGACY']})
            wid=prepare_challenge(j,'A_LEGACY')
            view=_worker_input(j,wid)['pinned_input']['authorized_historical_records'][0]
            self.assertEqual(view,{'id':'SRC_LEGACY','ref':'old-root#A0',
                'science':rec['science'],'tool_status':rec['tool_result']['status'],
                'science_sha256':rec['science_sha256']})

    def test_unknown_historical_source_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=EvolutionJournal(Path(tmp)/'UNKNOWN')
            j.init('P0, no facts assumed')
            j.add_source('SRC_UNKNOWN','HISTORICAL_AI',{'some_new_format':True},'unrecognized')
            j.append('HISTORICAL_ASSET_INDEXED',{
                'id':'A_UNKNOWN','kind':'HYPOTHESIS','problem_id':'P0',
                'parent_ids':[],'claim':'Unverified claim','scope':'Toy',
                'assumptions':'Unknown','source_ids':['SRC_UNKNOWN']})
            wid=prepare_challenge(j,'A_UNKNOWN')
            with self.assertRaisesRegex(EvidenceError,'UNKNOWN_HISTORICAL_AI_SOURCE_SCHEMA'):
                _worker_input(j,wid)


if __name__=='__main__':unittest.main()
