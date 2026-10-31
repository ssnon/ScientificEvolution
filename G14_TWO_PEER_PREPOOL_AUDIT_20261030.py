#!/usr/bin/env python3
"""G14 SYN_01 final interval and both peers' scientific receipts, read only.

Uses installed ScientificEvolution runtime, consumes no model calls, modifies no
research Journal. The exported report is not science certification.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import population_run as pop
import persistent_population as pp
import autonomous_population as aut

EXPECTED_BASE=(1016,'98d563bd4eeba986f96225fde786d1149e3db6fec644b322bc90eedc56df47b9')
EXPECTED_SYN01_PRIOR=(1058,'695187b5ab98889dc8808a9160667b0479e14925a341db00b2a030d7ace6e59f')
EXPECTED_SYN02=(1054,'717f1b88ceec7a9338e4a7e5a92119e55ac0fa400ff3c9e876fcc1c7ae8d2dda')
FULLTEXT={'OA_PDF_TEXT','OA_FULLTEXT_TEXT','OA_FULLTEXT_CAPTION','OA_SUPPLEMENT_TEXT'}

def dec(j,blob):
    value=j.raw(blob)
    if isinstance(value,bytes):value=value.decode('utf-8','replace')
    try:return json.loads(value)
    except (ValueError,TypeError):return value

def clip(value,n=10000):
    t=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,default=str)
    if len(t)>n:return t[:n]+f' [TRUNCATED {len(t)} chars; original preserved in Journal]'
    return t

def digest(mods,j,events=None):
    es=events if events is not None else j._events()
    return {'events':len(es),'head_sha256':mods.sha(mods.canon(es[-1])) if es else None}

def assure(mods,j,cnt,sha):
    assert digest(mods,j)=={'events':cnt,'head_sha256':sha},'JOURNAL_SNAPSHOT_MISMATCH:'+str(j.root)

def tool_receipt(j,e):
    p=e['payload']; req=dec(j,p['request_blob']);res=dec(j,p['result_blob'])
    req=req if isinstance(req,dict) else {};res=res if isinstance(res,dict) else {}
    nested=res.get('result') if isinstance(res.get('result'),dict) else {}
    evidence=res.get('evidence_class') or nested.get('evidence_class')
    return {'event_seq':e.get('seq'),'tool_id':p.get('id'),'work_id':p.get('work_id'),
      'request_kind':req.get('kind'),'request_arguments':req.get('arguments'),
      'status':res.get('status'),'evidence_class':evidence,
      'error_code':res.get('error_code'),'exception_type':res.get('exception_type'),
      'source_url':res.get('source_url') or nested.get('source_url'),
      'source_sha256':res.get('source_sha256') or nested.get('source_sha256'),
      'page':res.get('page') or nested.get('page'),'page_count':res.get('page_count') or nested.get('page_count'),
      'page_text_sha256':res.get('page_text_sha256') or nested.get('page_text_sha256'),
      'actual_page_text_evidence':res.get('status')=='DELIVERED' and evidence in FULLTEXT,
      'retrieval_attempts':res.get('retrieval_attempts',[]),
      'linked_source_id':res.get('linked_source_id'),
      'returned_data_excerpt':clip(res,14000)}

def step_detail(j,st):
    v=dec(j,st['raw_blob']);v=v if isinstance(v,dict) else {}
    out={'step':st.get('step'),'kind':st.get('kind')}
    if st.get('kind')=='MODEL_RESPONSE':
        raw=v.get('text','')
        try:science=json.loads(raw)
        except (TypeError,ValueError):out['unparsed_response']=clip(raw,10000)
        else:
            out.update({'call_id':v.get('call_id'),'next_action':science.get('next_action'),
              'scientific_text':clip(science.get('scientific_text',''),20000),
              'tool_request':science.get('tool_request'),
              'asset_ids_requested':[a.get('id') for a in science.get('assets',[]) if isinstance(a,dict)],
              'new_problem_ids_requested':[a.get('id') for a in science.get('new_problems',[]) if isinstance(a,dict)]})
    elif st.get('kind')=='TOOL_RESULT':
        r=v.get('result',{})
        out.update({'tool_id':v.get('tool_id'),'result_status':r.get('status') if isinstance(r,dict) else None,
                    'result_excerpt':clip(r,6500)})
    else:out['validation_metadata']=v
    return out

def work_detail(j,w):
    return {'id':w.get('id'),'status':w.get('status'),'mode':w.get('mode'),'operation':w.get('operation'),
      'question':w.get('question'),'published_ids':w.get('published',[]),'outcome':w.get('outcome'),
      'steps':[step_detail(j,st) for st in w.get('steps',[])]}

def asset_detail(s,aid):
    a=s.assets[aid]
    parents=[{'id':pid,'kind':s.assets.get(pid,{}).get('kind'),
              'origin':s.assets.get(pid,{}).get('origin'),
              'claim_excerpt':clip(s.assets.get(pid,{}).get('claim',''),1300)}
             for pid in a.get('parent_ids',[])]
    return {key:a.get(key) for key in ('id','kind','claim','scope','assumptions','predictions',
         'limitations','delta_from_parents','parent_ids','work_id','source_ids','certification','status')}|{'parents':parents}

def meta_decisions(j,s,gen):
    found=[]
    for d in s.controller_decisions:
        result=dec(j,d['parsed_blob'])
        call=s.model_calls.get(d['call_id'],{})
        wire=dec(j,call['request_blob']) if call.get('request_blob') else {}
        try: ctx=json.loads(wire['messages'][1]['content'])
        except (KeyError,IndexError,TypeError,ValueError):continue
        if ctx.get('stage')!='PEER' or ctx.get('cycle_number')!=gen:continue
        found.append({'peer':ctx.get('peer_name'),'id':d['id'],
           'decision':result.get('decision'),'rationale':result.get('rationale')})
    return found

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    exp=Path(args.experiment).expanduser().resolve()
    cycle=pp.latest_cycle(exp)
    assert cycle and cycle['index']==14 and cycle['stage']=='PEERS', 'G14_NOT_AT_EXPECTED_PEERS_STAGE'
    mods=pop.gen.modules(); aut.meta_check(mods,exp)
    base,bs=pop.root_status(mods,cycle['base']);assure(mods,base,*EXPECTED_BASE)
    assert len(bs.assets)==413 and digest(mods,base)==cycle['base_head'],'G14_BASE_DRIFT'
    j1,s1=pop.root_status(mods,cycle['peers']['SYN_01'])
    j2,s2=pop.root_status(mods,cycle['peers']['SYN_02']);assure(mods,j2,*EXPECTED_SYN02)
    events=j1._events();assert len(events)==1099,'SYN01_EXPECTED_1099_EVENTS_GOT_'+str(len(events))
    assert digest(mods,j1,events[:EXPECTED_SYN01_PRIOR[0]])=={'events':EXPECTED_SYN01_PRIOR[0],
         'head_sha256':EXPECTED_SYN01_PRIOR[1]},'SYN01_PRIOR_PREFIX_CHANGED'
    assert events[:EXPECTED_BASE[0]]==base._events(),'SYN01_BASE_PREFIX_CHANGED'
    assert len(s1.assets)==415,'SYN01_EXPECTED_415_ASSETS'
    for j,s in ((j1,s1),(j2,s2)):
        unknown=[{'id':k,'state':v['state']} for k,v in s.model_calls.items() if v['state']!='SAVED']
        assert not unknown,'UNRESOLVED_MODEL_CALLS_'+str(j.root)+':'+str(unknown[:3])
    recent=events[EXPECTED_SYN01_PRIOR[0]:]
    published_ids=[e['payload']['id'] for e in recent if e['kind']=='ASSET_PUBLISHED']
    receipts=[tool_receipt(j1,e) for e in recent if e['kind']=='TOOL_RECORDED']
    source_rows=[]
    for e in recent:
        if e['kind']!='SOURCE_REGISTERED':continue
        p=e['payload'];v=dec(j1,p['blob'])
        source_rows.append({'id':p.get('id'),'kind':p.get('kind'),'description':p.get('description'),
          'evidence_class':v.get('evidence_class') if isinstance(v,dict) else None,
          'tool_id':v.get('tool_id') if isinstance(v,dict) else None})
    meta,ms,_=aut.meta_check(mods,exp);mhead=digest(mods,meta)
    decisions=meta_decisions(meta,ms,14)
    latest={x['peer']:x['decision'] for x in decisions if x['peer'] in {'SYN_01','SYN_02'}}
    assert latest=={'SYN_01':'YIELD_TO_POPULATION','SYN_02':'YIELD_TO_POPULATION'},'TWO_PEER_YIELD_NOT_VERIFIED:'+str(latest)
    outcome={
      'status':'G14_TWO_PEER_PREPOOL_READ_ONLY_AUDIT',
      'stage':cycle['stage'],'base_head':digest(mods,base),'syn01_head':digest(mods,j1),'syn02_head':digest(mods,j2),
      'syn01_event_delta':dict(Counter(e['kind'] for e in recent)),
      'syn01_new_asset_ids':published_ids,'syn01_new_assets':[asset_detail(s1,aid) for aid in published_ids],
      'syn01_workers':[work_detail(j1,w) for w in s1.work.values()],
      'syn01_tools_since_previous_snapshot':receipts,
      'syn01_registered_sources_since_previous_snapshot':source_rows,
      'syn01_pdf_text_receipts_since_previous_snapshot':sum(x['actual_page_text_evidence'] for x in receipts),
      'syn01_tool_statuses_since_previous_snapshot':dict(Counter(str(x['status'])+' / '+str(x['evidence_class']) for x in receipts)),
      'syn01_controllers':[dec(j1,d['parsed_blob']) for d in s1.controller_decisions],
      'syn02_new_asset_ids':[a['id'] for a in s2.assets.values() if a.get('work_id')=='W_challenge_minimax_charge_intervention_002'],
      'syn02_worker_statuses':{k:v['status'] for k,v in s2.work.items()},
      'meta_head':mhead,'peer_council_decisions':decisions,
      'two_peers_yielded':True,'journal_modified':False,'provider_requests_sent':0,
      'level_ii_certification':False,
      'interpretation_notice':'Tool status is not evidence class. EXECUTION_FAILED and EXECUTED need request/result inspection. YIELD does not finish ACTIVE research Work.'
    }
    assert digest(mods,base)==outcome['base_head'] and digest(mods,j1)==outcome['syn01_head']
    assert digest(mods,j2)==outcome['syn02_head'] and digest(mods,meta)==mhead,'JOURNAL_CHANGED_DURING_AUDIT'
    dest=Path(args.out).expanduser().resolve();dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf8') as f:json.dump(outcome,f,ensure_ascii=False,indent=2,default=str);f.write('\n')
    print(json.dumps({'status':outcome['status'],'report':str(dest),'syn01_new_assets':published_ids,
       'syn01_tool_statuses':outcome['syn01_tool_statuses_since_previous_snapshot'],
       'syn01_pdf_text_receipts':outcome['syn01_pdf_text_receipts_since_previous_snapshot'],
       'peer_council':latest,'stage':cycle['stage'],
       'journal_modified':False,'provider_requests_sent':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
