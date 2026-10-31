#!/usr/bin/env python3
"""No provider, no WSL Journal mutation, tests exact historical wire replay."""
import hashlib, json, sys, types, unittest
from types import SimpleNamespace
import memory_bridge as mm

class EvidenceError(ValueError):pass

class SavedJournal:
    def __init__(self,ident,actor,work_id,system,payload,model='openai/gpt-5.6-luna',max_tokens=16000):
        self.wire={'model':model,'temperature':0.7,'max_tokens':max_tokens,
            'response_format':{'type':'json_object'},'messages':[
                {'role':'system','content':system},
                {'role':'user','content':json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False)}]}
        self.bytes=json.dumps(self.wire,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        self.digest=hashlib.sha256(self.bytes).hexdigest()
        self.record={'id':ident,'actor':actor,'work_id':work_id,'state':'SAVED','request_blob':self.digest}
    def verify(self):return SimpleNamespace(model_calls={self.record['id']:self.record})
    def raw(self,digest):
        assert digest==self.digest
        return self.bytes

class Gateway:
    def __init__(self,j):self.j=j;self.model='openai/gpt-5.6-luna';self.max_tokens=16000

class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=sys.modules.get('e2core.core')
        sys.modules['e2core.core']=types.SimpleNamespace(EvidenceError=EvidenceError)
    @classmethod
    def tearDownClass(cls):
        if cls.old is None:sys.modules.pop('e2core.core',None)
        else:sys.modules['e2core.core']=cls.old
    def test_saved_compacted_request_replayed_from_same_original_science(self):
        raw={'program':{'problem':'P0'},'active_work':['W_A'],'assets':[{'id':'A_01','claim':'science'}]}
        old_view={'program':raw['program'],'active_work':raw['active_work'],
            'science_memory_request_receipt':{'version':'OLD_V1_1',
                'original_payload_sha256':mm._digest(raw),'original_payload_chars':mm.jsize(raw)}}
        j=SavedJournal('CTRL_D00007','CONTROLLER',None,'Controller protocol',old_view)
        res=mm.replay_payload_for_saved(Gateway(j),'CTRL_D00007','CONTROLLER',None,'Controller protocol',raw)
        self.assertEqual(res,old_view)
        self.assertEqual(j.digest,hashlib.sha256(json.dumps({**j.wire,'messages':[
            {'role':'system','content':'Controller protocol'},
            {'role':'user','content':json.dumps(res,sort_keys=True,ensure_ascii=False,allow_nan=False)}]},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())
    def test_different_science_input_never_replayed(self):
        old_raw={'assets':[{'id':'A_01','claim':'one'}]}
        old_view={'assets':[], 'science_memory_request_receipt':{
            'original_payload_sha256':mm._digest(old_raw)}}
        j=SavedJournal('OPP_D00007','CONTROLLER',None,'Advisor',old_view)
        with self.assertRaisesRegex(EvidenceError,'MODEL_REPLAY_SCIENCE_INPUT_CHANGED:OPP_D00007'):
            mm.replay_payload_for_saved(Gateway(j),'OPP_D00007','CONTROLLER',None,'Advisor',{'assets':[{'id':'A_02'}]})
    def test_system_prompt_difference_never_replayed(self):
        raw={'question':'P0'}
        view={'science_memory_request_receipt':{'original_payload_sha256':mm._digest(raw)}}
        j=SavedJournal('CTRL_D00003','CONTROLLER',None,'Original system prompt',view)
        with self.assertRaisesRegex(EvidenceError,'MODEL_REPLAY_CONTRACT_CHANGED:CTRL_D00003'):
            mm.replay_payload_for_saved(Gateway(j),'CTRL_D00003','CONTROLLER',None,'New system prompt',raw)
    def test_worker_does_not_fake_replay_if_input_changes(self):
        j=SavedJournal('WK_W_A_00007','WORKER','W_A','Worker',{'input':'prior state'})
        with self.assertRaisesRegex(EvidenceError,'MODEL_REPLAY_SCIENCE_INPUT_CHANGED:WK_W_A_00007'):
            mm.replay_payload_for_saved(Gateway(j),'WK_W_A_00007','WORKER','W_A','Worker',{'input':'new state'})
    def test_safely_replay_exact_request_without_receipt(self):
        original={'input':'exact'}
        j=SavedJournal('WK_W_A_00007','WORKER','W_A','Worker',original)
        self.assertEqual(mm.replay_payload_for_saved(Gateway(j),'WK_W_A_00007','WORKER','W_A','Worker',original),original)
    def test_uncertain_outcome_fails_closed(self):
        j=SavedJournal('OPP_D00007','CONTROLLER',None,'Advisor',{'input':'old'})
        j.record['state']='INTENT'
        with self.assertRaisesRegex(EvidenceError,'MODEL_CALL_NOT_SAVED_MANUAL_REVIEW'):
            mm.replay_payload_for_saved(Gateway(j),'OPP_D00007','CONTROLLER',None,'Advisor',{'input':'old'})

if __name__=='__main__':unittest.main(verbosity=2)
