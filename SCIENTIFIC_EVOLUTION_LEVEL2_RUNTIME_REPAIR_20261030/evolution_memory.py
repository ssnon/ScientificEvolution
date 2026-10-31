#!/usr/bin/env python3
"""Autonomous Scientific Evolution — bounded scientific memory + tool truth.

Only model-facing attention is compacted. All E2 journal truth and original
scientific results remain in the unchanged E2 scientific runtime.
"""
from __future__ import annotations
import argparse,contextlib,json,os,sys
from pathlib import Path
import autonomous_population as aut
import population_run as pop
import persistent_population as pp
import evolution_frontier as old
import frontier_runtime as fr
import memory_bridge as mm
import science_frontier as sf
import safe_attempt as sa


def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2,default=str),flush=True)

def _current(experiment, strict=False):
    root=old._safe(experiment)
    mods=pop.gen.modules()
    if strict:aut.meta_check(mods,root)
    cycle,cp=old._current_root(root)
    j,s=pop.root_status(mods,cp)
    return root,mods,cycle,j,s

def _uncertain(s):
    return [{'id':k,'actor':v.get('actor'),'state':v['state']} for k,v in s.model_calls.items() if v['state']!='SAVED']

def preflight(a):
    root,mods,cycle,j,s=_current(a.experiment)
    before=pp.digest(mods,j)
    with fr.activate(mods,aut),mm.activate(mods):
        b=mods.v3._external_context(j,'NATIVE_RESEARCH_TOOLS')
        cs=mods.spe.target_claims(b,j)
        e=mods.spe.classified_evidence(j)
        working=mods.spe.working_problem_state(j)
        source={'program':b['program'],'target_claims':cs,'evidence':e,'prior_working_problem_state':working,
                'original_success_criterion':b['program'].get('criteria'),
                'source_policy':'Model judgement only; no experimental certification.'}
        counts={'nvt_candidate_input_chars':mm.jsize(source),'selected_claim_count':len(cs),
                'selected_evidence_count':len(e),'problem_context_chars':mm.jsize(b.get('problems',[])),
                'live_controller_base_chars':mm.jsize(b)}
        history=[]
        for ident,v in reversed(list(s.model_calls.items())):
            if ident.startswith(('OPP_','CTRL_')) and v['state']=='SAVED':
                msg=json.loads(j.raw(v['request_blob']))
                original=json.loads(msg['messages'][1]['content'])
                try:
                    sample=mm.bound_advisor_payload(original,ident)
                    history.append({'call_id':ident,'original_chars':mm.jsize(original),
                           'bounded_chars':mm.jsize(sample),'bounded_output_is_new_request_not_replay':True})
                except Exception as ex:history.append({'call_id':ident,'attention_error':str(ex)})
                if len(history)>=2:break
        counts['reference_saved_model_requests']=history
        attention_errors=[r for r in history if 'attention_error' in r]
        truth=mm.provenance(s,j.root,max_rows=8)
    after=pp.digest(mods,j)
    if before!=after:raise RuntimeError('READONLY_PREFLIGHT_MUTATED_JOURNAL')
    unresolved=_uncertain(s)
    try:
        aut.meta_check(mods,root)
        meta_check_error=None
    except BaseException as exc:
        meta_check_error=type(exc).__name__+':'+str(exc)
    stop_marker=(root/'STOP_REQUESTED').exists()
    emit({'status':'MEMORY_TOOL_TRUTH_PREFLIGHT_NO_PAID',
        'research_cycle':cycle['index'],'stage':cycle['stage'],
        'current_journal':str(j.root),'root_head':before,
        'usage':counts,'actual_tool_provenance':truth,
        'model_written_unexecuted_tool_preambles':mm.model_tool_contract_audit(j),
        'unresolved_model_intents':unresolved,
        'autonomous_meta_check_error':meta_check_error,
        'operator_stop_requested':stop_marker,
        'paid_run_ready':not (unresolved or meta_check_error or stop_marker or attention_errors),
        'next_request_validated_by_this_preflight':False,
        'attention_reference_checks_passed':not attention_errors,
        'journal_modified':False,
        'source_runtime_unchanged':True,
        'version':mm.VERSION})
    if unresolved or meta_check_error or stop_marker or attention_errors:return 3
    return 0

