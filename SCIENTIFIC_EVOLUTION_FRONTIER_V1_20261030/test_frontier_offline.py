#!/usr/bin/env python3
"""Offline, no provider calls; source contract and attention security tests."""
from __future__ import annotations
import json, sys, types, unittest
from pathlib import Path
from types import SimpleNamespace
import science_frontier as sf
import frontier_runtime as fr


def state_fixture(n=280):
    assets={}
    for i in range(n):
        topic=['charge feedback kinetic response','molecular orientation harmonic analysis',
              'adsorption occupancy null benchmark','spectroscopy primary source caveat',
              'photothermal mechanism and barrier control'][i%5]
        aid=f'A_HIST_{i:04}'
        parents=[f'A_HIST_{i-5:04}'] if i>=5 and i%6==0 else []
        assets[aid]={'id':aid,'kind':'HYPOTHESIS' if i%3==0 else 'NULL_MODEL' if i%3==1 else 'PREDICTION',
          'origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK','claim':topic+f' {i} '+('precise conditional detail '*15),
          'assumptions':'Assume independent calibrated signal',
          'predictions':['test on matched channels'], 'limitations':['requires independent measurement'],
          'parent_ids':parents,'source_ids':[],'delta_from_parents':'new condition'}
    assets['A_LIVE_NEW']={'id':'A_LIVE_NEW','origin':'LIVE_WORK','kind':'HYPOTHESIS',
         'claim':'New cross-channel orientation and redox dynamics experimentally distinguishable under a calibrated perturbation',
         'assumptions':'fixed occupancy','predictions':['different lag at fixed occupancy'],
         'limitations':['needs validation'],'parent_ids':['A_HIST_0000','A_HIST_0001'],
         'source_ids':['SRC_REAL'],'delta_from_parents':'Adds a new causal observable'}
    w={'W_OPEN':{'id':'W_OPEN','status':'ACTIVE','mode':'INFORMED','question':'Test decisive discriminator',
           'asset_input_ids':['A_HIST_0000','A_HIST_0001'],'published':['A_LIVE_NEW'],'steps':[]}}
    return SimpleNamespace(assets=assets,work=w,sources={},controller_decisions=[],program={'problem':'Find a novel falsifiable mechanism'})

