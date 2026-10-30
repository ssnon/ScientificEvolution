#!/usr/bin/env python3
"""Read-only, mock-only local scientific HOLD boundary regression tests."""
import contextlib
from types import SimpleNamespace
import autonomous_population as a
import persistent_population as pp
from test_autonomous_offline import setup, restore, Model


def test_classification():
    assert a.normalized_research_boundary('AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED',
        'HOLD_WITH_RATIONALE') == 'LOCAL_SCIENTIFIC_TERMINAL'
    assert a.normalized_research_boundary('AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED',
        'ONGOING') == 'AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED'
    assert a.normalized_research_boundary('SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED',
        'HOLD_WITH_RATIONALE') == 'SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED'
    assert a.normalized_research_boundary('CALL_BUDGET','ONGOING') == 'CALL_BUDGET'
    assert 'CONTINUE_RESEARCH' not in a.council_choices('POPULATION', True)
    assert 'CONTINUE_RESEARCH' in a.council_choices('POPULATION', False)
    assert 'CONTINUE_RESEARCH' not in a.council_choices('PEER', True)
    assert a.POP_CHOICES-a.council_choices('POPULATION', True)=={'CONTINUE_RESEARCH'}
    print('PASS: local scientific HOLD is not an operational error or global HOLD')


def test_drive_slice_reads_committed_status():
    old_root_status=a.pop.root_status
    old_bridge=pp.previous_population_bridge
    old_drive=a.pop.gen.drive
    root='/tmp/mock-science-boundary'
    ongoing=SimpleNamespace(program_reviews=[{'scientific_status':'ONGOING'}],assets={'a':1},controller_decisions=[1])
    held=SimpleNamespace(program_reviews=[{'scientific_status':'HOLD_WITH_RATIONALE'}],assets={'a':1,'b':2},controller_decisions=[1,2])
    calls=iter([(SimpleNamespace(),ongoing),(SimpleNamespace(),held)])
    a.pop.root_status=lambda mods,r:next(calls)
    pp.previous_population_bridge=lambda mods:contextlib.nullcontext()
    a.pop.gen.drive=lambda mods,r,spec,phase:{'stop_reason':'AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED','new_calls_this_launch':7}
    try:
        result=a.drive_slice(SimpleNamespace(),root,'PEER',SimpleNamespace(model='mock',slice_budget=8,
            checkpoint_iterations=12,max_parallel=2,max_tokens=16000,science_cpu_seconds=5,science_wall_seconds=5))
        assert result['stop']=='LOCAL_SCIENTIFIC_TERMINAL'
        assert result['engine_stop_reason']=='AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED'
        assert result['latest_scientific_disposition']=='HOLD_WITH_RATIONALE'
        assert result['spent']==7
        print('PASS: committed local scientific hold normalizes exact observed engine stop')
    finally:
        a.pop.root_status=old_root_status
        pp.previous_population_bridge=old_bridge
        a.pop.gen.drive=old_drive


def test_population_routing():
    old_current=a.current_cycle;old_root_status=a.pop.root_status
    old_drive=a.drive_slice;old_council=a.council;old_mark=a.mark_cycle
    cycle={'index':1,'stage':'POPULATION','population_root':'/tmp/example','peers':{'SYN_01':'/tmp/a'}}
    ongoing=SimpleNamespace(program_reviews=[{'scientific_status':'ONGOING'}])
    a.current_cycle=lambda experiment:cycle
    a.pop.root_status=lambda mods,root:(None,ongoing)
    a.drive_slice=lambda *args:{'stop':'LOCAL_SCIENTIFIC_TERMINAL','spent':7,'engine_stop_reason':'AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED'}
    seen=[]
    def council(*args):
        seen.append('COUNCIL')
        return ('NEXT_GENERATION',None)
    a.council=council
    a.mark_cycle=lambda c,root,stage:c.update(stage=stage)
    try:
        result=a.step_once(None,'/tmp/experiment',SimpleNamespace())
        assert result=='CONTINUE' and cycle['stage']=='COMPLETE' and seen==['COUNCIL']
        cycle['stage']='POPULATION'
        a.council=lambda *args:('CONFIRMED_TERMINAL','SCIENTIFIC_HOLD')
        result=a.step_once(None,'/tmp/experiment',SimpleNamespace())
        assert result=='SCIENTIFIC_TERMINAL' and cycle['stage']=='COMPLETE'
        print('PASS: local HOLD routes to council; both independent continuation and global stop supported')
    finally:
        a.current_cycle=old_current;a.pop.root_status=old_root_status
        a.drive_slice=old_drive;a.council=old_council;a.mark_cycle=old_mark


def test_council_cached_with_local_boundary():
    tmp,root,o,p=setup()
    old_snapshot=a.snapshot
    try:
        a.snapshot=lambda *args:{'cycle_number':1,'stage':'POPULATION',
            'current_research':{'status':'HOLD_WITH_RATIONALE','works':[],'head':{'events':1}}}
        Model.responses=[{'decision':'NEXT_GENERATION','rationale':'A separate independent branch remains plausible',
            'inherited_findings_considered':['Prior negative results'], 'new_scientific_delta':'No new live hypothesis',
            'remaining_opportunities':['Independent alternative mechanism'],
            'unresolved_uncertainties':['Lack of direct discrimination'], 'termination_scope':''}]
        Model.call_count=0
        mods=a.pop.gen.modules();cycle={'index':1}
        ans=a.council(mods,root,cycle,'POPULATION',SimpleNamespace(max_tokens=16000,model='mock'))
        assert ans[0]=='NEXT_GENERATION'
        assert Model.call_count==1
        # Repeated identical local scientific boundary reuses same recorded call.
        assert a.council(mods,root,cycle,'POPULATION',SimpleNamespace(max_tokens=16000,model='mock'))==ans
        assert Model.call_count==1
        print('PASS: locally terminal population asks AI for independent next generation and caches result')
    finally:
        a.snapshot=old_snapshot
        restore(tmp,o,p)

if __name__=='__main__':
    test_classification()
    test_drive_slice_reads_committed_status()
    test_population_routing()
    test_council_cached_with_local_boundary()
    print('LOCAL_SCIENCE_HOLD_OFFLINE_TESTS_PASS; paid WSL integration NOT RUN')