def inspect(a):
    root,mods,cycle,j,s=_current(a.experiment)
    before=pp.digest(mods,j)
    if a.asset_id:
        aid=a.asset_id
        if aid not in s.assets:raise RuntimeError('ASSET_ID_NOT_REGISTERED_IN_SELECTED_JOURNAL:'+aid)
        todo=[(aid,0)];seen=set();rows=[]
        while todo:
            ident,depth=todo.pop(0)
            if ident in seen:continue
            seen.add(ident)
            asset=s.assets[ident]
            sources=[]
            for sid in asset.get('source_ids',[]):
                r=s.sources.get(sid)
                sources.append({'id':sid,'source_kind':r['kind'] if r else None,
                   'original_blob_sha256':r['blob'] if r else None,
                   'actual_tool_result':bool(r and r['kind']=='TOOL_RESULT')})
            rows.append({'depth':depth,'asset':asset,'sources':sources})
            if depth<a.depth:
                todo.extend((p,depth+1) for p in asset.get('parent_ids',[]) if p in s.assets)
        result={'status':'VERIFIED_ARCHIVE_QUERY','query_id':aid,'parents':rows,
                'full_original_science_not_summarized':True,'executed_provenance':mm.provenance(s,j.root),
                'unexecuted_tool_preamble_audit':mm.model_tool_contract_audit(j)}
    elif a.problem_id:
        ident=a.problem_id
        if ident not in s.problems:raise RuntimeError('PROBLEM_ID_NOT_IN_JOURNAL:'+ident)
        result={'status':'VERIFIED_PROBLEM_QUERY','problem':s.problems[ident]}
    else:
        selected,selection=sf.select_assets(s)
        result={'status':'VERIFIED_SCIENTIFIC_MEMORY_INDEX','journal_root':str(j.root),
                'asset_count':len(s.assets),'problem_count':len(s.problems),
                'active_frontier':sf.frontier(s,selected,max_rows=22),
                'candidate_dossiers':sf.candidate_dossiers(s,selected,limit=5),
                'exact_problem_ids':list(s.problems),
                'reference_ids':selected,
                'all_asset_ids_index_sha256':selection['index_sha256'],
                'not_presented_does_not_mean_rejected':True,
                'provenance':mm.provenance(s,j.root),
                'unexecuted_tool_preamble_audit':mm.model_tool_contract_audit(j)}
    if before!=pp.digest(mods,j):raise RuntimeError('ARCHIVE_READ_MUTATED_SOURCE_JOURNAL')
    if a.out:
        dest=Path(a.out).expanduser().absolute()
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise RuntimeError('READ_ONLY_REPORT_EXISTS_NO_OVERWRITE')
        with dest.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,ensure_ascii=False,default=str)
        emit({'status':result['status'],'out':str(dest),'original_journal_unchanged':True})
    else:emit(result)
    return 0

def run(a):
    if not a.paid or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        raise RuntimeError('PAID_REQUIREMENT_UNSATISFIED')
    # Fail before any new paid request if an unfinished call has unknown billing.
    root,mods,cycle,j,s=_current(a.experiment,strict=True)
    if (root/'STOP_REQUESTED').exists():raise RuntimeError('STOP_REQUESTED_PRESENT_REMOVE_ONLY_ON_INTENTIONAL_RESTART')
    if _uncertain(s):raise RuntimeError('UNRESOLVED_MODEL_CALL_MANUAL_BILLING_REVIEW_REQUIRED:'+str(_uncertain(s)[:3]))
    # The same read-only next-request builder is used in EVERY Population
    # generation, not just the historical G13 D00007/D00008 incident.
    if cycle['stage']=='POPULATION':
        import attention_probe
        check=attention_probe.check(str(root),a.model,a.max_tokens)
        ok=check.get('status')=='NEXT_ATTENTION_READY_NO_PAID' and all(check.get('integrity',{}).values())
        # Fresh initial research may first require a new NVT or PMI; it is
        # not an OPP-size failure. The provider still has its own pay gate.
        new_assessor=(check.get('status')=='NEW_NON_ADVISOR_CALL_NO_PAID'
                      and str(check.get('next_call_id','')).startswith(('NVT_','PMI_')))
        if not (ok or new_assessor):
            raise RuntimeError('UNIVERSAL_NEXT_REQUEST_PREFLIGHT_FAILED_NO_PAID:'+
                str(check.get('status'))+':'+str(check.get('reason',''))[:140])
        print(json.dumps({'status':'UNIVERSAL_NEXT_REQUEST_CHECK_OK_NO_PAID',
            'next_call_id':check.get('next_call_id'),
            'raw_chars':check.get('original_input_chars'),
            'bounded_chars':check.get('bounded_input_chars'),
            'journal_unchanged':check.get('journal_unchanged'),
            'provider_requests_sent':0},ensure_ascii=False),flush=True)
    with fr.activate(mods,aut),mm.activate(mods),sa.activate(mods,j),sa.stop_after_segments(aut,root,a.max_operational_segments):
        return aut.run(a) or 0

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='cmd',required=True)
    for c in ('preflight','inspect','run'):
        x=sub.add_parser(c);x.add_argument('--experiment',required=True)
        if c=='inspect':
            g=x.add_mutually_exclusive_group();g.add_argument('--asset-id');g.add_argument('--problem-id')
            x.add_argument('--depth',type=int,default=2);x.add_argument('--out')
        if c=='run':
            x.add_argument('--paid',action='store_true');x.add_argument('--model',default='openai/gpt-5.6-luna')
            x.add_argument('--bootstrap-peers',type=int,default=2);x.add_argument('--slice-budget',type=int,default=8)
            x.add_argument('--checkpoint-iterations',type=int,default=12);x.add_argument('--max-parallel',type=int,default=2)
            x.add_argument('--max-tokens',type=int,default=16000);x.add_argument('--science-cpu-seconds',type=int,default=120)
            x.add_argument('--science-wall-seconds',type=int,default=160);x.add_argument('--notice-every-segments',type=int,default=3)
            x.add_argument('--max-operational-segments',type=int,default=1,
                help='Operator cost observation boundary, not a scientific stopping criterion; marker is left for explicit restart')
    a=ap.parse_args()
    try:
        return {'preflight':preflight,'inspect':inspect,'run':run}[a.cmd](a)
    except KeyboardInterrupt:
        emit({'status':'OPERATOR_PAUSED_NOT_SCIENTIFIC_HOLD'});return 130
    except BaseException as ex:
        emit({'status':'MEMORY_LAYER_OPERATIONAL_PAUSE_NOT_SCIENTIFIC_HOLD',
              'exception_type':type(ex).__name__,'detail':str(ex)})
        return 3
if __name__=='__main__':sys.exit(main())
