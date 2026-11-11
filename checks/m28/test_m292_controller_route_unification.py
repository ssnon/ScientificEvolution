"""M29.2: no-paid, real V3/V4 Controller route capture and contract parity.

These tests intentionally inspect the final Controller assessor's *model input*
and do not merely test controller_plan's validator. No journal is mutated in the
fake-call tests; no external model provider is used.
"""
from __future__ import annotations
import json
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

import e2core.engine as engine
import e2core.m291_frontier_contract as m291
import e2core.math_claim_selection as math_selection
import e2core.m232_ondemand as ondemand
import e2core.m232_namespace as namespace
import e2core.m233_model_metadata as metadata
import scientific_closed_loop_v3 as v3
import scientific_research_readiness_v4 as v4


def _context():
    return {
        'program':{'id':'P0','problem':'DAC original scientific question'},
        'problems':[{'id':'P0','question':'DAC original scientific question'}],
        'assets':[],
        'm23_root_scoped_asset_namespace':{
            'canonical_asset_ids':[], 'verified_original_to_canonical':{}},
        'existing_scientific_reason':'unknown, not falsely resolved',
    }


class FakeJournal:
    def __init__(self,meta=True,collab=True,e3r1=True,r5=True):
        self.state=SimpleNamespace(
            meta_research_autonomy=meta,meta_collaboration=collab,
            e3r1_policy=e3r1,r5_policy=r5,model_calls={},
        )
        self.events=[]
    def verify(self):return self.state
    def append(self,kind,payload):self.events.append((kind,payload))
    def blob(self,data):return 'a'*64


class FakeModel:
    def __init__(self):self.calls=[]
    def call(self,*args):
        self.calls.append(args)
        return '{}'


