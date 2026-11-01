"""No-paid real parser/provenance tests for M22 rejected PEER handoff."""
import json
import unittest
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch

from e2core.core import canon, sha
from e2core.peer_rejected_continuity import (
    collect_verified_peer_rejections, PeerRejectedContinuityError)
from e2core.research_continuity import live_opportunities, validate_record

class FakeJ:
    root='/tmp/TEST_M22_PEER_SYN_02'
    def __init__(self,blobs,state):
        self.blobs=blobs;self.state=state
    def raw(self,key):return self.blobs[key]
    def verify(self):return self.state

def fixture():
    response={'scientific_text':'Conditional charge-state and geometry feedback with explicit null comparisons.',
              'next_action':'CONTINUE',
              'new_problems':[{'id':'P1_OWN','question':'Does nuisance explain switching?'}],
              'assets':[{'id':'A_LOCAL','kind':'HYPOTHESIS','claim':'Charge geometry gating',
                         'parent_ids':['A_OTHER_NOT_PINNED']}],
              'tool_request':None}
    authored=json.dumps(response)
    step1={'call_id':'WK_W1_00001','text':authored,'parse_ok':True}
    step2={'status':'PARTIALLY_ACCEPTED','accepted':1,'rejected':[
        {'kind':'ASSET','index':0,'error':'UNAUTHORIZED_ASSET_PARENT'}]}
    digest1=sha(canon(step1)); digest2=sha(canon(step2))
    steps=[{'kind':'MODEL_RESPONSE','step':1,'raw_blob':digest1},
           {'kind':'OUTPUT_VALIDATION','step':2,'raw_blob':digest2}]
    wire=canon({'choices':[{'message':{'content':authored}}]})
    response_wire_sha=sha(wire)
    state=SimpleNamespace(
      work={'W1':{'mode':'INFORMED','status':'ACTIVE','steps':steps,'asset_input_ids':['A_PINNED'],'published':[]}},
      model_calls={'WK_W1_00001':{'state':'SAVED','actor':'WORKER','work_id':'W1',
                                'request_blob':'c'*64,'response_blob':response_wire_sha}})
    j=FakeJ({digest1:canon(step1),digest2:canon(step2),response_wire_sha:wire},state)
    return j,state,response

class Tests(unittest.TestCase):
    def test_authored_rejected_science_is_carried_not_promoted(self):
        j,s,r=fixture()
        rs=collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
        self.assertEqual(len(rs),1)
        oid,op=next(iter(rs.items()))
        self.assertTrue(oid.startswith('OPP_'))
        self.assertEqual(op['status'],'UNREGISTERED_PROPOSAL_REJECTED')
        self.assertEqual(op['original_submission'],r['assets'][0])
        self.assertEqual(op['unregistered_worker_scientific_text'],r['scientific_text'])
        self.assertTrue(op['not_an_asset'])
        self.assertTrue(op['not_a_primary_source'])
        self.assertTrue(op['not_an_accepted_asset'])
        self.assertEqual(op['origin']['original_peer'],'SYN_02')
        validate_record(op)
    def test_original_live_rejection_still_exists(self):
        j,s,_=fixture()
        self.assertEqual(len(live_opportunities(j,s)),1)
    def test_no_accepted_asset_no_opportunity(self):
        j,s,_=fixture();s.work['W1']['steps']=[]
        rs=collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
        self.assertEqual(rs,{})
    def test_wrong_saved_actor_fails_closed(self):
        j,s,_=fixture();s.model_calls['WK_W1_00001']['actor']='CONTROLLER'
        with self.assertRaisesRegex(PeerRejectedContinuityError,'UNSAVED_OR_WRONG_ACTOR'):
            collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
    def test_tampered_step_link_fails_closed(self):
        j,s,_=fixture()
        s.work['W1']['steps'][1]['raw_blob']='b'*64
        with self.assertRaisesRegex(PeerRejectedContinuityError, 'STEP_BLOB_MISSING_OR_INVALID'):
            collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
    def test_tampered_model_response_link_fails_closed(self):
        j,s,_=fixture()
        s.work['W1']['steps'][0]['raw_blob']='b'*64
        with self.assertRaisesRegex(PeerRejectedContinuityError,
                                    'STEP_BLOB_MISSING_OR_INVALID'):
            collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
    def test_validation_link_to_existing_wrong_blob_fails_closed(self):
        j,s,_=fixture()
        s.work['W1']['steps'][1]['raw_blob']=s.work['W1']['steps'][0]['raw_blob']
        with self.assertRaisesRegex(PeerRejectedContinuityError,
                                    'VALIDATION_SHAPE_INVALID'):
            collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
    def test_tampered_existing_blob_bytes_fails_closed(self):
        j,s,_=fixture()
        digest=s.work['W1']['steps'][1]['raw_blob']
        j.blobs[digest]=canon({'status':'PARTIALLY_ACCEPTED','rejected':[]})
        with self.assertRaisesRegex(PeerRejectedContinuityError,
                                    'BLOB_HASH_MISMATCH'):
            collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
    def test_valid_format_repair_validation_without_rejections(self):
        j,s,_=fixture()
        validation={'status':'FORMAT_REPAIR_REQUIRED',
                    'no_tool_executed_from_invalid_response':True}
        blob=canon(validation);digest=sha(blob)
        j.blobs[digest]=blob
        s.work['W1']['steps'][1]['raw_blob']=digest
        self.assertEqual(collect_verified_peer_rejections(
            j,s,'SYN_02','a'*64,sha=sha,canon=canon),{})
    def test_deterministic_id(self):
        j,s,_=fixture()
        x=collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
        y=collect_verified_peer_rejections(j,s,'SYN_02','a'*64,sha=sha,canon=canon)
        self.assertEqual(x,y)
        z=collect_verified_peer_rejections(j,s,'SYN_01','a'*64,sha=sha,canon=canon)
        self.assertNotEqual(set(x),set(z))

if __name__=='__main__':unittest.main()
