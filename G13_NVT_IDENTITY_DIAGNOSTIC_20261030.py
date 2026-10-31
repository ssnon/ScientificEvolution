#!/usr/bin/env python3
"""Read-only report: compare next new NVT with prior SAVED NVT input.

No provider instance with external credentials; relies on the existing
safe_resume_probe's ReadonlyJournal and model-gateway intercept. It does not
modify the scientific Journal or reinterpret a saved model response.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys


def serialized(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(x):
    return hashlib.sha256(serialized(x).encode('utf-8')).hexdigest()


def chars(x):
    return len(serialized(x))


def row_ids(rows):
    if not isinstance(rows, list):
        return None
    return [r.get('id',r.get('asset_id',r.get('evidence_id'))) for r in rows if isinstance(r,dict)]


def compare_payload(previous, current):
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return {'comparison_supported': False}
    all_keys=sorted(set(previous)|set(current))
    changes=[]
    for k in all_keys:
        a=previous.get(k);b=current.get(k)
        if a==b:
            continue
        detail={'field':k,'previous_sha256':digest(a),'current_sha256':digest(b),
                'previous_chars':chars(a),'current_chars':chars(b)}
        if k not in previous:detail['state']='NEW_FIELD'
        elif k not in current:detail['state']='REMOVED_FIELD'
        else:detail['state']='VALUE_CHANGED'
        if isinstance(a,dict) and isinstance(b,dict):
            detail['changed_direct_children']=sorted(x for x in set(a)|set(b) if a.get(x)!=b.get(x))[:80]
        if isinstance(a,list) and isinstance(b,list):
            detail['previous_count']=len(a);detail['current_count']=len(b)
            old=row_ids(a);new=row_ids(b)
            if old is not None and new is not None:
                detail['ids_removed']=sorted(set(old)-set(new),key=str)[:15]
                detail['ids_added']=sorted(set(new)-set(old),key=str)[:15]
                detail['common_ids_same_order']=old==new
                detail['modified_row_count_if_id_order_unchanged']=(sum(x!=y for x,y in zip(a,b)) if old==new else None)
        changes.append(detail)
    core=('program','target_claims','evidence','original_success_criterion')
    return {'comparison_supported':True, 'previous_payload_sha256':digest(previous),
            'current_payload_sha256':digest(current),
            'core_scientific_fields_identical':all(previous.get(x)==current.get(x) for x in core),
            'prior_working_problem_state_identical':previous.get('prior_working_problem_state')==current.get('prior_working_problem_state'),
            'source_policy_identical':previous.get('source_policy')==current.get('source_policy'),
            'changed_fields':changes}


def diagnose(experiment,model,max_tokens):
    # Delay all project imports until this method: the pure diff is testable
    # without any runtime dependencies or external network.
    import safe_resume_probe as sr
    from pending_replay_probe import StopProbe
    base=sr.ProbeModel
    class DiagnosticModel(base):
        def call(self,ident,actor,work_id,system,payload):
            calls=self.j.verify().model_calls
            if ident not in calls and ident.startswith('NVT_'):
                items=[]
                for cid,rec in calls.items():
                    if not cid.startswith('NVT_') or rec.get('state')!='SAVED':continue
                    try:
                        saved_wire=json.loads(self.j.raw(rec['request_blob']))
                        saved_input=json.loads(saved_wire['messages'][1]['content'])
                        cmp=compare_payload(saved_input,payload)
                        items.append({'call_id':cid,'saved_request_sha256':rec['request_blob'],
                                      'saved_model':saved_wire.get('model'),
                                      'system_prompt_identical':saved_wire['messages'][0]['content']==system,
                                      **cmp})
                    except (ValueError,IndexError,KeyError,TypeError) as e:
                        items.append({'call_id':cid,'unreadable_request_error':type(e).__name__})
                latest=items[-6:]
                raise StopProbe({'status':'NEW_NVT_INPUT_DIFF_NO_PAID',
                    'next_call_id':ident,'actor':actor,'new_input_sha256':digest(payload),
                    'new_input_chars':chars(payload),'recent_saved_nvt_count_compared':len(latest),
                    'latest_saved_nvt_diffs':list(reversed(latest)),
                    'saved_replays_before_new_nvt':list(self.history),
                    'any_prior_nvt_exact_input':any(x.get('previous_payload_sha256')==digest(payload) for x in items),
                    'provider_requests_sent':0,'journal_unchanged':True,
                    'warning':'Comparison only. Never authorize saved-response reuse without exact provider wire agreement.'})
            return super().call(ident,actor,work_id,system,payload)
    sr.ProbeModel=DiagnosticModel
    try:
        return sr.probe(experiment,model,max_tokens)
    finally:
        sr.ProbeModel=base


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',required=True)
    p.add_argument('--model',default='openai/gpt-5.6-luna')
    p.add_argument('--max-tokens',type=int,default=16000)
    args=p.parse_args()
    try:out=diagnose(args.experiment,args.model,args.max_tokens)
    except BaseException as exc:
        out={'status':'DIAGNOSTIC_SETUP_ERROR','error_type':type(exc).__name__,
             'reason':str(exc),'provider_requests_sent':0}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if out.get('status')=='NEW_NVT_INPUT_DIFF_NO_PAID' else 3


if __name__=='__main__':sys.exit(main())
