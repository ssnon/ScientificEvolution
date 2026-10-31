#!/usr/bin/env python3
"""Persistent scientific population: autonomous research, independent peer SYN,
pooled selection, verified intergeneration asset inheritance, repeat.

Operational rounds are NOT scientific success, and budgets/peer count are execution
limits, not required scientific quotas. Each new round has a clean, provenance-
carrying portfolio; no Work, model output, or tool execution is fabricated.
"""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, shutil, sys
from pathlib import Path
from types import SimpleNamespace

import population_run as pop
import population_resume as compat
from e2core.research_continuity import opportunities_for_journal

PROTOCOL='SCIENTIFIC_PERSISTENT_POPULATION_V1'
TERMINAL={'HOLD_WITH_RATIONALE','SCOPED_NEGATIVE','REVIEW_WORTHY_CANDIDATE'}
SCIENTIFIC={'HYPOTHESIS','PREDICTION','CALCULATION','COUNTEREXAMPLE','NULL_MODEL','SCOPED_NEGATIVE','SUBPROBLEM'}

def fail(msg): raise RuntimeError(msg)
def jload(p): return json.loads(Path(p).read_text(encoding='utf8'))
def atomic_write(p,x): pop.dump(p,x,overwrite=Path(p).exists())
def newwrite(p,x): pop.dump(p,x)
def digest(mods,j):
    rows=j._events();return {'events':len(rows),'head_sha256':mods.sha(mods.canon(rows[-1]))}
def cpath(x): return str(Path(x).expanduser().resolve())

def verify(mods,root): return pop.root_status(mods,root)

def last_disposition(s):
    return s.program_reviews[-1]['scientific_status'] if s.program_reviews else None

def paid_calls(s):
    return len([c for c in s.model_calls.values() if c.get('billing_mode')=='EXTERNAL' and c['state']=='SAVED'])

def _ordered_problems(state):
    found={'P0'};queue=[v for k,v in state.problems.items() if k!='P0'];out=[]
    while queue:
        ready=[x for x in queue if all(p in found for p in x['parents'])]
        if not ready:fail('INVALID_OR_CYCLIC_SOURCE_PROBLEM_GRAPH')
        for x in ready:
            out.append(x);found.add(x['id']);queue.remove(x)
    return out

def carry_registered_external_evidence(mods,dest,source,state):
    """Carry verified Journal-registered source records without claiming re-reading.

    The donor may contain primary excerpts obtained by its own real TOOL_RESULT,
    or older already-inherited excerpts. Both are preserved as inherited evidence
    (NOT a new tool execution); exact original payload and hashes stay traceable.
    """
    entries=[]
    for sid,rec in state.sources.items():
        if rec.get('kind')!='EXTERNAL_AUDIT':continue
        if not sid.startswith(('SRC_INHERITED_TOOL_','SRC_PRIOR_')):continue
        raw=source.raw(rec['blob'])
        data=json.loads(raw)
        if sid.startswith('SRC_INHERITED_TOOL_'):
            if not isinstance(data,dict) or not isinstance(data.get('original_returned_data'),dict) \
                or not data.get('evidence_class'):
                fail('INHERITED_TOOL_SOURCE_MALFORMED:'+sid)
            new_id=pop.hname(mods,'SRC_INHERITED_TOOL_',{'origin':str(source.root),'sid':sid},23)
            copy={**data,'carried_from_source_root':str(source.root),
                'carried_from_source_id':sid,'carried_original_blob_sha256':rec['blob'],
                'is_a_new_tool_execution':False,'not_independently_certified':True}
        else:
            if not isinstance(data,dict) or not isinstance(data.get('record'),dict):
                fail('OPERATOR_EVIDENCE_SOURCE_MALFORMED:'+sid)
            new_id=pop.hname(mods,'SRC_PRIOR_',{'origin':str(source.root),'sid':sid},22)
            copy={**data,'carried_from_source_root':str(source.root),
                'carried_from_source_id':sid,'carried_original_blob_sha256':rec['blob'],
                'operator_supplied_not_new_observation':True}
        dest.add_source(new_id,'EXTERNAL_AUDIT',copy,
            'Carried source-level prior record, NOT new source inspection: '+sid)
        entries.append({'prior_id':sid,'current_id':new_id,'original_blob_sha256':rec['blob']})
    return entries


