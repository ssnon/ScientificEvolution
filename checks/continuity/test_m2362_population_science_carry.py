"""M23.6.2: no-paid synthetic real-Journal population science-tool transfer tests.

Tests operate only on TemporaryDirectory. No model/provider or real ROOT mutation.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from e2core.core import EvolutionJournal
import population_run as pop
import persistent_population as pp


class PopulationScienceToolCarryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='m2362_synth_')
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.source=EvolutionJournal(self.home/'SOURCE')
        self.source.init('Synthetic science-tool provenance, not experimental data')
        self.source.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        self.source.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        self.source.evolve('EV_SYNTH','FRESH',[],{
            'id':'W_SYNTH','mode':'FRESH','problem_id':'P0',
            'question':'Synthetic tool provenance test',
            'research_rationale':'Test only', 'source_ids':[]},
            'Synthetic independent test')
        self.source.start('W_SYNTH')
        self.source.step('W_SYNTH','MODEL_RESPONSE',{'text':'Synthetic model decision, not a scientific finding'})
        self.source.asset('A_SYNTH','W_SYNTH','CALCULATION','P0',
                          'Synthetic unverified calculation claim','Toy parameters','Synthetic only')
        # Leave W_SYNTH ACTIVE: must carry historical status, never current executable Work.
        self.tools=[]

    def add_tool(self, ident,kind,status):
        req={'kind':kind,'arguments':{'code':'result=1+1','description':'synthetic test'}}
        result={'status':status,'result':{'status':'synthetic_scaffold_only'},
                'scientific_computation_validated':False}
        self.source.append('TOOL_RECORDED',{
            'id':ident,'work_id':'W_SYNTH',
            'request_blob':self.source.blob(req),
            'result_blob':self.source.blob(result)})
        self.source.step('W_SYNTH','TOOL_RESULT',{
            'tool_id':ident,'result':result,'is_empirical_evidence':False})
        self.tools.append((ident,req,result))

    def carry(self):
        mods=pop.gen.modules()
        before=pp.digest(mods,self.source)
        receipt=pp.prepare_clean_portfolio(mods,self.source.root,self.home/'BASE_000')
        after=pp.digest(mods,self.source)
        self.assertEqual(before,after,'ORIGINAL_JOURNAL_WAS_MUTATED')
        base=EvolutionJournal(self.home/'BASE_000'); s=base.verify()
        self.assertEqual(len(s.assets),1)
        self.assertFalse(s.work)
        self.assertFalse(s.model_calls)
        self.assertFalse(s.controller_decisions)
        self.assertEqual(receipt['source_head'],before)
        self.assertTrue(receipt['unfinished_work_statuses_preserved_as_history'])
        self.assertEqual(receipt['new_research_executed'],False)
        status=json.loads(base.raw(s.sources['SRC_PREVIOUS_POPULATION_STATUS']['blob']))
        self.assertEqual(status['work_statuses']['W_SYNTH']['status'],'ACTIVE')
        return receipt,base,s

    def test_executed_population_python_tool_is_historical_source(self):
        self.add_tool('TOOL_SYNTH_EXEC','python_science','EXECUTED')
        receipt,base,s=self.carry()
        carried=receipt['prior_population_science_tool_carry']
        self.assertEqual(carried['registered_science_tools'],1)
        self.assertEqual(len(carried['ids']),1)
        raw=json.loads(base.raw(s.sources[carried['ids'][0]]['blob']))
        self.assertEqual(s.sources[carried['ids'][0]]['kind'],'EXTERNAL_AUDIT')
        self.assertEqual(raw['origin_peer'],'PRIOR_POPULATION') # existing shared helper field
        self.assertEqual(raw['original_root'],str(self.source.root))
        self.assertEqual(raw['original_tool_id'],'TOOL_SYNTH_EXEC')
        self.assertEqual(raw['evidence_class'],'EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED')
        self.assertIs(raw['is_a_new_tool_execution'],False)
        self.assertIs(raw['not_independently_certified'],True)
        self.assertEqual(raw['original_returned_data']['request'],self.tools[0][1])
        self.assertEqual(raw['original_returned_data']['result'],self.tools[0][2])
        old=self.source.verify().tool_results['TOOL_SYNTH_EXEC']
        self.assertEqual(raw['original_request_blob_sha256'],old['request_blob'])
        self.assertEqual(raw['original_result_blob_sha256'],old['result_blob'])
        self.assertFalse(s.tool_results,'CARRY_MUST_NOT_BE_NEW_TOOL_EXECUTION')

    def test_failed_calculation_is_not_a_scientific_negative(self):
        self.add_tool('TOOL_SYNTH_REJECTED','verified_calculation','REJECTED')
        receipt,base,s=self.carry()
        sid=receipt['prior_population_science_tool_carry']['ids'][0]
        rec=json.loads(base.raw(s.sources[sid]['blob']))
        self.assertEqual(rec['evidence_class'],'FAILED_CALCULATION_ATTEMPT_NOT_SCIENTIFIC_NEGATIVE')
        self.assertIs(rec['is_a_new_tool_execution'],False)

    def test_no_population_tools_does_not_create_fictitious_history(self):
        receipt,base,s=self.carry()
        self.assertEqual(receipt['prior_population_science_tool_carry'],{
            'registered_science_tools':0,'ids':[]})
        self.assertFalse(any('PRIOR_POPULATION' in json.dumps(json.loads(base.raw(r['blob'])))
                             for r in s.sources.values()))


if __name__=='__main__':unittest.main()
