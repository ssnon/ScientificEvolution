"""M23.5 no-paid regression: lineage rejection causality and budget boundaries.

No network, model billing, or mutation of a historical experiment.
"""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from e2core.m235_lineage_feedback import own_lineage_feedback, rejected_asset_fields
from e2core.m235_operational_boundary import (
    BUDGET_GUARD_ERROR, BUDGET_PAUSE, is_dev_budget_error, is_dev_budget_pause,
)

BAD_SOURCE = 'SRC_INHERITED_TOOL_3e50faa9d0f069a47a757'
VALID_SOURCE = 'SRC_INHERITED_TOOL_b680a8b55c283cf0d2e61b1'
A2 = 'A_activity_gated_resident_microstate_002'
A3 = 'A_ion_gate_null_matrix_003'
A5 = 'A_threeway_ion_potential_memory_005'
A6 = 'A_order_effect_generic_hidden_state_null_006'


def make_lineage_journal():
    """Faithful IDs, two validation steps, and the actual 3 -> 7 cascade."""
    blobs = {}
    steps = []
    def add(kind, payload):
        step = len(steps) + 1
        key = 'blob_'+str(step)
        blobs[key] = json.dumps(payload, ensure_ascii=False).encode('utf8')
        steps.append({'kind': kind, 'raw_blob': key, 'step': step})

    initial = [
        {'id': A2, 'source_ids': [BAD_SOURCE, VALID_SOURCE],
         'parent_ids': ['A_ion_gated_orientation_001']},
        {'id': A3, 'source_ids': [BAD_SOURCE, VALID_SOURCE],
         'parent_ids': ['A_ion_gated_orientation_001']},
    ]
    descendants = [
        {'id': A5, 'source_ids': [VALID_SOURCE],
         'parent_ids': ['A_order_sensitive_hydration_gate_004', A2]},
        {'id': A6, 'source_ids': [VALID_SOURCE],
         'parent_ids': ['A_order_sensitive_hydration_gate_004', A3]},
    ]
    add('MODEL_RESPONSE', {'text':json.dumps({'assets':initial})})
    add('TOOL_RESULT', {'result':{'status':'DELIVERED'}})
    add('OUTPUT_VALIDATION', {'status':'REJECTED','rejected':[
        {'kind':'ASSET','index':0,'error':'UNKNOWN_ASSET_SOURCE'},
        {'kind':'ASSET','index':1,'error':'UNKNOWN_ASSET_SOURCE'},
    ]})
    add('MODEL_RESPONSE', {'text':json.dumps({'assets':[]})})
    add('TOOL_RESULT', {'result':{'status':'DELIVERED'}})
    add('MODEL_RESPONSE', {'text':json.dumps({'assets':descendants})})
    add('OUTPUT_VALIDATION', {'status':'REJECTED','rejected':[
        {'kind':'ASSET','index':0,'error':'BAD_ASSET_PARENTS'},
        {'kind':'ASSET','index':1,'error':'BAD_ASSET_PARENTS'},
    ]})
    # Rejected steps must remain accessible even when outside prior[-5:].
    for _ in range(7):
        add('MODEL_RESPONSE', {'text':json.dumps({'assets':[]})})

    w = {'id':'W_verify_cb7_source_boundary_001','status':'ACTIVE','mode':'INFORMED',
         'steps':steps,'asset_input_ids':['A_ion_gated_orientation_001'],
         'source_ids':[VALID_SOURCE], 'published':['A_order_sensitive_hydration_gate_004'],
         'opportunity_input_ids':[]}
    fw={'id':'W_isolated_fresh','status':'ACTIVE','mode':'FRESH',
        'steps':[], 'asset_input_ids':[], 'source_ids':[], 'published':[],
        'opportunity_input_ids':[]}
    state=SimpleNamespace(
        work={w['id']:w,fw['id']:fw},
        sources={VALID_SOURCE:{'kind':'EXTERNAL_AUDIT'}},
        assets={'A_ion_gated_orientation_001': {'source_ids':[VALID_SOURCE]},
                'A_order_sensitive_hydration_gate_004':{'source_ids':[VALID_SOURCE]}},
        r5_policy=True,
    )
    class Journal:
        root=Path('/tmp/mock_m235_no_writes')
        def verify(self): return state
        def raw(self,key):return blobs[key]
        def input_for(self,wid):return {'parent_assets':[], 'work':{'id':wid},
                                        'source_entries':[]}
    return Journal(),state


