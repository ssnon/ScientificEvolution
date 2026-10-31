#!/usr/bin/env python3
"""Read-only audit of G14 SYN_01 science and actual literature tool receipts.

No model/provider calls; no E2 Journal mutations. Requires local ScientificEvolution
PYTHONPATH with population_run. The full source records remain in E2 blobs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import population_run as pop

DIRECT = {
    'DIRECT_FULLTEXT_EXCERPT','DIRECT_FIGURE_OR_METHOD_EXCERPT','OA_FULLTEXT_TEXT',
    'OA_FULLTEXT_CAPTION','OA_PDF_TEXT','OA_SUPPLEMENT_TEXT',
    'DIRECT_SUPPLEMENT_EXCERPT',
}

def decode(j, blob):
    raw = j.raw(blob)
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw.decode('utf-8', errors='replace')

def short(x, limit=7000):
    text = x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,default=str)
    return text if len(text)<=limit else text[:limit]+f' … [TRUNCATED; full original in Journal, {len(text)} chars]'

def summarize_tool(j, event, idx):
    p=event['payload']
    req=decode(j,p['request_blob'])
    result=decode(j,p['result_blob'])
    arg=req.get('arguments',{}) if isinstance(req,dict) else {}
    r=result if isinstance(result,dict) else {}
    records=r.get('records') or (r.get('result') or {}).get('records') or []
    if not isinstance(records,list):records=[]
    status=r.get('status')
    evidence_class=r.get('evidence_class') or (r.get('result') or {}).get('evidence_class') or None
    def brief_row(z):
        if not isinstance(z,dict):return {'unstructured':short(z,500)}
        keys=('id','title','year','doi','source_url','best_oa_pdf_url','best_oa_landing_url',
              'evidence_class','claims_about_experiments_verified','open_access','publication_date')
        return {k:z[k] for k in keys if k in z}
    return {
        'event_seq':event['seq'], 'id':p.get('id'), 'work_id':p.get('work_id'),
        'request_kind':req.get('kind') if isinstance(req,dict) else None,
        'request_arguments':arg,
        'status':status, 'error_code':r.get('error_code'), 'detail':short(r.get('detail',''),1300),
        'evidence_class':evidence_class,
        'linked_source_id':r.get('linked_source_id'),
        'retrieval_attempts':r.get('retrieval_attempts',[]),
        'record_count':len(records), 'records':list(map(brief_row,records[:20])),
        'reported_primary_verification':r.get('primary_observation_verification'),
        'direct_fulltext_class':evidence_class in DIRECT,
        'other_result_fields':sorted(r.keys()),
        'result_excerpt':short(r,8000),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--experiment', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--allow-changed-head',action='store_true')
    a=ap.parse_args()
    exp=Path(a.experiment).expanduser().resolve()
    root=exp/'CYCLE_014'/'SYN_01'
    cycle_path=exp/'CYCLE_014'/'cycle.json'
    cycle=json.loads(cycle_path.read_text(encoding='utf-8'))
    assert cycle['index']==14, 'NOT_G14'
    assert str(root)==str(Path(cycle['peers']['SYN_01']).resolve()), 'SYN_01_ROOT_CHANGED'
    mods=pop.gen.modules()
    j,s=pop.root_status(mods,root)
    events=j._events()
    head=mods.sha(mods.canon(events[-1]))
    if not a.allow_changed_head:
        assert len(events)==1058, f'EVENT_COUNT_CHANGED:{len(events)}'
        # Verify count and source history, but do not guess an unseen last-event hash.
    un=[{'id':k,'state':v['state']} for k,v in s.model_calls.items() if v['state']!='SAVED']
    assert not un, f'UNRESOLVED_MODEL_CALLS:{un[:3]}'
    work_details=[]
    for wid,w in s.work.items():
        steps=[]
        for st in w.get('steps',[]):
            r=decode(j,st['raw_blob'])
            v={'step':st['step'],'kind':st['kind']}
            if isinstance(r,dict):
                v['call_id']=r.get('call_id');v['parse_ok']=r.get('parse_ok')
                if st['kind']=='MODEL_RESPONSE':
                    raw=r.get('text','')
                    try:
                        o=json.loads(raw)
                        v.update({'scientific_text':short(o.get('scientific_text',''),12000),
                                  'next_action':o.get('next_action'),
                                  'submitted_asset_ids':[x.get('id') for x in o.get('assets',[]) if isinstance(x,dict)],
                                  'tool_request':o.get('tool_request')})
                    except (ValueError, TypeError):v['unparsed_model_response']=short(raw,4500)
                elif st['kind']=='TOOL_RESULT':
                    x=r.get('result',{})
                    v.update({'tool_id':r.get('tool_id'),
                              'tool_status':x.get('status') if isinstance(x,dict) else None,
                              'result_excerpt':short(x,2000)})
                else:v['metadata']=r
            steps.append(v)
        work_details.append({'id':wid,'status':w['status'],'mode':w.get('mode'),
                             'operation':w.get('operation'),'question':w.get('question'),
                             'published_ids':w.get('published',[]),'steps':steps})
    recent=events[1016:]
    receipts=[summarize_tool(j,e,e['seq']) for e in recent if e['kind']=='TOOL_RECORDED']
    new_sources=[]
    for e in recent:
        if e['kind']=='SOURCE_REGISTERED':
            p=e['payload'];src=decode(j,p['blob'])
            new_sources.append({'id':p['id'],'kind':p['kind'],
                'description':p.get('description'),
                'evidence_class':src.get('evidence_class') if isinstance(src,dict) else None,
                'tool_id':src.get('tool_id') if isinstance(src,dict) else None})
    controllers=[]
    for d in s.controller_decisions:
        ob=decode(j,d['parsed_blob'])
        controllers.append({'id':d['id'],'rationale':ob.get('rationale'),
            'disposition':ob.get('disposition'),
            'actions':ob.get('actions',[])})
    result={
        'status':'G14_SYN01_READ_ONLY_SCIENCE_AUDIT',
        'peer_root':str(root),'stage':cycle['stage'],
        'journal_events':len(events),'head_sha256':head,
        'new_events':len(recent),'assets':len(s.assets),'new_live_assets':[
            {'id':e['payload'].get('id'),'claim':e['payload'].get('claim')}
            for e in recent if e['kind']=='ASSET_PUBLISHED'],
        'saved_calls':sum(x['state']=='SAVED' for x in s.model_calls.values()),
        'unresolved_calls':un,
        'tool_receipt_counts':{
            'total':len(receipts),'delivered':sum(x['status']=='DELIVERED' for x in receipts),
            'rejected':sum(x['status']=='REJECTED' for x in receipts),
            'direct_fulltext_class':sum(x['direct_fulltext_class'] for x in receipts)},
        'actual_tool_receipts':receipts,
        'new_registered_sources':new_sources,
        'works':work_details,'controller_decisions':controllers,
        'does_not_certify_primary_evidence_or_novelty':True,
        'journal_modified':False,'provider_requests_sent':0,
    }
    # Reverify before persisting read-only report.
    again=j._events()
    assert len(again)==len(events) and mods.sha(mods.canon(again[-1]))==head, 'JOURNAL_CHANGED_DURING_AUDIT'
    dest=Path(a.out).expanduser().resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,default=str)
        f.write('\n')
    print(json.dumps({'status':result['status'],'file':str(dest),
      'stage':result['stage'],'journal_events':len(events),
      'tool_receipt_counts':result['tool_receipt_counts'],
      'new_live_assets':len(result['new_live_assets']),
      'journal_unchanged':True,'provider_requests_sent':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
