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
from e2core.peer_rejected_continuity import collect_verified_peer_rejections

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
        # M23.6.2: The immediately preceding Population also executes real
        # python_science/verified_calculation tools. Preserve its exact request
        # and result as historical EXTERNAL_AUDIT sources, just like peer tools.
        # Never replay a tool, promote an execution to scientific certification,
        # or expose inherited evidence as a new FRESH observation.
        population_science_tools=pop.record_science_tool_results(
            mods,j,source,ss,'PRIOR_POPULATION')
        # M19: Before starting a newly pinned root, recover genuine science
        # tool executions left in prior PEER journals, including unreviewed
        # Python results not yet represented in the source Population.
        # Require exact peer Journal head: never import from changed provenance.
        historical_peer_science=[]
        for sid,rec in ss.sources.items():
            if not (sid.startswith('SRC_PEER_DECISION_') and rec.get('kind')=='HISTORICAL_AI'):
                continue
            report=json.loads(source.raw(rec['blob']))
            peer_root=Path(report['original_root']).expanduser().resolve()
            if not peer_root.is_dir():fail('PRIOR_PEER_JOURNAL_NOT_FOUND:'+sid)
            peer_j,peer_s=pop.root_status(mods,peer_root)
            actual_peer_head=mods.sha(mods.canon(peer_j._events()[-1]))
            if actual_peer_head!=report['head_sha256']:
                fail('PRIOR_PEER_JOURNAL_HEAD_CHANGED:'+sid)
            name=report['peer_syn']
            record=pop.record_science_tool_results(mods,j,peer_j,peer_s,name)
            # M22: Native-source-versioned peer Worker lineage closure. This
            # replays neither research nor tools, and imports no science Asset.
            # The previous PEER Journal's saved Worker+validation steps are
            # checked before carrying rejected proposals as opportunities.
            peer_opportunities=collect_verified_peer_rejections(
                peer_j,peer_s,name,actual_peer_head,sha=mods.sha,canon=mods.canon)
            existing=set(j.verify().carried_opportunities)
            for oid,opportunity in sorted(peer_opportunities.items()):
                if oid in existing:
                    fail('M22_PEER_OPPORTUNITY_ID_ALREADY_CARRIED:'+oid)
                j.append('OPPORTUNITY_CARRIED',{
                    'opportunity':opportunity,
                    'upstream_root':str(peer_root),
                    'upstream_head_sha256':actual_peer_head,
                    'not_registered_science':True})
            historical_peer_science.append({'peer':name,'original_root':str(peer_root),
                'verified_head_sha256':actual_peer_head,
                'transferred_science_tool_results':record['registered_science_tools'],
                'new_source_ids':record['ids'],
                'rejected_worker_opportunities_carried':len(peer_opportunities),
                'rejected_opportunity_ids':sorted(peer_opportunities)})
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
            'prior_population_science_tool_carry':population_science_tools,
            'historical_peer_science_tool_carry':historical_peer_science,
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
        if getattr(args,'math_verification',False):
            from e2core.math_cycle import enable_on_clean_root
            enable_on_clean_root(mods.J(root/'BASE_000'))
        manifest={'protocol':PROTOCOL,'root':str(root),'original_source':str(source),
            'source_head':digest(mods,sj), 'P0_sha256':pop.p0hash(ss),
            'generation_zero_base':str(root/'BASE_000'),
            'math_verification_cycle':bool(getattr(args,'math_verification',False)),
            'scientific_policy':'AUTONOMOUS_EXISTING_V4_V3_CONTROLLER; NO_FORCED_FUSE_OR_WORK',
            'source_work_is_only_historical_not_SILENTLY_FINISHED':True,
            'science_certification':False}
        newwrite(root/'persistent.json',manifest)
        # The ordinary init path must pin the exact new Native source,
        # just as the frozen PEER snapshot path already does.
        # Historical source roots are NOT repinned or modified.
        pop.gen.pin_native_source(root)
        pop.gen.verify_runtime_source(mods,root/'BASE_000')
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
        if plan_at(root).get('math_verification_cycle',False):
            from e2core.math_cycle import enable_on_clean_root
            enable_on_clean_root(mods.J(base))
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
    for name,expected in cycle.get('external_peer_snapshot_heads',{}).items():
        if name not in cycle['peers']:fail('UNKNOWN_FROZEN_PEER_SNAPSHOT:'+name)
        donor,_=verify(mods,cycle['peers'][name])
        if digest(mods,donor)!=expected:fail('FROZEN_PEER_SNAPSHOT_CHANGED:'+name)
    return j,s



