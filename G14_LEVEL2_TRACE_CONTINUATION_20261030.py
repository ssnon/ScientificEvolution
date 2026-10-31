#!/usr/bin/env python3
"""Continue the real G14 Population and export verifiable, read-only Level-II provenance checkpoints.

Runs the existing evolution_pdf entry point with G14_EXACT_ID_REQUEST_GUARD activated
for newly created calls. No original research prompt, model response, validator,
scientific decision, or Journal event is rewritten. Outputs are outside Journal.

The digest of the 1101-event prior checkpoint must remain an immutable PREFIX.
This script never decides or certifies Level II; it preserves the history needed
for a later independent scientific review.
"""
from __future__ import annotations
import argparse
from collections import Counter
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

BASE_EVENTS = 1101
BASE_SHA = 'e86ce5d8bef7de3cc77aaf35b6f03cf20cde0fde01c920adec95ed2db500c3cf'
POP_IMPORTED_EVENTS = 1028
POP_IMPORTED_SHA = 'fe1b3b96176c62705dd512ea4693eaa40a4e499f62afde4763974e9fcc91f1a2'
CANDIDATE = 'A_electrocapillary_mechanochemical_feedback_005'
WORK_ID = 'W_P0_charge_multichannel_model_001'
RETRIEVAL_WORK = 'W_P0_primary_sers_precedent_retrieval_002'
DIRECT_EVIDENCE = {'OA_PDF_TEXT', 'OA_FULLTEXT_TEXT', 'OA_FULLTEXT_CAPTION', 'OA_SUPPLEMENT_TEXT'}


def _decode(j, hash_value):
    if not hash_value: return None
    v = j.raw(hash_value)
    if isinstance(v, bytes): v = v.decode('utf-8','replace')
    try: return json.loads(v)
    except (ValueError, TypeError): return v


def _digest(mods, events):
    return {'events':len(events), 'head_sha256':mods.sha(mods.canon(events[-1])) if events else None}


def _parent_closure(assets, focus):
    seen = set()
    def add(aid):
        if aid in seen: return
        if aid not in assets: raise AssertionError('UNKNOWN_ANCESTOR:'+aid)
        seen.add(aid)
        for parent in assets[aid].get('parent_ids',[]): add(parent)
    for aid in focus: add(aid)
    return seen


def verify(exp, *, expect_stage=True):
    import population_run as pop
    import persistent_population as pp
    import autonomous_population as aut
    import G14_EXACT_ID_REQUEST_GUARD_20261030 as guard
    exp = Path(exp).expanduser().resolve(strict=True)
    assert exp.is_dir(), 'EXPERIMENT_MISSING'
    mods = pop.gen.modules()
    aut.meta_check(mods, exp)
    latest = pp.latest_cycle(exp)
    assert latest and latest['index'] >= 14, 'G14_CYCLE_NOT_RECORDED'
    assert (exp/'CYCLE_014'/'cycle.json').is_file(), 'G14_CYCLE_FILE_MISSING'
    c = json.loads((exp/'CYCLE_014'/'cycle.json').read_text(encoding='utf-8'))
    if expect_stage:
        assert latest['index'] == 14 and latest['stage'] == 'POPULATION', 'G14_NOT_ACTIVE_POPULATION'
        assert c['stage'] == 'POPULATION', 'G14_STAGE_CHANGED'
    root = (exp/'CYCLE_014'/'POPULATION').resolve(strict=True)
    assert root == Path(c['population_root']).resolve(strict=True), 'POP_ROOT_ID_CHANGED'
    j, s = pop.root_status(mods,root)
    events = j._events()
    assert len(events) >= 1143, 'BEFORE_LAST_CONFIRMED_G14_SNAPSHOT'
    assert _digest(mods,events[:POP_IMPORTED_EVENTS]) == {'events':POP_IMPORTED_EVENTS,'head_sha256':POP_IMPORTED_SHA}, 'IMPORTED_PREFIX_CHANGED'
    assert _digest(mods,events[:BASE_EVENTS]) == {'events':BASE_EVENTS,'head_sha256':BASE_SHA}, 'PREVIOUS_JOURNAL_PREFIX_CHANGED'
    assert CANDIDATE in s.assets, 'KNOWN_CANDIDATE_MISSING'
    assert WORK_ID in s.work and RETRIEVAL_WORK in s.work, 'G14_WORK_MISSING'
    assert len(s.assets)>=418, 'ASSETS_WERE_LOST'
    assert all(v['state']=='SAVED' for v in s.model_calls.values()), 'UNRESOLVED_PROVIDER_CALL'
    guard.assert_state(s)
    return exp,c,mods,j,s,events


