"""M19 no-paid tests of evidence handoff, isolation and unfinished feedback."""
from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'runtime'))
sys.path.insert(0,str(REPO/'AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029'))
from e2core.core import EvolutionJournal,canon,sha
from e2core.engine import Engine
from e2core.evidence_continuity import uninterpreted_last_tool_feedback
import population_run as pop

class M19EvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='m19_evidence_')
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.j=EvolutionJournal(self.base/'root')
        self.j.init('Synthetic source-grounded scientific problem.')
        self.j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        self.sid='SRC_INHERITED_TOOL_FAKE01'
        self.j.add_source(self.sid,'EXTERNAL_AUDIT',{
            'kind':'INHERITED_REAL_EXECUTION_TOOL_RESULT_NOT_NEW_OBSERVATION',
            'origin_peer':'SYN_TEST','original_root':'mock:donor',
            'original_tool_id':'TOOL_01','evidence_class':'OA_FULLTEXT_TEXT',
            'original_record_sha256':'0'*64,'not_independently_certified':True,
            'original_returned_data':{
                'request':{'kind':'literature_research','arguments':{'action':'read_fulltext','pmcid':'PMC42'}},
                'result':{'status':'DELIVERED','action':'read_fulltext','pmcid':'PMC42',
                          'title':'Synthetic SERS Article','paragraphs':[{'text':'Synthetic paragraph evidence'}],
                          'evidence_class':'OA_FULLTEXT_TEXT'}}},'synthetic only')
        def work(wid,mode,operation):
            self.j.evolve('EV_'+wid,operation,[],{
                'id':wid,'mode':mode,'problem_id':'P0','question':'Synthetic audit',
                'research_rationale':'No actual science','source_ids':[]},'Synthetic test')
        work('W_FRESH','FRESH','FRESH')
        work('W_INFORMED','INFORMED','REFRAME')
        self.engine=Engine(self.j,object())

    def call_tool(self,work_id,kind,args):
        return self.engine._tool({'kind':kind,'arguments':args},{'work_id':work_id})

    def test_fresh_never_discovers_or_reads_historical_evidence(self):
        r=self.call_tool('W_FRESH','source_catalog',{'query':'SERS'})
        self.assertEqual(r['error_code'],'FRESH_HISTORICAL_EVIDENCE_BLOCKED')
        r=self.call_tool('W_FRESH','source_lookup',{'source_ids':[self.sid]})
        self.assertEqual(r['error_code'],'UNAUTHORIZED_SOURCE')
        from e2core.research_context import research_worker_context
        ctx=research_worker_context(self.j,'W_FRESH','NATIVE_RESEARCH_TOOLS')
        self.assertEqual(ctx['inherited_evidence']['readable_inherited_source_count'],0)

    def test_informed_catalog_search_and_paginated_read(self):
        r=self.call_tool('W_INFORMED','source_catalog',{'query':'PMC42','offset':0,'limit':2})
        self.assertEqual(r['status'],'DELIVERED')
        self.assertEqual(r['total_matches'],1)
        self.assertEqual(r['source_records'][0]['source_id'],self.sid)
        self.assertTrue(r['source_records'][0]['not_a_new_tool_execution'])
        first=self.call_tool('W_INFORMED','source_lookup',{
            'source_ids':[self.sid],'offset':0,'limit':90})
        self.assertEqual(first['status'],'DELIVERED')
        self.assertEqual(first['source_records'][0]['encoding'],'canonical_json_text_chunk')
        self.assertIsNotNone(first['source_records'][0]['next_offset'])
        second=self.call_tool('W_INFORMED','source_lookup',{
            'source_ids':[self.sid],'offset':90,'limit':16000})
        self.assertEqual(second['status'],'DELIVERED')
        complete=first['source_records'][0]['text']+second['source_records'][0]['text']
        data=json.loads(complete)
        self.assertEqual(data['original_returned_data']['result']['pmcid'],'PMC42')
        self.assertIn('Synthetic paragraph evidence',complete)

    def test_pending_tool_feedback_tracks_actual_uninterpreted_tail(self):
        self.j.start('W_INFORMED')
        self.j.step('W_INFORMED','MODEL_RESPONSE',{'call_id':'MOCK1','text':'Synthetic'})
        self.j.append('TOOL_RECORDED',{
            'id':'TOOL_TEST01','work_id':'W_INFORMED',
            'request_blob':self.j.blob({'kind':'python_science','arguments':{'code':'result=2'}}),
            'result_blob':self.j.blob({'status':'EXECUTED','result':2})})
        self.j.step('W_INFORMED','TOOL_RESULT',{'tool_id':'TOOL_TEST01','result':{'status':'EXECUTED'}})
        result=uninterpreted_last_tool_feedback(self.j,self.j.verify())
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['tool_kind'],'python_science')
        self.j.step('W_INFORMED','MODEL_RESPONSE',{'call_id':'MOCK2','text':'Read feedback'})
        self.assertEqual(uninterpreted_last_tool_feedback(self.j,self.j.verify()),[])

    def test_science_tool_transfer_verified_and_recallable(self):
        donor=self.j
        donor.start('W_INFORMED')
        q={'kind':'python_science','arguments':{'code':'result={"x":42}'}}
        r={'status':'EXECUTED','result':{'x':42}}
        donor.append('TOOL_RECORDED',{'id':'TOOL_M19SCI','work_id':'W_INFORMED',
            'request_blob':donor.blob(q),'result_blob':donor.blob(r)})
        donor.step('W_INFORMED','TOOL_RESULT',{'tool_id':'TOOL_M19SCI','result':r})
        target=EvolutionJournal(self.base/'population')
        target.init('Synthetic science.')
        class Mods:pass
        Mods.sha=staticmethod(sha)
        Mods.canon=staticmethod(canon)
        count=pop.record_science_tool_results(Mods,target,donor,donor.verify(),'SYN_TEST')
        self.assertEqual(count['registered_science_tools'],1)
        tid=count['ids'][0]
        archive=json.loads(target.raw(target.verify().sources[tid]['blob']))
        self.assertTrue(archive['pending_worker_interpretation'])
        self.assertEqual(archive['original_returned_data']['result']['result']['x'],42)
        self.assertEqual(archive['original_result_blob_sha256'],donor.verify().tool_results['TOOL_M19SCI']['result_blob'])

    def test_model_can_cite_actual_archived_lookup_via_own_tool_source(self):
        from e2core.engine import Engine
        journal=self.j
        class SavedMock:
            def __init__(self):self.replies=[]
            def call(self,ident,actor,work_id,system,payload):
                rendered=self.replies.pop(0)
                journal.append('MODEL_CALL_INTENT',{
                    'id':ident,'actor':actor,'work_id':work_id,
                    'request_blob':journal.blob({'synthetic':True,'id':ident}),
                    'model':'MOCK','billing_mode':'MOCK'})
                journal.append('MODEL_CALL_SAVED',{
                    'id':ident,'response_blob':journal.blob({'choices':[
                        {'message':{'content':rendered},'finish_reason':'stop'}]}),
                    'usage':{}})
                return rendered
        model=SavedMock()
        model.replies=[json.dumps({
            'scientific_text':'Synthetic request for archived source.',
            'next_action':'CONTINUE','assets':[],'new_problems':[],
            'tool_request':{'kind':'source_lookup',
                'arguments':{'source_ids':[self.sid],'offset':0,'limit':5000}}})]
        engine=Engine(journal,model)
        first=engine.worker_step('W_INFORMED')
        self.assertEqual(first['status'],'TOOL_FEEDBACK_PENDING')
        state=journal.verify()
        linked=[sid for sid,v in state.sources.items()
                if sid.startswith('SRC_EVIDENCE_') and v.get('kind')=='TOOL_RESULT']
        self.assertEqual(len(linked),1)
        ref=linked[0]
        self.assertEqual(next(iter(state.tool_results.values()))['work_id'],'W_INFORMED')
        model.replies=[json.dumps({
            'scientific_text':'Synthetic source reading, not a scientific discovery.',
            'next_action':'RETURN','new_problems':[], 'tool_request':None,
            'assets':[{'id':'A_M19_SYNTHETIC','kind':'LITERATURE_CLAIM',
                'problem_id':'P0','claim':'Synthetic source contains synthetic text.',
                'assumptions':'Synthetic-only example', 'scope':'Mock source only',
                'predictions':[],'limitations':['No empirical claim'],
                'source_ids':[ref], 'parent_ids':[], 'delta_from_parents':'Synthetic test'}]})]
        second=engine.worker_step('W_INFORMED')
        self.assertEqual(second['status'],'RETURN')
        after=journal.verify()
        self.assertIn('A_M19_SYNTHETIC',after.assets)
        self.assertEqual(after.assets['A_M19_SYNTHETIC']['source_ids'],[ref])
        self.assertEqual(after.work['W_INFORMED']['status'],'DONE')

if __name__=='__main__':unittest.main()
