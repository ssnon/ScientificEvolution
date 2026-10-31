#!/usr/bin/env python3
"""Free read-only probe of the ACTUAL pending V3 Controller sequence.

No provider client is constructed; every Saved call is answered from the
immutable E2 Journal. A NEW call stops the probe before provider dispatch.
The Journal proxy forbids append/blob even on failed validators.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from types import SimpleNamespace

import population_run as pop
import frontier_runtime as fr
import autonomous_population as aut
import memory_bridge as mm
from e2core.core import canon, sha
from e2core.provider import content_from_wire

class StopProbe(Exception):
    def __init__(self, record):
        super().__init__(record['status']);self.record=record

class ReadonlyJournal:
    def __init__(self,j):self._j=j;self.root=j.root
    def verify(self):return self._j.verify()
    def raw(self,h):return self._j.raw(h)
    def _events(self):return self._j._events()
    def input_for(self,*a,**kw):return self._j.input_for(*a,**kw)
    def append(self,*a,**kw):raise StopProbe({'status':'READONLY_MUTATION_PREVENTED','attempt':'append'})
    def blob(self,*a,**kw):raise StopProbe({'status':'READONLY_MUTATION_PREVENTED','attempt':'blob'})

class ProbeModel:
    def __init__(self,j,model,max_tokens):
        self.j=j;self.model=model;self.max_tokens=max_tokens;self.history=[]
    def call(self,ident,actor,work_id,system,payload):
        rec=self.j.verify().model_calls.get(ident)
        if rec is None:
            raise StopProbe({'status':'NEXT_MODEL_CALL_IS_NEW','next_call_id':ident,
                 'previous_saved_calls_replayed':self.history,
                 'zero_provider_requests_sent':True})
        try:
            safe=mm.replay_payload_for_saved(self,ident,actor,work_id,system,payload)
        except Exception as exc:
            raise StopProbe({'status':'PENDING_REPLAY_BLOCKED',
                'conflicting_call_id':ident,'error_type':type(exc).__name__,
                'reason':str(exc),'saved_calls_replayed_before_collision':self.history,
                'zero_provider_requests_sent':True}) from exc
        request={'model':self.model,'temperature':0.7,'max_tokens':self.max_tokens,
           'response_format':{'type':'json_object'},'messages':[
             {'role':'system','content':system},
             {'role':'user','content':json.dumps(safe,ensure_ascii=False,sort_keys=True,allow_nan=False)}]}
        if sha(canon(request))!=rec['request_blob']:
            raise StopProbe({'status':'PENDING_REPLAY_WIRE_MISMATCH',
                  'call_id':ident,'zero_provider_requests_sent':True})
        self.history.append(ident)
        return content_from_wire(self.j.raw(rec['response_blob']))

def probe(experiment,model,max_tokens):
    mods=pop.gen.modules()
    root=Path(experiment).expanduser().resolve()
    cycle,cp=__import__('evolution_frontier')._current_root(root)
    j=mods.J(cp)
    initial=j.verify()
    event_count=len(j._events())
    head=sha(canon(j._events()[-1]))
    if any(v['state']!='SAVED' for v in initial.model_calls.values()):
        return {'status':'UNRESOLVED_MODEL_CALL_DO_NOT_RESTART','zero_provider_requests_sent':True}
    # Ask only the actual Controller that would run next, independent of paid calls.
    import e2core.engine as engine
    read_only=ReadonlyJournal(j)
    model_gateway=ProbeModel(read_only,model,max_tokens)
    scope=SimpleNamespace(j=read_only,model=model_gateway,_native_tool_contract=True)
    ident=engine.Engine._next_controller_id(scope)
    with fr.activate(mods,aut),mm.activate(mods):
        try:
            outcome=mods.v3.controller_v3(scope,ident)
            data={'status':'CONTROLLER_PROBE_RETURNED_WITHOUT_NEW_CALL',
                  'outcome':outcome,'saved_calls_replayed':model_gateway.history}
        except StopProbe as stop:
            data=stop.record
        except Exception as exc:
            data={'status':'PROBE_UNEXPECTED_ERROR','error_type':type(exc).__name__,
                  'detail':str(exc),'saved_calls_replayed':model_gateway.history}
    events_now=j._events()
    if len(events_now)!=event_count or sha(canon(events_now[-1]))!=head:
        raise RuntimeError('READ_ONLY_PROBE_JOURNAL_CHANGED_ABORT')
    return {'generation':cycle['index'],'journal_root':str(cp),
            'controller_attempt_id':ident,'original_head_sha256':head,
            'original_event_count':event_count,'original_journal_unchanged':True,
            'provider_requests_sent':0,**data}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',required=True)
    p.add_argument('--model',default='openai/gpt-5.6-luna')
    p.add_argument('--max-tokens',type=int,default=16000)
    a=p.parse_args()
    try:
        out=probe(a.experiment,a.model,a.max_tokens)
    except Exception as exc:
        out={'status':'PROBE_SETUP_ERROR','error_type':type(exc).__name__,'detail':str(exc),
             'provider_requests_sent':0}
    print(json.dumps(out,ensure_ascii=False,indent=2),flush=True)
    sys.exit(0 if out['status']=='NEXT_MODEL_CALL_IS_NEW' else 3)