def _verified_peer_work_frontier(mods,j,peer,peer_root,import_receipt):
    """Transfer an exact donor Work-status SNAPSHOT, never executable Work.

    Model-authored assets stay provisional. Incomplete verification is NOT a
    scientific HOLD, a null result, a completed review, or a new calculation.
    """
    from e2core.math_cycle import pending_math_work
    donor,ds=verify(mods,peer_root)
    head=digest(mods,donor)
    if head['head_sha256']!=import_receipt['head_sha256']:
        fail('PEER_HANDOFF_HEAD_MISMATCH:'+peer)
    if pop.p0hash(ds)!=pop.p0hash(j.verify()):
        fail('PEER_HANDOFF_P0_MISMATCH:'+peer)
    source_id='SRC_PEER_DECISION_'+peer
    s=j.verify()
    if source_id not in s.sources or import_receipt['decision_receipt']!=source_id:
        fail('PEER_HANDOFF_DECISION_RECEIPT_MISSING:'+peer)
    decision=json.loads(j.raw(s.sources[source_id]['blob']))
    translations=decision['asset_id_translation']
    math_pending=set(pending_math_work(donor))
    if math_pending-set(ds.work):
        fail('PEER_HANDOFF_UNKNOWN_MATH_WORK:'+peer)
    unfinished=[]
    for wid,w in ds.work.items():
        if w['status'] not in {'ACTIVE','QUEUED','DEFERRED'} and wid not in math_pending:
            continue
        original=list(w.get('published',[]))
        mapped=[translations.get(a,a) for a in original]
        if not all(a in s.assets for a in mapped):
            fail('PEER_HANDOFF_MAPPED_ASSET_NOT_REGISTERED:'+peer+':'+wid)
        unfinished.append({
            'original_work_id':wid,'status_at_checkpoint':w['status'],
            'outcome_at_checkpoint':w.get('outcome'),
            'mode':w.get('mode'),'operation':w.get('operation'),
            'question':w.get('question'),
            'original_asset_input_ids':list(w.get('asset_input_ids',[])),
            'original_published_asset_ids':original,
            'mapped_current_root_asset_ids':mapped,
            'step_count_at_checkpoint':len(w.get('steps',[])),
            'math_verification_pending_at_checkpoint':wid in math_pending,
            'historical_not_runnable_current_root':True,
            'not_a_math_certificate_or_scientific_hold':True})
    if digest(mods,donor)!=head:
        fail('PEER_HANDOFF_DONOR_CHANGED_DURING_SNAPSHOT:'+peer)
    receipt={'kind':'VERIFIED_PEER_UNFINISHED_WORK_FRONTIER',
        'peer_syn':peer,'original_peer_root':str(donor.root),
        'original_peer_head':head,'decision_source_id':source_id,
        'unfinished_works':unfinished,
        'pending_math_review_ids':sorted(math_pending),
        'historical_work_not_executable_in_population':True,
        'population_autonomously_selects_any_follow_up':True,
        'no_automatic_rejection_certification_or_completion':True,
        'not_a_primary_source_or_new_scientific_evidence':True,
        'new_model_calls':0,'new_science_tool_executions':0}
    sid='SRC_PEER_WORK_FRONTIER_'+peer
    # Match the existing native historical-source reader shape; never promote
    # status to primary evidence or manufacture a completed tool result.
    record={**receipt,'ref':str(donor.root)+'#UNFINISHED_WORK_FRONTIER',
        'science':receipt,
        'tool_result':{'status':'HISTORICAL_WORK_STATUS_ONLY_NO_NEW_EXECUTION'},
        'science_sha256':mods.sha(mods.canon(receipt))}
    j.add_source(sid,'HISTORICAL_AI',record,
        'Verified PEER unfinished Work checkpoint, including unresolved mathematics; historical status, not completed science')
    return {'peer':peer,'source_id':sid,
        'unfinished_work_count':len(unfinished),
        'pending_math_count':len(math_pending),'original_peer_head':head}


