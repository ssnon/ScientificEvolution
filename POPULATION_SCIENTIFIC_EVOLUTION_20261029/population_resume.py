#!/usr/bin/env python3
"""Fail-closed compatibility runner for Population G1/G2 INFORMED Worker inputs.

Preserves append-only Journals and original runtime source; no changes to
Controller science policy or input of any FRESH Work. Only normalizes a PEER
HISTORICAL_AI source at the moment an authorized INFORMED Worker reads it.
"""
from __future__ import annotations
import argparse, contextlib, json, os, sys
from pathlib import Path

# Put this file alongside population_run.py in the existing KIT directory.
import population_run as pop

PREFIX = 'SRC_PEER_ASSET_'


def fail(msg):
    raise RuntimeError(msg)


def peer_science_record(mods, sid, data):
    """Convert an *actually imported* peer asset to old E2 read shape.

    This is a runtime view, never a new SOURCE_REGISTERED event or evidence.
    The object is inspected only through the source ID already authorized to
    the receiving INFORMED Work. We never invent a model/tool execution.
    """
    if not sid.startswith(PREFIX):
        fail('NONSTANDARD_HISTORICAL_SOURCE_REQUIRES_REVIEW:' + sid)
    if not isinstance(data, dict) or data.get('kind') != 'PEER_RESEARCH_RESULT_HISTORICAL_AI_NOT_NEW_EXECUTION':
        fail('PEER_SOURCE_KIND_MISMATCH:' + sid)
    if data.get('verification') != 'SAVED_WORKER_MODEL_CALL_AND_ORIGIN_STEP_MATCHED':
        fail('PEER_SOURCE_NOT_VALIDATED:' + sid)
    if data.get('not_primary_literature') is not True:
        fail('PEER_SOURCE_MISLABELED_AS_PRIMARY:' + sid)
    a = data.get('original_asset')
    if not isinstance(a, dict) or not isinstance(a.get('claim'), str) or not a['claim']:
        fail('PEER_SOURCE_MISSING_ORIGINAL_ASSET:' + sid)
    if data.get('original_asset_sha256') != mods.sha(mods.canon(a)):
        fail('PEER_ASSET_DIGEST_MISMATCH:' + sid)
    root, oldid = data.get('original_root'), data.get('original_asset_id')
    if not root or not oldid or a.get('id') != oldid:
        fail('PEER_SOURCE_INVALID_ORIGIN:' + sid)
    exact_ref = root + '#' + oldid
    science = {
        'scientific_work': a['claim'],
        'scientific_delta': a.get('delta_from_parents', ''),
        'scope': a.get('scope', ''),
        'assumptions': a.get('assumptions', ''),
        'predictions': a.get('predictions', []),
        'limitations': a.get('limitations', []),
        'original_parent_ids': a.get('parent_ids', []),
        'original_asset': a,
        'original_model_call_id': data.get('original_model_call_id'),
        'original_model_response_sha256': data.get('original_model_response_sha256'),
        'source_type': 'INHERITED_PEER_AI_NOT_PRIMARY_EVIDENCE',
    }
    return {'ref': exact_ref, 'science': science,
            'tool_status': 'NO_NEW_TOOL_EXECUTION',
            'science_sha256': data['original_asset_sha256']}


def preflight(args):
    mods = pop.gen.modules()
    plan = pop.plan_at(args.experiment)
    root = Path(plan['g2_root' if args.g2 else 'population_root'])
    if not root.is_dir():fail('POPULATION_ROOT_NOT_PRESENT')
    j, st = pop.root_status(mods, root)
    if pop.p0hash(st) != plan['P0_sha256']:fail('P0_CHECKSUM_MISMATCH')
    source_count = 0
    for sid, record in st.sources.items():
        if sid.startswith(PREFIX):
            if record['kind'] != 'HISTORICAL_AI':fail('PEER_SOURCE_NOT_HISTORICAL_AI:' + sid)
            peer_science_record(mods, sid, json.loads(j.raw(record['blob'])))
            source_count += 1
    if source_count == 0:fail('NO_PEER_ASSETS_FOR_COMPATIBLE_POPULATION')
    # This particular bug occurs during Work prompt construction, *after*
    # any already-saved Controller decisions. Respect every stored call state.
    unsaved = [{'call_id': cid, 'state': c['state']} for cid,c in st.model_calls.items() if c['state']!='SAVED']
    if unsaved:fail('UNSAVED_CALLS_MANUAL_REVIEW_REQUIRED:'+str(unsaved[:5]))
    row = j._events()[-1]
    print(json.dumps({
        'status':'PEER_HISTORICAL_SOURCE_COMPAT_PREFLIGHT_OK_NO_PAID',
        'root':str(root),'event_count':len(j._events()),
        'head_sha256':mods.sha(mods.canon(row)),
        'peer_asset_sources_validated':source_count,
        'saved_model_calls':len(st.model_calls),
        'controller_decisions':len(st.controller_decisions),
        'work_statuses':{k: {'mode':v['mode'], 'status':v['status'],
                             'source_ids':v.get('source_ids',[]),
                             'parent_asset_ids':v.get('asset_input_ids',[])} for k,v in st.work.items()},
        'no_unsaved_model_calls':True,
        'journal_mutated':False,
        'no_new_source_registry_entries':True,
        'science_certified':False
    },indent=2,ensure_ascii=False))
    return mods,plan