def prepare_clean_portfolio(mods,source_root,dest):
    """Reindex previous claims as explicitly provisional historical AI.

    An ACTIVE source Work is preserved as historical, unresolved status and NEVER
    falsely marked DONE. Old source runs are only referenced, not mutated.
    """
    source,ss=verify(mods,source_root); before=digest(mods,source)
    dest=Path(dest).expanduser().resolve()
    if dest.exists():fail('NEW_BASE_ROOT_ALREADY_EXISTS')
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage=dest.with_name(dest.name+'.STAGING')
    if stage.exists():fail('STAGING_EXISTS')
    j=mods.J(stage)
    try:
        j.init(ss.program['problem'],origin='PERSISTENT_POPULATION_CLEAN_GENERATION_CARRY',
               criteria=ss.program.get('criteria'))
        j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        pmap={'P0':'P0'}
        for old in _ordered_problems(ss):
            new=pop.hname(mods,'P_CARRY_',{'root':str(source.root),'id':old['id']},22)
            obj={k:v for k,v in old.items() if k not in {'id','parents','status'}}
            obj.update(id=new,parents=[pmap[x] for x in old['parents']])
            j.append('PROBLEM_CREATED',obj);pmap[old['id']]=new
        amap={};transfers=[]
        for aid,a in ss.assets.items():
            new=pop.hname(mods,'A_CARRY_',{'root':str(source.root),'id':aid},23)
            parents=a.get('parent_ids',[])
            if any(p not in amap for p in parents):fail('SOURCE_ASSET_GRAPH_NOT_TOPOLOGICAL:'+aid)
            source_id=pop.hname(mods,'SRC_CARRY_ASSET_',{'root':str(source.root),'id':aid},24)
            science={'scientific_work':a['claim'], 'scientific_delta':a.get('delta_from_parents',''),
                'scope':a.get('scope'), 'assumptions':a.get('assumptions'),
                'predictions':a.get('predictions',[]), 'limitations':a.get('limitations',[]),
                'original_asset':a, 'original_parent_ids':parents,
                'previous_source_ids':a.get('source_ids',[]),
                'scientific_certification':False}
            record={'ref':str(source.root)+'#'+aid,'science':science,
                'tool_result':{'status':'HISTORICAL_ONLY_NO_NEW_TOOL_EXECUTION'},
                'science_sha256':mods.sha(mods.canon(a)),
                'original_asset':a,'upstream_root':str(source.root),'upstream_asset_id':aid,
                'source_head_sha256':before['head_sha256'],
                'claim_not_independently_verified':True}
            j.add_source(source_id,'HISTORICAL_AI',record,
                'Verbatim science assertion from previous verified Journal; NOT new evidence')
            payload={k:a[k] for k in ('kind','claim','scope','assumptions')}
            payload.update({'id':new,'problem_id':pmap[a['problem_id']],
                'parent_ids':[amap[p] for p in parents],
                'predictions':a.get('predictions',[]),
                'delta_from_parents':a.get('delta_from_parents',''),
                'limitations':a.get('limitations',[]),
                'source_ids':[source_id], 'source_ref':record['ref'],
                'source_science_sha256':record['science_sha256'],
                'carried_from_root':str(source.root),'carried_original_asset_id':aid})
            j.append('HISTORICAL_ASSET_INDEXED',payload)
            amap[aid]=new
            transfers.append({'upstream_id':aid,'current_id':new,
                              'upstream_parents':parents,'current_parents':payload['parent_ids'],
                              'origin_source':source_id})
        # Preserve independent work outcomes and model decision evidence without
        # reclassifying those records as scientific evidence or completed research.
        recent=[]
        for d in ss.controller_decisions[-6:]:
            response=json.loads(source.raw(d['parsed_blob']))
            recent.append({'decision_id':d['id'],'response_sha256':d['parsed_blob'],
                'disposition':response.get('disposition'),
                'rationale':response.get('rationale'),
                'actions':response.get('actions',[]),
                'not_independent_certification':True})
        receipt={'kind':'PREVIOUS_POPULATION_STATUS_NOT_NEW_SCIENCE',
            'source_root':str(source.root),'source_head':before,
            'work_statuses':{wid:{'status':w['status'],'operation':w.get('operation'),
                'mode':w.get('mode'),'question':w.get('question'),
                'published':w.get('published',[]),
                'unfinished_at_checkpoint':w['status'] in {'ACTIVE','QUEUED','DEFERRED'}}
                for wid,w in ss.work.items()},
            'previous_review':ss.program_reviews[-1] if ss.program_reviews else None,
            'recent_controller_decisions':recent,
            'original_sources_remain_in_upstream_journal':True,
            'no_autonomous_scientific_decision_in_transfer':True}
        # Native INFORMED legacy reader requires ref/science/tool_result fields.
        # The same full receipt remains available inside science without upgrading
        # it to primary evidence or making it an executed research result.
        j.add_source('SRC_PREVIOUS_POPULATION_STATUS','HISTORICAL_AI',{
            **receipt, 'ref':str(source.root)+'#PREVIOUS_POPULATION_STATUS',
            'science':receipt,
            'tool_result':{'status':'HISTORICAL_STATUS_ONLY_NO_NEW_EXECUTION'},
            'science_sha256':mods.sha(mods.canon(receipt))},
            'Prior ROOT statuses and decisions, not primary experimental data')
        # Actual direct evidence remains a referenced original TOOL_RESULT,
        # with its original request and execution checked before exposure.
        # Carry rejected proposals separately from accepted Assets and
        # registered primary/source evidence. Peers retain blind independence:
        # native context only exposes this ledger at POPULATION stage.
        prior_unregistered=opportunities_for_journal(source)
        for opportunity_id in sorted(prior_unregistered):
            j.append('OPPORTUNITY_CARRIED',{
                'opportunity':prior_unregistered[opportunity_id],
                'upstream_root':str(source.root),
                'upstream_head_sha256':before['head_sha256'],
                'not_registered_science':True})
        carried_sources=carry_registered_external_evidence(mods,j,source,ss)
        imported_sources=pop.record_direct_tool_sources(mods,j,source,ss,'PRIOR_GENERATION')
        if len(j.verify().assets)!=len(ss.assets):fail('CARRY_LOST_SCIENCE_ASSETS')
        ids=list(j.verify().assets)
        atomic_write(stage/'FEEDBACK_PREPARE_MANIFEST.json',{
            'selected_assets':ids,'origin':'FULL_POPULATION_WITHOUT_HUMAN_HYPOTHESIS_SELECTION',
            'science_certification':False})
        j.append('R5_INTEGRATION_REQUESTED',{
            'foreign_root':str(source.root),'asset_ids':ids,
            'event_seq':len(j._events())+1,
            'reason':'Next generation is asked to independently evaluate all inherited scientific claims and prior work status. No forced continuation.'})
        result={'source_root':str(source.root),'source_head':before,
            'base_root':str(dest),'source_assets':len(ss.assets),'new_ids':amap,
            'edges':transfers,'inherited_direct_tool_sources':imported_sources,
            'previously_registered_external_sources_carried':carried_sources,
            'unfinished_work_statuses_preserved_as_history':True,
            'unregistered_opportunities_preserved_not_scientific_assets':len(prior_unregistered),
            'new_research_executed':False,'scientific_certification':False}
        newwrite(stage/'carry_receipt.json',result)
        j.verify()
        if digest(mods,source)!=before:fail('UPSTREAM_CHANGED_DURING_CARRY')
        stage.rename(dest)
    except BaseException:
        if stage.exists():shutil.rmtree(stage)
        raise
    return result