class M235LineageTests(unittest.TestCase):
    def test_step3_step7_chain_is_visible_without_auto_registration(self):
        j,s=make_lineage_journal()
        result=own_lineage_feedback(j,s,'W_verify_cb7_source_boundary_001')
        events=result['rejected_asset_events']
        self.assertEqual([v['model_asset_id'] for v in events],[A2,A3,A5,A6])
        self.assertEqual([v['error'] for v in events],
                         ['UNKNOWN_ASSET_SOURCE']*2+['BAD_ASSET_PARENTS']*2)
        for v in events[:2]:self.assertEqual(v['currently_missing_source_ids'],[BAD_SOURCE])
        self.assertEqual(events[2]['parents_rejected_earlier_in_this_work'],[A2])
        self.assertEqual(events[3]['parents_rejected_earlier_in_this_work'],[A3])
        self.assertEqual(events[2]['currently_missing_parent_ids'],[A2])
        self.assertEqual(events[3]['currently_missing_parent_ids'],[A3])
        self.assertTrue(all(not v['currently_registered_as_asset'] for v in events))
        self.assertEqual(len(result['unregistered_proposals']),4)
        self.assertTrue(all(x not in s.assets for x in [A2,A3,A5,A6]))

    def test_fresh_work_never_sees_informed_rejections(self):
        j,s=make_lineage_journal()
        fresh=own_lineage_feedback(j,s,'W_isolated_fresh')
        self.assertEqual(fresh['rejected_asset_events'],[])
        self.assertEqual(fresh['registered_parent_ids'],[])
        self.assertNotIn(BAD_SOURCE,json.dumps(fresh))

    def test_rejected_diagnostics_describe_missing_not_rewrite_ids(self):
        _,s=make_lineage_journal()
        asset={'id':A2,'source_ids':[BAD_SOURCE,VALID_SOURCE],
               'parent_ids':['A_ion_gated_orientation_001']}
        original=json.dumps(asset,sort_keys=True)
        diag=rejected_asset_fields(asset,s)
        self.assertEqual(diag['missing_source_ids'],[BAD_SOURCE])
        self.assertEqual(diag['missing_parent_ids'],[])
        self.assertEqual(diag['model_asset_id'],A2)
        self.assertEqual(json.dumps(asset,sort_keys=True),original)
        self.assertNotIn(A2,s.assets)

    def test_registered_later_does_not_rewrite_historical_rejection(self):
        j,s=make_lineage_journal()
        s.assets[A2]={'source_ids':[]}
        s.work['W_verify_cb7_source_boundary_001']['published'].append(A2)
        out=own_lineage_feedback(j,s,'W_verify_cb7_source_boundary_001')
        first=out['rejected_asset_events'][0]
        self.assertTrue(first['currently_registered_as_asset'])
        self.assertEqual(first['error'],'UNKNOWN_ASSET_SOURCE')
        self.assertNotIn(A2,[x['model_asset_id'] for x in out['unregistered_proposals']])

    def test_worker_input_contains_persistent_lineage_without_sibling_leak(self):
        from e2core import engine as eng
        j,s=make_lineage_journal()
        with patch.object(eng,'research_worker_context',return_value={}):
            data=eng._worker_input(j,'W_isolated_fresh','NATIVE_RESEARCH_TOOLS')
            self.assertEqual(data['m235_own_lineage_feedback']['rejected_asset_events'],[])
            informed=eng._worker_input(j,'W_verify_cb7_source_boundary_001',
                                        'NATIVE_RESEARCH_TOOLS')
        self.assertEqual(len(informed['m235_own_lineage_feedback']['rejected_asset_events']),4)