def _verify_snapshot_external_source_pin(source_experiment):
    """Verify original V1.1 source bytes using its ORIGINAL repo, not V1.2."""
    pinfile=source_experiment/'NATIVE_RUNTIME_SOURCE_PIN.json'
    if not pinfile.is_file():fail('SNAPSHOT_ORIGINAL_PIN_MISSING')
    pin=jload(pinfile)
    if pin.get('protocol')!='M16_NATIVE_EXECUTION_SOURCE_V1':
        fail('SNAPSHOT_ORIGINAL_PIN_PROTOCOL_MISMATCH')
    oldrepo=Path(pin.get('repository','')).expanduser().resolve()
    if not oldrepo.is_dir():fail('SNAPSHOT_ORIGINAL_SOURCE_WORKTREE_MISSING')
    paths=pin.get('files')
    if not isinstance(paths,dict) or not paths:fail('SNAPSHOT_ORIGINAL_PIN_FILES_MISSING')
    actual={}
    for folder in ('runtime','AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029'):
        for file in sorted((oldrepo/folder).rglob('*.py')):
            if file.is_symlink():fail('SNAPSHOT_ORIGINAL_SOURCE_SYMLINK')
            actual[file.relative_to(oldrepo).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    if paths!=actual:fail('SNAPSHOT_ORIGINAL_NATIVE_SOURCE_PIN_MISMATCH')
    return {'original_source_worktree':str(oldrepo),
        'verified_file_count':len(actual),
        'original_pin_sha256':hashlib.sha256(pinfile.read_bytes()).hexdigest()}


def init_peer_snapshot(args):
    """No-paid, no-replay continuation using two frozen V1.1 donor PEERs.

    The V1.1 journals remain in their original pinned experiment. A NEW V1.2
    Population imports them after an exact source and Journal-head audit.
    """
    mods=pop.gen.modules()
    old_root=Path(args.source_experiment).expanduser().resolve()
    new_root=Path(args.out).expanduser().resolve()
    if new_root.exists():fail('SNAPSHOT_DESTINATION_ALREADY_EXISTS')
    old_plan=plan_at(old_root)
    if not old_plan.get('math_verification_cycle',False):
        fail('SNAPSHOT_ORIGINAL_NOT_MATH_ENABLED')
    old_cycle=latest_cycle(old_root)
    if old_cycle is None or old_cycle['index']!=0 or old_cycle['stage']!='PEERS':
        fail('SNAPSHOT_EXPECTS_V11_CYCLE_ZERO_PEERS')
    if Path(old_cycle['population_root']).exists():
        fail('SNAPSHOT_ORIGINAL_POPULATION_ALREADY_EXISTS')
    if sorted(old_cycle['peers'])!=['SYN_01','SYN_02']:
        fail('SNAPSHOT_EXPECTS_TWO_NAMED_PEERS')
    original_pin=_verify_snapshot_external_source_pin(old_root)
    old_base,old_bs=assert_source_stable(mods,old_cycle)
    source_base,source_bs=verify(mods,old_plan['generation_zero_base'])
    if old_bs.work or old_bs.model_calls or old_bs.controller_decisions:
        fail('SNAPSHOT_SOURCE_BASE_NOT_CLEAN')
    if source_bs.work or source_bs.model_calls or source_bs.controller_decisions:
        fail('SNAPSHOT_SOURCE_GEN0_BASE_NOT_CLEAN')
    if pop.p0hash(old_bs)!=old_plan['P0_sha256'] or pop.p0hash(source_bs)!=old_plan['P0_sha256']:
        fail('SNAPSHOT_ORIGINAL_P0_MISMATCH')
    before_base=digest(mods,old_base)
    before_zero=digest(mods,source_base)
    snapshots={}
    for name,path in old_cycle['peers'].items():
        donor,ds=verify(mods,path)
        if pop.p0hash(ds)!=old_plan['P0_sha256'] or not ds.controller_decisions:
            fail('SNAPSHOT_UNVERIFIED_PEER:'+name)
        if not any(c['state']=='SAVED' and c.get('actor')=='CONTROLLER' for c in ds.model_calls.values()):
            fail('SNAPSHOT_PEER_HAS_NO_SAVED_CONTROLLER:'+name)
        if not set(old_bs.assets).issubset(ds.assets):fail('SNAPSHOT_PEER_MISSING_BASE_ASSETS:'+name)
        snapshots[name]=digest(mods,donor)
    new_root.mkdir(parents=True)
    try:
        newzero=new_root/'BASE_000'
        pop.clone_at_checkpoint(mods,source_base.root,newzero,before_zero['events'],before_zero['head_sha256'])
        folder=new_root/'CYCLE_000'
        folder.mkdir()
        newbase=folder/'BASE'
        pop.clone_at_checkpoint(mods,old_base.root,newbase,before_base['events'],before_base['head_sha256'])
        basecheck,bs=verify(mods,newbase)
        if digest(mods,basecheck)!=before_base or pop.p0hash(bs)!=old_plan['P0_sha256']:
            fail('SNAPSHOT_CLONED_BASE_MISMATCH')
        manifest={**old_plan,'root':str(new_root),
            'generation_zero_base':str(newzero),
            'scientific_policy':'UNCHANGED_NATIVE_RESEARCH; VERIFIED_FROZEN_V11_PEER_SNAPSHOT_HANDOFF',
            'no_new_peer_research_in_snapshot':True,
            'math_verification_cycle':True,
            'not_scientific_certification':True}
        newwrite(new_root/'persistent.json',manifest)
        new_cycle={**old_cycle,'base':str(newbase),'base_head':before_base,
            'peers':{name:str(Path(path).resolve()) for name,path in old_cycle['peers'].items()},
            'population_root':str(folder/'POPULATION'),
            'stage':'COMBINE',
            'external_peer_snapshot_heads':snapshots,
            'source_snapshot_no_new_model_calls':True,
            'no_automatic_completion_of_unfinished_peer_work':True}
        newwrite(folder/'cycle.json',new_cycle)
        newwrite(new_root/'PEER_SNAPSHOT_IMPORT_RECEIPT.json',{
            'protocol':'V12_EXTERNAL_V11_FROZEN_PEER_SNAPSHOT_V1',
            'source_experiment':str(old_root),
            'source_persistent_sha256':hashlib.sha256((old_root/'persistent.json').read_bytes()).hexdigest(),
            'original_runtime_pin':original_pin,
            'original_generation_zero_head':before_zero,
            'original_cycle_base_head':before_base,
            'peer_heads':snapshots,'original_p0_sha256':old_plan['P0_sha256'],
            'new_model_calls':0,'new_tool_executions':0,'no_scientific_selection_during_transfer':True,
            'unfinished_work_will_be_preserved_as_history_not_current_work':True,
            'science_certified':False})
        # New root must pin the new repo's Python bytes, never edit old pins.
        pop.gen.pin_native_source(new_root)
        pop.gen.verify_runtime_source(mods,newbase)
        if digest(mods,old_base)!=before_base or digest(mods,source_base)!=before_zero:
            fail('SNAPSHOT_UPSTREAM_BASE_CHANGED_DURING_IMPORT')
        for name,path in old_cycle['peers'].items():
            dj,_=verify(mods,path)
            if digest(mods,dj)!=snapshots[name]:
                fail('SNAPSHOT_PEER_CHANGED_DURING_IMPORT:'+name)
    except BaseException:
        shutil.rmtree(new_root)
        raise
    print(json.dumps({'status':'FROZEN_V11_PEER_SNAPSHOT_PREPARED_NO_PAID',
        'new_experiment':str(new_root),'source_untouched':True,
        'new_model_calls':0,'phase':'COMBINE',
        'historical_peer_call_count':sum(paid_calls(verify(mods,r)[1]) for r in old_cycle['peers'].values()),
        'scientific_certification':False},ensure_ascii=False,indent=2))


def combine_snapshot(args):
    """Commit ONLY no-paid native COMBINE after exact source/donor checks."""
    mods=pop.gen.modules()
    m=plan_at(args.experiment)
    cycle=latest_cycle(args.experiment)
    if not cycle or cycle['stage']!='COMBINE' or not cycle.get('external_peer_snapshot_heads'):
        fail('NOT_AT_FROZEN_SNAPSHOT_COMBINE_BOUNDARY')
    if not m.get('math_verification_cycle',False):fail('MATH_CYCLE_NOT_ENABLED')
    pop.gen.verify_runtime_source(mods,cycle['base'])
    assert_source_stable(mods,cycle)
    import_receipt=jload(Path(args.experiment).expanduser().resolve()/'PEER_SNAPSHOT_IMPORT_RECEIPT.json')
    if import_receipt.get('protocol')!='V12_EXTERNAL_V11_FROZEN_PEER_SNAPSHOT_V1':
        fail('SNAPSHOT_IMPORT_RECEIPT_INVALID')
    prior_pin=_verify_snapshot_external_source_pin(
        Path(import_receipt['source_experiment']).expanduser().resolve())
    if prior_pin!=import_receipt['original_runtime_pin']:
        fail('SNAPSHOT_ORIGINAL_RUNTIME_PIN_CHANGED_BEFORE_COMBINE')
    result=combine(mods,cycle)
    cycle['stage']='POPULATION'
    update_cycle(args.experiment,cycle)
    print(json.dumps({'status':'SNAPSHOT_COMBINE_FINISHED_NO_PAID',
        'combine_result':result,'phase':'POPULATION',
        'new_model_calls':0,'scientific_certification':False},ensure_ascii=False,indent=2))


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
            current_work=j.verify().work
            current_ids=sorted(current_work)
            historical_ids=sorted(old['work_statuses'])
            ctx['previous_generation_scientific_portfolio']={
                'source_root':old['source_root'],
                'head':old['source_head'],
                'work_statuses':old['work_statuses'],
                'previous_review':old['previous_review'],
                'recent_controller_decisions':old['recent_controller_decisions'],
                'historical_status_only_not_new_execution':True,
                'historical_work_ids':historical_ids,
                'historical_status_is_original_root_snapshot':True,
                'historical_active_does_not_mean_current_active':True,
                'historical_work_not_auto_resumed':True}
            ctx['current_journal_work_execution_scope']={
                'current_root':str(j.root),
                'current_root_work_ids':current_ids,
                'eligible_portfolio_decisions_work_ids':current_ids,
                'currently_runnable_work_ids':sorted(
                    wid for wid,w in current_work.items() if w['status'] in ('QUEUED','ACTIVE')),
                'historical_work_ids_not_executable_here':historical_ids,
                'no_automatic_cross_generation_work_resumption':True,
                'model_must_authorize_new_work_if_historical_science_warrants_continuation':True,
                'instruction':('Historical ACTIVE/QUEUED/DEFERRED are past statuses. '                             'portfolio_decisions may name only current-root Work. '
                             'For a valuable historical frontier, independently choose a NEW '
                             'actions work with a unique work.id, or justify no continuation.')}
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
            frontier_sid='SRC_PEER_WORK_FRONTIER_'+name
            if frontier_sid in ss.sources:
                frontier=json.loads(j.raw(ss.sources[frontier_sid]['blob']))
                if (frontier.get('peer_syn')!=name or
                        frontier.get('original_peer_head',{}).get('head_sha256')!=report['head_sha256']):
                    fail('PEER_FRONTIER_SOURCE_MISMATCH:'+name)
                reports[-1]['historical_work_frontier_source_id']=frontier_sid
                reports[-1]['unresolved_peer_works']=frontier['unfinished_works']
                reports[-1]['pending_math_review_ids']=frontier['pending_math_review_ids']
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
            report['unfinished_work_frontier']=_verified_peer_work_frontier(
                mods,j,peer,path,report)
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
            if m.get('math_verification_cycle',False):
                from e2core.math_cycle import pending_math_work
                pending={name:pending_math_work(mods.J(path)) for name,path in cycle['peers'].items()}
                pending={name:items for name,items in pending.items() if items}
                if pending:
                    print(json.dumps({'status':'PEER_MATH_REVIEW_UNFINISHED_WILL_TRANSFER',
                        'pending':pending,'work_not_completed_or_certified':True,
                        'not_scientific_disposition':True}),flush=True)
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
            if m.get('math_verification_cycle',False):
                from e2core.math_cycle import pending_math_work
                remaining=pending_math_work(mods.J(cycle['population_root']))
                if remaining:
                    print(json.dumps({'status':'POPULATION_MATH_REVIEW_UNFINISHED_RETAINED_AS_HISTORY',
                        'pending_work_ids':remaining,
                        'not_scientific_disposition':True,
                        'no_automatic_math_certification':True}),flush=True)
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
    from e2core import math_cycle as _native_math_cycle
    for row in cycles:
        pop_row=row.get('population')
        if pop_row is not None:
            cj=mods.J(str(Path(args.experiment)/f"CYCLE_{row['generation']:03d}"/'POPULATION'))
            pop_row['native_math_verification_cycle']=_native_math_cycle.controller_context(cj)
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
    a.add_argument('--math-verification',action='store_true',help='Opt in to native recursive mathematics verification for NEW roots')
    a=subs.add_parser('init-peer-snapshot')
    a.add_argument('--source-experiment',required=True);a.add_argument('--out',required=True)
    a=subs.add_parser('combine-snapshot');a.add_argument('--experiment',required=True)
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
        {'init':init,'init-peer-snapshot':init_peer_snapshot,
         'combine-snapshot':combine_snapshot,
         'preflight':preflight,'status':status,'run':run}[args.command](args)
    except Exception as e:
        print(json.dumps({'status':'OPERATIONAL_ERROR_NOT_SCIENTIFIC_HOLD',
            'error_type':type(e).__name__,'detail':str(e)},ensure_ascii=False),file=sys.stderr)
        return 3
    return 0
if __name__=='__main__':raise SystemExit(main())