def init(args):
    mods=pop.gen.modules()
    source=Path(args.source_root).expanduser().resolve()
    sj,ss=verify(mods,source)
    root=Path(args.out).expanduser().resolve()
    if root.exists():fail('DEST_EXISTS')
    root.mkdir(parents=True)
    try:
        carry=prepare_clean_portfolio(mods,source,root/'BASE_000')
        manifest={'protocol':PROTOCOL,'root':str(root),'original_source':str(source),
            'source_head':digest(mods,sj), 'P0_sha256':pop.p0hash(ss),
            'generation_zero_base':str(root/'BASE_000'),
            'scientific_policy':'AUTONOMOUS_EXISTING_V4_V3_CONTROLLER; NO_FORCED_FUSE_OR_WORK',
            'source_work_is_only_historical_not_SILENTLY_FINISHED':True,
            'science_certification':False}
        newwrite(root/'persistent.json',manifest)
        print(json.dumps({'status':'PERSISTENT_POPULATION_PREPARED_NO_PAID',
            'root':str(root),'first_base':str(root/'BASE_000'),
            'carried_science_assets':carry['source_assets'],
            'inherited_direct_tool_sources':carry['inherited_direct_tool_sources']['registered_direct_sources'],
            'source_untouched':True},ensure_ascii=False,indent=2))
    except BaseException:
        if root.exists():shutil.rmtree(root)
        raise


def plan_at(root):
    root=Path(root).expanduser().resolve();m=jload(root/'persistent.json')
    if m.get('protocol')!=PROTOCOL or m.get('root')!=str(root):fail('MANIFEST_ROOT_MISMATCH')
    return m


def cycle_file(root,n):return Path(root)/f'CYCLE_{n:03d}'/'cycle.json'

