#!/usr/bin/env python3
"""Read-only forensic report for Autonomous Scientific Evolution journal trees.

No provider calls, no runtime import, no writes into the experiment ROOT.
Models' judgments are NOT scientific certificates.
"""
import argparse, hashlib, json, pathlib, re, tarfile
from collections import Counter


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_events(root):
    root = pathlib.Path(root)
    location = root / 'events'
    if not location.is_dir():
        raise ValueError(f'Journal events missing: {root}')
    files = sorted(location.glob('*.json'))
    previous = None
    events=[]
    for i,p in enumerate(files,1):
        if p.name != f'{i:08d}.json': raise ValueError(f'Event gap or bad filename: {p}')
        raw=p.read_bytes();row=json.loads(raw)
        if raw != canonical(row) or row.get('seq') != i or row.get('prev') != previous:
            raise ValueError(f'Journal event hash-chain mismatch: {p}')
        previous=digest(raw)
        events.append(row)
    return events,previous


def blob(root,blob_hash):
    if not isinstance(blob_hash,str) or not re.fullmatch(r'[0-9a-f]{64}',blob_hash):
        raise ValueError('Bad blob hash')
    data=(pathlib.Path(root)/'blobs'/blob_hash).read_bytes()
    if digest(data)!=blob_hash:raise ValueError(f'Blob integrity mismatch: {blob_hash}')
    return data


def details_of_invalid(root, events, n=5):
    saves={x['payload']['id']:x['payload'] for x in events if x['kind']=='MODEL_CALL_SAVED'}
    intents={x['payload']['id']:x['payload'] for x in events if x['kind']=='MODEL_CALL_INTENT'}
    bad=[x for x in events if x['kind']=='OPERATIONAL_PAUSE' and 'INVALID_PROBLEM_IMPACT_JSON' in str(x['payload'].get('reason',''))]
    results=[]
    for event in bad[-n:]:
        p=event['payload'];cid=p.get('call_id');r={'event_seq':event['seq'],'reason':p.get('reason'),'model_call_id':cid}
        save=saves.get(cid)
        if not save:
            r['saved_response_available']=False;results.append(r);continue
        intent=intents.get(cid,{})
        raw=blob(root,save['response_blob'])
        r['saved_response_available']=True
        r['response_blob_sha256']=save['response_blob']
        r['request_blob_sha256']=intent.get('request_blob')
        try:
            response=json.loads(raw)
            r['provider_finish_reasons']=[z.get('finish_reason') for z in response.get('choices',[]) if isinstance(z,dict)]
            r['provider_usage']=response.get('usage')
            c=response['choices'][0]['message']['content']
            text=json.dumps(c,ensure_ascii=False) if isinstance(c,dict) else str(c)
            r['content_character_count']=len(text)
            try:
                value=json.loads(text)
                r['content_json_valid']=True;r['top_level_type']=type(value).__name__
                r['top_level_keys']=list(value)[:30] if isinstance(value,dict) else None
            except json.JSONDecodeError as exc:
                r['content_json_valid']=False
                r['json_error']={'message':exc.msg,'line':exc.lineno,'column':exc.colno,'position':exc.pos}
            # Upstream strict_envelope's fallback recognizes 'actions' or
            # 'scientific_text', not the PMI contract. A correctly formed PMI
            # object in a fenced/preambled response may therefore be rejected.
            decoder=json.JSONDecoder();pmi_candidates=[]
            for ix,ch in enumerate(text):
                if ch!='{':continue
                try:value,end=decoder.raw_decode(text,ix)
                except (ValueError,TypeError):continue
                if isinstance(value,dict) and 'problem_impact' in value and 'claim_to_problem' in value:
                    pmi_candidates.append({'position':ix,'end':end,'keys':list(value)[:20]})
                if len(pmi_candidates)>=3:break
            r['embedded_pmi_envelope_candidates']=pmi_candidates
            r['possible_upstream_strict_envelope_mismatch']=bool(pmi_candidates and not r.get('content_json_valid'))
            r['content_prefix']=text[:1300]
            r['content_suffix']=text[-1300:]
        except Exception as exc:
            r['provider_decode_issue']=type(exc).__name__+': '+str(exc)[:200]
        results.append(r)
    return results