def _tool_records(j, events):
    out=[]
    for e in events[POP_IMPORTED_EVENTS:]:
        if e['kind'] != 'TOOL_RECORDED': continue
        p=e['payload']
        req = _decode(j,p['request_blob']) or {}
        res = _decode(j,p['result_blob']) or {}
        if not isinstance(req,dict) or not isinstance(res,dict): continue
        nested=res.get('result',{})
        if not isinstance(nested,dict): nested={}
        cls=res.get('evidence_class') or nested.get('evidence_class')
        out.append({'seq':e['seq'],'work_id':p.get('work_id'),'tool_id':p['id'],
          'kind':req.get('kind'),'arguments':req.get('arguments'),
          'request_blob':p['request_blob'],'result_blob':p['result_blob'],
          'status':res.get('status'),'error_code':res.get('error_code'),
          'evidence_class':cls,'actual_fulltext_return':res.get('status')=='DELIVERED' and cls in DIRECT_EVIDENCE,
          'linked_source_id':res.get('linked_source_id'),
          'source_sha256':res.get('source_sha256') or nested.get('source_sha256'),
          'source_url':res.get('source_url') or nested.get('source_url'),
          'page':res.get('page') or nested.get('page')})
    return out


def _work_record(j,w):
    steps=[]
    for st in w.get('steps',[]):
        kind=st.get('kind'); row={'step':st.get('step'),'kind':kind,'content_blob':st.get('raw_blob')}
        raw=_decode(j,st.get('raw_blob'))
        if kind=='MODEL_RESPONSE' and isinstance(raw,dict):
            row['call_id']=raw.get('call_id');row['parse_ok']=raw.get('parse_ok')
            try: parsed=json.loads(raw['text'])
            except (KeyError,ValueError,TypeError): parsed=None
            if isinstance(parsed,dict):
                row['scientific_text']=parsed.get('scientific_text')
                row['next_action']=parsed.get('next_action')
                row['submitted_assets']=parsed.get('assets',[])
                row['submitted_problems']=parsed.get('new_problems',[])
                row['requested_tool']=parsed.get('tool_request')
        elif kind=='OUTPUT_VALIDATION' and isinstance(raw,dict):
            row['validation']=raw
        elif kind=='TOOL_RESULT' and isinstance(raw,dict):
            r=raw.get('result')
            row['tool_id']=raw.get('tool_id')
            row['status']=r.get('status') if isinstance(r,dict) else None
            row['error_code']=r.get('error_code') if isinstance(r,dict) else None
        steps.append(row)
    return {k:w.get(k) for k in ('id','status','mode','operation','question','research_rationale','asset_input_ids','published','source_ids')}|{'steps':steps}


