#!/usr/bin/env python3
"""G14 POPULATION science delta auditor; read-only, no API/model calls.

Requires existing ScientificEvolution imports (population_run, persistent_population,
 autonomous_population). Does not import the experimental PDF bridge, as this audit
 examines recorded execution rather than providing new runtime tools.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import population_run as pop
import persistent_population as pp
import autonomous_population as aut

EXPECTED=(1028,'fe1b3b96176c62705dd512ea4693eaa40a4e499f62afde4763974e9fcc91f1a2')
DIRECT_CLASSES={'OA_PDF_TEXT','OA_FULLTEXT_TEXT','OA_FULLTEXT_CAPTION','OA_SUPPLEMENT_TEXT'}

def decode(j,blob):
    if not blob:return None
    raw=j.raw(blob)
    if isinstance(raw,bytes):raw=raw.decode('utf-8','replace')
    try:return json.loads(raw)
    except (ValueError,TypeError):return raw

def truncate(v,n=14000):
    t=v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,default=str)
    if len(t)>n:return t[:n]+f' [TRUNCATED; original length={len(t)} in Journal]'
    return t

def head(mods,events):
    return {'events':len(events),'head_sha256':mods.sha(mods.canon(events[-1])) if events else None}

def get_step(j,step):
    raw=decode(j,step.get('raw_blob'))
    out={'step':step.get('step'),'kind':step.get('kind')}
    if step['kind']=='MODEL_RESPONSE':
        if not isinstance(raw,dict):
            out['unparsed_response']=truncate(raw,11000);return out
        src=raw.get('text')
        try:v=json.loads(src) if isinstance(src,str) else src
        except (ValueError,TypeError):v=None
        if not isinstance(v,dict):
            out['unparsed_response']=truncate(src,11000);return out
        out.update({'call_id':raw.get('call_id'),'next_action':v.get('next_action'),
          'scientific_text':truncate(v.get('scientific_text',''),24000),
          'tool_request':v.get('tool_request'),
          'submitted_assets':[a.get('id') for a in v.get('assets',[]) if isinstance(a,dict)],
          'submitted_problems':[x.get('id') for x in v.get('new_problems',[]) if isinstance(x,dict)]})
    elif step['kind']=='TOOL_RESULT':
        r=raw.get('result',{}) if isinstance(raw,dict) else {}
        out.update({'tool_id':raw.get('tool_id') if isinstance(raw,dict) else None,
                    'result_status':r.get('status') if isinstance(r,dict) else None,
                    'result_excerpt':truncate(r,15000)})
    else:out['validation_metadata']=truncate(raw,9000)
    return out

def receipt(j,event):
    p=event['payload'];req=decode(j,p.get('request_blob'));res=decode(j,p.get('result_blob'))
    req=req if isinstance(req,dict) else {};res=res if isinstance(res,dict) else {}
    nested=res.get('result') if isinstance(res.get('result'),dict) else {}
    cls=res.get('evidence_class') or nested.get('evidence_class')
    return {'seq':event.get('seq'),'tool_id':p.get('id'),'work_id':p.get('work_id'),
       'kind':req.get('kind'),'request':req.get('arguments'),
       'status':res.get('status'),'error_code':res.get('error_code'),
       'evidence_class':cls,'verified_pdf_or_fulltext':res.get('status')=='DELIVERED' and cls in DIRECT_CLASSES,
       'source_url':res.get('source_url') or nested.get('source_url'),
       'source_sha256':res.get('source_sha256') or nested.get('source_sha256'),
       'page':res.get('page') or nested.get('page'),
       'retrieval_attempts':res.get('retrieval_attempts') or nested.get('retrieval_attempts') or [],
       'result':truncate(res,21000)}

def asset_details(s,aid):
    a=s.assets[aid]
    out={key:a.get(key) for key in ('id','kind','claim','scope','assumptions','predictions',
            'limitations','delta_from_parents','parent_ids','work_id','source_ids','status','certification')}
    out['parents']=[{'id':x,'kind':s.assets.get(x,{}).get('kind'),
         'claim_excerpt':truncate(s.assets.get(x,{}).get('claim',''),1500)} for x in a.get('parent_ids',[])]
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--experiment',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args();exp=Path(args.experiment).expanduser().resolve()
    cycle=pp.latest_cycle(exp)
    assert cycle and cycle['index']==14 and cycle['stage']=='POPULATION', 'EXPECTED_G14_POPULATION'
    mods=pop.gen.modules();aut.meta_check(mods,exp)
    j,s=pop.root_status(mods,cycle['population_root']);events=j._events()
    assert head(mods,events[:EXPECTED[0]])=={'events':EXPECTED[0], 'head_sha256':EXPECTED[1]},'PRE_RESEARCH_PREFIX_CHANGED'
    assert len(s.assets)>=417,'MISSING_IMPORTED_ASSETS'
    assert not [cid for cid,v in s.model_calls.items() if v['state']!='SAVED'],'UNRESOLVED_PAID_CALLS'
    start=events[:EXPECTED[0]];new=events[EXPECTED[0]:]
    prev_assets=set()
    for e in start:
        if e['kind'] in ('ASSET_PUBLISHED','HISTORICAL_ASSET_INDEXED'):
            prev_assets.add(e['payload']['id'])
    new_a=[e['payload']['id'] for e in new if e['kind'] in ('ASSET_PUBLISHED','HISTORICAL_ASSET_INDEXED')]
    receipts=[receipt(j,e) for e in new if e['kind']=='TOOL_RECORDED']
    recent_work={e['payload']['id'] for e in new if e['kind']=='WORK_STARTED'}
    active_work=[w for w in s.work.values() if w['status'] in ('ACTIVE','QUEUED','DEFERRED')]
    interesting=[]
    for e in new:
        if ('CONTROLLER' in e['kind'] or 'VALIDATION' in e['kind'] or 'REJECT' in e['kind']):
            item={'seq':e.get('seq'),'kind':e['kind'],'payload':{}}
            for k,v in e.get('payload',{}).items():
                if k.endswith('_blob'):item['payload'][k]=v
                else:item['payload'][k]=v
            interesting.append(item)
    source_rows=[]
    for e in new:
        if e['kind']!='SOURCE_REGISTERED':continue
        p=e['payload'];v=decode(j,p.get('blob'))
        source_rows.append({'id':p.get('id'),'kind':p.get('kind'),
            'description':p.get('description'),
            'evidence_class':v.get('evidence_class') if isinstance(v,dict) else None,
            'tool_id':v.get('tool_id') if isinstance(v,dict) else None})
    outcome={'status':'G14_POPULATION_SCIENCE_DELTA_READ_ONLY',
        'phase':cycle['stage'],'population_root':str(j.root),
        'initial_head':head(mods,start),'current_head':head(mods,events),
        'new_event_counts':dict(Counter(e['kind'] for e in new)),
        'initial_imported_assets':417,'current_asset_count':len(s.assets),
        'new_asset_ids':new_a,'new_assets':[asset_details(s,x) for x in new_a],
        'controller_decisions':[decode(j,d['parsed_blob']) for d in s.controller_decisions],
        'controller_or_rejection_events':interesting,
        'work_states':{k:w['status'] for k,w in s.work.items()},
        'works':[{'id':w.get('id'),'status':w.get('status'),'mode':w.get('mode'),
           'operation':w.get('operation'),'question':w.get('question'),
           'asset_input_ids':w.get('asset_input_ids'),
           'published':w.get('published'),'steps':[get_step(j,x) for x in w.get('steps',[])]}
           for w in active_work if w['id'] in recent_work or w['status']=='ACTIVE'],
        'tools_since_population_start':receipts,
        'fulltext_receipts':sum(t['verified_pdf_or_fulltext'] for t in receipts),
        'source_receipts_since_population_start':source_rows,
        'unresolved_model_calls':[],
        'journal_modified':False,'provider_requests_sent':0,
        'science_certified':False,
        'caution':'Code EXECUTED is only execution truth; literary DELIVERED metadata is not full-text evidence. Rejected controller plan is not a committed decision.'}
    assert head(mods,j._events())==outcome['current_head'],'JOURNAL_CHANGED_DURING_AUDIT'
    out=Path(args.out).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:json.dump(outcome,f,ensure_ascii=False,indent=2,default=str);f.write('\n')
    print(json.dumps({'status':outcome['status'],'report':str(out),
       'events':outcome['current_head']['events'],'assets':len(s.assets),
       'works':outcome['work_states'],
       'new_asset_ids':new_a,
       'tool_statuses':dict(Counter(str(r['kind'])+'/'+str(r['status'])+'/'+str(r['evidence_class']) for r in receipts)),
       'fulltext_receipts':outcome['fulltext_receipts'],
       'journal_modified':False,'provider_requests_sent':0},indent=2,ensure_ascii=False))

if __name__=='__main__':main()