class M235BudgetBoundaryTests(unittest.TestCase):
    def test_exact_guard_error_only(self):
        self.assertTrue(is_dev_budget_error(RuntimeError(BUDGET_GUARD_ERROR)))
        self.assertFalse(is_dev_budget_error(RuntimeError('OTHER_ERROR')))
        self.assertFalse(is_dev_budget_error(RuntimeError(BUDGET_GUARD_ERROR+'EXTRA')))

    def test_new_and_historical_pause_messages(self):
        self.assertTrue(is_dev_budget_pause([{'operational_pause':BUDGET_PAUSE}]))
        self.assertTrue(is_dev_budget_pause([{'operational_pause':
             'WORKER_OR_CONTROLLER_RUNTIME_ERROR:'+BUDGET_GUARD_ERROR}]))
        self.assertFalse(is_dev_budget_pause([{'operational_pause':
             'WORKER_OR_CONTROLLER_RUNTIME_ERROR:UNRELATED'}]))
        self.assertFalse(is_dev_budget_pause([{'operational_pause':
             'OPERATIONAL_CALL_BUDGET_REACHED'}]))
        self.assertFalse(is_dev_budget_pause([]))

    def test_campaign_does_not_request_second_call_after_budget_pause(self):
        from contextlib import nullcontext
        from e2core import long_campaign as lc
        state=SimpleNamespace(
            e3r1_policy=True,program_reviews=[],objective_assessments=[],
            controller_decisions=[],assets={},work={},model_calls={})
        class FakeJournal:
            root=Path('/tmp/m235_no_write_campaign')
            def __init__(self,*_): pass
            def verify(self):return state
            def report(self):return {'program_reviews':[]}
            def _events(self):return []
        class FakeModel:
            new_calls=0
            def __init__(self,*args,**kwargs): pass
        class FakeEngine:
            run_count=0
            def __init__(self,*args,**kwargs): pass
            def run(self,**kwargs):
                type(self).run_count+=1
                return {'status':'OPERATIONAL_RUN_BOUNDARY',
                        'decisions':[{'operational_pause':BUDGET_PAUSE}]}
        with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'}), \
             patch.object(lc,'locked_sources',return_value=nullcontext()), \
             patch.object(lc,'EvolutionJournal',FakeJournal), \
             patch.object(lc,'DurableModel',FakeModel), \
             patch.object(lc,'Engine',FakeEngine):
            output=lc.drive('fake',budget=8,chunk=4,max_tokens=1000,
                         model='mock',cpu=18,wall=22,paid=True)
        self.assertEqual(output['stop_reason'],BUDGET_PAUSE)
        self.assertEqual(output['total_paid_new_calls'],0)
        self.assertEqual(FakeEngine.run_count,1)

    def test_autonomous_run_exits_cleanly_with_no_council_call(self):
        from AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029 import autonomous_population as ap
        with tempfile.TemporaryDirectory() as d:
            msgs=[]
            args=SimpleNamespace(experiment=d,paid=True,slice_budget=8,bootstrap_peers=2,
                                 notice_every_segments=3)
            mockmods=SimpleNamespace(Error=ValueError)
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'}), \
                 patch.object(ap.pop.gen,'modules',return_value=mockmods), \
                 patch.object(ap.pop.gen,'verify_runtime_source'), \
                 patch.object(ap,'meta_check'), \
                 patch.object(ap,'last_meta_outcome',return_value=None), \
                 patch.object(ap,'step_once',return_value='BUDGET_PAUSE') as once, \
                 patch.object(ap,'current_cycle',return_value={'stage':'POPULATION'}), \
                 patch.object(ap,'ensure_not_stopped',return_value=True), \
                 patch.object(ap,'out',side_effect=msgs.append):
                ap.run(args)
            self.assertEqual(once.call_count,1)
            self.assertEqual(len(msgs),1)
            self.assertEqual(msgs[0]['status'],
                 'AUTONOMOUS_DEVELOPMENT_BUDGET_PAUSE_NOT_SCIENTIFIC_HOLD')
            self.assertEqual(msgs[0]['cycle_stage'],'POPULATION')
            self.assertTrue(msgs[0]['no_automatic_paid_retry'])

if __name__=='__main__': unittest.main()
