#!/usr/bin/env python3
"""No network, no paid requests, no mutation of existing E2 journals."""
from __future__ import annotations
import copy,json,sys,types,unittest
from pathlib import Path
from types import SimpleNamespace
import memory_bridge as mm
import science_frontier as sf


class Fixture:
    def __init__(self):
        self.assets={}
        for i in range(130):
            ident=f'A_HIST_{i:03}'
            self.assets[ident]={'id':ident,'kind':'HYPOTHESIS',
                'claim':f'Physically conditional mechanism {i} '+('not experimentally certified '*12),
                'parent_ids':[f'A_HIST_{i-1:03}'] if i>0 else [],'source_ids':[],
                'work_id':'W_OLD'}
        self.assets['A_TOOLLESS_NEG']={'id':'A_TOOLLESS_NEG','kind':'SCOPED_NEGATIVE',
            'claim':'Reported searches returned no source','source_ids':[],'work_id':'W_FRESH',
            'parent_ids':[]}
        self.work={'W_FRESH':{'id':'W_FRESH','mode':'FRESH','status':'DONE','problem_id':'P1',
            'asset_input_ids':[],'published':['A_TOOLLESS_NEG'],'steps':[{'kind':'MODEL_RESPONSE',
                 'raw_blob':'xx'}]},
            'W_ACTIVE':{'id':'W_ACTIVE','mode':'INFORMED','status':'ACTIVE','problem_id':'P7',
                'asset_input_ids':['A_HIST_003'],'published':[],'steps':[]}}
        self.tool_results={};self.sources={}
        self.problems={f'P{i}':{'id':f'P{i}','parents':['P0'] if i else [],
            'question':('Research and contrast two physically different hypotheses '*12)+str(i)} for i in range(140)}
        self.model_calls={}


def legacy_context():
    return {'program':{'problem':'SERS research problem'},
       'problems':list(Fixture().problems.values()),
       'assets':[{'id':f'A_{i}','kind':'HYPOTHESIS','claim':'huge competing claim '*25,
                  'assumptions':'conditional', 'parent_ids':[]} for i in range(90)],
       'scientific_archive_manifest':{'all_asset_ids':[f'A_{i}' for i in range(600)]},
       'independent_peer_syn_portfolio':[{'name':'SYN_A','decisions':[{'id':'D1',
             'rationale':'long reasoning '*400,'actions':[]}],'all_peer_assets':[]}],
       'unreviewed_frontier_events':[{'kind':'PROBLEM_CREATED','id':str(i)} for i in range(150)],
       'scientific_portfolio_frontier':{'recent_scientific_changes':[{'id':str(i),'claim':'x'*500} for i in range(50)]}}


class J:
    root=Path('/synthetic/verified/root')
    def __init__(self,s):self.s=s
    def verify(self):return self.s
    def raw(self,key):return self.raw_data[key]


