"""Pure no-cost proof of reserved fresh Controller attempts and old V4 guidance."""
from __future__ import annotations
import contextlib,json,sys,types,unittest
from types import SimpleNamespace
import safe_attempt as sa

class Journal:
    def __init__(self,prompt_base='Opportunity base',old_prompt=None,missing_controller=True):
        old_prompt=old_prompt if old_prompt is not None else prompt_base+'\n'+sa.LEGACY_V4_MARKER+' (advisory): compare independent alternatives.'
        self.archive={'messages':[{'role':'system','content':old_prompt},
                   {'role':'user','content':json.dumps({'sci':'old'})}]}
        self.blob=b'archived-byte-wire'
        self.rec={'state':'SAVED','actor':'CONTROLLER','work_id':None,'request_blob':'archived'}
        self.calls={'OPP_D00007':self.rec}
        self.decisions=[{'id':'D00006'}]
        if not missing_controller:
            self.calls['CTRL_D00007']={'state':'SAVED','request_blob':'ctrl'}
        self.prompt_base=prompt_base
        self.cnt=0
    def verify(self):
        self.cnt+=1
        return SimpleNamespace(model_calls=self.calls,controller_decisions=self.decisions)
    def raw(self,digest):
        assert digest=='archived';return json.dumps(self.archive).encode()

