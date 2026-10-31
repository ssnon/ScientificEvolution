import json,unittest
from opp_contract_diff import compare_call
from opp_contract_diff import canon,sha

class ContractDiffTests(unittest.TestCase):
    def fake(self):
        self.system='OPP system prompt'
        self.payload={'science_memory_disclosure':{'version':'x'},'some_science':'A'}
        view={'science_memory_request_receipt':{'version':'x','original_payload_sha256':'wrong'},'some_science':'A'}
        wire={'model':'model','temperature':0.7,'max_tokens':16000,'response_format':{'type':'json_object'},
              'messages':[{'role':'system','content':self.system},
                          {'role':'user','content':json.dumps(view)}]}
        rec={'id':'OPP_D00007','actor':'CONTROLLER','work_id':None,'request_blob':sha(canon(wire))}
        return rec,wire
    def test_contract_equal_is_identified_without_replay_authorization(self):
        rec,wire=self.fake()
        out=compare_call(rec,wire,'CONTROLLER',None,self.system,self.payload,'model',16000)
        self.assertEqual(out['mismatched_contract_fields'],[])
        self.assertFalse(out['safe_to_replay'])
    def test_system_prompt_diff_is_precisely_identified(self):
        rec,wire=self.fake()
        out=compare_call(rec,wire,'CONTROLLER',None,self.system+' altered',self.payload,'model',16000)
        self.assertEqual(out['mismatched_contract_fields'],['system_prompt'])
        self.assertTrue(out['prompt_changed_line_previews'])
    def test_model_and_max_tokens_are_identified(self):
        rec,wire=self.fake()
        out=compare_call(rec,wire,'CONTROLLER',None,self.system,self.payload,'newmodel',4096)
        self.assertEqual(out['mismatched_contract_fields'],['model','max_tokens'])
    def test_does_not_normalize_arbitrary_science(self):
        rec,wire=self.fake()
        out=compare_call(rec,wire,'CONTROLLER',None,self.system,{'some_science':'B'},'model',16000)
        self.assertFalse(out['raw_science_input_matches_archived_precompaction'])
        self.assertFalse(out['safe_to_replay'])
if __name__=='__main__':unittest.main(verbosity=2)
