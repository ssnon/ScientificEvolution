#!/usr/bin/env python3
"""Read-only G14 SYN_02 science, tool and cross-peer provenance audit.

Does not mutate E2 journals, create scientific claims, or contact providers.
Usage: python G14_SYN02_LEVEL2_SCIENCE_REVIEW_20261030.py --experiment "$EXP" --out "$HOME/G14_SYN02_LEVEL2_SCIENCE_REVIEW.json"
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import population_run as pop
import autonomous_population as aut

FULLTEXT = {'OA_PDF_TEXT','OA_FULLTEXT_TEXT','OA_FULLTEXT_CAPTION','OA_SUPPLEMENT_TEXT',
            'DIRECT_FULLTEXT_EXCERPT','DIRECT_FIGURE_OR_METHOD_EXCERPT','DIRECT_SUPPLEMENT_EXCERPT'}

def decode(j,b):
    v=j.raw(b)
    if isinstance(v, bytes): v=v.decode('utf-8','replace')
    try: return json.loads(v)
    except (ValueError,TypeError): return v

def txt(o,maximum=12000):
    v = o if isinstance(o,str) else json.dumps(o,ensure_ascii=False,default=str)
    return v if len(v)<=maximum else v[:maximum]+f' ... [TRUNCATED FROM {len(v)} chars; raw in Journal]'

def head(mods,j):
    events=j._events()
    return {'events':len(events),'head_sha256':mods.sha(mods.canon(events[-1])) if events else None}

def assert_unchanged(mods,j,initial):
    assert head(mods,j)==initial, f'JOURNAL_MUTATED_DURING_READ:{str(j.root)}'

def summarize_tool(j,e):
    p=e['payload']
    request=decode(j,p['request_blob'])
    result=decode(j,p['result_blob'])
    req=request if isinstance(request,dict) else {}
    r=result if isinstance(result,dict) else {}
    data=r.get('result',{}) if isinstance(r.get('result'),dict) else {}
    evidence=r.get('evidence_class') or data.get('evidence_class')
    output={
        'event_seq':e.get('seq'),'id':p.get('id'),'work_id':p.get('work_id'),
        'request_kind':req.get('kind'),'request_arguments':req.get('arguments'),
        'status':r.get('status'),'evidence_class':evidence,
        'error_code':r.get('error_code'),'exception_type':r.get('exception_type'),
        'source_url':r.get('source_url') or data.get('source_url'),
        'doi':r.get('doi') or data.get('doi'),
        'source_sha256':r.get('source_sha256') or data.get('source_sha256'),
        'page':r.get('page') or data.get('page'),
        'page_count':r.get('page_count') or data.get('page_count'),
        'page_text_sha256':r.get('page_text_sha256') or data.get('page_text_sha256'),
        'primary_source_text_read':evidence in FULLTEXT and r.get('status')=='DELIVERED',
        'retrieval_attempts':r.get('retrieval_attempts',[]),
        'linked_source_id':r.get('linked_source_id'),
        'result_excerpt':txt(r,12500),
    }
    return output

def summarize_work(j,w):
    steps=[]
    for st in w.get('steps',[]):
        v=decode(j,st['raw_blob'])
        raw=v if isinstance(v,dict) else {}
        info={'step':st.get('step'),'kind':st.get('kind'),'call_id':raw.get('call_id')}
        if st.get('kind')=='MODEL_RESPONSE':
            original=raw.get('text','')
            try: obj=json.loads(original)
            except (ValueError,TypeError):
                info['model_output_unparsed']=txt(original,6000)
            else:
                info.update({'scientific_text':txt(obj.get('scientific_text',''),17000),
                    'next_action':obj.get('next_action'), 'tool_request':obj.get('tool_request'),
                    'submitted_asset_ids':[a.get('id') for a in obj.get('assets',[]) if isinstance(a,dict)],
                    'submitted_problem_ids':[a.get('id') for a in obj.get('new_problems',[]) if isinstance(a,dict)]})
        elif st.get('kind')=='TOOL_RESULT':
            result=raw.get('result') or {}
            info.update({'tool_id':raw.get('tool_id'),
                'result_status':result.get('status') if isinstance(result,dict) else None,
                'result_excerpt':txt(result,4200)})
        else: info['validation_or_metadata']=raw
        steps.append(info)
    return {'id':w.get('id'),'mode':w.get('mode'),'operation':w.get('operation'),
        'status':w.get('status'),'question':w.get('question'),
        'research_rationale':w.get('research_rationale'),
        'asset_input_ids':w.get('asset_input_ids',[]),'published':w.get('published',[]),
        'outcome':w.get('outcome'),'steps':steps}

def safe_peer_decisions(j,s,peer_name,cycle_number):
    entries=[]
    for d in s.controller_decisions:
        obj=decode(j,d['parsed_blob'])
        call=s.model_calls.get(d['call_id'],{})
        user={}
        if call.get('request_blob'):
            wire=decode(j,call['request_blob'])
            if isinstance(wire,dict):
                messages=wire.get('messages',[])
                if len(messages)>1 and isinstance(messages[1],dict):
                    try: user=json.loads(messages[1].get('content','{}'))
                    except (ValueError,TypeError): pass
        if user.get('stage')=='PEER' and user.get('peer_name')==peer_name and user.get('cycle_number')==cycle_number:
            entries.append({'id':d['id'],'decision':obj.get('decision'),'rationale':obj.get('rationale'),
                            'peer_name':user.get('peer_name'),'cycle_number':user.get('cycle_number')})
    return entries

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--experiment',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    exp=Path(args.experiment).expanduser().resolve()
    cycle=json.loads((exp/'CYCLE_014'/'cycle.json').read_text(encoding='utf-8'))
    assert cycle.get('index')==14, 'NOT_G14'
    assert cycle.get('stage')=='PEERS', f'G14_STAGE_CHANGED:{cycle.get("stage")}'
    mods=pop.gen.modules()
    base,base_state=pop.root_status(mods,cycle['base'])
    base_head=head(mods,base)
    assert base_head==cycle['base_head'], 'G14_BASE_HEAD_DRIFT'
    assert len(base_state.assets)==413, 'G14_BASE_NOT_413'
    peer_views={}
    for name in ('SYN_01','SYN_02'):
        assert name in cycle['peers'], 'MISSING_PEER:'+name
        peer,s=pop.root_status(mods,cycle['peers'][name]);h=head(mods,peer)
        peer_views[name]=(peer,s,h)
    j,s,initial=peer_views['SYN_02']
    other,os,other_head=peer_views['SYN_01']
    unknown=[{'id':k,'state':v.get('state')} for k,v in s.model_calls.items() if v.get('state')!='SAVED']
    events=j._events()
    assert len(events)>=len(base._events()), 'SYN02_EVENT_PREFIX_SHORTER_THAN_BASE'
    prefix=events[:len(base._events())]
    assert prefix==base._events(), 'SYN02_CLONE_PREFIX_DIFFERENT_FROM_G14_BASE'
    recent=events[len(prefix):]
    assets=[]
    for e in recent:
        if e['kind']!='ASSET_PUBLISHED':continue
        aid=e['payload'].get('id')
        a=s.assets.get(aid,{})
        assets.append({'id':aid,'kind':a.get('kind'),'claim':a.get('claim'),
            'scope':a.get('scope'),'assumptions':a.get('assumptions'),
            'predictions':a.get('predictions',[]), 'limitations':a.get('limitations',[]),
            'delta_from_parents':a.get('delta_from_parents'),
            'parent_ids':a.get('parent_ids',[]),
            'parents_inherited_or_live':[{'id':pid,'origin':s.assets.get(pid,{}).get('origin'),
                'claim_excerpt':txt(s.assets.get(pid,{}).get('claim',''),1300)} for pid in a.get('parent_ids',[])],
            'work_id':a.get('work_id'),'source_ids':a.get('source_ids',[]),
            'certification':a.get('certification'),'status':a.get('status')})
    receipts=[summarize_tool(j,e) for e in recent if e['kind']=='TOOL_RECORDED']
    sources=[]
    for e in recent:
        if e['kind']=='SOURCE_REGISTERED':
            p=e['payload']
            source=decode(j,p['blob'])
            sources.append({'id':p.get('id'),'kind':p.get('kind'),
                'description':p.get('description'),
                'evidence_class':source.get('evidence_class') if isinstance(source,dict) else None,
                'tool_id':source.get('tool_id') if isinstance(source,dict) else None})
    meta,ms,_=aut.meta_check(mods,exp)
    meta_head=head(mods,meta)
    report={
        'status':'G14_SYN02_READ_ONLY_SCIENCE_AND_EVIDENCE_AUDIT',
        'g14_stage':cycle['stage'], 'g14_base_head':base_head,
        'syn01_head':other_head,'syn01_statuses':{k:v['status'] for k,v in os.work.items()},
        'syn02_root':str(j.root),'syn02_head':initial,
        'syn02_new_event_counts':dict(Counter(e['kind'] for e in recent)),
        'syn02_saved_model_calls':sum(v.get('state')=='SAVED' for v in s.model_calls.values()),
        'syn02_unresolved_model_calls':unknown,
        'syn02_new_assets':assets,'syn02_works':[summarize_work(j,w) for w in s.work.values()],
        'syn02_actual_tools':receipts,'syn02_tool_receipt_counts':dict(Counter(str(r.get('status')) + ' / ' + str(r.get('evidence_class')) for r in receipts)),
        'syn02_actual_primary_pdf_text_receipts':sum(bool(r['primary_source_text_read']) for r in receipts),
        'syn02_sources_registered_this_segment':sources,
        'syn02_controller_decisions':[decode(j,d['parsed_blob']) for d in s.controller_decisions],
        'meta_head':meta_head,
        'meta_syn02_council_decisions':safe_peer_decisions(meta,ms,'SYN_02',14),
        'meta_syn01_council_decisions':safe_peer_decisions(meta,ms,'SYN_01',14),
        'read_only':True,'provider_requests_sent':0,
        'novelty_or_scientific_certification':False,
        'limitations':['The user WSL journals have been read; no primary PDF claims are independently verified by this export.',
                       'A tool DELIVERED status is not equivalent to full-text evidence; inspect evidence_class.']
    }
    assert_unchanged(mods,base,base_head)
    assert_unchanged(mods,j,initial)
    assert_unchanged(mods,other,other_head)
    assert_unchanged(mods,meta,meta_head)
    dest=Path(args.out).expanduser().resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2,default=str);f.write('\n')
    print(json.dumps({'status':report['status'],'out':str(dest),
        'g14_stage':report['g14_stage'],
        'syn02_head':initial, 'syn02_new_assets':len(assets),
        'syn02_tool_receipts':len(receipts),
        'syn02_primary_pdf_text_receipts':report['syn02_actual_primary_pdf_text_receipts'],
        'syn02_work_statuses':{wid:w['status'] for wid,w in s.work.items()},
        'syn02_council':[z['decision'] for z in report['meta_syn02_council_decisions']],
        'journal_unchanged':True,'provider_requests_sent':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