def create_cycle(mods,root,n,peer_count,source):
    folder=Path(root)/f'CYCLE_{n:03d}'
    if folder.exists():fail('CYCLE_FOLDER_ALREADY_EXISTS')
    folder.mkdir(parents=True)
    try:
        base=folder/'BASE'
        if n==0:
            # The BASE_000 root was generated and audited at init.
            pop.clone_at_checkpoint(mods,Path(root)/'BASE_000',base,
                 len(mods.J(Path(root)/'BASE_000')._events()))
        else:
            prepare_clean_portfolio(mods,source,base)
        b,bs=verify(mods,base)
        if bs.work or bs.model_calls or bs.controller_decisions:fail('CLEAN_BASE_HAS_ACTIVE_WORK')
        peers={}
        for k in range(peer_count):
            name=f'SYN_{k+1:02d}'
            target=folder/name
            pop.clone_at_checkpoint(mods,base,target,len(b._events()),digest(mods,b)['head_sha256'])
            peers[name]=str(target)
        state={'protocol':'PERSISTENT_POPULATION_CYCLE_V1','index':n,
            'base':str(base),'base_head':digest(mods,b),
            'peers':peers,'population_root':str(folder/'POPULATION'),
            'previous_root':str(source), 'stage':'PEERS',
            'initial_asset_count':len(bs.assets),
            'no_scientific_selection_by_operator':True}
        newwrite(folder/'cycle.json',state)
    except BaseException:
        if folder.exists():shutil.rmtree(folder)
        raise
    return state


def latest_cycle(root):
    rows=sorted(Path(root).glob('CYCLE_*/cycle.json'), key=lambda p: int(p.parent.name[6:]))
    if not rows:return None
    return jload(rows[-1])


def update_cycle(root,cycle):atomic_write(cycle_file(root,cycle['index']),cycle)


def assert_source_stable(mods,cycle):
    j,s=verify(mods,cycle['base'])
    if digest(mods,j)!=cycle['base_head']:fail('BASE_CHECKPOINT_MUTATED')
    return j,s


@contextlib.contextmanager
def previous_population_bridge(mods):
    """Show actual old Work dispositions to independent SYN researchers.

    These states come from the verified previous Journal and never silently turn
    an unfinished Work into a scientific negative, a success, or a new Work.
    """
    orig=mods.v3._external_context
    def bridge(j,*a,**kw):
        ctx=orig(j,*a,**kw)
        rec=j.verify().sources.get('SRC_PREVIOUS_POPULATION_STATUS')
        if rec:
            old=json.loads(j.raw(rec['blob']))
            ctx['previous_generation_scientific_portfolio']={
                'source_root':old['source_root'],
                'head':old['source_head'],
                'work_statuses':old['work_statuses'],
                'previous_review':old['previous_review'],
                'recent_controller_decisions':old['recent_controller_decisions'],
                'historical_status_only_not_new_execution':True}
        return ctx
    mods.v3._external_context=bridge
    try:yield
    finally:mods.v3._external_context=orig


@contextlib.contextmanager
def population_science_bridge(mods,root,peer_names):
    orig=mods.v3._external_context
    def bridge(j,*a,**kw):
        ctx=orig(j,*a,**kw)
        ss=j.verify();reports=[]
        for name in peer_names:
            sid='SRC_PEER_DECISION_'+name
            if sid not in ss.sources:fail('MISSING_PEER_DECISION_SOURCE:'+name)
            report=json.loads(j.raw(ss.sources[sid]['blob']))
            decisions=report['decisions'];opps=report['opportunity_assessments']
            visible=decisions if len(decisions)<=3 else [decisions[0]]+decisions[-2:]
            reports.append({'name':name,'provenance':'INDEPENDENT_MODEL_DECISIONS_NOT_EXPERIMENT',
                'source_id':sid,'original_root':report['original_root'],
                'original_head_sha256':report['head_sha256'],
                'decisions_total':len(decisions),'decisions':visible,
                'opportunities_total':len(opps),'recent_opportunities':opps[-2:],
                'asset_id_translation':report['asset_id_translation'],
                'all_peer_assets':report['new_assets']})
        prior=ss.sources.get('SRC_PREVIOUS_POPULATION_STATUS')
        if prior:
            past=json.loads(j.raw(prior['blob']))
            ctx['previous_population_scientific_status']={
                'source_root':past['source_root'],'work_statuses':past['work_statuses'],
                'previous_review':past['previous_review'],
                'recent_controller_decisions':past['recent_controller_decisions'],
                'status_is_historical_not_current_experiment':True}
        ctx['independent_peer_syn_portfolio']=reports
        ctx['population_coordination_instruction']=(
            'The peers independently evaluated the entire inherited population. '
            'Compare their actual scientific proposals, nulls, critiques and objections; '
            'no scientifically predetermined winners, mandatory research action, FUSE, or quota. '
            'Retain independent alternative frontiers if they have research value, '
            'and respect evidence limits. For a peer asset use its mapped current-root ID, '
            'not its donor original ID. Genuine inheritance requires a parent-linked Work '
            'and a substantive scientific delta, not simply an inherited source mention. '
            'A prior Work that was ACTIVE at checkpoint was not completed by this transfer.')
        return ctx
    mods.v3._external_context=bridge
    try:yield
    finally:mods.v3._external_context=orig