def journal_summary(root, detail=False):
    root=pathlib.Path(root); events,head=read_events(root)
    assets={};works={};completed=[];decisions=[];program_reviews=[];pending={}
    kinds=Counter(x['kind'] for x in events)
    operational=[]
    for row in events:
        k,p=row['kind'],row['payload']
        if k in ('ASSET_PUBLISHED','HISTORICAL_ASSET_INDEXED'):
            assets[p['id']]={'origin_kind':k,'parents':p.get('parent_ids',[]),'claim':p.get('claim',''),
                 'delta':p.get('delta_from_parents',''),'kind':p.get('kind'),'work_id':p.get('work_id')}
        elif k=='EVOLUTION_APPLIED':
            work=p.get('work') or {}
            works[work.get('id')]={'id':work.get('id'),'operation':p.get('operation'),
                'parents':p.get('asset_ids',[]),'question':work.get('question',''),
                'mode':work.get('mode'),'status':'QUEUED'}
        elif k=='WORK_STARTED' and p.get('id') in works:
            works[p['id']]['status']='ACTIVE'
        elif k=='WORK_FINISHED' and p.get('id') in works:
            works[p['id']]['status']='DONE';works[p['id']]['outcome']=p.get('outcome')
        elif k=='WORK_PORTFOLIO_ASSESSED' and p.get('id') in works:
            if p.get('action')=='CANCEL':works[p['id']]['status']='CANCELLED'
            elif p.get('action')=='DEFER':works[p['id']]['status']='DEFERRED'
            elif p.get('action')=='REACTIVATE':works[p['id']]['status']='QUEUED'
        elif k=='PROGRAM_REVIEWED':program_reviews.append({'scientific_status':p.get('scientific_status'),'rationale':p.get('rationale','')})
        elif k=='CONTROLLER_DECISION':
            decisions.append({'id':p.get('id'),'rationale':p.get('rationale','')})
        elif k=='OPERATIONAL_PAUSE':
            operational.append({'seq':row['seq'],'reason':p.get('reason',''), 'call_id':p.get('call_id')})
        elif k=='MODEL_CALL_INTENT':pending[p['id']]='INTENT'
        elif k=='MODEL_CALL_SAVED':pending[p['id']]='SAVED'
        elif k=='MODEL_CALL_UNCERTAIN':pending[p['id']]='UNCERTAIN'
    historic={a for a,r in assets.items() if r['origin_kind']=='HISTORICAL_ASSET_INDEXED'}
    live={a for a,r in assets.items() if r['origin_kind']=='ASSET_PUBLISHED'}
    if any(p not in assets for x in assets.values() for p in x['parents']):
        raise ValueError(f'Unknown asset parent in {root}')
    memo={}
    def inherited(a, stack=frozenset()):
        if a in memo:return memo[a]
        if a in stack:raise ValueError('Cycle in asset ancestry')
        value=a in historic or any(inherited(p,stack | {a}) for p in assets[a]['parents'])
        memo[a]=value;return value
    desc=[a for a in live if any(inherited(p) for p in assets[a]['parents'])]
    direct=[a for a in live if any(p in historic for p in assets[a]['parents'])]
    summary={'root':str(root),'event_count':len(events),'head_sha256':head,
         'total_assets':len(assets),'historical_assets':len(historic),'live_assets':len(live),
         'live_asset_kinds':dict(Counter(assets[a]['kind'] for a in live)),
         'direct_inherited_parent_live_assets':len(direct),
         'transitive_inherited_parent_live_assets':len(desc),
         'work_count':len(works),'work_statuses':dict(Counter(w['status'] for w in works.values())),
         'work_modes':dict(Counter(w['mode'] for w in works.values())),
         'works_with_inherited_parent':sum(any(a in historic for a in w['parents']) for w in works.values()),
         'controller_decisions':len(decisions),
         'last_scientific_disposition':program_reviews[-1]['scientific_status'] if program_reviews else None,
         'saved_calls':sum(v=='SAVED' for v in pending.values()),
         'uncertain_or_pending_calls':[{'id':k,'state':v} for k,v in pending.items() if v!='SAVED'],
         'last_operational_pauses':operational[-8:],
         'invalid_pmi_diagnostics':details_of_invalid(root,events),
         'latest_work':list(works.values())[-6:]}
    if detail:
        summary['recent_scientific_reviews']=program_reviews[-4:]
        summary['recent_controller_rationales']=decisions[-3:]
        summary['latest_live_assets']=[{'id':aid,'kind':assets[aid]['kind'],
            'claim':assets[aid]['claim'][:1200], 'parent_ids':assets[aid]['parents'],
            'delta_from_parents':assets[aid]['delta'][:1200]}
           for aid in list(live)[-12:]]
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--experiment',required=True)
    ap.add_argument('--out',required=True,help='NEW report folder outside experiment root')
    args=ap.parse_args()
    experiment=pathlib.Path(args.experiment).expanduser().resolve()
    output=pathlib.Path(args.out).expanduser().resolve()
    if output == experiment or experiment in output.parents:
        raise SystemExit('Output must be OUTSIDE original experiment root')
    if output.exists():raise SystemExit('Output already exists: choose new folder')
    cycles=[]
    for path in sorted(experiment.glob('CYCLE_*/cycle.json')):
        match=re.fullmatch(r'CYCLE_(\d+)',path.parent.name)
        if not match:continue
        record=json.loads(path.read_text())
        if record.get('index') != int(match.group(1)):
            raise ValueError('Cycle index mismatch: '+str(path))
        peers={}
        for name,location in (record.get('peers') or {}).items():
            if (pathlib.Path(location)/'events').is_dir():
                peers[name]=journal_summary(location)
        poproot=pathlib.Path(record.get('population_root',''))
        population=journal_summary(poproot,detail=True) if (poproot/'events').is_dir() else None
        cycles.append({'cycle':record['index'],'phase':record.get('stage'),
            'previous_root':record.get('previous_root'),
            'peers':peers,'population':population})
    if not cycles:raise SystemExit('No CYCLE_*/cycle.json found in experiment')
    last=cycles[-1]
    summary={'protocol':'AUTONOMOUS_READONLY_FORENSICS_V1',
        'this_script_does_not_run_paid_models_or_modify_source':True,
        'science_certified':False,
        'number_of_cycles':len(cycles),
        'last_cycle':last['cycle'],'last_phase':last['phase'],
        'number_of_probed_journals':sum(len(c['peers'])+(c['population'] is not None) for c in cycles),
        'total_saved_model_calls_excluding_meta':sum(
            sum(p['saved_calls'] for p in c['peers'].values())+(c['population']['saved_calls'] if c['population'] else 0)
            for c in cycles),
        'last_population':last['population'],
        'cycle_summary':[{'cycle':c['cycle'],'phase':c['phase'],
            'peer_count':len(c['peers']),
            'peer_new_live_assets':sum(p['live_assets'] for p in c['peers'].values()),
            'peer_total_decisions':sum(p['controller_decisions'] for p in c['peers'].values()),
            'population_live_assets':c['population']['live_assets'] if c['population'] else None,
            'population_inherited_descendants':c['population']['transitive_inherited_parent_live_assets'] if c['population'] else None,
            'population_inherited_works':c['population']['works_with_inherited_parent'] if c['population'] else None,
            'population_last_disposition':c['population']['last_scientific_disposition'] if c['population'] else None}
            for c in cycles]}
    output.mkdir(parents=True)
    (output/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'CYCLES.json').write_text(json.dumps(cycles,ensure_ascii=False,indent=2),encoding='utf-8')
    with tarfile.open(str(output)+'.tar.gz','w:gz') as f:
        for x in sorted(output.iterdir()):f.add(x,arcname=x.name)
    print(json.dumps({'status':'READ_ONLY_AUDIT_COMPLETE','last_cycle':last['cycle'],
        'cycles':len(cycles),'summary':str(output/'SUMMARY.json'),
        'archive':str(output)+'.tar.gz',
        'last_pmi_diagnostics':last['population']['invalid_pmi_diagnostics'] if last['population'] else []},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
