#!/usr/bin/env python3
"""Read-only replay-risk inventory. Never dispatches models or alters Journal."""
import argparse,json
from pathlib import Path
from e2core.core import EvolutionJournal


def inspect(root):
    j=EvolutionJournal(root);s=j.verify()
    controller_used={d['call_id'] for d in s.controller_decisions}
    worker_used=set()
    for w in s.work.values():
        for rec in w.get('steps',[]):
            if rec.get('kind')!='MODEL_RESPONSE':continue
            try:
                row=json.loads(j.raw(rec['raw_blob']))
                if row.get('call_id'):worker_used.add(row['call_id'])
            except (ValueError,TypeError,KeyError):pass
    # An NVT, PMI or OPP can be accepted via Controller context without being
    # a controller's decision-call ID. They remain visible for provenance.
    items=[]
    for ident,rec in s.model_calls.items():
        if rec['state']!='SAVED':continue
        stored=json.loads(j.raw(rec['request_blob']))
        try:
            payload=json.loads(stored['messages'][1]['content'])
        except (ValueError,KeyError,IndexError,TypeError):payload={}
        receipt=payload.get('science_memory_request_receipt',{}) if isinstance(payload,dict) else {}
        kind=('controller_decision' if ident in controller_used else
              'worker_step' if ident in worker_used else 'not_directly_committed_as_decision_or_worker_step')
        items.append({'call_id':ident,'actor':rec.get('actor'),
            'saved_request_sha256':rec['request_blob'],
            'recorded_in':kind,
            'stored_memory_view_version':receipt.get('version'),
            'stored_original_precompression_sha256':receipt.get('original_payload_sha256'),
            'stored_model':stored.get('model'),
            'stored_max_tokens':stored.get('max_tokens')})
    return {'status':'READ_ONLY_SAVED_CALL_REPLAY_INVENTORY',
        'journal_root':str(j.root),'journal_events':len(j._events()),
        'controller_decisions':len(s.controller_decisions),
        'unresolved_model_calls':[{'id':i,'state':r['state']} for i,r in s.model_calls.items() if r['state']!='SAVED'],
        'recent_saved_calls':items[-25:],
        'note':'Potential replay candidates only; actual conflicting call ID requires runtime compare. No model requests were sent.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--journal',required=True)
    p.add_argument('--out')
    a=p.parse_args()
    result=inspect(Path(a.journal).expanduser().resolve())
    if a.out:
        path=Path(a.out).expanduser().absolute()
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False)
        print(json.dumps({'status':result['status'],'report':str(path),'journal_unchanged':True}))
    else:print(json.dumps(result,indent=2,ensure_ascii=False))
