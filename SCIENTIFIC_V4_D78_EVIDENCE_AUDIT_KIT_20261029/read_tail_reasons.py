#!/usr/bin/env python3
"""Read-only committed-Journal audit. Does not print raw provider/evidence blobs."""
import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--limit',type=int,default=50)
    a=p.parse_args()
    from e2core.core import EvolutionJournal
    j=EvolutionJournal(a.root.expanduser().resolve())
    s=j.verify()
    rows=j._events()
    safe={"seq","kind","id","call_id","reason","work_id","source_id","asset_id","status","state","model_call_id","original_call_id"}
    out=[]
    for e in rows[-max(1,min(a.limit,200)):]:
        q=e.get('payload') or {}
        extracted={k:v for k,v in q.items() if k in safe and isinstance(v,(str,int,bool,type(None)))}
        out.append({'seq':e.get('seq'),'kind':e.get('kind'),'detail':extracted})
    recent_pause=[{'seq':e['seq'],'reason':e.get('payload',{}).get('reason'),'call_id':e.get('payload',{}).get('call_id')}
       for e in rows if e.get('kind')=='OPERATIONAL_PAUSE'][-12:]
    unresolved=[{'call_id':k,'actor':v.get('actor'),'state':v.get('state')} for k,v in s.model_calls.items() if v.get('state')!='SAVED']
    print(json.dumps({'root':str(j.root),'verified':True,'events':len(rows),'decisions':len(s.controller_decisions),
      'last_decision':s.controller_decisions[-1]['id'] if s.controller_decisions else None,
      'active_work':[{'id':i,'mode':w.get('mode'),'status':w.get('status')} for i,w in s.work.items() if w.get('status') in {'ACTIVE','QUEUED','DEFERRED'}],
      'model_calls_not_saved':unresolved,'recent_pauses':recent_pause,'tail':out},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
