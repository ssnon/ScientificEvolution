#!/usr/bin/env python3
"""Autonomous population scientist: scientific disposition, not generation/call quotas.

Runs existing V4/V3 scientific research segments with independently logged AI
population orchestration. A slice is ONLY a provider/Journal transaction boundary;
there is no maximum generation count or cumulative call quota. Root scientific
HOLD is not automatically transferred to the whole population. Every global
terminal proposal is independently challenged and adjudicated by actual model
calls. Paid execution always requires explicit --paid and a separate opt-in env.
"""
from __future__ import annotations
import argparse, contextlib, fcntl, json, os, re, sys, time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import persistent_population as pp
import population_run as pop
import population_resume as compat
from e2core.research_continuity import opportunities_for_journal, concise_index

PROTO='AUTONOMOUS_POPULATION_DISPOSITION_V1'
PEER_CHOICES={'CONTINUE_RESEARCH','YIELD_TO_POPULATION','ADD_INDEPENDENT_PEER'}
POP_CHOICES={'CONTINUE_RESEARCH','NEXT_GENERATION','SCIENTIFIC_HOLD','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}
TERMINAL={'SCIENTIFIC_HOLD','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}
REVIEW_CHOICES={'SUPPORT_TERMINAL','CHALLENGE_TERMINAL'}
FINAL_CHOICES={'CONFIRM_TERMINAL','CONTINUE_RESEARCH','NEXT_GENERATION'}
# A successful scientific pause is a LOCAL research disposition, never an
# operational failure or an automatic population-wide terminal declaration.
# Reject unrelated engine failures even if the Journal happens to say HOLD.
LOCAL_TERMINAL_ENGINE_STOPS={
    'AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED',
    'SCIENTIFIC_DISPOSITION_PROPOSED',
    'CALL_BUDGET',
    'ALREADY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS',
    'LOCAL_SCIENTIFIC_TERMINAL',
}

def normalized_research_boundary(raw_stop, journal_disposition):
    if journal_disposition in pp.TERMINAL and raw_stop in LOCAL_TERMINAL_ENGINE_STOPS:
        return 'LOCAL_SCIENTIFIC_TERMINAL'
    return raw_stop

def council_choices(phase, local_root_terminal=False):
    # A root committed to HOLD cannot execute more Work in that SAME Journal.
    # This is a runtime feasibility restriction, not an AI scientific verdict.
    if phase=='PEER':
        return PEER_CHOICES-({'CONTINUE_RESEARCH'} if local_root_terminal else set())
    if phase=='POPULATION':
        return POP_CHOICES-({'CONTINUE_RESEARCH'} if local_root_terminal else set())
    fail('UNKNOWN_COUNCIL_PHASE:'+str(phase))

S_PROMPT='''You are an autonomous POPULATION scientific steering researcher, not an operator budget planner or experimental certifier.
Your goal is an original, physically plausible, falsifiable Level-II pre-experiment scientific hypothesis or a carefully bounded scientifically justified end of investigation. Claims from AI workers are not laboratory observations; model novelty assessments are not proven novelty. Preserve the exact original P0.
Use the supplied actual Journal snapshot, worker status, independent peer proposals, and historical source limitations to decide whether this particular research population needs more investigation, should hand off completed interim research to the shared population, or should open an independent generation. DO NOT require a fixed number of calls, workers, generations, proposals, or FUSE actions. If a worker is ACTIVE, it may still have useful research; deciding to hand off does NOT mark it scientifically finished. A worker HOLD does not imply population HOLD. If the same science is being rediscovered, say so and compare actionable alternatives and independent hypotheses; do not invent new tasks to satisfy a quota. Source retrieval failure is not a negative scientific finding.
For PEER stage choose exactly one decision: CONTINUE_RESEARCH / YIELD_TO_POPULATION / ADD_INDEPENDENT_PEER. YIELD means the current peer may be handed off, whether or not local work is completed. ADD_INDEPENDENT_PEER asks for a *new independent scientific judgement* with the same source base, not a duplicate paid retry; provide the scientific justification. The current peer yields after requesting an additional peer.
For POPULATION stage choose: CONTINUE_RESEARCH / NEXT_GENERATION / SCIENTIFIC_HOLD / REVIEW_WORTHY_CANDIDATE / SCOPED_NEGATIVE. NEXT_GENERATION may be selected even with zero new assets if there is a meaningful new independent research opportunity. CONTINUE_RESEARCH requires material information value from existing Work. TERMINAL options are provisional and will be independently reviewed; they are NOT proofs. Explain why independent frontiers, unfinished Work and prior cycles do or do not justify further research. A novel proposal can be review-worthy without proven laboratory mechanism, but must include genuinely discriminating predictions and strong nulls.
Return exactly one JSON object: {"decision":"ONE_ALLOWED_LABEL","rationale":"scientific reasoning grounded in actual items","inherited_findings_considered":["ids or clear descriptions"],"new_scientific_delta":"what materially changed or has not changed","remaining_opportunities":["concrete possible scientific actions or none"],"unresolved_uncertainties":["..."],"termination_scope":"scope and limitations if terminal, otherwise empty"}. No fabricated observations, model calls, or provenance.''' 
R_PROMPT='''You are a scientifically independent skeptical reviewer of a PROPOSED population-level terminal decision. This is NOT proof/certification, and a negative result for a single candidate cannot prove the original scientific problem impossible. Review the full independent population research summary, prior Work statuses and remaining frontiers, mechanism novelty and null discriminators. Identify any scientifically valuable feasible path that the proposed termination prematurely neglects. Do not force infinite research: HOLD can be appropriate if the available methods and knowledge cannot support any genuinely worthwhile continuation. Review-worthy does not require laboratory confirmation, but does require a defensible conditional claim and test against strong nulls.
Return JSON: {"assessment":"SUPPORT_TERMINAL|CHALLENGE_TERMINAL","rationale":"...","unexplored_material_frontiers":[],"risks_of_premature_or_endless_research":[],"limits_of_conclusion":"..."}.'''
A_PROMPT='''You are the final independent POPULATION science adjudicator. Given a provisional population-wide terminal judgement, an independent skeptical review, and the actual scientific Journal snapshot, resolve whether the WHOLE population should stop or continue. No minimum number of generations or model calls; no forced scientific progress. Scientific judgement is not proof or human certification. Choose CONFIRM_TERMINAL only for the supplied proposed terminal category; otherwise choose CONTINUE_RESEARCH if the present active research has high information value, or NEXT_GENERATION if new independent work on inherited results is worth trying. A single worker HOLD cannot force global termination. Do not treat costs/budgets as scientific reasons.
Return JSON {"decision":"CONFIRM_TERMINAL|CONTINUE_RESEARCH|NEXT_GENERATION","rationale":"...","remaining_opportunities":[],"termination_scope":"..."}.'''

def fail(s): raise RuntimeError(s)
def out(obj): print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)
def atomic(path,data): pp.atomic_write(path,data)
def canon_file(p): return pp.jload(p)
def registered_primary_sources(s): return len([x for x in s.sources.values() if x.get('kind')=='PRIMARY'])
def current_cycle(root):return pp.latest_cycle(root)

def all_cycle_files(root):
    result=[]
    for d in Path(root).glob('CYCLE_*/cycle.json'):
        if re.fullmatch(r'CYCLE_\d+',d.parent.name):result.append(d)
    return sorted(result,key=lambda p:int(p.parent.name[6:]))

def root_view(mods,root):
    j,s=pop.root_status(mods,root)
    head=pp.digest(mods,j)
    imported={aid:a for aid,a in s.assets.items() if a.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
    live={aid:a for aid,a in s.assets.items() if aid not in imported}
    calls=[{'id':k,'state':v['state']} for k,v in s.model_calls.items() if v['state']!='SAVED']
    if calls:fail('UNSAVED_ROOT_MODEL_CALLS_MANUAL_REVIEW:'+str(calls[:3]))
    def as_asset(a):
        return {'id':a['id'],'kind':a['kind'],'claim':a.get('claim',''),
           'origin':a.get('origin','LIVE_WORK'),'parents':a.get('parent_ids',[]),
           'delta_from_parents':a.get('delta_from_parents',''),
           'predictions':a.get('predictions',[]),'limitations':a.get('limitations',[]),
           'source_ids':a.get('source_ids',[]),'status':a.get('status')}
    history=[{'id':k,'kind':a['kind'],'claim':a.get('claim',''),
             'parents':a.get('parent_ids',[]),'source_ids':a.get('source_ids',[])} for k,a in imported.items()]
    works=[{'id':wid,'status':w['status'],'mode':w.get('mode'),'operation':w.get('operation'),
            'question':w.get('question'), 'input_assets':w.get('asset_input_ids',[]),
            'published':w.get('published',[]),'outcome':w.get('outcome'),
            'steps':len(w.get('steps',[]))} for wid,w in s.work.items()]
    decisions=[]
    for d in s.controller_decisions[-5:]:
        raw=json.loads(j.raw(d['parsed_blob']))
        decisions.append({'id':d['id'],'disposition':raw.get('disposition'),
            'rationale':raw.get('rationale'),'actions':[
               {'operation':a.get('operation'),'asset_ids':a.get('asset_ids'),
               'question':(a.get('work') or {}).get('question')} for a in raw.get('actions',[])]})
    return {'root':str(j.root),'head':head,
        'status':pp.last_disposition(s), 'P0_sha256':pop.p0hash(s),
        'historical_asset_count':len(imported),'historical_assets':history,
        'live_asset_count':len(live),'live_assets':[as_asset(x) for x in live.values()],
        'works':works,'recent_controller_decisions':decisions,
        'sources':{'actual_tool_results':len(s.tool_results),'historical_ai':len(imported),
                   'registered_primary':registered_primary_sources(s)},
        'saved_external_calls':pp.paid_calls(s),'program_reviews_total':len(s.program_reviews)}

def snapshot(mods,experiment,cycle,stage,peer=None):
    base=cycle['base'];cbase=root_view(mods,base)
    context={'original_p0_sha256':pop.p0hash(mods.J(base).verify()),
        'cycle_number':cycle['index'],'stage':stage,
        'provenance':'VERIFIED_APPEND_ONLY_JOURNALS_UNCERTIFIED_SCIENCE',
        'population_history_recent':[],
        'inherited_base':{'root':cbase['root'],'head':cbase['head'],
            'all_inherited_assets':cbase['historical_assets']},
        'previous_population_scientific_status':None}
    for f in all_cycle_files(experiment)[-5:]:
        c=canon_file(f)
        if c['index']>=cycle['index']:continue
        if Path(c['population_root']).exists():
            v=root_view(mods,c['population_root'])
            context['population_history_recent'].append({'cycle':c['index'],
                'status':v['status'],'assets':v['live_assets'],
                'recent_decisions':v['recent_controller_decisions'],
                'open_work':[w for w in v['works'] if w['status'] in ('ACTIVE','QUEUED','DEFERRED')]})
    if stage=='PEER':
        if peer not in cycle['peers']:fail('UNKNOWN_PEER:'+str(peer))
        context['current_research']=root_view(mods,cycle['peers'][peer]);context['peer_name']=peer
        context['independent_sibling_peers']=[{'name':name, 'status':root_view(mods,path)['status'],
            'new_asset_count':root_view(mods,path)['live_asset_count']}
            for name,path in cycle['peers'].items() if name!=peer]
    else:
        context['current_research']=root_view(mods,cycle['population_root'])
        context['independent_peers']=[{'name':name,'research':root_view(mods,path)} for name,path in cycle['peers'].items()]
    return context

def meta_path(experiment):return Path(experiment)/'AUTONOMOUS_META'
def bootstrap(args):
    if args.paid:fail('BOOTSTRAP_MUST_BE_NO_PAID')
    pp.init(SimpleNamespace(source_root=args.source_root,out=args.out))
    pop.gen.pin_native_source(args.out)
    init_meta(SimpleNamespace(experiment=args.out,paid=False))

def init_meta(args):
    if args.paid:fail('INIT_MUST_BE_NO_PAID')
    mods=pop.gen.modules();m=pp.plan_at(args.experiment)
    root=Path(args.experiment).resolve();metadata=meta_path(root)
    if metadata.exists():fail('META_ALREADY_INITIALIZED_NO_OVERWRITE')
    source=mods.J(m['generation_zero_base']);source_state=source.verify()
    j=mods.J(metadata)
    j.init(source_state.program['problem'],origin='INDEPENDENT_POPULATION_SCIENCE_COORDINATOR',
           criteria=source_state.program.get('criteria'))
    j.append('OPERATIONAL_PAUSE',{'reason':'AUTONOMOUS_INITIALIZED_READ_ONLY_ROOT_REFERENCES',
        'persistent_root':str(root),'persistent_manifest_sha256':mods.sha((root/'persistent.json').read_bytes()),
        'original_p0_sha256':m['P0_sha256'],
        'all_study_root_science_remains_unverified':True})
    pp.newwrite(root/'autonomous.json',{'protocol':PROTO,'experiment':str(root),
         'meta_root':str(metadata), 'persistent_manifest_sha256':mods.sha((root/'persistent.json').read_bytes()),
         'native_source_pin_sha256':mods.sha((root/pop.gen.NATIVE_PIN_NAME).read_bytes()) if (root/pop.gen.NATIVE_PIN_NAME).is_file() else None,
         'P0_sha256':m['P0_sha256'],'model_choices_are_scientific_judgements_not_certificates':True,
         'no_generation_or_cumulative_call_limit':True,'operator_controls':{'stop_file':'STOP_REQUESTED',
         'explicit_paid_consent_each_run':True}})
    out({'status':'AUTONOMOUS_COORDINATOR_READY_NO_PAID','experiment':str(root),
         'meta_root':str(metadata),'existing_cycles':len(all_cycle_files(root))})

def meta_check(mods,experiment):
    m=pp.plan_at(experiment);cfg=canon_file(Path(experiment)/'autonomous.json')
    if cfg.get('protocol')!=PROTO or cfg.get('experiment')!=str(Path(experiment).resolve()):fail('AUTONOMOUS_MANIFEST_MISMATCH')
    if cfg['persistent_manifest_sha256']!=mods.sha((Path(experiment)/'persistent.json').read_bytes()):fail('PERSISTENT_MANIFEST_CHANGED')
    if cfg['P0_sha256']!=m['P0_sha256']:fail('P0_MISMATCH')
    if cfg.get('native_source_pin_sha256') is not None:
        pin=Path(experiment)/pop.gen.NATIVE_PIN_NAME
        if not pin.is_file() or mods.sha(pin.read_bytes())!=cfg['native_source_pin_sha256']:
            fail('NATIVE_SOURCE_PIN_MANIFEST_CHANGED')
    j=mods.J(cfg['meta_root']);s=j.verify()
    if any(c['state']!='SAVED' for c in s.model_calls.values()):fail('META_UNSAVED_MODEL_CALL_NO_RETRY')
    return j,s,cfg

def model_decision(mods,experiment,kind,ctx,prompt,choices,max_tokens,model):
    from e2core.provider import DurableModel
    j,s,cfg=meta_check(mods,experiment)
    ident='M_'+mods.sha(mods.canon({'kind':kind,'context':ctx}))[:30]
    prev=[x for x in s.controller_decisions if x['id']==ident]
    if prev:
        obj=json.loads(j.raw(prev[0]['parsed_blob']))
        if obj.get('decision',obj.get('assessment')) not in choices:fail('CACHED_INVALID_META_DECISION')
        if not any(r.get('reviewer_id')==ident for r in s.program_reviews):
            prior_category=(ctx.get('proposed_scientific_terminal_decision') or {}).get('decision') if isinstance(ctx,dict) else None
            repaired_status=({'SCIENTIFIC_HOLD':'HOLD_WITH_RATIONALE',
                'REVIEW_WORTHY_CANDIDATE':'REVIEW_WORTHY_CANDIDATE',
                'SCOPED_NEGATIVE':'SCOPED_NEGATIVE'}.get(prior_category,'ONGOING')
                if obj.get('decision')=='CONFIRM_TERMINAL' else 'ONGOING')
            j.append('PROGRAM_REVIEWED',{'reviewer_id':ident,'scientific_status':repaired_status,
                'rationale':obj['rationale'],'considered_asset_ids':[],
                'unresolved_opportunities':obj.get('remaining_opportunities',[]),
                'recovered_prior_committed_meta_decision':True})
        return obj,ident,False
    dm=DurableModel(j,approved=True,max_new_calls=1,model=model,max_tokens=max_tokens)
    raw=dm.call('CALL_'+ident,'CONTROLLER',None,prompt,ctx)
    # DurableModel saves response before parsing; invalid response must not be re-billed.
    try:obj=json.loads(raw)
    except (TypeError,ValueError):fail('META_INVALID_JSON_SAVED_NO_AUTOMATIC_REISSUE:'+ident)
    if not isinstance(obj,dict):fail('META_NONOBJECT_JSON_SAVED_NO_REISSUE:'+ident)
    label=obj.get('decision',obj.get('assessment'))
    if label not in choices or not isinstance(obj.get('rationale'),str) or not obj['rationale'].strip():
        fail('META_INVALID_DECISION_SCHEMA_SAVED_NO_AUTOMATIC_REISSUE:'+ident)
    if kind=='STEER' and not isinstance(obj.get('remaining_opportunities'),list):fail('META_OPPORTUNITIES_MISSING_SAVED:'+ident)
    if kind=='STEER' and not isinstance(obj.get('inherited_findings_considered'),list):fail('META_FINDINGS_MISSING_SAVED:'+ident)
    j.append('CONTROLLER_DECISION',{'id':ident,'call_id':'CALL_'+ident,
        'parsed_blob':j.blob(obj),'rationale':obj['rationale']})
    # A steering model's proposed STOP is NOT the final science disposition.
    # Only the adjudicator's confirmed category receives terminal program status.
    preliminary = ctx.get('proposed_scientific_terminal_decision',{}) if isinstance(ctx,dict) else {}
    confirmed_type = preliminary.get('decision') if label=='CONFIRM_TERMINAL' else None
    science_status = {'SCIENTIFIC_HOLD':'HOLD_WITH_RATIONALE',
        'REVIEW_WORTHY_CANDIDATE':'REVIEW_WORTHY_CANDIDATE',
        'SCOPED_NEGATIVE':'SCOPED_NEGATIVE'}.get(confirmed_type,'ONGOING')
    j.append('PROGRAM_REVIEWED',{'reviewer_id':ident,'scientific_status':science_status,
        'rationale':obj['rationale'],'considered_asset_ids':[],
        'unresolved_opportunities':obj.get('remaining_opportunities',[]),
        'not_scientific_certification':True, 'step_kind':kind})
    return obj,ident,True

def terminal_adjudication(mods,experiment,ctx,proposed,origin,args):
    review_ctx={'proposed_scientific_terminal_decision':proposed,
        'underlying_research':ctx,'original_model_call':origin}
    obj,rid,_=model_decision(mods,experiment,'INDEPENDENT_TERMINAL_REVIEW',review_ctx,R_PROMPT,
                             REVIEW_CHOICES,args.max_tokens,args.model)
    verdict_ctx={'proposed_scientific_terminal_decision':proposed,
        'independent_skeptical_review':obj,
        'underlying_research':ctx,'original_model_call':origin,'review_id':rid}
    locally_terminal=(ctx.get('current_research') or {}).get('status') in pp.TERMINAL
    final_options=FINAL_CHOICES-({'CONTINUE_RESEARCH'} if locally_terminal else set())
    prompt=A_PROMPT
    if locally_terminal:
        verdict_ctx['runtime_feasibility']={
            'research_root_locally_terminal':True,
            'same_root_continuation_is_not_executable':True,
            'allowed_decisions':sorted(final_options),
            'if_material_frontier_remains':'NEXT_GENERATION'}
        prompt+='\nOPERATIONAL FACT: Current research ROOT has committed a local terminal program review. CONTINUE_RESEARCH on this same immutable Journal is not executable. If independent science justifies more research, choose NEXT_GENERATION. Otherwise CONFIRM_TERMINAL if justified. This restriction does not decide the science for you.'
    res,aid,_=model_decision(mods,experiment,'FINAL_TERMINAL_ADJUDICATION',verdict_ctx,prompt,
        final_options,args.max_tokens,args.model)
    return res,aid,obj

def last_meta_outcome(mods,experiment):
    j,s,_=meta_check(mods,experiment)
    term=[]
    for d in s.controller_decisions:
        data=json.loads(j.raw(d['parsed_blob']))
        if data.get('decision')=='CONFIRM_TERMINAL':term.append((d,data))
    return term[-1] if term else None

SCHEMA_QUARANTINE_REASON='PEER_SCHEMA_RECOVERY_EXHAUSTED_OPERATIONAL_QUARANTINE_NOT_SCIENCE'

def schema_rejection_evidence(mods,peer_root):
    """Read actual rejected plan events; never infer a scientific outcome."""
    donor,state=pop.root_status(mods,peer_root)
    if state.controller_decisions:
        fail('SCHEMA_RECOVERY_TARGET_ALREADY_HAS_COMMITTED_DECISION')
    if state.work or any(a.get('origin')!='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'
                         for a in state.assets.values()):
        fail('SCHEMA_RECOVERY_TARGET_HAS_LIVE_SCIENCE_REQUIRES_MANUAL_REVIEW')
    problems=[]
    for e in donor._events():
        if e['kind']=='OPERATIONAL_PAUSE':
            reason=e['payload'].get('reason','')
            if reason.startswith('CONTROLLER_PLAN_REJECTED:'):
                cid=e['payload'].get('call_id')
                call=state.model_calls.get(cid)
                if not call or call['actor']!='CONTROLLER' or call['state']!='SAVED':
                    fail('SCHEMA_REJECTION_WITHOUT_SAVED_CONTROLLER_CALL')
                problems.append({'reason':reason,'call_id':cid,
                                 'response_blob':call['response_blob']})
    # Never classify a single bad answer as repeated schema exhaustion.
    if len(problems)<3:
        fail('SCHEMA_EXHAUSTION_REQUIRES_AT_LEAST_3_SAVED_REJECTIONS')
    return {'root':str(donor.root),'head':pp.digest(mods,donor),
        'rejected_controller_attempts':problems,'controller_decisions':0,
        'science_extracted_from_rejected_plan':False}

def schema_quarantines(mods,experiment,cycle,verify_heads=True):
    """The meta Journal, not a file flag, authorizes a no-science peer report."""
    j,s,_=meta_check(mods,experiment)
    found={}
    for e in j._events():
        if e['kind']!='OPERATIONAL_PAUSE':continue
        p=e['payload']
        if p.get('reason')!=SCHEMA_QUARANTINE_REASON or p.get('cycle_number')!=cycle['index']:
            continue
        peer=p.get('peer')
        if peer not in cycle['peers'] or peer in found:fail('SCHEMA_QUARANTINE_DUPLICATE_OR_UNKNOWN_PEER')
        if p.get('peer_root')!=cycle['peers'][peer]:fail('SCHEMA_QUARANTINE_ROOT_CHANGED')
        if verify_heads:
            actual=schema_rejection_evidence(mods,p['peer_root'])
            if actual['head']!=p['peer_head'] or \
               actual['rejected_controller_attempts']!=p['rejected_controller_attempts']:
                fail('QUARANTINED_PEER_JOURNAL_DRIFT_OR_TAMPER')
        found[peer]=p
    return found

def quarantine_peer_schema(mods,experiment,cycle,peer,reported_stop):
    """Explicitly preserve a failed peer and allow healthy peers to progress."""
    if reported_stop!='SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED':
        fail('UNSUPPORTED_OPERATIONAL_STOP_FOR_QUARANTINE')
    if cycle['stage']!='PEERS' or peer not in cycle['peers']:
        fail('SCHEMA_QUARANTINE_WRONG_STAGE_OR_PEER')
    if peer in schema_quarantines(mods,experiment,cycle):
        return {'status':'ALREADY_QUARANTINED_NO_NEW_CALLS','peer':peer}
    evidence=schema_rejection_evidence(mods,cycle['peers'][peer])
    j,_,_=meta_check(mods,experiment)
    j.append('OPERATIONAL_PAUSE',{
        'reason':SCHEMA_QUARANTINE_REASON,'cycle_number':cycle['index'],
        'peer':peer,'peer_root':cycle['peers'][peer],
        'peer_head':evidence['head'],
        'rejected_controller_attempts':evidence['rejected_controller_attempts'],
        'reported_stop_reason':reported_stop,
        'scientific_disposition':None,'not_a_scientific_hold':True,
        'no_controller_decision_fabricated':True,'no_paid_retry':True})
    return {'status':'SCHEMA_EXHAUSTED_PEER_QUARANTINED_NO_PAID',
            'peer':peer,'cycle_number':cycle['index'],
            'rejected_controller_attempts':len(evidence['rejected_controller_attempts']),
            'healthy_peer_research_preserved':True}

def recover_schema(args):
    """Recover the exact previous operational boundary from verified saved history."""
    if args.paid:fail('SCHEMA_RECOVERY_MUST_BE_NO_PAID')
    mods=pop.gen.modules();meta_check(mods,args.experiment)
    cycle=current_cycle(args.experiment)
    if not cycle:fail('SCHEMA_RECOVERY_NO_CYCLE')
    print(json.dumps(quarantine_peer_schema(mods,args.experiment,cycle,args.peer,
        'SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED'),ensure_ascii=False,indent=2))

def stop_requested(experiment):return (Path(experiment)/'STOP_REQUESTED').exists()
def ensure_not_stopped(experiment):
    if stop_requested(experiment):
        out({'status':'OPERATIONAL_PAUSE_USER_STOP_FILE_NOT_SCIENTIFIC_HOLD',
             'file':str(Path(experiment)/'STOP_REQUESTED')})
        return False
    return True

def drive_slice(mods,root,kind,args,peer_names=()):
    j,s=pop.root_status(mods,root)
    if pp.last_disposition(s) in pp.TERMINAL:
        return {'stop':'LOCAL_SCIENTIFIC_TERMINAL','spent':0}
    spec=SimpleNamespace(paid=True,model=args.model,max_new_calls=args.slice_budget,
        slice_budget=args.slice_budget,checkpoint_iterations=args.checkpoint_iterations,
        max_parallel=args.max_parallel,max_tokens=args.max_tokens,
        science_cpu_seconds=args.science_cpu_seconds,science_wall_seconds=args.science_wall_seconds)
    if kind=='PEER':
        with pp.previous_population_bridge(mods):
            r=pop.gen.drive(mods,root,spec,'syn')
    else:
        with pp.population_science_bridge(mods,root,peer_names),compat.historical_input_compat(mods,root):
            r=pop.gen.drive(mods,root,spec,'syn')
    _,s2=pop.root_status(mods,root)
    original_stop=r.get('stop_reason')
    recorded_disposition=pp.last_disposition(s2)
    normalized=normalized_research_boundary(original_stop,recorded_disposition)
    return {'stop':normalized, 'engine_stop_reason':original_stop,
            'spent':r.get('new_calls_this_launch',0),
            'latest_scientific_disposition':recorded_disposition,
            'assets':len(s2.assets),'decisions':len(s2.controller_decisions)}

def mark_cycle(cycle,root,new_stage):
    cycle['stage']=new_stage;pp.update_cycle(root,cycle)

def add_peer(mods,experiment,cycle):
    # Scientific peer-addition is model-selected and recorded, never a fixed population quota.
    n=len(cycle['peers'])+1
    name=f'SYN_{n:02d}'
    folder=Path(cycle['base']).parent/name
    if name in cycle['peers'] or folder.exists():fail('ADDITIONAL_PEER_ALREADY_EXISTS_MANUAL_REVIEW')
    b,s=pp.assert_source_stable(mods,cycle)
    pop.clone_at_checkpoint(mods,cycle['base'],folder,len(b._events()),cycle['base_head']['head_sha256'])
    cycle['peers'][name]=str(folder)
    pp.update_cycle(experiment,cycle)
    out({'status':'AI_SELECTED_ADDITIONAL_INDEPENDENT_PEER','generation':cycle['index'],
         'peer':name,'original_base_unchanged':True})

def council(mods,experiment,cycle,phase,args,peer=None):
    ctx=snapshot(mods,experiment,cycle,phase,peer)
    if phase=='POPULATION':
        # The independent G0 PEER council never receives external inherited
        # rejected proposals. Model may choose or ignore them after pooling.
        idx=opportunities_for_journal(mods.J(cycle['population_root']))
        if idx:
            ctx['unregistered_opportunity_index']=concise_index(idx)
    local_root_terminal=ctx['current_research'].get('status') in pp.TERMINAL
    options=council_choices(phase,local_root_terminal)
    prompt=S_PROMPT+'\nCurrent decision stage: '+phase
    if ctx.get('unregistered_opportunity_index'):
        prompt+=('\nThe optional unregistered_opportunity_index contains previously '
                 'rejected model proposals, NOT scientific results or primary '
                 'sources. Decide freely whether any merits INFORMED follow-up '
                 'after independent peers have been pooled; no forced retry.')
    if local_root_terminal:
        ctx['runtime_feasibility']={
            'research_root_locally_terminal':True,
            'same_root_continuation_is_not_executable':True,
            'allowed_decisions':sorted(options),
            'research_can_continue_in_a_new_independent_root':True}
        prompt+='\nOPERATIONAL FACT: Local research Controller has already committed a terminal program review. It does NOT automatically terminate the global population. This same Journal cannot accept new Work. Evaluate remaining scientific opportunities autonomously: POPULATION may choose NEXT_GENERATION or propose a terminal decision for independent skeptical review; PEER may YIELD_TO_POPULATION or ADD_INDEPENDENT_PEER. CONTINUE_RESEARCH on this same ROOT is not executable. Do not reinterpret this as proof of P0 resolution.'
    decision,ident,new=model_decision(mods,experiment,'STEER',ctx,prompt,options,args.max_tokens,args.model)
    result=decision['decision']
    out({'status':'AI_POPULATION_SCIENCE_JUDGMENT','generation':cycle['index'],
         'phase':phase,'peer':peer,'decision':result,'model_journal_id':ident,
         'new_model_call':new,'rationale':decision['rationale']})
    if phase=='POPULATION' and result in TERMINAL:
        # Prevent treating a single model's terminal judgment as global truth.
        final,review_id,rev=terminal_adjudication(mods,experiment,ctx,decision,ident,args)
        out({'status':'INDEPENDENT_SCIENTIFIC_TERMINAL_REVIEW',
           'proposed_terminal':result,'skeptical_review':rev['assessment'],
           'adjudication':final['decision'],'review_journal_id':review_id,
           'rationale':final['rationale']})
        if final['decision']=='CONFIRM_TERMINAL':return 'CONFIRMED_TERMINAL',result
        return final['decision'],None
    return result,None

def step_once(mods,experiment,args):
    if not ensure_not_stopped(experiment):return 'PAUSE'
    cycle=current_cycle(experiment)
    if cycle is None:
        c=pp.create_cycle(mods,experiment,0,args.bootstrap_peers,pp.plan_at(experiment)['original_source'])
        c['initial_peer_count']=args.bootstrap_peers;pp.update_cycle(experiment,c)
        return 'CONTINUE'
    if cycle['stage']=='COMPLETE':
        # No automatic generation just because a fixed call budget expired.
        # A scientific council decides whether to keep the live population or
        # start another independent generation, even when asset count did not rise.
        decision,terminal=council(mods,experiment,cycle,'POPULATION',args)
        if decision=='CONFIRMED_TERMINAL':return 'SCIENTIFIC_TERMINAL'
        if decision=='CONTINUE_RESEARCH':
            if pp.last_disposition(pop.root_status(mods,cycle['population_root'])[1]) in pp.TERMINAL:
                fail('COUNCIL_WANTS_CONTINUE_ON_LOCALLY_TERMINAL_ROOT_USE_NEXT_GENERATION')
            mark_cycle(cycle,experiment,'POPULATION')
            return 'CONTINUE'
        if decision!='NEXT_GENERATION':fail('UNEXPECTED_POPULATION_DECISION:'+decision)
        # Reset lineage through a clean, auditable generation boundary without
        # coercing old ACTIVE Work into DONE or erasing their historical status.
        c=pp.create_cycle(mods,experiment,cycle['index']+1,args.bootstrap_peers,cycle['population_root'])
        c['initial_peer_count']=args.bootstrap_peers;pp.update_cycle(experiment,c)
        return 'CONTINUE'
    if cycle['stage']=='PEERS':
        # One atomic step per peer; council, not a number of research calls,
        # chooses the moment a peer yields scientific work for pooling.
        j,s,_=meta_check(mods,experiment)
        yielded=set()
        for d in s.controller_decisions:
            raw=json.loads(j.raw(d['parsed_blob']))
            if raw.get('decision') in ('YIELD_TO_POPULATION','ADD_INDEPENDENT_PEER'):
                request=json.loads(j.raw(s.model_calls[d['call_id']]['request_blob']))
                user=json.loads(request['messages'][1]['content'])
                if user.get('stage')=='PEER' and user.get('cycle_number')==cycle['index']:
                    yielded.add(user.get('peer_name'))
        # Operational schema quarantine is NOT a scientific HOLD or a fabricated
        # Controller judgement. Preserve the saved rejection attempts as such.
        quarantine=schema_quarantines(mods,experiment,cycle)
        yielded.update(quarantine)
        # Repair a crash between a committed ADD_PEER decision and its clone.
        add_ids=[d for d in s.controller_decisions if json.loads(j.raw(d['parsed_blob'])).get('decision')=='ADD_INDEPENDENT_PEER']
        current_adds=0
        for d in add_ids:
            wire=json.loads(j.raw(s.model_calls[d['call_id']]['request_blob']))
            rec=json.loads(wire['messages'][1]['content'])
            if rec.get('stage')=='PEER' and rec.get('cycle_number')==cycle['index']:
                current_adds+=1
        baseline=cycle.get('initial_peer_count',args.bootstrap_peers)
        if len(cycle['peers'])<baseline+current_adds:
            add_peer(mods,experiment,cycle)
            return 'CONTINUE'
        if len(cycle['peers'])>baseline+current_adds:fail('PEER_COUNT_RECEIPT_INCONSISTENT')
        todo=[(name,root) for name,root in cycle['peers'].items() if name not in yielded]
        if not todo:
            mark_cycle(cycle,experiment,'COMBINE')
            return 'CONTINUE'
        # Rotate using smallest existing paid call count, not pre-assigned favored topic.
        name,root=min(todo,key=lambda v:(pp.paid_calls(pop.root_status(mods,v[1])[1]),v[0]))
        before=pp.digest(mods,mods.J(root))
        result=drive_slice(mods,root,'PEER',args)
        out({'status':'PEER_RESEARCH_SEGMENT','generation':cycle['index'], 'peer':name,**result})
        if result['stop']=='SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED':
            out(quarantine_peer_schema(mods,experiment,cycle,name,result['stop']))
            return 'CONTINUE'
        if result['spent']==0 and result['stop'] not in ('ALREADY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS','LOCAL_SCIENTIFIC_TERMINAL'):
            fail('NO_PROVIDER_PROGRESS_OPERATIONAL_REVIEW_REQUIRED')
        if result['stop'] not in ('CALL_BUDGET','ALREADY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS','LOCAL_SCIENTIFIC_TERMINAL'):
            fail('PEER_OPERATIONAL_STOP_REQUIRES_REVIEW:'+str(result['stop']))
        if result['spent']==0 and before==pp.digest(mods,mods.J(root)) and result['stop']=='CALL_BUDGET':
            fail('PEER_NO_PROGRESS_AFTER_RESEARCH_SEGMENT')
        # A peer must have one actual committed scientific Controller judgement
        # before its result can be imported by the existing population bridge.
        if not pop.root_status(mods,root)[1].controller_decisions:
            out({'status':'PEER_STILL_ACQUIRING_FIRST_COMMITTED_CONTROLLER_DECISION',
                 'peer':name,'not_a_scientific_quota':True})
            return 'CONTINUE'
        decision,_=council(mods,experiment,cycle,'PEER',args,name)
        if decision=='CONTINUE_RESEARCH' and pp.last_disposition(pop.root_status(mods,root)[1]) in pp.TERMINAL:
            fail('PEER_LOCAL_TERMINAL_CANNOT_CONTINUE_SAME_ROOT')
        if decision=='ADD_INDEPENDENT_PEER':add_peer(mods,experiment,cycle)
        return 'CONTINUE'
    if cycle['stage']=='COMBINE':
        outcome=pp.combine(mods,cycle,blocked_peers=schema_quarantines(mods,experiment,cycle))
        out(outcome)
        mark_cycle(cycle,experiment,'POPULATION')
        return 'CONTINUE'
    if cycle['stage']=='POPULATION':
        root=cycle['population_root']
        ss=pop.root_status(mods,root)[1]
        if pp.last_disposition(ss) not in pp.TERMINAL:
            result=drive_slice(mods,root,'POPULATION',args,tuple(cycle['peers']))
            out({'status':'POPULATION_RESEARCH_SEGMENT','generation':cycle['index'],**result})
            if result['spent']==0 and result['stop'] not in ('ALREADY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS','LOCAL_SCIENTIFIC_TERMINAL'):
                fail('NO_POPULATION_PROVIDER_PROGRESS_OPERATIONAL_REVIEW_REQUIRED')
            if result['stop'] not in ('CALL_BUDGET','ALREADY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS','LOCAL_SCIENTIFIC_TERMINAL'):
                fail('POPULATION_OPERATIONAL_STOP_REQUIRES_REVIEW:'+str(result['stop']))
        decision,terminal=council(mods,experiment,cycle,'POPULATION',args)
        if decision=='CONFIRMED_TERMINAL':
            mark_cycle(cycle,experiment,'COMPLETE')
            return 'SCIENTIFIC_TERMINAL'
        if decision=='NEXT_GENERATION':
            mark_cycle(cycle,experiment,'COMPLETE')
            return 'CONTINUE'
        if decision=='CONTINUE_RESEARCH':
            if pp.last_disposition(pop.root_status(mods,root)[1]) in pp.TERMINAL:
                fail('LOCALLY_TERMINAL_ROOT_REQUIRES_NEXT_GENERATION_OR_GLOBAL_STOP')
            return 'CONTINUE'
        fail('UNEXPECTED_POPULATION_DECISION:'+decision)
    fail('UNKNOWN_CYCLE_STAGE:'+str(cycle['stage']))

def latest_science_report(mods,experiment):
    j,s,cfg=meta_check(mods,experiment)
    decisions=[]
    for d in s.controller_decisions:
        v=json.loads(j.raw(d['parsed_blob']))
        decisions.append({'id':d['id'],'decision':v.get('decision',v.get('assessment')),
                          'rationale':v.get('rationale'),'review_call_id':d['call_id']})
    found=last_meta_outcome(mods,experiment)
    latest=current_cycle(experiment)
    return {'protocol':PROTO,'meta_root':str(j.root),'decisions':decisions,
        'global_scientific_terminal_confirmed':bool(found),
        'last_scientific_terminal':found[1] if found else None,
        'cycles':len(all_cycle_files(experiment)),
        'latest_cycle':{'index':latest['index'],'stage':latest['stage']} if latest else None,
        'total_paid_in_research_roots':pp.total_paid_in_experiment(mods,experiment),
        'total_paid_in_meta_root':pp.paid_calls(s),
        'operationally_quarantined_peers':({k:{'cycle':v['cycle_number'],
            'reason':v['reason'],'saved_rejections':len(v['rejected_controller_attempts'])}
            for k,v in schema_quarantines(mods,experiment,latest).items()} if latest else {}),
        'no_scientific_certification':True}

def run(args):
    if not args.paid or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':fail('EXPLICIT_PAID_APPROVAL_REQUIRED')
    if args.slice_budget<1 or args.bootstrap_peers<1:fail('INVALID_ATOMIC_SLICE_OR_INITIAL_PEER_COUNT')
    mods=pop.gen.modules();pop.gen.verify_runtime_source(mods,args.experiment);meta_check(mods,args.experiment)
    root=Path(args.experiment).resolve();
    if last_meta_outcome(mods,root):
        out({'status':'ALREADY_GLOBALLY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS'});return
    lock=root/'.autonomous_population.lock'
    with lock.open('a+b') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:fail('ANOTHER_AUTONOMOUS_RUN_ACTIVE')
        try:
            begin=time.monotonic();iterations=0;last_notice=0
            while True:
                if not ensure_not_stopped(root):return
                state=step_once(mods,root,args)
                iterations+=1
                if state=='SCIENTIFIC_TERMINAL':
                    out({'status':'AUTONOMOUS_GLOBAL_SCIENTIFIC_DISPOSITION_RECORDED',
                        'not_proof_of_scientific_discovery':True});return
                if state=='PAUSE':return
                if iterations-last_notice>=args.notice_every_segments:
                    last_notice=iterations
                    report=latest_science_report(mods,root)
                    out({'status':'OPERATIONAL_HEARTBEAT_NO_AUTOMATIC_LIMIT',
                         'segments_since_start':iterations,'elapsed_seconds':round(time.monotonic()-begin,1),
                         'cycles':report['cycles'],'total_paid_calls':report['total_paid_in_research_roots']+report['total_paid_in_meta_root'],
                         'stop_with':'touch '+str(root/'STOP_REQUESTED')})
        finally:fcntl.flock(handle,fcntl.LOCK_UN)

def preflight(args):
    mods=pop.gen.modules();pop.gen.verify_runtime_source(mods,args.experiment);meta_check(mods,args.experiment)
    pp.preflight(SimpleNamespace(experiment=args.experiment))
    out({'status':'AUTONOMOUS_PREFLIGHT_OK_NO_PAID',
         'no_generation_or_call_quota':True,'scientific_disposition_requires_independent_review':True,
         'current_science':latest_science_report(mods,args.experiment)})

def status(args):
    mods=pop.gen.modules();meta_check(mods,args.experiment)
    report=latest_science_report(mods,args.experiment)
    if args.out:pp.atomic_write(args.out,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    subs=cli.add_subparsers(dest='cmd',required=True)
    for cmd in ('bootstrap','init','preflight','status','run','recover-schema'):
        p=subs.add_parser(cmd)
        if cmd=='bootstrap':
            p.add_argument('--source-root',required=True);p.add_argument('--out',required=True)
            p.add_argument('--paid',action='store_true')
        else:p.add_argument('--experiment',required=True)
        if cmd=='init':p.add_argument('--paid',action='store_true')
        if cmd=='status':p.add_argument('--out')
        if cmd=='recover-schema':
            p.add_argument('--peer',required=True);p.add_argument('--paid',action='store_true')
        if cmd=='run':
            p.add_argument('--paid',action='store_true');p.add_argument('--model',default='openai/gpt-5.6-luna')
            p.add_argument('--bootstrap-peers',type=int,default=2)
            p.add_argument('--slice-budget',type=int,default=8)
            p.add_argument('--checkpoint-iterations',type=int,default=12)
            p.add_argument('--max-parallel',type=int,default=2)
            p.add_argument('--max-tokens',type=int,default=16000)
            p.add_argument('--science-cpu-seconds',type=int,default=120)
            p.add_argument('--science-wall-seconds',type=int,default=160)
            p.add_argument('--notice-every-segments',type=int,default=3)
    args=cli.parse_args()
    try: {'bootstrap':bootstrap,'init':init_meta,'preflight':preflight,'status':status,'run':run,'recover-schema':recover_schema}[args.cmd](args)
    except KeyboardInterrupt:
        out({'status':'USER_INTERRUPTED_OPERATIONAL_PAUSE_NOT_SCIENTIFIC_HOLD'});return 130
    except BaseException as exc:
        print(json.dumps({'status':'OPERATIONAL_ERROR_NOT_SCIENTIFIC_HOLD',
             'error_type':type(exc).__name__,'detail':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 3
    return 0

if __name__=='__main__':raise SystemExit(main())