class MemoryTests(unittest.TestCase):
    def test_all_problem_ids_and_active_full_text(self):
        s=Fixture();row=list(s.problems.values());before=sf.sha(row)
        new=mm.bound_problems(row,{'P7'})
        self.assertEqual([x['id'] for x in new],list(s.problems))
        self.assertFalse([x for x in new if x['id'] in ('P0','P7') and x['question']== ''])
        self.assertLess(mm.jsize(new),22000)
        self.assertEqual(sf.sha(row),before)

    def test_bounded_advisor_preserves_exact_references_and_full_hash(self):
        source=legacy_context();s=Fixture()
        base=mm.bound_base(source,s,'/synthetic')
        self.assertEqual(len(base['problems']),140)
        self.assertIn('verified_execution_provenance',base)
        ctx={**base,'claim_prior_art_assessment':{'claim_assessments':[
           {'asset_id':f'A_HIST_{i:03}','relation':'UNCERTAIN','evidence_ids':[],'reason':'x'*700}
           for i in range(45)]},'problem_level_impact':{'problem_impact':{'state':'UNCHANGED'}}}
        before=sf.sha(ctx);small=mm.bound_advisor_payload(ctx,'OPP_D0041')
        self.assertLess(mm.jsize(small),86000)
        self.assertEqual(small['science_memory_request_receipt']['original_payload_sha256'],before)
        self.assertEqual(before,sf.sha(ctx))
        self.assertEqual(len(small['problems']),140)

    def test_unexecuted_source_failure_never_promoted_to_actual_tool_result(self):
        s=Fixture();truth=mm.provenance(s)
        self.assertEqual(truth['actual_executed_tool_receipts'],0)
        self.assertEqual(truth['unverified_status_claims'][0]['asset_id'],'A_TOOLLESS_NEG')
        s.tool_results['T1']={'id':'T1','work_id':'W_FRESH','request_blob':'a','result_blob':'b'}
        truth=mm.provenance(s)
        self.assertEqual(truth['actual_executed_tool_receipts'],1)
        self.assertFalse(truth['unverified_status_claims'])

    def test_model_written_tool_preamble_is_not_an_executed_tool(self):
        s=Fixture();j=J(s)
        science={'scientific_text':'Searches were issued, but no data returned',
              'next_action':'HOLD','tool_request':None,'assets':[]}
        text='{"kind":"literature_research","arguments":{"action":"search"}}\n\n'+json.dumps(science)
        j.raw_data={'xx':json.dumps({'text':text,'parse_ok':True}).encode()}
        flags=mm.model_tool_contract_audit(j)
        self.assertEqual(len(flags),1)
        self.assertEqual(flags[0]['work_id'],'W_FRESH')
        self.assertEqual(flags[0]['actual_tool_receipts_in_work'],0)
        self.assertTrue(flags[0]['model_wrote_tool_shaped_preamble'])
        self.assertEqual(len(s.tool_results),0)

    def test_activation_restores_patches_and_does_not_rebill_existing(self):
        import memory_bridge as mm
        fake_engine=types.ModuleType('e2core.engine');fake_engine.WORKER_PROMPT='original worker'
        fake_provider=types.ModuleType('e2core.provider')
        class Model:
            def call(self,ident,actor,work_id,system,payload):return payload
        fake_provider.DurableModel=Model
        package=types.ModuleType('e2core');package.engine=fake_engine;package.provider=fake_provider
        imports={n:sys.modules.get(n) for n in ('e2core','e2core.engine','e2core.provider')}
        sys.modules.update({'e2core':package,'e2core.engine':fake_engine,'e2core.provider':fake_provider})
        fake_fr=types.ModuleType('frontier_runtime')
        def base(d,s,sel,report):return d
        fake_fr._research_context=base
        oldfr=sys.modules.get('frontier_runtime');sys.modules['frontier_runtime']=fake_fr
        mods=SimpleNamespace(spe=SimpleNamespace(target_claims=lambda c,j:[]))
        original=Model.call;target=mods.spe.target_claims
        model=Model();model.j=SimpleNamespace(verify=lambda:SimpleNamespace(model_calls={}))
        try:
            with self.assertRaisesRegex(RuntimeError,'test exception'):
                with mm.activate(mods):
                    self.assertIsNot(Model.call,original)
                    self.assertIsNot(mods.spe.target_claims,target)
                    result=model.call('OPP_D0001','CONTROLLER',None,'test',legacy_context())
                    self.assertLess(mm.jsize(result),86000)
                    raise RuntimeError('test exception')
            self.assertIs(Model.call,original)
            self.assertIs(mods.spe.target_claims,target)
            self.assertIs(fake_fr._research_context,base)
            self.assertEqual(fake_engine.WORKER_PROMPT,'original worker')
        finally:
            if oldfr is None:sys.modules.pop('frontier_runtime',None)
            else:sys.modules['frontier_runtime']=oldfr
            for name,old in imports.items():
                if old is None:sys.modules.pop(name,None)
                else:sys.modules[name]=old


if __name__=='__main__':unittest.main(verbosity=2)