@contextlib.contextmanager
def historical_input_compat(mods, target_root):
    """Intercept only legacy HISTORICAL_AI fields for an INFORMED worker.

    The E2 default _worker_input expects every HISTORICAL_AI record to contain
    ref/science/tool_result/science_sha256. Population transfer instead stores
    original_root/original_asset. Build an authorized read-only legacy view.
    """
    from e2core.research_context import research_worker_context
    original = mods.spe._ORIGINAL_WORKER_INPUT
    target = Path(target_root).resolve()

    def compatible_input(j, wid, tool_capabilities=None):
        if Path(j.root).resolve() != target:
            return original(j,wid,tool_capabilities)
        state=j.verify();w=state.work[wid]
        if w['mode'] == 'FRESH':
            return original(j,wid,tool_capabilities)
        allowed=set(w.get('source_ids',[]))
        for a in j.input_for(wid).get('parent_assets',[]):
            allowed.update(a.get('source_ids',[]))
        needs_bridge = any(sid in state.sources and
                           state.sources[sid]['kind']=='HISTORICAL_AI' and
                           sid.startswith(PREFIX)
                           for sid in allowed)
        if not needs_bridge:
            return original(j,wid,tool_capabilities)

        pinned=j.input_for(wid)
        prior=[]
        for step in w['steps'][-5:]:
            prior.append({'kind':step['kind'],
                          'content':json.loads(j.raw(step['raw_blob']))})
        historical=[]
        for sid in sorted(allowed):
            if sid not in state.sources:continue
            rec=state.sources[sid]
            if rec['kind']!='HISTORICAL_AI':continue
            data=json.loads(j.raw(rec['blob']))
            if sid.startswith(PREFIX):
                info=peer_science_record(mods,sid,data)
                # Cross-check the mapped current-root asset has the same
                # source_ref, preventing an unrelated peer source substitution.
                candidates=[a for a in pinned['parent_assets']
                            if sid in a.get('source_ids',[])]
                for a in candidates:
                    if a.get('source_ref') != info['ref']:
                        fail('PARENT_ASSET_SOURCE_REF_MISMATCH:'+sid)
            else:
                # Preserve native E2 interpretation exactly for G0/HISTORICAL_AI.
                if not all(k in data for k in ('ref','science','science_sha256')):
                    fail('UNHANDLED_LEGACY_HISTORICAL_SOURCE:'+sid)
                tool=data.get('tool_result') or {}
                info={'ref':data['ref'],'science':data['science'],
                      'tool_status':tool.get('status') if isinstance(tool,dict) else 'UNKNOWN',
                      'science_sha256':data['science_sha256']}
            historical.append({'id':sid,**info})
        pinned['authorized_historical_records']=historical
        return {
            'pinned_input':pinned,
            'own_prior_steps':prior,
            'research_capability_state':research_worker_context(j,wid,tool_capabilities),
            'research_action': 'Make next scientific judgement. If missing primary evidence would materially change the research, consider actual available literature/data tools. Search is a scientific option, never a quota; record a causal scientific delta from any retrieved text.'
        }

    mods.spe._ORIGINAL_WORKER_INPUT=compatible_input
    try:
        yield
    finally:
        mods.spe._ORIGINAL_WORKER_INPUT=original


def run(args):
    if not args.paid or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        fail('EXPLICIT_PAID_APPROVAL_REQUIRED')
    mods,plan=preflight(args)
    root=plan['g2_root' if args.g2 else 'population_root']
    with historical_input_compat(mods,root):
        pop.run_population(args,g2=args.g2)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=['preflight','run'])
    ap.add_argument('--experiment',required=True)
    ap.add_argument('--g2',action='store_true')
    ap.add_argument('--paid',action='store_true')
    ap.add_argument('--model',default='openai/gpt-5.6-luna')
    ap.add_argument('--max-new-calls',type=int,default=48)
    ap.add_argument('--slice-budget',type=int,default=12)
    ap.add_argument('--checkpoint-iterations',type=int,default=12)
    ap.add_argument('--max-parallel',type=int,default=2)
    ap.add_argument('--max-tokens',type=int,default=16000)
    ap.add_argument('--science-cpu-seconds',type=int,default=120)
    ap.add_argument('--science-wall-seconds',type=int,default=160)
    ns=ap.parse_args(argv)
    try:
        if ns.command=='preflight':preflight(ns)
        else:run(ns)
    except Exception as exc:
        print(json.dumps({'status':'OPERATIONAL_ERROR_NOT_SCIENTIFIC_HOLD',
              'type':type(exc).__name__,'detail':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 3
    return 0

if __name__=='__main__':raise SystemExit(main())