def _import_quarantined_peer(mods,j,base_state,peer,path,receipt):
    """No scientific assets or Controller decisions invented for a failed peer."""
    donor,state=pop.root_status(mods,path)
    head=digest(mods,donor)
    if receipt.get('peer')!=peer or receipt.get('peer_root')!=str(donor.root) or \
       receipt.get('peer_head')!=head or receipt.get('scientific_disposition','WRONG') is not None:
        fail('SCHEMA_QUARANTINE_RECEIPT_MISMATCH:'+peer)
    if state.controller_decisions or state.work or any(
        x not in base_state.assets for x in state.assets):
        fail('QUARANTINED_PEER_HAS_UNEXPECTED_LIVE_RESEARCH:'+peer)
    rejected=receipt.get('rejected_controller_attempts',[])
    if len(rejected)<3:fail('QUARANTINED_PEER_INSUFFICIENT_REJECTION_EVIDENCE')
    for x in rejected:
        c=state.model_calls.get(x.get('call_id'))
        if not c or c.get('state')!='SAVED' or c.get('actor')!='CONTROLLER' \
            or c.get('response_blob')!=x.get('response_blob'):
            fail('QUARANTINED_PEER_REJECTION_NOT_SAVED:'+peer)
    sid='SRC_PEER_DECISION_'+peer
    report={'peer_syn':peer,'original_root':str(donor.root),
       'head_sha256':head['head_sha256'],'events':head['events'],
       'asset_id_translation':{},'decisions':[],'opportunity_assessments':[],
       'new_assets':[],'imported_G0_assets':len(base_state.assets),
       'last_program_review':None,'scientific_disposition':None,
       'operational_status':'SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED',
       'operationally_blocked_not_a_scientific_hold':True,
       'saved_controller_rejections':rejected,
       'rejected_model_output_is_not_a_valid_scientific_decision':True,
       'not_scientific_certification':True}
    j.add_source(sid,'HISTORICAL_AI',report,
        'Blocked independent peer; no committed Controller science; preserved schema failures')
    return {'peer':peer,'source':str(donor.root),'head_sha256':head['head_sha256'],
       'new_assets_imported':0,'direct_tool_sources':0,'decisions':0,
       'last_disposition':None,'decision_receipt':sid,
       'operationally_blocked_not_a_scientific_hold':True}

def combine(mods,cycle,blocked_peers=None):
    folder=Path(cycle['base']).parent
    target=Path(cycle['population_root'])
    if target.exists():fail('POPULATION_ALREADY_EXISTS_NO_REIMPORT')
    base,bs=assert_source_stable(mods,cycle)
    stage=target.with_name(target.name+'.STAGING')
    if stage.exists():fail('STAGING_EXISTS')
    shutil.copytree(cycle['base'],stage)
    try:
        j,s=verify(mods,stage)
        reports=[]
        blocked_peers=blocked_peers or {}
        if set(blocked_peers)-set(cycle['peers']):fail('UNKNOWN_QUARANTINED_PEER')
        if len(blocked_peers)==len(cycle['peers']):
            fail('ALL_PEERS_OPERATIONALLY_BLOCKED_NO_POPULATION_SCIENCE_TO_COMBINE')
        for peer,path in cycle['peers'].items():
            if peer in blocked_peers:
                report=_import_quarantined_peer(mods,j,bs,peer,path,blocked_peers[peer])
            else:
                # The normal path still enforces genuine paid Controller decisions,
                # verified worker steps, provenance and parent mapping.
                report=pop.import_peer(mods,j,bs,peer,path)
            reports.append(report)
        all_ids=list(j.verify().assets)
        atomic_write(stage/'FEEDBACK_PREPARE_MANIFEST.json',{
            'selected_assets':all_ids,
            'origin':'INDEPENDENT_PEER_REPORTS_AND_FULL_INHERITED_POPULATION',
            'science_certification':False})
        j.append('R5_INTEGRATION_REQUESTED',{
            'foreign_root':'INDEPENDENT_SCIENTIFIC_POPULATION_PEERS',
            'asset_ids':all_ids,'event_seq':len(j._events())+1,
            'reason':'Assess independent peer reports, real science and provenance. No compulsory research or merger.'})
        ss=j.verify()
        newwrite(stage/'integration_receipt.json',{
            'base_head':cycle['base_head'],'peer_reports':reports,
            'total_assets':len(ss.assets),'P0_sha256':pop.p0hash(ss),
            'new_model_calls_during_merge':0,'science_certification':False})
        stage.rename(target)
    except BaseException:
        if stage.exists():shutil.rmtree(stage)
        raise
    return {'status':'POPULATION_COMBINED_NO_PAID','assets':len(all_ids),
            'new_peer_assets':sum(x['new_assets_imported'] for x in reports)}


