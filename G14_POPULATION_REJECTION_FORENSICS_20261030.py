#!/usr/bin/env python3
"""Read-only exact-cause audit of G14 post-parent-feedback Population segment.

Inspects the three saved-but-rejected controller plans, the Worker proposed
assets, validation records and tools. Nothing is rewritten or replayed.
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
from pathlib import Path
from collections import Counter

START=1071
EXPECTED_START_SHA='f02e43ec2b3a3c1fe475d6da8995eedb95bc0f6bcc62470ff941e049f4cde4e3'
EXPECTED_TOTAL=1101
WORK='W_P0_charge_multichannel_model_001'


def dec(j,blob):
    if not blob: return None
    raw=j.raw(blob)
    if isinstance(raw,bytes): raw=raw.decode('utf-8','replace')
    try: return json.loads(raw)
    except (ValueError,TypeError): return raw


def h(mods,rows):
    return {'events':len(rows), 'head_sha256':mods.sha(mods.canon(rows[-1])) if rows else None}


def close(identifier, pool):
    if not isinstance(identifier,str):return []
    return difflib.get_close_matches(identifier, list(pool),n=4,cutoff=0.66)


def classify_review(review,s,mods):
    rid=review.get('id') if isinstance(review,dict) else None
    actual=s.assets.get(rid) if isinstance(rid,str) else None
    decision=review.get('decision') if isinstance(review,dict) else None
    rationale=review.get('rationale') if isinstance(review,dict) else None
    import re
    # These are independent checks; the first failure can differ from full
    # controller-plan simulation if the same response also creates problems.
    return {'id':rid, 'id_exists_as_asset':bool(actual),
            'exact_asset_kind':actual.get('kind') if actual else None,
            'decision':decision,
            'decision_nonempty_string':isinstance(decision,str) and bool(decision),
            'rationale_nonempty_string':isinstance(rationale,str) and bool(rationale.strip()),
            'nearest_existing_asset_ids':close(rid,s.assets.keys()) if not actual else [],
            'matches_work_proposed_but_unregistered_asset':rid in {
                 'A_bounded_charge_tensor_intervention_001', 'A_charge_tensor_power_bound_002'}}


def parse_model_output(j,call):
    from e2core.provider import content_from_wire,strict_envelope
    raw=j.raw(call['response_blob'])
    original=content_from_wire(raw)
    parsed=strict_envelope(original)
    return parsed,original


def run(exp,out):
    import population_run as pop
    import persistent_population as pp
    import autonomous_population as aut

    if os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES':
        raise RuntimeError('THIS_AUDITOR_REQUIRES_PAID_DISABLED')
    if not (exp/'STOP_REQUESTED').exists():
        raise RuntimeError('STOP_MARKER_REQUIRED_TO_AVOID_CONCURRENT_LIVE_RUN')
    mods=pop.gen.modules()
    cycle=pp.latest_cycle(exp)
    if not cycle or cycle['index']!=14 or cycle['stage']!='POPULATION':
        raise RuntimeError('NOT_G14_POPULATION')
    j,s=pop.root_status(mods,cycle['population_root'])
    rows=j._events()
    before=h(mods,rows)
    if h(mods,rows[:START])!={'events':START,'head_sha256':EXPECTED_START_SHA}:
        raise RuntimeError('PREVIOUS_JOURNAL_PREFIX_CHANGED')
    if len(rows)!=EXPECTED_TOTAL:
        raise RuntimeError('EXPECTED_1101_EVENTS_FOUND_'+str(len(rows))+'_REVIEW_BEFORE_AUDITING')
    if any(x.get('state')!='SAVED' for x in s.model_calls.values()):
        raise RuntimeError('UNRESOLVED_MODEL_CALL_REQUIRES_MANUAL_REVIEW')
    w=s.work[WORK]
    recent=rows[START:]
    pauses=[{'seq':e['seq'],**e['payload']} for e in recent if e['kind']=='OPERATIONAL_PAUSE']
    rejects=[]
    for p in pauses:
        reason=p.get('reason','')
        if not str(reason).startswith(('CONTROLLER_PLAN_REJECTED:', 'CONTROLLER_INVALID_JSON')):continue
        cid=p.get('call_id');call=s.model_calls.get(cid)
        rec={'seq':p['seq'],'call_id':cid,'recorded_reason':reason,
             'saved_call':bool(call and call.get('state')=='SAVED')}
        if call and call.get('state')=='SAVED':
            obj,original=parse_model_output(j,call)
            rec['parse_ok']=isinstance(obj,dict)
            rec['response_chars']=len(original)
            if isinstance(obj,dict):
                rec.update({'disposition':obj.get('disposition'),
                    'rationale_excerpt':str(obj.get('rationale',''))[:2100],
                    'reviews':[classify_review(r,s,mods) for r in obj.get('reviews',[]) if isinstance(r,dict)],
                    'reviews_not_objects':sum(not isinstance(r,dict) for r in obj.get('reviews',[])),
                    'actions':[{'id':a.get('id'), 'operation':a.get('operation'),
                         'asset_ids':a.get('asset_ids'), 'work_id':a.get('work',{}).get('id') if isinstance(a.get('work'),dict) else None}
                        for a in obj.get('actions',[]) if isinstance(a,dict)],
                    'new_problems':[x.get('id') for x in obj.get('new_problems',[]) if isinstance(x,dict)]})
            else:rec['original_response_excerpt']=original[:4000]
        rejects.append(rec)
    work_steps=[]
    invalid_proposals=[]
    for st in w['steps']:
        if st['kind']=='MODEL_RESPONSE':
            raw=dec(j,st['raw_blob'])
            parsed=None
            if isinstance(raw,dict) and isinstance(raw.get('text'),str):
                try:parsed=json.loads(raw['text'])
                except ValueError:pass
            if not isinstance(parsed,dict):continue
            assets=[]
            for a in parsed.get('assets',[]):
                if not isinstance(a,dict):continue
                parents=a.get('parent_ids',[])
                missing=[p for p in parents if p not in s.assets] if isinstance(parents,list) else ['NON_LIST']
                unauthorized=[p for p in parents if p not in set(w['asset_input_ids'])|set(w['published'])] if isinstance(parents,list) else ['NON_LIST']
                rec={'id':a.get('id'),'kind':a.get('kind'),'parent_ids':parents,
                    'missing_parent_ids':missing,'unauthorized_parent_ids':unauthorized,
                    'closest_to_missing':{p:close(p,s.assets.keys()) for p in missing if isinstance(p,str)},
                    'registered_in_state':a.get('id') in s.assets,
                    'claim_excerpt':str(a.get('claim',''))[:1000]}
                assets.append(rec)
                if not rec['registered_in_state']:invalid_proposals.append({'step':st['step'],**rec})
            if st['step']>6:
                work_steps.append({'step':st['step'],'kind':'MODEL_RESPONSE','call_id':raw.get('call_id'),
                    'scientific_text':str(parsed.get('scientific_text',''))[:6500],
                    'next_action':parsed.get('next_action'),'assets':assets,
                    'new_problems':[p.get('id') for p in parsed.get('new_problems',[]) if isinstance(p,dict)],
                    'tool_request':parsed.get('tool_request')})
        elif st['kind']=='OUTPUT_VALIDATION' and st['step']>6:
            work_steps.append({'step':st['step'],'kind':st['kind'],
                               'validation':dec(j,st['raw_blob'])})
        elif st['kind']=='TOOL_RESULT' and st['step']>6:
            v=dec(j,st['raw_blob'])
            toolres=v.get('result',{}) if isinstance(v,dict) else {}
            work_steps.append({'step':st['step'],'kind':'TOOL_RESULT',
                               'tool_id':v.get('tool_id') if isinstance(v,dict) else None,
                               'status':toolres.get('status') if isinstance(toolres,dict) else None,
                               'evidence_class':toolres.get('evidence_class') if isinstance(toolres,dict) else None,
                               'error_code':toolres.get('error_code') if isinstance(toolres,dict) else None,
                               'result_excerpt':json.dumps(toolres,ensure_ascii=False,default=str)[:6000]})
    new_tools=[]
    for e in recent:
        if e['kind']!='TOOL_RECORDED':continue
        req=dec(j,e['payload'].get('request_blob'))
        response=dec(j,e['payload'].get('result_blob'))
        new_tools.append({'seq':e['seq'],'kind':req.get('kind') if isinstance(req,dict) else None,
             'action':(req.get('arguments') or {}).get('action') if isinstance(req,dict) else None,
             'status':response.get('status') if isinstance(response,dict) else None,
             'evidence_class':response.get('evidence_class') if isinstance(response,dict) else None,
             'error_code':response.get('error_code') if isinstance(response,dict) else None})
    report={'status':'G14_CONTROLLER_REJECTION_FORENSICS_READ_ONLY',
            'head':before,'new_events':len(recent),
            'new_event_counts':dict(Counter(e['kind'] for e in recent)),
            'controller_rejections':rejects,'controller_rejection_count':len(rejects),
            'work':{'id':WORK,'status':w['status'],'asset_input_ids':w['asset_input_ids'],
                    'published':w['published'],'steps_after_previous_snapshot':work_steps},
            'unregistered_proposals':invalid_proposals,
            'new_tool_receipts':new_tools,'new_live_assets': [e['payload']['id'] for e in recent if e['kind']=='ASSET_PUBLISHED'],
            'journal_unchanged':h(mods,j._events())==before,
            'provider_requests_sent':0}
    if not report['journal_unchanged']:raise RuntimeError('JOURNAL_CHANGED_DURING_READ')
    if out.exists():raise RuntimeError('OUTPUT_EXISTS_REFUSE_OVERWRITE:'+str(out))
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    summary={'status':report['status'],'out':str(out),'head':before,
            'controller_rejections':len(rejects),
            'invalid_reviews_per_rejection':[sum(not r['id_exists_as_asset'] for r in x.get('reviews',[])) for x in rejects],
            'unregistered_worker_proposals':len(invalid_proposals),
            'new_live_assets':len(report['new_live_assets']),
            'new_tool_receipts':new_tools,
            'journal_unchanged':True,'provider_requests_sent':0}
    print(json.dumps(summary,ensure_ascii=False,indent=2))


def selftest():
    class S:pass
    s=S();s.assets={'A_CARRY_f1ddae09f1c863fc3ee9c6f':{'kind':'COUNTEREXAMPLE'}}
    report=classify_review({'id':'A_CARRY_f1ddae09f1c863fc3ee9c6fb','decision':'CONDITIONAL','rationale':'x'},s,None)
    assert report['id_exists_as_asset'] is False
    assert report['nearest_existing_asset_ids']==['A_CARRY_f1ddae09f1c863fc3ee9c6f']
    assert close('A_xyz',[])==[]
    assert h(type('Mods',(),{'sha':lambda self,x:'a','canon':lambda self,x:b'b'})(),[{'kind':'A'}])['events']==1
    print('G14_CONTROLLER_REJECTION_AUDIT_SELFTEST_OK')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selftest',action='store_true')
    p.add_argument('--experiment')
    p.add_argument('--out')
    a=p.parse_args()
    if a.selftest:selftest()
    else:
        if not a.experiment or not a.out:p.error('--experiment and --out required')
        run(Path(a.experiment).expanduser().resolve(strict=True),Path(a.out).expanduser())