def report(exp,c,mods,j,s,events):
    import population_run as pop
    current_head=_digest(mods,events)
    peer_heads={}
    for name,root in c.get('peers',{}).items():
        peer_j,peer_s=pop.root_status(mods,root)
        peer_heads[name]={'head':_digest(mods,peer_j._events()), 'model_call_count':len(peer_s.model_calls)}
    base_j,base_s=pop.root_status(mods,c['base'])
    # The entire current-generation science genealogy is recorded. Historical
    # imported ancestors and source evidence are linked to immutable Journal refs.
    current_assets=[e['payload']['id'] for e in events[POP_IMPORTED_EVENTS:]
        if e['kind'] in ('ASSET_PUBLISHED','HISTORICAL_ASSET_INDEXED')]
    focus=set(current_assets+[CANDIDATE])
    ancestors=_parent_closure(s.assets,focus)
    ordered_assets=[aid for aid in s.assets if aid in ancestors]
    tools=_tool_records(j,events)
    lineage=[]
    for cp in sorted(exp.glob('CYCLE_*/cycle.json')):
        cdata=json.loads(cp.read_text(encoding='utf-8'))
        lineage.append({'generation':cdata.get('index'),'stage':cdata.get('stage'),
            'base':cdata.get('base'),'base_head':cdata.get('base_head'),
            'previous_root':cdata.get('previous_root'),
            'peers':cdata.get('peers'),
            'population_root':cdata.get('population_root'),
            'initial_asset_count':cdata.get('initial_asset_count'),
            'cycle_manifest_file':str(cp),
            'verification_note':'Historical roots remain separately verifiable; this checkpoint does not certify their science'})
    work={wid:_work_record(j,w) for wid,w in s.work.items()}
    decisions=[]
    for d in s.controller_decisions:
        v=_decode(j,d.get('parsed_blob'))
        decisions.append({'id':d.get('id'),'call_id':d.get('call_id'),'parsed_blob':d.get('parsed_blob'),
             'rationale':v.get('rationale') if isinstance(v,dict) else None,
             'disposition':v.get('disposition') if isinstance(v,dict) else None,
             'actions':v.get('actions') if isinstance(v,dict) else None})
    return {'status':'G14_SCIENTIFIC_PROVENANCE_CHECKPOINT_NO_PAID',
        'not_level2_certification':True,'scientific_goal':'Discover one independently reviewable Level-II hypothesis',
        'original_problem_unchanged':True,'generation':14, 'phase':c['stage'],
        'root':str(j.root),'journal_head':current_head,
        'verified_prefix':{'events':BASE_EVENTS,'head_sha256':BASE_SHA},
        'imported_prefix':{'events':POP_IMPORTED_EVENTS,'head_sha256':POP_IMPORTED_SHA},
        'base_head':_digest(mods,base_j._events()),'peer_heads':peer_heads,
        'all_generation_lineage':lineage,
        'asset_count':len(s.assets), 'assets_added_during_population':current_assets,
        'candidate_focus_ids':[CANDIDATE],
        'ancestor_asset_records':[{k:v for k,v in s.assets[aid].items()} for aid in ordered_assets],
        'work_research_traces':work,
        'controller_decisions':decisions,
        'program_objective_assessments':s.objective_assessments,
        'tool_receipts':tools,
        'actual_fulltext_receipts':sum(bool(t['actual_fulltext_return']) for t in tools),
        'source_manifest':[{**{k:v for k,v in src.items() if k!='blob'},'id':sid,
           'source_blob':src.get('blob')} for sid,src in s.sources.items()],
        'model_call_manifest':[{'id':cid,'actor':rec.get('actor'),'work_id':rec.get('work_id'),
             'state':rec.get('state'),'request_blob':rec.get('request_blob'),'response_blob':rec.get('response_blob')}
             for cid,rec in s.model_calls.items()],
        'validation_failures':[{'work_id':wid,'step':st['step'],'validation':st.get('validation')}
             for wid,w in work.items() for st in w['steps'] if st.get('kind')=='OUTPUT_VALIDATION'
             and st.get('validation',{}).get('rejected')],
        'event_kind_counts_since_pop':dict(Counter(e['kind'] for e in events[POP_IMPORTED_EVENTS:])),
        'review_requirements':['Explicit physical mechanism and quantitative parameter regime',
             'Predictions outside physically defensible strong null models',
             'Primary prior-art inspected with precise overlap boundaries',
             'Reproducible computation and genuinely discriminating falsifier',
             'Independent review of Level-II proposal, not experimental Level-III certification']}


def checkpoint(exp,outdir,*,expect_stage=True):
    exp,c,mods,j,s,events=verify(exp,expect_stage=expect_stage)
    data=report(exp,c,mods,j,s,events)
    path=Path(outdir).expanduser().resolve()
    path.mkdir(parents=True,exist_ok=True)
    head=data['journal_head']
    target=path/f'G14_{head["events"]}_{head["head_sha256"][:16]}_LEVEL2_TRACE.json'
    serialized=json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True,default=str)+'\n'
    try:
        with target.open('x',encoding='utf-8') as f:f.write(serialized)
    except FileExistsError:
        if target.read_text(encoding='utf-8')!=serialized:raise AssertionError('SNAPSHOT_FILENAME_COLLISION')
    print(json.dumps({'status':data['status'],'file':str(target),
      'checkpoint_file_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
      'events':head['events'],'assets':data['asset_count'],
      'new_population_assets':data['assets_added_during_population'],
      'active_works':[wid for wid,w in s.work.items() if w['status'] in ('ACTIVE','QUEUED')],
      'actual_fulltext_receipts':data['actual_fulltext_receipts'],
      'provider_requests_sent':0, 'journal_modified':False},ensure_ascii=False),flush=True)
    return data