def budgeted_drive(mods,root,args,total_before,mode,peer_names=()):
    j,s=verify(mods,root)
    target=args.peer_calls if mode=='peer' else args.population_calls
    left=target-paid_calls(s)
    cap=args.max_total_new_calls-(total_paid_in_experiment(mods,args.experiment)-total_before)
    if cap<=0:return {'stop':'GLOBAL_CALL_BUDGET','spent':0}
    if last_disposition(s) in TERMINAL:
        return {'stop':'SCIENTIFIC_TERMINAL','spent':0,'disposition':last_disposition(s)}
    if left<=0:return {'stop':'ROOT_CALL_BUDGET','spent':0}
    spec=SimpleNamespace(paid=True,model=args.model,
        max_new_calls=min(left,cap),slice_budget=args.slice_budget,
        checkpoint_iterations=args.checkpoint_iterations,max_parallel=args.max_parallel,
        max_tokens=args.max_tokens,science_cpu_seconds=args.science_cpu_seconds,
        science_wall_seconds=args.science_wall_seconds)
    if mode=='peer':
        with previous_population_bridge(mods):
            result=pop.gen.drive(mods,root,spec,'syn')
    else:
        with population_science_bridge(mods,root,peer_names),compat.historical_input_compat(mods,root):
            result=pop.gen.drive(mods,root,spec,'syn')
    j,s=verify(mods,root)
    scientific_end=last_disposition(s) in TERMINAL
    return {'stop':'SCIENTIFIC_TERMINAL' if scientific_end else result.get('stop_reason'),
        'spent':result.get('new_calls_this_launch',0),
        'new_controller_decisions':result.get('new_controller_decisions'),
        'last_disposition':last_disposition(s),'assets':len(s.assets),
        'works':{w:v['status'] for w,v in s.work.items()},'head':digest(mods,j)}


def total_paid_in_experiment(mods,root):
    total=0
    for folder in Path(root).glob('CYCLE_*'):
        path=folder/'cycle.json'
        if not path.exists():continue
        cycle=jload(path)
        for p in list(cycle.get('peers',{}).values())+[cycle.get('population_root')]:
            if p and Path(p).is_dir():
                total+=paid_calls(verify(mods,p)[1])
    return total


