"""No-paid behavioral regression for V1.2 unfinished PEER Work handoff."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'runtime'))
sys.path.insert(0,str(REPO/'AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029'))
import persistent_population as pp
import e2core.math_cycle as math_cycle


class Donor:
    root=Path('/original-v11/CYCLE_000/SYN_01')
    def __init__(self,state):self.state=state
    def verify(self):return self.state

class Destination:
    def __init__(self,state,decision):
        self.state=state
        self.decision=decision
        self.added=[]
    def verify(self):return self.state
    def raw(self,hashval):
        if hashval!='decision-receipt-blob':raise AssertionError('wrong source')
        return json.dumps(self.decision).encode('utf8')
    def add_source(self,*args):self.added.append(args)


class NativeHandoffTests(unittest.TestCase):
    def fixture(self):
        ds=types.SimpleNamespace(
           program={'problem':'same P0'},
           work={
              'W_REASSESS':{
                 'id':'W_REASSESS','status':'ACTIVE','mode':'INFORMED','operation':'DEVELOP',
                 'question':'Reassess review; no compelled answer','asset_input_ids':['A_BASE'],
                 'published':[],'steps':[]},
              'W_UNFINISHED_SCIENCE':{
                 'id':'W_UNFINISHED_SCIENCE','status':'ACTIVE','mode':'INFORMED','operation':'DEVELOP',
                 'question':'Evaluate matched null','asset_input_ids':['A_BASE'],
                 'published':['A_NEW'],'steps':[{'kind':'MODEL_RESPONSE'}]},
              'W_REVIEW_DONE':{
                 'id':'W_REVIEW_DONE','status':'DONE','mode':'INFORMED','operation':'VERIFY',
                 'question':'Review already done','published':[],'steps':[]},
             },assets={'A_BASE':{},'A_NEW':{}},model_calls={})
        destination=Destination(types.SimpleNamespace(
          program={'problem':'same P0'},
          sources={'SRC_PEER_DECISION_SYN_01':{'blob':'decision-receipt-blob'}},
          assets={'A_BASE':{},'A_PEER_NEW':{}}),
          {'asset_id_translation':{'A_NEW':'A_PEER_NEW'}})
        receipt={'head_sha256':'correct-hash','decision_receipt':'SRC_PEER_DECISION_SYN_01'}
        donor=Donor(ds)
        return donor,ds,destination,receipt

    def test_open_math_review_and_science_work_remain_historical(self):
        donor,ds,destination,receipt=self.fixture()
        mods=types.SimpleNamespace(sha=lambda v:'receipt-sha',canon=lambda v:json.dumps(v).encode())
        with patch.object(pp,'verify',return_value=(donor,ds)),\
             patch.object(pp,'digest',return_value={'events':42,'head_sha256':'correct-hash'}),\
             patch.object(math_cycle,'pending_math_work',return_value=['W_REASSESS']):
            out=pp._verified_peer_work_frontier(mods,destination,'SYN_01',str(donor.root),receipt)
        self.assertEqual(out['pending_math_count'],1)
        self.assertEqual(out['unfinished_work_count'],2)
        self.assertEqual(len(destination.added),1)
        sid,kind,record,_=destination.added[0]
        self.assertEqual(sid,'SRC_PEER_WORK_FRONTIER_SYN_01')
        self.assertEqual(kind,'HISTORICAL_AI')
        self.assertEqual(record['pending_math_review_ids'],['W_REASSESS'])
        self.assertEqual(record['new_model_calls'],0)
        self.assertEqual(record['tool_result']['status'],'HISTORICAL_WORK_STATUS_ONLY_NO_NEW_EXECUTION')
        work=next(v for v in record['unfinished_works'] if v['original_work_id']=='W_UNFINISHED_SCIENCE')
        self.assertEqual(work['mapped_current_root_asset_ids'],['A_PEER_NEW'])
        self.assertTrue(work['historical_not_runnable_current_root'])
        self.assertTrue(work['not_a_math_certificate_or_scientific_hold'])

    def test_unknown_asset_mapping_rejected_without_source(self):
        donor,ds,destination,receipt=self.fixture()
        destination.decision['asset_id_translation']={}
        mods=types.SimpleNamespace(sha=lambda v:'receipt-sha',canon=lambda v:json.dumps(v).encode())
        with patch.object(pp,'verify',return_value=(donor,ds)),\
             patch.object(pp,'digest',return_value={'events':42,'head_sha256':'correct-hash'}),\
             patch.object(math_cycle,'pending_math_work',return_value=['W_REASSESS']):
            with self.assertRaisesRegex(RuntimeError,'PEER_HANDOFF_MAPPED_ASSET_NOT_REGISTERED'):
                pp._verified_peer_work_frontier(mods,destination,'SYN_01',str(donor.root),receipt)
        self.assertFalse(destination.added)

    def test_original_peer_head_mismatch_rejected(self):
        donor,ds,destination,receipt=self.fixture()
        receipt['head_sha256']='incorrect'
        mods=types.SimpleNamespace(sha=lambda v:'receipt-sha',canon=lambda v:json.dumps(v).encode())
        with patch.object(pp,'verify',return_value=(donor,ds)),\
             patch.object(pp,'digest',return_value={'events':42,'head_sha256':'correct-hash'}),\
             patch.object(math_cycle,'pending_math_work',return_value=[]):
            with self.assertRaisesRegex(RuntimeError,'PEER_HANDOFF_HEAD_MISMATCH'):
                pp._verified_peer_work_frontier(mods,destination,'SYN_01',str(donor.root),receipt)
        self.assertFalse(destination.added)

if __name__=='__main__':unittest.main()