class TestM292ControllerRouteUnification(unittest.TestCase):
    def test_native_meta_prompt_context_have_all_contracts_and_no_duplicate(self):
        j=FakeJournal()
        with patch.object(engine,'meta_organization_context',return_value={
             'enabled':True,'requested':[],'child_research_reports':[]}), \
             patch.object(m291,'active',return_value=True):
            prompt,context=engine.effective_controller_contract(j,'NATIVE_BASE',_context())
        self.assertEqual(prompt.count('M28-A1 META-RESEARCH AUTONOMY'),1)
        self.assertEqual(prompt.count('M28-A2 SELECTIVE SCIENTIFIC COLLABORATION'),1)
        self.assertEqual(prompt.count('M29 EVIDENCE-TO-RESEARCH-FRONTIER HANDOFF'),1)
        self.assertEqual(prompt.count('M29.1 EXPLICIT SCIENTIFIC FRONTIER ASSESSMENT CONTRACT'),2)
        self.assertTrue(prompt.startswith('M29.1 EXPLICIT SCIENTIFIC'))
        self.assertIn('M29.1 EXPLICIT',prompt[-2500:])
        self.assertEqual(context['meta_research_organization_context']['enabled'],True)
        self.assertEqual(context['existing_scientific_reason'],_context()['existing_scientific_reason'])

    def test_legacy_nonmeta_prompt_and_context_unchanged(self):
        j=FakeJournal(meta=False,collab=False)
        base=_context();p='LEGACY_PROMPT_UNMODIFIED'
        newp,newctx=engine.effective_controller_contract(j,p,base)
        self.assertIs(newp,p)
        self.assertIs(newctx,base)

    def test_meta_only_without_collaboration_does_not_enable_new_protocols(self):
        j=FakeJournal(meta=True,collab=False)
        with patch.object(engine,'meta_organization_context',return_value={'enabled':True}):
            p,c=engine.effective_controller_contract(j,'BASE',_context())
        self.assertIn('M28-A1 META-RESEARCH AUTONOMY',p)
        self.assertNotIn('M28-A2 SELECTIVE SCIENTIFIC',p)
        self.assertNotIn('M29 EVIDENCE-',p)
        self.assertNotIn('M29.1 EXPLICIT',p)
        self.assertIn('meta_research_organization_context',c)

    def test_m291_is_not_activated_on_other_meta_roots(self):
        j=FakeJournal()
        with patch.object(engine,'meta_organization_context',return_value={'enabled':True}), \
             patch.object(m291,'active',return_value=False):
            p,_=engine.effective_controller_contract(j,'BASE',_context())
        self.assertIn('M28-A1 META-RESEARCH AUTONOMY',p)
        self.assertIn('M28-A2 SELECTIVE SCIENTIFIC',p)
        self.assertIn('M29 EVIDENCE-TO-RESEARCH-FRONTIER',p)
        self.assertNotIn('M29.1 EXPLICIT',p)

    def test_native_engine_final_model_call_uses_effective_contract(self):
        j=FakeJournal()
        model=FakeModel()
        model.call=lambda *args: (model.calls.append(args) or json.dumps({
            'rationale':'No scientific claim certified','disposition':'ONGOING',
            'new_problems':[],'reviews':[],'actions':[],
        }))
        with patch.object(engine,'_external_context',return_value=_context()), \
             patch.object(engine,'meta_organization_context',return_value={
                 'enabled':True,'child_research_reports':[]}), \
             patch.object(m291,'active',return_value=True), \
             patch.object(engine,'controller_plan',return_value=[]):
            runtime=engine.Engine(j,model,tool_backend=lambda *a,**k: None)
            result=runtime.controller('D00077')
        self.assertEqual(result['status'],'CONTROLLER_COMMITTED')
        self.assertEqual(len(model.calls),1)
        prompt,payload=model.calls[0][3:5]
        self.assertIn('M28-A1 META-RESEARCH AUTONOMY',prompt)
        self.assertIn('M29.1 EXPLICIT SCIENTIFIC FRONTIER',prompt)
        self.assertIn('meta_research_organization_context',payload)

    def _capture_real_v4_v3_controller(self,meta,collab):
        j=FakeJournal(meta=meta,collab=collab)
        model=FakeModel();captured=[]
        runtime=SimpleNamespace(j=j,model=model,_native_tool_contract=True)

        def fake_assessor(model,j,ident,prompt,payload,stage,*,mode):
            captured.append((ident,prompt,payload,stage,mode))
            if stage=='OPPORTUNITY':return json.dumps({'opportunities':[]}),ident,None
            return json.dumps({'disposition':'ONGOING','rationale':'mock only',
                'new_problems':[],'reviews':[],'actions':[]}),ident,None

        # Exercise the actual V4/V3 entrypoint and the actual V3
        # controller_v3 implementation. Only advisory provider/model calls
        # and science validators are stubs, with zero paid call potential.
        with v4.runtime(),v3.v3_runtime():
            self.assertIs(v3.spe.feedback_controller,v3.controller_v3)
            with ExitStack() as stack:
                def mock(obj,name,value):
                    stack.enter_context(patch.object(obj,name,value))
                mock(v3,'_external_context',lambda *a,**k:_context())
                mock(v3,'_m232_syn_pmi_mode',lambda *a,**k:'FULL')
                mock(v3,'selected_mode',lambda *a,**k:'ON_DEMAND')
                mock(v3,'_science_fingerprint',lambda *a,**k:'synthetic-fingerprint')
                mock(v3,'_last_controller_input',lambda *a,**k:None)
                mock(v3,'_m232_syn_impact_input',lambda *a,**k:{
                    'program':_context()['program'],'assets':[],
                    'problems':_context()['problems'],
                    'evidence':[]})
                mock(v3,'_work_options',lambda *a,**k:{'active_scientific_work':[]})
                mock(v3,'assessor_call',fake_assessor)
                mock(v3,'strict_envelope',json.loads)
                mock(v3,'controller_plan',lambda *a,**k:[])
                mock(v3.spe,'classified_evidence',lambda *a,**k:[])
                mock(v3.spe,'target_claims',lambda *a,**k:[])
                mock(v3.spe,'working_problem_state',lambda *a,**k:{})
                mock(v3.spe,'_call_id',lambda *a,**k:'NVT_FAKE')
                mock(v3.spe,'validate_novelty',lambda *a,**k:{})
                mock(v3.spe,'validate_impact',lambda *a,**k:{})
                mock(v3.spe,'validate_opp',lambda *a,**k:{})
                mock(v3.spe,'prior_art_delta',lambda *a,**k:{})
                mock(v3.spe,'problem_impact_delta',lambda *a,**k:{})
                mock(math_selection,'controller_context',lambda *a,**k:None)
                mock(engine,'meta_organization_context',lambda *a,**k:{
                    'enabled':bool(meta),'child_research_reports':[
                        {'report_id':'RPT_VERIFIED_BUT_AI_FALLIBLE','status':'AI_CLAIM'}]})
                mock(m291,'active',lambda *a,**k:bool(meta and collab))
                status=v3.controller_v3(runtime,'D00078')
        self.assertEqual(status['status'],'CONTROLLER_COMMITTED')
        finals=[c for c in captured if c[3]=='CONTROLLER']
        self.assertEqual(len(finals),1)
        return finals[0],j

    def test_actual_v4_v3_controller_model_input_contains_contracts(self):
        (ident,prompt,ctx,stage,mode),j=self._capture_real_v4_v3_controller(True,True)
        self.assertEqual(ident,'CTRL_D00078')
        self.assertEqual(mode,'ON_DEMAND')
        self.assertIn('M28-A1 META-RESEARCH AUTONOMY',prompt)
        self.assertIn('M28-A2 SELECTIVE SCIENTIFIC COLLABORATION',prompt)
        self.assertIn('M29 EVIDENCE-TO-RESEARCH-FRONTIER',prompt)
        self.assertIn('M29.1 EXPLICIT SCIENTIFIC FRONTIER ASSESSMENT',prompt)
        self.assertEqual(ctx['meta_research_organization_context']['child_research_reports'][0]['status'],
                         'AI_CLAIM')
        self.assertEqual(j.events[0][0],'CONTROLLER_DECISION')

    def test_actual_v4_v3_legacy_does_not_inherit_optin_contracts(self):
        (_,prompt,ctx,_,_),j=self._capture_real_v4_v3_controller(False,False)
        self.assertNotIn('M28-A1 META-RESEARCH AUTONOMY',prompt)
        self.assertNotIn('M29 EVIDENCE-TO-RESEARCH-FRONTIER',prompt)
        self.assertNotIn('M29.1 EXPLICIT SCIENTIFIC',prompt)
        self.assertNotIn('meta_research_organization_context',ctx)

    def test_on_demand_compact_separate_preserves_organization_context(self):
        j=FakeJournal()
        with patch.object(engine,'meta_organization_context',return_value={
              'enabled':True,'requested':[],
              'child_research_reports':[{'report_id':'RPT_REAL','science_certification':False}]}), \
             patch.object(m291,'active',return_value=True):
            _,full=engine.effective_controller_contract(j,'PROMPT',_context())
        session=ondemand.DetailSession(full,'CONTROLLER')
        initial=session.model_input()
        compact=namespace.compact_payload(initial,set())
        separated=metadata.compact_presentation_metadata(compact)
        for view in (initial,compact,separated):
            self.assertEqual(view['meta_research_organization_context'],full['meta_research_organization_context'])
        self.assertTrue(session.verify_all_reconstructable())

if __name__=='__main__':unittest.main()