def run(args):
    if not args.paid or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        fail('EXPLICIT_--paid_AND_FAKG_RESEARCH_ALLOW_PAID=YES_REQUIRED')
    if not (1<=args.max_cycles<=30 and 1<=args.peer_count<=5 and
            1<=args.peer_calls<=200 and 1<=args.population_calls<=200 and
            1<=args.max_total_new_calls<=10000 and args.slice_budget>=1):
        fail('INVALID_OPERATIONAL_EXECUTION_LIMIT')
    mods=pop.gen.modules();m=plan_at(args.experiment)
    before=total_paid_in_experiment(mods,args.experiment)
    completed=0
    while completed<args.max_cycles:
        cycle=latest_cycle(args.experiment)
        if cycle is None or cycle['stage']=='COMPLETE':
            if cycle is not None:
                prev_root=cycle['population_root']
                j,st=verify(mods,prev_root)
                if last_disposition(st) in TERMINAL:
                    print(json.dumps({'status':'SCIENTIFIC_TERMINAL_MODEL_DISPOSITION',
                        'disposition':last_disposition(st),'no_claim_of_proven_P0_solution':True}))
                    break
                baseline=cycle.get('initial_asset_count',0)
                if len(st.assets)<=baseline:
                    print(json.dumps({'status':'NO_NEW_ASSETS_FOR_CONTINUATION_NOT_P0_IMPOSSIBILITY'}))
                    break
                if len([a for a in st.assets.values() if a.get('origin')!='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK' and a.get('kind') in SCIENTIFIC])==0:
                    # Peer outputs can still be scientifically useful; the next
                    # iteration needs a research-relevant candidate, not only metadata.
                    new_peer= len(st.assets)-baseline
                    if new_peer<=0:break
                source=prev_root
                n=cycle['index']+1
            else:
                source=m['original_source'];n=0
            if n>=30:fail('TOO_MANY_CYCLES_FOR_BOUNDED_RUN')
            if total_paid_in_experiment(mods,args.experiment)-before>=args.max_total_new_calls:break
            cycle=create_cycle(mods,args.experiment,n,args.peer_count,source)
            print(json.dumps({'status':'NEW_GENERATION_PREPARED_NO_PAID','index':n,'peers':list(cycle['peers']),
                'imported_assets':cycle['initial_asset_count']},ensure_ascii=False),flush=True)
        _,bs=assert_source_stable(mods,cycle)
        if pop.p0hash(bs)!=m['P0_sha256']:fail('P0_CHANGED_IN_GENERATION')
        if cycle['stage']=='PEERS':
            for peer,root in cycle['peers'].items():
                result=budgeted_drive(mods,root,args,before,'peer')
                print(json.dumps({'phase':'PEER','generation':cycle['index'],
                    'peer':peer,**result},ensure_ascii=False),flush=True)
                if result.get('stop')=='GLOBAL_CALL_BUDGET':return
                if result.get('stop') not in {'CALL_BUDGET','ROOT_CALL_BUDGET','SCIENTIFIC_TERMINAL'}:
                    fail('PEER_OPERATIONAL_PAUSE_NEEDS_REVIEW:'+str(result.get('stop')))
            if any(paid_calls(verify(mods,r)[1])==0 for r in cycle['peers'].values()):
                fail('PEER_WITHOUT_REAL_MODEL_CALLS_STOP')
            cycle['stage']='COMBINE';update_cycle(args.experiment,cycle)
        if cycle['stage']=='COMBINE':
            outcome=combine(mods,cycle)
            print(json.dumps(outcome,ensure_ascii=False),flush=True)
            cycle['stage']='POPULATION';update_cycle(args.experiment,cycle)
        if cycle['stage']=='POPULATION':
            result=budgeted_drive(mods,cycle['population_root'],args,before,'population',tuple(cycle['peers']))
            print(json.dumps({'phase':'POPULATION','generation':cycle['index'],**result},
                ensure_ascii=False),flush=True)
            if result.get('stop')=='GLOBAL_CALL_BUDGET':return
            if result.get('stop') not in {'CALL_BUDGET','ROOT_CALL_BUDGET','SCIENTIFIC_TERMINAL'}:
                fail('POPULATION_OPERATIONAL_PAUSE_NEEDS_REVIEW:'+str(result.get('stop')))
            cycle['stage']='COMPLETE';update_cycle(args.experiment,cycle)
        completed+=1
        print(json.dumps({'status':'POPULATION_CYCLE_RECORDED','generation':cycle['index'],
           'cycles_completed_this_launch':completed,
           'model_calls_this_launch':total_paid_in_experiment(mods,args.experiment)-before,
           'not_scientific_certification':True},ensure_ascii=False),flush=True)
    print(json.dumps({'status':'STOPPED_AT_SCIENTIFIC_OR_OPERATIONAL_BOUNDARY',
        'cycles_completed_this_launch':completed,
        'new_paid_calls':total_paid_in_experiment(mods,args.experiment)-before,
        'not_a_scientific_certificate':True},ensure_ascii=False))