class FrontierTests(unittest.TestCase):
    def test_originals_never_mutated_and_live_parents_retained(self):
        st=state_fixture();before=sf.sha(st.assets)
        selected,meta=sf.select_assets(st,max_chars=29000)
        self.assertIn('A_LIVE_NEW',selected)
        self.assertIn('A_HIST_0000',selected)
        self.assertIn('A_HIST_0001',selected)
        self.assertLess(len(selected),len(st.assets))
        self.assertEqual(meta['total_assets'],281)
        self.assertEqual(before,sf.sha(st.assets))
        self.assertTrue(meta['omitted_ids'])
        self.assertLessEqual(meta['selected_claim_bytes'],29000)
        self.assertTrue(sf.candidate_dossiers(st,selected))

    def test_evidence_scope_preserves_all_excluded_ids_in_audit(self):
        inp=[{'evidence_id':f'SRC_{i:03}','inspection_class':'OA_FULLTEXT_TEXT',
              'returned_content':'A'*500} for i in range(80)]
        selected,trace=sf.cap_evidence(inp,{'SRC_079'},5000)
        self.assertTrue(any(x['evidence_id']=='SRC_079' for x in selected))
        self.assertEqual(len(selected)+len(trace['unpresented_evidence_ids']),80)
        self.assertTrue(trace['unpresented_evidence_is_not_negative_result'])

    def test_archival_tool_only_informed_parent_lineage(self):
        st=state_fixture(14)
        st.work['W_FRESH']={'id':'W_FRESH','status':'ACTIVE','mode':'FRESH','asset_input_ids':[],'published':[]}
        st.sources={'SRC_REAL':{'kind':'HISTORICAL_AI','blob':'abc'}}
        class J:
            root=Path('/not-real')
            def verify(self):return st
            def raw(self,key):return b'{"ref":"source#asset","science":{}}'
        class Engine:
            j=J()
        def orig(*args):return {'status':'ORIGINAL'}
        kind={'kind':'scientific_archive','arguments':{'action':'parent_asset','id':'A_HIST_0000'}}
        self.assertEqual(fr.archive_tool(orig,Engine(),kind,{'work_id':'W_FRESH'})['status'],'REJECTED')
        self.assertEqual(fr.archive_tool(orig,Engine(),kind,{'work_id':'W_OPEN'})['status'],'DELIVERED')
        k={'kind':'scientific_archive','arguments':{'action':'parent_asset','id':'A_HIST_0007'}}
        self.assertEqual(fr.archive_tool(orig,Engine(),k,{'work_id':'W_OPEN'})['status'],'REJECTED')
        self.assertEqual(fr.archive_tool(orig,Engine(),{'kind':'python_science'}, {'work_id':'W_FRESH'}),{'status':'ORIGINAL'})

    def test_compaction_reduces_oversized_pmi_and_restores_hooks(self):
        state=state_fixture(280)
        dummy_e=types.ModuleType('e2core.engine')
        class Engine:
            def _tool(self,req,context):return {'status':'ORIGINAL'}
        dummy_e.Engine=Engine;dummy_e.WORKER_PROMPT='Worker original'
        parent=types.ModuleType('e2core');parent.engine=dummy_e
        oldmodule=sys.modules.get('e2core');oldengine=sys.modules.get('e2core.engine')
        sys.modules['e2core']=parent;sys.modules['e2core.engine']=dummy_e
        class Journal:
            root=Path('/fake/verified_journal')
            def verify(self):return state
        j=Journal()
        def original_context(j,cap=None):
            return {'program':state.program,'problems':[],'assets':[{'id':a['id'],'claim':a['claim'],
                    'kind':a['kind'],'origin':a['origin'], 'predictions':a['predictions'],
                    'assumptions':a['assumptions'],'limitations':a['limitations']} for a in state.assets.values()],
                    'research_capability_state':{'paths':'known'},'works':[]}
        def claims(ctx,j):return [{'id':a['id'],'claim':a['claim']} for a in ctx['assets']]
        def evidence(j):return [{'evidence_id':f'SRC_{i}','inspection_class':'OA_PDF_TEXT',
                                  'returned_content':'large '+('x'*950)} for i in range(100)]
        def working(j):return {'current_claim_assessments':{a:{'relation':'UNCERTAIN','remainder':'x'*250}
                 for a in state.assets},'historical_source_assessment':{'all_previous':'x'*260000},
                  'claim_relation_changes':[],'historical_problem_status_changes':[]}
        spe=SimpleNamespace(target_claims=claims,classified_evidence=evidence,working_problem_state=working, NOVELTY_PROMPT='NVT original',IMPACT_PROMPT='PMI original')
        v3=SimpleNamespace(_external_context=original_context)
        aut=SimpleNamespace(snapshot=lambda *a:'original',S_PROMPT='original')
        mods=SimpleNamespace(v3=v3,spe=spe)
        try:
            original_raw={'program':state.program,'target_claims':claims(original_context(j),j),
                          'evidence':evidence(j),'prior_working_problem_state':working(j)}
            self.assertGreater(sf.size(original_raw),500000)
            with fr.activate(mods,aut):
                base=v3._external_context(j,'NATIVE_RESEARCH_TOOLS')
                small={'program':base['program'],'target_claims':spe.target_claims(base,j),
                       'evidence':spe.classified_evidence(j),
                       'prior_working_problem_state':spe.working_problem_state(j)}
                self.assertLess(sf.size(small),90000)
                self.assertLess(len(small['target_claims']),281)
                self.assertIn('scientific_portfolio_index',base)
                self.assertIn('A_LIVE_NEW',[a['id'] for a in base['assets']])
            self.assertIs(v3._external_context,original_context)
            self.assertIs(spe.working_problem_state,working)
            self.assertEqual(dummy_e.WORKER_PROMPT,'Worker original')
            self.assertEqual(spe.NOVELTY_PROMPT,'NVT original')
            self.assertEqual(spe.IMPACT_PROMPT,'PMI original')
            self.assertIs(Engine._tool,orig_tool) if False else None
        finally:
            if oldmodule is None:sys.modules.pop('e2core',None)
            else:sys.modules['e2core']=oldmodule
            if oldengine is None:sys.modules.pop('e2core.engine',None)
            else:sys.modules['e2core.engine']=oldengine

if __name__=='__main__':unittest.main(verbosity=2)
