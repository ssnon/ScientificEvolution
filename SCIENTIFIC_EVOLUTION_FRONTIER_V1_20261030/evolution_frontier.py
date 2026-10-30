#!/usr/bin/env python3
"""Scientific Evolution V2: bounded model attention + persistent lineage portfolios.

Do not modify the original ScientificEvolution source files or existing E2
journals. Existing failed/invalid model responses remain immutable. This runner
changes the *next* model-facing advisory context (and therefore durable request
hash), not the contents of previously paid calls. Old scientific judgments are
not interpreted as new facts.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import autonomous_population as aut
import population_run as pop
import persistent_population as pp
import science_frontier as sf
import frontier_runtime as fr


def _out(v):print(json.dumps(v,ensure_ascii=False,indent=2,default=str),flush=True)
def _safe(experiment):
    root=Path(experiment).expanduser().resolve()
    if not (root/'autonomous.json').is_file() or not (root/'persistent.json').is_file():
        raise RuntimeError('NOT_AN_EXISTING_AUTONOMOUS_POPULATION_ROOT')
    return root

def _current_root(experiment):
    cycle=pp.latest_cycle(experiment)
    if not cycle:raise RuntimeError('NO_CYCLE_TO_INSPECT')
    if cycle['stage']=='PEERS':return cycle,cycle['base']
    if cycle['stage']=='COMBINE':return cycle,cycle['base']
    return cycle,cycle['population_root']

def _view_report(j):
    state=j.verify()
    selected,selection=sf.select_assets(state)
    groups=sf.catalog(state,selected)
    progress=sf.frontier(state,selected)
    source_kinds=Counter(r.get('kind','UNKNOWN') for r in state.sources.values())
    descendants=[]
    for a in state.assets.values():
        if a.get('origin','LIVE_WORK')=='LIVE_WORK' and a.get('parent_ids'):
            descendants.append({'id':a['id'],'kind':a['kind'],'parent_ids':a['parent_ids'],
                                'scientific_delta':sf.short(a.get('delta_from_parents'),420),
                                'not_certification':True})
    tool_states=Counter(v.get('status','UNKNOWN') for v in state.tool_results.values())
    return {'root':str(j.root),'head_sha256':sf.sha(j._events()[-1]) if j._events() else None,
       'version':fr.VIEW_VERSION,'all_assets':len(state.assets),
       'selected_for_model_attention':len(selected),'unpresented_in_attention_view':len(selection['omitted_ids']),
       'all_asset_ids_sha256':selection['index_sha256'],
       'attention_view':selection,'portfolio_clusters':groups,'frontier':progress,
       'live_parent_linked_outputs':descendants,
       'provisional_level_ii_candidate_dossiers':sf.candidate_dossiers(state,selected,limit=18),
       'source_kinds':dict(source_kinds),'actual_tool_statuses':dict(tool_states),
       'controller_decisions':len(state.controller_decisions),'science_certified':False,
       'source_journal_not_mutated':True}

def preflight(args):
    experiment=_safe(args.experiment)
    mods=pop.gen.modules()
    # Verify origin and all pending source calls before attempting new paid work.
    aut.meta_check(mods,experiment)
    cycle,root=_current_root(experiment)
    j,s=pop.root_status(mods,root)
    head_before=pp.digest(mods,j)
    with fr.activate(mods,aut):
        if cycle['stage'] in ('POPULATION','COMPLETE'):
            base=mods.v3._external_context(j,'NATIVE_RESEARCH_TOOLS')
            source={'program':base['program'],
                    'target_claims':mods.spe.target_claims(base,j),
                    'evidence':mods.spe.classified_evidence(j),
                    'prior_working_problem_state':mods.spe.working_problem_state(j),
                    'original_success_criterion':base['program'].get('criteria'),
                    'source_policy':'Model judgement only. Not proof or experimental certification.'}
            estimate={'scoped_nvt_input_chars':sf.size(source),'scoped_target_claims':len(source['target_claims']),
                 'scoped_evidence':len(source['evidence']),
                 'compaction_not_information_deletion':True}
        else:
            estimate={'stage':cycle['stage'],'no_population_controller_reassessment_yet':True}
        cview=aut.snapshot(mods,experiment,cycle,'POPULATION' if cycle['stage'] in ('POPULATION','COMPLETE') else 'PEER',
                next(iter(cycle['peers'])) if cycle['stage']=='PEERS' and cycle['peers'] else None)
        estimate['population_council_view_chars']=sf.size(cview)
    after=pp.digest(mods,j)
    if head_before!=after:raise RuntimeError('READONLY_PREFLIGHT_CHANGED_JOURNAL')
    _out({'status':'FRONTIER_V2_PREFLIGHT_OK_NO_PAID','cycle':cycle['index'],
       'stage':cycle['stage'],'active_root':root,'source_head':head_before,
       'previous_invalid_pmi_is_never_overwritten':True,
       'model_input_estimate':estimate,
       'scoped_attention_budget_chars':29000,
       'existing_past_research_source_is_unchanged':True,
       'context_change_may_create_distinct_durable_model_request_ids':True,
       'paid_calls_executed':0})

def audit(args):
    root=_safe(args.experiment);mods=pop.gen.modules()
    before={}
    cycles=aut.all_cycle_files(root)
    rows=[]
    for path in cycles:
        c=pp.jload(path)
        roots=[('BASE',c['base'])]+[(k,v) for k,v in c['peers'].items()]
        if Path(c['population_root']).exists():roots.append(('POPULATION',c['population_root']))
        observations=[]
        for name,p in roots:
            j,s=pop.root_status(mods,p)
            obs={'name':name,'root':p,'head':pp.digest(mods,j),'total_assets':len(s.assets),
               'live_assets':[a['id'] for a in s.assets.values() if a.get('origin','LIVE_WORK')=='LIVE_WORK'],
               'new_parent_linked':[], 'work_dispositions':dict(Counter(w['status'] for w in s.work.values())),
               'review_dispositions':dict(Counter(v['scientific_status'] for v in s.program_reviews)),
               'controller_decisions':len(s.controller_decisions),'actual_tool_results':len(s.tool_results)}
            for a in s.assets.values():
                if a.get('origin','LIVE_WORK')=='LIVE_WORK' and a.get('parent_ids'):
                    obs['new_parent_linked'].append({'id':a['id'],'parents':a['parent_ids'],
                      'delta':a.get('delta_from_parents'),'kind':a.get('kind'),
                      'not_proof_of_improved_hypothesis':True})
            observations.append(obs)
        rows.append({'generation':c['index'],'stage':c['stage'],'researchers':observations})
    latest=pp.latest_cycle(root);j=mods.J(latest['population_root'] if Path(latest['population_root']).exists() else latest['base'])
    payload={'protocol':'FRONTIER_V2_SCIENCE_LINEAGE_AUDIT','science_certified':False,
            'total_cycles':len(rows),'cycles':rows,'current_view':_view_report(j),
            'read_only':True}
    if args.out:
        p=Path(args.out).expanduser().resolve();p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():raise RuntimeError('AUDIT_OUTPUT_EXISTS_NO_OVERWRITE')
        p.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
        _out({'status':'FRONTIER_V2_READONLY_AUDIT_SAVED','file':str(p),'cycles':len(rows)})
    else:_out(payload)

def run(args):
    experiment=_safe(args.experiment)
    if not args.paid or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        raise RuntimeError('EXPLICIT_PAID_APPROVAL_REQUIRED')
    # Preserve exact existing Autonomous CLI / lock / global terminal contracts.
    mods=pop.gen.modules()
    with fr.activate(mods,aut):
        return aut.run(args)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='cmd',required=True)
    for mode in ('preflight','audit','run'):
        x=sub.add_parser(mode);x.add_argument('--experiment',required=True)
        if mode=='audit':x.add_argument('--out')
        if mode=='run':
            x.add_argument('--paid',action='store_true')
            x.add_argument('--model',default='openai/gpt-5.6-luna')
            x.add_argument('--bootstrap-peers',type=int,default=2)
            x.add_argument('--slice-budget',type=int,default=8)
            x.add_argument('--checkpoint-iterations',type=int,default=12)
            x.add_argument('--max-parallel',type=int,default=2)
            x.add_argument('--max-tokens',type=int,default=16000)
            x.add_argument('--science-cpu-seconds',type=int,default=120)
            x.add_argument('--science-wall-seconds',type=int,default=160)
            x.add_argument('--notice-every-segments',type=int,default=3)
    args=ap.parse_args()
    try:return {'preflight':preflight,'audit':audit,'run':run}[args.cmd](args) or 0
    except KeyboardInterrupt:
        _out({'status':'USER_INTERRUPTED_OPERATIONAL_PAUSE_NOT_SCIENTIFIC_HOLD'})
        return 130
    except BaseException as exc:
        _out({'status':'FRONTIER_V2_OPERATIONAL_STOP_NOT_SCIENTIFIC_HOLD',
              'error_type':type(exc).__name__,'detail':str(exc)})
        return 3
if __name__=='__main__':sys.exit(main())