class Tests(unittest.TestCase):
    def test_orphan_opp_reserves_fresh_attempt_id(self):
        j=Journal()
        self.assertEqual(sa.reserved_next_id(j,'D00007'),'D00008')
        self.assertEqual(sa.reserved_next_id(j,'D00008'),'D00008')
        self.assertEqual(sa.reserved_next_id(j,'D00009'),'D00009')
        self.assertEqual(list(j.calls),['OPP_D00007'])
    def test_many_orphans_cannot_reuse_historical_paid_call(self):
        j=Journal()
        j.calls['OPP_D00009']={'state':'SAVED','request_blob':'other'}
        self.assertEqual(sa.reserved_next_id(j,'D00007'),'D00010')
    def test_expected_v4_append_only_prompt_restoration(self):
        j=Journal()
        prompt,metadata=sa.archived_opportunity_prompt(j,j.prompt_base)
        self.assertIn(sa.LEGACY_V4_MARKER,prompt)
        self.assertTrue(metadata['restored_v4_addendum'])
        self.assertEqual(metadata['source_call_id'],'OPP_D00007')
    def test_no_other_science_prompt_change_accepted(self):
        j=Journal(old_prompt='Scientific opportunity changed in middle\n'+sa.LEGACY_V4_MARKER)
        with self.assertRaisesRegex(RuntimeError,'NOT_APPEND_ONLY'):
            sa.archived_opportunity_prompt(j,j.prompt_base)
    def test_unknown_suffix_denied(self):
        j=Journal(old_prompt='Opportunity base\nAn unverified instruction')
        with self.assertRaisesRegex(RuntimeError,'UNKNOWN_SUFFIX'):
            sa.archived_opportunity_prompt(j,j.prompt_base)
    def test_completed_prior_assessment_does_not_block_future_generation(self):
        # Older G13-only guard rejected every root lacking its orphan OPP;
        # that would make a clean G14 unusable. Existing saved responses are
        # preserved and never silently repurposed.
        j=Journal(missing_controller=False)
        r=sa.safety_report(j,j.prompt_base)
        self.assertIsNone(r['abandoned_partial_opportunity'])
        self.assertEqual(r['reserved_new_controller_attempt'],'D00008')
        self.assertEqual(r['opportunity_prompt_provenance']['reason'],'NO_ORPHAN_OPPORTUNITY')
    def test_unsaved_call_prevents_restart(self):
        j=Journal();j.calls['WK_0001']={'state':'INTENT'}
        with self.assertRaisesRegex(RuntimeError,'UNRESOLVED_PROVIDER_OUTCOME'):
            sa.safety_report(j,j.prompt_base)
    def test_overlay_restores_engine_and_prompt(self):
        j=Journal()
        package=types.ModuleType('e2core')
        engine=types.ModuleType('e2core.engine')
        class Engine:
            def _next_controller_id(self):return 'D00007'
        engine.Engine=Engine;package.engine=engine
        prior={n:sys.modules.get(n) for n in ('e2core','e2core.engine')}
        sys.modules.update({'e2core':package,'e2core.engine':engine})
        mods=SimpleNamespace(spe=SimpleNamespace(OPPORTUNITY_PROMPT=j.prompt_base))
        @contextlib.contextmanager
        def v4run():
            old=mods.spe.OPPORTUNITY_PROMPT
            mods.spe.OPPORTUNITY_PROMPT=j.archive['messages'][0]['content']
            try:yield
            finally:mods.spe.OPPORTUNITY_PROMPT=old
        mods.v4=SimpleNamespace(runtime=v4run)
        original=Engine._next_controller_id
        try:
            with sa.activate(mods,j) as safety:
                e=Engine();e.j=j
                self.assertEqual(e._next_controller_id(),'D00008')
                self.assertTrue(safety['restored_system_prompt_is_recorded_historical_v4'])
                self.assertEqual(mods.spe.OPPORTUNITY_PROMPT,j.prompt_base)
            self.assertEqual(mods.spe.OPPORTUNITY_PROMPT,j.prompt_base)
            self.assertIs(Engine._next_controller_id,original)
            self.assertEqual(list(j.calls),['OPP_D00007'])
        finally:
            for n,old in prior.items():
                if old is None:sys.modules.pop(n,None)
                else:sys.modules[n]=old
    def test_overlay_restores_on_exception(self):
        j=Journal();package=types.ModuleType('e2core')
        engine=types.ModuleType('e2core.engine')
        class Engine:
            def _next_controller_id(self):return 'D00007'
        engine.Engine=Engine;package.engine=engine
        prior={n:sys.modules.get(n) for n in ('e2core','e2core.engine')}
        sys.modules.update({'e2core':package,'e2core.engine':engine})
        mods=SimpleNamespace(spe=SimpleNamespace(OPPORTUNITY_PROMPT=j.prompt_base))
        @contextlib.contextmanager
        def v4run():
            old=mods.spe.OPPORTUNITY_PROMPT
            mods.spe.OPPORTUNITY_PROMPT=j.archive['messages'][0]['content']
            try:yield
            finally:mods.spe.OPPORTUNITY_PROMPT=old
        mods.v4=SimpleNamespace(runtime=v4run)
        orig=Engine._next_controller_id
        try:
            with self.assertRaisesRegex(ValueError,'stop'):
                with sa.activate(mods,j):raise ValueError('stop')
            self.assertIs(Engine._next_controller_id,orig)
            self.assertEqual(mods.spe.OPPORTUNITY_PROMPT,j.prompt_base)
        finally:
            for n,old in prior.items():
                if old is None:sys.modules.pop(n,None)
                else:sys.modules[n]=old

    def test_operation_boundary_not_scientific_stop(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            count=[]
            def step(*a,**kw):count.append(1);return 'CONTINUE'
            module=SimpleNamespace(step_once=step)
            with sa.stop_after_segments(module,tmp,2):
                self.assertEqual(module.step_once(),'CONTINUE')
                self.assertFalse((Path(tmp)/'STOP_REQUESTED').exists())
                self.assertEqual(module.step_once(),'CONTINUE')
                self.assertTrue((Path(tmp)/'STOP_REQUESTED').exists())
            self.assertIs(module.step_once,step)
            self.assertEqual(len(count),2)
    def test_terminal_step_does_not_create_operator_stop(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            def terminal(*a,**kw):return 'SCIENTIFIC_TERMINAL'
            module=SimpleNamespace(step_once=terminal)
            with sa.stop_after_segments(module,tmp,1):
                self.assertEqual(module.step_once(),'SCIENTIFIC_TERMINAL')
            self.assertFalse((Path(tmp)/'STOP_REQUESTED').exists())

if __name__=='__main__':unittest.main(verbosity=2)
