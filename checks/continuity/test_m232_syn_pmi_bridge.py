"""M23.2 actual v3 SYN route, FULL backward compatibility + opt-in scoped PMI."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import scientific_closed_loop_v3 as v3
from e2core.core import EvidenceError, EvolutionJournal


class DummyJournal:
    def __init__(self, model_calls=None):
        self.state=type('State',(),{'model_calls':model_calls or {},'assets':{},'work':{}})()
    def verify(self): return self.state


class SynPMIBridgeTests(unittest.TestCase):
    def setUp(self):
        self.full={'program':{'problem':'P0'},
           'problems':[{'id':'P0','question':'Why?','status':'OPEN','parents':[]},
                       {'id':'P1','question':'Alternative','status':'OPEN','parents':['P0'],
                        'decomposition_rationale':'quantitative test'}]}
        self.evidence=[{'evidence_id':'SRC1','inspection_class':'OA_PDF_TEXT','returned_content':'actual'},
                       {'evidence_id':'SRC2','inspection_class':'OA_PDF_TEXT','returned_content':'other'}]
        self.novelty={'claim_assessments':[{'asset_id':'A1','evidence_ids':['SRC1']}]}
        self.state={}
        self.delta={'x':1}

    def test_full_mode_is_original_exact_input(self):
        res=v3._m232_syn_impact_input(DummyJournal(),self.full,self.novelty,
             self.evidence,self.state,self.delta,[],mode='FULL')
        self.assertEqual(set(res),{'program','current_problems','novelty','evidence',
                                   'original_p0_unchanged','prior_working_problem_state','prior_art_delta'})
        self.assertEqual(res['evidence'],self.evidence)
        self.assertEqual(res['current_problems'],self.full['problems'])
        self.assertNotIn('context_scope',res)

    def test_scoped_keeps_cited_and_all_catalog_ids(self):
        out=v3._m232_syn_impact_input(DummyJournal(),self.full,self.novelty,
             self.evidence,self.state,self.delta,[],mode='SCOPED')
        self.assertEqual(out['current_problems'][0],self.full['problems'][0])
        self.assertEqual({e['evidence_id'] for e in out['evidence']},{'SRC1','SRC2'})
        e={x['evidence_id']:x for x in out['evidence']}
        self.assertEqual(e['SRC1'],self.evidence[0])
        self.assertFalse(e['SRC2']['detail_present_in_this_call'])
        self.assertEqual(out['context_scope']['protocol'],
                         'M232_PMI_SCIENTIFICALLY_CONSERVATIVE_SCOPED_EVIDENCE_V1')

    def test_invalid_mode_fails_closed(self):
        with patch.dict('os.environ',{'M232_SYN_PMI_MODE':'BAD'}):
            with self.assertRaisesRegex(EvidenceError,'INVALID_MODE'):
                v3._m232_syn_pmi_mode(DummyJournal())

    def test_scoped_on_root_with_full_pmi_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            j=EvolutionJournal(Path(d)/'root');j.init('test root')
            original={'messages':[{'role':'user','content':json.dumps({'evidence':[]})}]}
            j.append('MODEL_CALL_INTENT',{'id':'PMI_TEST','actor':'CONTROLLER','work_id':None,
                     'request_blob':j.blob(original),'model':'x','billing_mode':'EXTERNAL'})
            with patch.dict('os.environ',{'M232_SYN_PMI_MODE':'SCOPED'}):
                with self.assertRaisesRegex(EvidenceError,'MODE_DRIFT'):
                    v3._m232_syn_pmi_mode(j)

    def test_source_guard_still_exists_and_controller_uses_bridge(self):
        import inspect
        s=inspect.getsource(v3.controller_v3)
        self.assertIn('_m232_syn_pmi_mode(j)',s)
        self.assertIn('_m232_syn_impact_input(',s)
        self.assertIn("impact_input['evidence']",s)
        self.assertTrue(callable(v3.source_code_guard))

if __name__=='__main__':unittest.main()
