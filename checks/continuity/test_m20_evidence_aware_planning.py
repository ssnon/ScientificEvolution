"""M20 source-aware planning index: no-paid, no source mutation tests."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'runtime'))
from e2core.core import EvolutionJournal
from e2core.evidence_continuity import inherited_planning_brief
from e2core.research_context import research_capability_state, research_worker_context

class EvidenceAwarePlanningTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='m20_planning_')
        self.addCleanup(tmp.cleanup)
        self.j=EvolutionJournal(Path(tmp.name)/'root')
        self.j.init('Synthetic unresolved problem')
        self.j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        for x,action in enumerate(('read_fulltext','figure_captions'),1):
            self.j.add_source('SRC_INHERITED_TOOL_DOC'+str(x),'EXTERNAL_AUDIT',{
                'kind':'INHERITED_REAL_EXECUTION_TOOL_RESULT_NOT_NEW_OBSERVATION',
                'original_tool_id':'TOOL_SYN_'+str(x),'evidence_class':'OA_FULLTEXT_TEXT' if x==1 else 'OA_FULLTEXT_CAPTION',
                'origin_peer':'SYN_02','original_request_blob_sha256':'a'*64,
                'original_result_blob_sha256':'b'*64,
                'pending_worker_interpretation':False,
                'original_returned_data':{
                    'request':{'kind':'literature_research','arguments':{'action':action,'pmcid':'PMC123'}},
                    'result':{'status':'DELIVERED','action':action,'pmcid':'PMC123',
                        'title':'Synthetic Paper','source_sha256':'1'*64}}},'fixture')
        self.j.add_source('SRC_INHERITED_TOOL_CALC','EXTERNAL_AUDIT',{
            'kind':'INHERITED_SCIENCE_TOOL_EXECUTION_NOT_NEW_OBSERVATION',
            'original_tool_id':'TOOL_CALC','evidence_class':'EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED',
            'origin_peer':'SYN_01','pending_worker_interpretation':True,
            'original_request_blob_sha256':'c'*64,
            'original_result_blob_sha256':'d'*64,
            'original_returned_data':{
                'request':{'kind':'python_science','arguments':{'code':'result=1'}},
                'result':{'status':'EXECUTED','result':1}}},'fixture')
        self.j.evolve('EV_F','FRESH',[],{
            'id':'W_F','mode':'FRESH','problem_id':'P0','question':'Fresh independent',
            'research_rationale':'Test','source_ids':[]},'Test')
        self.j.evolve('EV_I','DECOMPOSE',[],{
            'id':'W_I','mode':'INFORMED','problem_id':'P0','question':'Informed science',
            'research_rationale':'Test','source_ids':[]},'Test')

    def test_grouping_and_recall_ids(self):
        view=inherited_planning_brief(self.j,self.j.verify())
        self.assertEqual(view['readable_source_records'],3)
        self.assertEqual(view['distinct_document_or_execution_groups'],2)
        doc=next(x for x in view['source_groups'] if x['pmcid']=='PMC123')
        self.assertEqual(doc['source_records'],2)
        self.assertEqual(len(doc['example_source_ids']),2)
        self.assertEqual(doc['title'],'Synthetic Paper')
        self.assertEqual(doc['direct_fulltext_source_id'],'SRC_INHERITED_TOOL_DOC1')
        self.assertEqual(len(view['pending_results']),1)
        self.assertEqual(view['pending_results'][0]['source_id'],'SRC_INHERITED_TOOL_CALC')
        self.assertEqual(view['pending_results'][0]['original_result_blob_sha256'],'d'*64)
        self.assertTrue(view['historical_sources_are_not_new_current_root_tool_executions'])

    def test_fresh_isolation_and_informed_access_to_planning_index(self):
        view=inherited_planning_brief(self.j,self.j.verify(),'FRESH')
        self.assertEqual(view['source_groups'],[])
        self.assertNotIn('readable_source_records',view)
        fresh=research_worker_context(self.j,'W_F','NATIVE_RESEARCH_TOOLS')
        self.assertNotIn('inherited_evidence_planning_brief',fresh)
        informed=research_worker_context(self.j,'W_I','NATIVE_RESEARCH_TOOLS')
        self.assertEqual(informed['inherited_evidence_planning_brief']['readable_source_records'],3)
        controller=research_capability_state(self.j,'NATIVE_RESEARCH_TOOLS')
        self.assertEqual(controller['inherited_evidence_planning_brief']['distinct_document_or_execution_groups'],2)

    def test_index_is_bounded_but_not_an_evidence_delete(self):
        view=inherited_planning_brief(self.j,self.j.verify(),max_groups=1)
        self.assertEqual(len(view['source_groups']),1)
        self.assertEqual(view['undisplayed_groups'],1)
        self.assertEqual(len(view['pending_results']),1)
        self.assertEqual(len(self.j.verify().sources),3)
        with self.assertRaises(ValueError):
            inherited_planning_brief(self.j,self.j.verify(),max_groups=0)

if __name__=='__main__':unittest.main()