def status(args):
    mods=pop.gen.modules();m=plan_at(args.experiment)
    cycles=[]
    for path in sorted(Path(args.experiment).glob('CYCLE_*/cycle.json')):
        c=jload(path);obj={'generation':c['index'],'phase':c['stage'],
            'previous_root':c['previous_root'],'peers':{},'population':None}
        for name,root in c['peers'].items():
            j,s=verify(mods,root)
            obj['peers'][name]={'paid_calls':paid_calls(s),'decisions':len(s.controller_decisions),
                'assets':len(s.assets)-c['initial_asset_count'],
                'disposition':last_disposition(s),'works':{x:y['status'] for x,y in s.work.items()}}
        if Path(c['population_root']).is_dir():
            j,s=verify(mods,c['population_root'])
            base,_=verify(mods,c['base'])
            base_ids=set(base.verify().assets)
            new={aid:a for aid,a in s.assets.items() if aid not in base_ids}
            live={aid:a for aid,a in new.items() if a.get('origin')!='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
            imported={aid:a for aid,a in new.items() if aid not in live}
            def reaches_previous(aid,seen=None):
                if aid in base_ids:return True
                seen=seen or set()
                if aid in seen:return False
                return any(reaches_previous(par,seen|{aid})
                           for par in s.assets[aid].get('parent_ids',[]))
            obj['population']={'paid_calls':paid_calls(s),'decisions':len(s.controller_decisions),
                'works_with_previous_generation_parents':[wid for wid,w in s.work.items()
                      if any(a in base_ids for a in w.get('asset_input_ids',[]))],
                'works_with_peer_parent_assets':[wid for wid,w in s.work.items()
                      if any(a in imported for a in w.get('asset_input_ids',[]))],
                'live_descendants_of_previous_generation':[aid for aid in live if reaches_previous(aid)],
                'new_peer_assets':len(imported),'live_science_assets':len(live),
                'works':[{'id':wid,'status':w['status'],'operation':w['operation'],
                    'mode':w['mode'],'asset_input_ids':w['asset_input_ids'],
                    'published':w.get('published',[])} for wid,w in s.work.items()],
                'claims':[{'id':aid,'kind':a['kind'],'claim':a.get('claim'),
                    'parent_ids':a.get('parent_ids',[]),
                    'scientific_delta':a.get('delta_from_parents')} for aid,a in live.items()],
                'disposition':last_disposition(s),
                'verified_no_unknown_calls':True,'head':digest(mods,j)}
        cycles.append(obj)
    output={'protocol':'PERSISTENT_POPULATION_READONLY_AUDIT_V1',
        'original_p0_sha256':m['P0_sha256'],'cycles':cycles,
        'total_new_paid_calls':total_paid_in_experiment(mods,args.experiment),
        'no_science_certification':True}
    if args.out:atomic_write(args.out,output)
    print(json.dumps(output,ensure_ascii=False,indent=2))


def preflight(args):
    mods=pop.gen.modules();m=plan_at(args.experiment)
    j,s=verify(mods,m['generation_zero_base'])
    if pop.p0hash(s)!=m['P0_sha256']:fail('P0_CHANGED')
    if s.work or s.controller_decisions or s.model_calls:fail('BASE_NOT_CLEAN')
    for path in Path(args.experiment).glob('CYCLE_*/cycle.json'):
        c=jload(path);assert_source_stable(mods,c)
        for r in list(c.get('peers',{}).values())+[c.get('population_root')]:
            if r and Path(r).is_dir():
                jj,ss=verify(mods,r)
                if pop.p0hash(ss)!=m['P0_sha256']:fail('P0_MISMATCH')
                pop.gen.assert_fresh_prompts(mods,jj,ss)
    print(json.dumps({'status':'PERSISTENT_PREFLIGHT_OK_NO_PAID',
        'source_original_untouched':True,'P0_unchanged':True,
        'cycles_created':len(list(Path(args.experiment).glob('CYCLE_*/cycle.json'))),
        'no_mutation_by_preflight':True},ensure_ascii=False,indent=2))


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    subs=cli.add_subparsers(dest='command',required=True)
    a=subs.add_parser('init');a.add_argument('--source-root',required=True);a.add_argument('--out',required=True)
    for cmd in ('preflight','status','run'):
        a=subs.add_parser(cmd);a.add_argument('--experiment',required=True)
        if cmd=='status':a.add_argument('--out')
        if cmd=='run':
            a.add_argument('--paid',action='store_true');a.add_argument('--model',default='openai/gpt-5.6-luna')
            a.add_argument('--max-cycles',type=int,default=2)
            a.add_argument('--peer-count',type=int,default=2)
            a.add_argument('--peer-calls',type=int,default=16)
            a.add_argument('--population-calls',type=int,default=32)
            a.add_argument('--max-total-new-calls',type=int,default=128)
            a.add_argument('--slice-budget',type=int,default=8)
            a.add_argument('--checkpoint-iterations',type=int,default=12)
            a.add_argument('--max-parallel',type=int,default=2)
            a.add_argument('--max-tokens',type=int,default=16000)
            a.add_argument('--science-cpu-seconds',type=int,default=120)
            a.add_argument('--science-wall-seconds',type=int,default=160)
    args=cli.parse_args()
    try:
        {'init':init,'preflight':preflight,'status':status,'run':run}[args.command](args)
    except Exception as e:
        print(json.dumps({'status':'OPERATIONAL_ERROR_NOT_SCIENTIFIC_HOLD',
            'error_type':type(e).__name__,'detail':str(e)},ensure_ascii=False),file=sys.stderr)
        return 3
    return 0
if __name__=='__main__':raise SystemExit(main())