def selftest():
    from types import SimpleNamespace
    from G14_EXACT_ID_REQUEST_GUARD_20261030 import selftest as guard_selftest
    assets={
      'ROOT':{'parent_ids':[]},'X':{'parent_ids':['ROOT']},
      'Y':{'parent_ids':['X']},'UNRELATED':{'parent_ids':[]}}
    assert _parent_closure(assets,['Y'])=={'Y','X','ROOT'}
    try:_parent_closure(assets,['UNKNOWN'])
    except AssertionError as ex:assert 'UNKNOWN_ANCESTOR' in str(ex)
    else:raise AssertionError('MISSING_PARENT_NOT_DETECTED')
    class TestMods:
        @staticmethod
        def canon(v):return json.dumps(v,sort_keys=True).encode()
        @staticmethod
        def sha(v):import hashlib;return hashlib.sha256(v).hexdigest()
    head=_digest(TestMods,[{'event':1}]);assert head['events']==1 and len(head['head_sha256'])==64
    guard_selftest()
    print(json.dumps({'status':'G14_CONTINUATION_AND_TRACE_SELFTEST_OK','journal_modified':False,
      'provider_requests_sent':0},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['selftest','checkpoint','run'])
    parser.add_argument('--experiment')
    parser.add_argument('--trace-dir')
    opts,remaining=parser.parse_known_args()
    if opts.command=='selftest':selftest();return 0
    assert opts.experiment and opts.trace_dir, 'EXPERIMENT_AND_TRACE_DIR_REQUIRED'
    if opts.command=='checkpoint':
        assert not remaining,'UNKNOWN_CHECKPOINT_OPTIONS:'+repr(remaining)
        checkpoint(opts.experiment,opts.trace_dir,expect_stage=False);return 0
    assert opts.command=='run'
    if '--paid' not in remaining or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        raise RuntimeError('EXPLICIT_--paid_AND_ENV_APPROVAL_REQUIRED')
    if '--max-operational-segments' not in remaining:
        raise RuntimeError('MAX_OPERATIONAL_SEGMENTS_REQUIRED')
    pos=remaining.index('--max-operational-segments')
    if pos+1>=len(remaining) or remaining[pos+1]!='1':
        raise RuntimeError('ONE_OPERATIONAL_SEGMENT_PER_RUN_REQUIRED')
    assert not (Path(opts.experiment)/'STOP_REQUESTED').exists(),'OPERATOR_STOP_PRESENT'
    checkpoint(opts.experiment,opts.trace_dir,expect_stage=True)
    import evolution_pdf
    import G14_EXACT_ID_REQUEST_GUARD_20261030 as guard
    exp,c,mods,j,s,events=verify(opts.experiment,expect_stage=True)
    original_argv=sys.argv
    sys.argv=[str(Path(evolution_pdf.__file__).resolve()),'run',
        '--experiment',str(exp),*remaining]
    try:
        # Old, immutable provider calls stay byte-identical. New G14 requests
        # get exact IDs; validation remains unchanged.
        with guard.activate(Path(c['population_root'])):
            return evolution_pdf.main()
    finally:
        sys.argv=original_argv
        # Even when a research segment errors, attempt to preserve the final
        # signed Journal head in a separate read-only trace, not by fixing it.
        try:checkpoint(opts.experiment,opts.trace_dir,expect_stage=False)
        except Exception as e:
            print('TRACE_EXPORT_AFTER_RUN_FAILED:'+type(e).__name__+':'+str(e),file=sys.stderr)


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(json.dumps({'status':'G14_CONTINUATION_OPERATIONAL_PAUSE',
          'error_type':type(exc).__name__,'detail':str(exc),
          'not_scientific_hold':True},ensure_ascii=False),file=sys.stderr)
        sys.exit(3)
