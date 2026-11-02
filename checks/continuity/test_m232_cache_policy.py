"""Offline M23.2 selective cache policy tests, no model/network calls."""
import json
import os
import unittest
from unittest.mock import patch

from e2core.core import EvidenceError, canon
from e2core.m232_cache_policy import selected_cache_fields

class J:
    def __init__(self, old=None):
        self.old=old or {}
        self.data={k:canon(v) for k,v in self.old.items()}
    def verify(self):
        return type('S',(),{'model_calls':{
            k:{'actor':'CONTROLLER','request_blob':k}
            for k in self.old}})()
    def raw(self,which):
        return self.data[which]

class CachePolicyTests(unittest.TestCase):
    def choose(self,mode,stage='OPP_D00001',journal=None,actor='CONTROLLER',work_id=None,model='openai/gpt-5.6-luna'):
        with patch.dict(os.environ,{'M232_CACHE_POLICY':mode}):
            return selected_cache_fields(journal or J(),stage,actor,work_id,model)
    def test_default_auto_no_wire_change(self):
        self.assertEqual(self.choose('AUTO'),{})
        self.assertEqual(self.choose('AUTO',stage='NVT_1'),{})
    def test_selective_only_assessor_stages(self):
        for st in ('PMI_1','OPP_D00001','CTRL_D00001'):
            self.assertEqual(self.choose('SELECTIVE_NO_WRITE',stage=st),{'prompt_cache_options':{'mode':'explicit'}})
        self.assertEqual(self.choose('SELECTIVE_NO_WRITE',stage='NVT_1'),{})
        self.assertEqual(self.choose('SELECTIVE_NO_WRITE',stage='WORK_1',actor='WORKER',work_id='W1'),{})
    def test_invalid_setting_fails_closed(self):
        with self.assertRaises(EvidenceError):self.choose('UNKNOWN')
    def test_other_model_fails_closed(self):
        with self.assertRaises(EvidenceError):self.choose('SELECTIVE_NO_WRITE',model='example/other')
    def test_sticky_journal_policy(self):
        auto={'model':'openai/gpt-5.6-luna','messages':[]}
        no_write={'model':'openai/gpt-5.6-luna','messages':[], 'prompt_cache_options':{'mode':'explicit'}}
        self.assertEqual(self.choose('AUTO',journal=J({'PMI_1':auto})),{})
        self.assertEqual(self.choose('SELECTIVE_NO_WRITE',journal=J({'PMI_1':no_write})),{'prompt_cache_options':{'mode':'explicit'}})
        for prior,mode in ((auto,'SELECTIVE_NO_WRITE'),(no_write,'AUTO')):
            with self.assertRaises(EvidenceError):self.choose(mode,journal=J({'PMI_1':prior}))
    def test_no_model_payload_changes(self):
        original={'model':'openai/gpt-5.6-luna','temperature':0.7,'max_tokens':16000,
                  'messages':[{'role':'system','content':'test'}, {'role':'user','content':'science'}]}
        with patch.dict(os.environ,{'M232_CACHE_POLICY':'AUTO'}):
            patched=original|selected_cache_fields(J(),'OPP_1','CONTROLLER',None,original['model'])
        self.assertEqual(canon(original),canon(patched))
        with patch.dict(os.environ,{'M232_CACHE_POLICY':'SELECTIVE_NO_WRITE'}):
            patched=original|selected_cache_fields(J(),'OPP_1','CONTROLLER',None,original['model'])
        self.assertEqual(patched['messages'],original['messages'])
        self.assertEqual(patched['temperature'],original['temperature'])
        self.assertEqual(patched['prompt_cache_options'],{'mode':'explicit'})

if __name__=='__main__':unittest.main()
