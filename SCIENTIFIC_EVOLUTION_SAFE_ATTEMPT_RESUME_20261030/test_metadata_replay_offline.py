#!/usr/bin/env python3
"""Offline compatibility proof; no provider calls or on-disk Journal writes."""
import json, sys, types, unittest
from types import SimpleNamespace
import memory_bridge as mm

class EvidenceError(ValueError): pass

class FakeJournal:
    def __init__(self, ident, old_view):
        self.ident=ident
        self.wire={'model':'openai/gpt-5.6-luna','temperature':0.7,'max_tokens':16000,
                   'response_format':{'type':'json_object'},'messages':[
                    {'role':'system','content':'prompt'},
                    {'role':'user','content':json.dumps(old_view,sort_keys=True,ensure_ascii=False,allow_nan=False)}]}
        self.sha=mm._digest(self.wire)
        self.rec={'state':'SAVED','actor':'CONTROLLER','work_id':None,'request_blob':self.sha}
    def verify(self):return SimpleNamespace(model_calls={self.ident:self.rec})
    def raw(self, sha):
        assert sha==self.sha
        return json.dumps(self.wire,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=sys.modules.get('e2core.core')
        sys.modules['e2core.core']=types.SimpleNamespace(EvidenceError=EvidenceError)
    @classmethod
    def tearDownClass(cls):
        if cls.before is None:sys.modules.pop('e2core.core',None)
        else:sys.modules['e2core.core']=cls.before
    def context(self):
        raw={'science_memory_disclosure':{'version':mm.V1_2_CONTRACT,'all_asset_count':42},
             'verified_execution_provenance':{'contract':mm.V1_2_CONTRACT,'tool_count_by_work':{'W':2}},
             'assets':[{'id':'A','claim':'physical claim'}],
             'v3_science_work_options':{'active_scientific_work':[{'work_id':'W','question':'can we distinguish?' }]}}
        old,_=mm.normalized_provenance_version_candidate(raw,mm.V1_1_CONTRACT)
        view={'assets':[],'science_memory_request_receipt':{'version':mm.V1_1_CONTRACT,
                 'original_payload_sha256':mm._digest(old),'original_payload_chars':mm.jsize(old)}}
        return raw,old,view
    def test_version_only_bridge_exact_archived_replay(self):
        raw,old,view=self.context()
        j=FakeJournal('OPP_D00007',view)
        model=SimpleNamespace(j=j,model='openai/gpt-5.6-luna',max_tokens=16000)
        self.assertEqual(mm.replay_payload_for_saved(model,j.ident,'CONTROLLER',None,'prompt',raw),view)
        self.assertNotEqual(mm._digest(raw),mm._digest(old))
    def test_science_claim_changed_fails_even_if_version_compatible(self):
        raw,old,view=self.context()
        raw['assets'][0]['claim']='a different physical theory'
        j=FakeJournal('OPP_D00007',view)
        model=SimpleNamespace(j=j,model='openai/gpt-5.6-luna',max_tokens=16000)
        with self.assertRaisesRegex(EvidenceError,'MODEL_REPLAY_SCIENCE_INPUT_CHANGED:OPP_D00007'):
            mm.replay_payload_for_saved(model,j.ident,'CONTROLLER',None,'prompt',raw)
    def test_tool_receipt_change_fails(self):
        raw,old,view=self.context()
        raw['verified_execution_provenance']['tool_count_by_work']['W']=3
        j=FakeJournal('OPP_D00007',view)
        model=SimpleNamespace(j=j,model='openai/gpt-5.6-luna',max_tokens=16000)
        with self.assertRaisesRegex(EvidenceError,'MODEL_REPLAY_SCIENCE_INPUT_CHANGED'):
            mm.replay_payload_for_saved(model,j.ident,'CONTROLLER',None,'prompt',raw)
    def test_no_normalization_of_arbitrary_user_science_text(self):
        raw,old,view=self.context()
        raw['assets'][0]['claim']+=' '+mm.V1_2_CONTRACT
        candidate,keys=mm.normalized_provenance_version_candidate(raw,mm.V1_1_CONTRACT)
        self.assertIn(mm.V1_2_CONTRACT,candidate['assets'][0]['claim'])
        self.assertEqual(keys,['science_memory_disclosure.version','verified_execution_provenance.contract'])
    def test_unknown_contract_not_accepted(self):
        raw,old,view=self.context()
        candidate,keys=mm.normalized_provenance_version_candidate(raw,'OTHER_VERSION')
        self.assertIsNone(candidate);self.assertEqual(keys,[])
    def test_prompt_change_rejected(self):
        raw,old,view=self.context()
        j=FakeJournal('OPP_D00007',view)
        model=SimpleNamespace(j=j,model='openai/gpt-5.6-luna',max_tokens=16000)
        with self.assertRaisesRegex(EvidenceError,'MODEL_REPLAY_CONTRACT_CHANGED'):
            mm.replay_payload_for_saved(model,j.ident,'CONTROLLER',None,'changed prompt',raw)

if __name__=='__main__':unittest.main(verbosity=2)
