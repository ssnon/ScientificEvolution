#!/usr/bin/env python3
"""No-cost end-to-end probe: saved NVT/PMI must replay, OPP_D00008 must be NEW.

This uses the actual Controller code on an immutable Journal wrapper; it never
instantiates a paid DurableModel and does not mutate the research source.
"""
from __future__ import annotations
import argparse,contextlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import population_run as pop
import frontier_runtime as fr
import autonomous_population as aut
import memory_bridge as mm
import safe_attempt as sa
import persistent_population as pp
import population_resume as compat
from pending_replay_probe import ReadonlyJournal,ProbeModel,StopProbe
from e2core.core import sha,canon


def probe(experiment,model,max_tokens):
    mods=pop.gen.modules()
    root=Path(experiment).expanduser().resolve()
    cycle,cp=__import__('evolution_frontier')._current_root(root)
    j=mods.J(cp)
    initial=j.verify();old_events=j._events();original_head=sha(canon(old_events[-1]))
    if any(c['state']!='SAVED' for c in initial.model_calls.values()):
        return {'status':'PROBE_BLOCKED_UNRESOLVED_CALL','provider_requests_sent':0}
    readonly=ReadonlyJournal(j)
    gateway=ProbeModel(readonly,model,max_tokens)
    scope=SimpleNamespace(j=readonly,model=gateway,_native_tool_contract=True)
    import e2core.engine as engine
    # Exact nested contexts of autonomous_population.drive_slice ->
    # generational_run.drive(phase='syn'), not just the V3 Controller alone.
    with fr.activate(mods,aut),mm.activate(mods),sa.activate(mods,j) as info:
        ident=engine.Engine._next_controller_id(scope)
        with pp.population_science_bridge(mods,cp,tuple(cycle['peers'])), \
             compat.historical_input_compat(mods,cp), \
             mods.v4.runtime(), mods.v3.v3_runtime():
            before=mods.v3._external_context
            _,cohort=pop.gen.cohort_context_bridge(mods)
            mods.v3._external_context=cohort
            try:
                try:
                    mods.v3.controller_v3(scope,ident)
                    result={'status':'UNEXPECTED_CONTROLLER_COMPLETED_NO_NEW_CALL',
                            'saved_replays':gateway.history}
                except StopProbe as e:
                    result=e.record
                except Exception as e:
                    result={'status':'PROBE_REJECTED','type':type(e).__name__,'detail':str(e),
                            'saved_replays':gateway.history,'provider_requests_sent':0}
            finally:
                mods.v3._external_context=before
    current=j._events()
    if sha(canon(current[-1]))!=original_head or len(current)!=len(old_events):
        raise RuntimeError('ORIGINAL_JOURNAL_CHANGED_DURING_READONLY_PROBE')
    result.update({'generation':cycle['index'],'controller_attempt_id':ident,
        'journal_events':len(old_events),'journal_head_sha256':original_head,
        'journal_unchanged':True,'safety':info,'provider_requests_sent':0})
    if (result['status']=='NEXT_MODEL_CALL_IS_NEW' and result.get('next_call_id')=='OPP_'+ident
            and 'NVT_014f30d89ea5bfb2a0a23c1' in result.get('previous_saved_calls_replayed',[])
            and 'PMI_ede5a8558471f09cff0fa6e' in result.get('previous_saved_calls_replayed',[])):
        result['status']='SAFE_NEW_OPPORTUNITY_READY_NO_PAID'
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--experiment',required=True)
    a.add_argument('--model',default='openai/gpt-5.6-luna')
    a.add_argument('--max-tokens',type=int,default=16000)
    x=a.parse_args()
    try:r=probe(x.experiment,x.model,x.max_tokens)
    except Exception as ex:r={'status':'PROBE_SETUP_ERROR','type':type(ex).__name__,
                             'detail':str(ex),'provider_requests_sent':0}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r['status']=='SAFE_NEW_OPPORTUNITY_READY_NO_PAID' else 3)
