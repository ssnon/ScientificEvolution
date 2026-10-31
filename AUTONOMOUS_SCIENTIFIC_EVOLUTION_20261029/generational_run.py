#!/usr/bin/env python3
"""Minimal multi-researcher -> autonomous SYN -> inherited science runner.

This is an operational bridge around existing ScientificEvolution source, not a
new scientific policy. No model, Work, or science asset is fabricated by it.
Run from the ScientificEvolution checkout with PYTHONPATH=<repo>/runtime.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace


def modules():
    try:
        from e2core.core import EvolutionJournal, EvidenceError, sha, canon
        from e2core.long_campaign import prepare_isolated_fresh, transfer_isolated_fresh
        import e2core.long_campaign as lc
        import scientific_problem_evolution as spe
        import scientific_closed_loop_v3 as v3
        import scientific_research_readiness_v4 as v4
    except ImportError as exc:
        raise RuntimeError('Set PYTHONPATH=$PWD/runtime in the ScientificEvolution repo: '+str(exc)) from exc
    return SimpleNamespace(J=EvolutionJournal,Error=EvidenceError,sha=sha,canon=canon,
        prepare=prepare_isolated_fresh,transfer=transfer_isolated_fresh,
        lc=lc,spe=spe,v3=v3,v4=v4)


NATIVE_PIN_NAME = 'NATIVE_RUNTIME_SOURCE_PIN.json'
NATIVE_SOURCE_PROTOCOL = 'M16_NATIVE_EXECUTION_SOURCE_V1'


def _native_inventory():
    """Hash actual local Python source at the verified development worktree.

    This is a new-run provenance pin. Historical V3 source pins are untouched.
    Do not infer source authority from Git HEAD alone: local uncommitted code
    can exist during the required test-before-commit development workflow.
    """
    repo = Path(__file__).resolve().parents[1]
    found = {}
    for subdir in ('runtime', 'AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029'):
        folder = repo / subdir
        if not folder.is_dir():
            raise RuntimeError('NATIVE_SOURCE_DIRECTORY_MISSING:' + subdir)
        for file in sorted(folder.rglob('*.py')):
            if file.is_symlink():
                raise RuntimeError('NATIVE_SOURCE_SYMLINK_REJECTED:' + str(file))
            key = file.relative_to(repo).as_posix()
            found[key] = hashlib.sha256(file.read_bytes()).hexdigest()
    if not found:
        raise RuntimeError('NATIVE_SOURCE_INVENTORY_EMPTY')
    return repo, found


def pin_native_source(experiment):
    """Create a single immutable source pin in a NEW autonomous experiment."""
    exp = Path(experiment).expanduser().resolve()
    if not (exp / 'persistent.json').is_file():
        raise RuntimeError('NATIVE_PIN_REQUIRES_INITIALIZED_PERSISTENT_EXPERIMENT')
    repo, files = _native_inventory()
    record = {'protocol': NATIVE_SOURCE_PROTOCOL, 'repository': str(repo),
              'files': files, 'source_verification': 'EXACT_PYTHON_BYTES_SHA256',
              'not_historical_v3_replay': True, 'not_scientific_certification': True}
    save_new(exp / NATIVE_PIN_NAME, record)
    return record


def verify_runtime_source(mods, research_root):
    """New-run pin when present; otherwise preserve exact historical V3 guard.

    No V3 hash is rewritten or silently accepted as the new native source.
    Research roots are nested below the autonomous experiment directory.
    """
    target = Path(research_root).expanduser().resolve()
    found = next((p / NATIVE_PIN_NAME for p in (target, *target.parents)
                  if (p / NATIVE_PIN_NAME).is_file()), None)
    if found is None:
        mods.v3.source_code_guard()
        return {'source_contract': 'HISTORICAL_V3_PINNED_SOURCE'}
    pinned = json.loads(found.read_text(encoding='utf8'))
    repo, observed = _native_inventory()
    if (pinned.get('protocol') != NATIVE_SOURCE_PROTOCOL
            or pinned.get('repository') != str(repo)
            or pinned.get('files') != observed):
        raise RuntimeError('NATIVE_EXECUTION_SOURCE_PIN_MISMATCH')
    # Import resolution is distinct from file hashing: reject overlay modules.
    for name in ('e2core.core', 'e2core.engine', 'e2core.provider',
                 'e2core.research_continuity', 'scientific_problem_evolution',
                 'scientific_closed_loop_v3', 'scientific_research_readiness_v4',
                 'generational_run', 'population_run', 'persistent_population',
                 'autonomous_population', 'population_resume'):
        loaded = sys.modules.get(name)
        if loaded is None:
            continue
        location = Path(loaded.__file__).resolve()
        if not location.is_relative_to(repo):
            raise RuntimeError('NATIVE_EXECUTION_MODULE_OVERLAY:' + name)
        if location.relative_to(repo).as_posix() not in observed:
            raise RuntimeError('NATIVE_EXECUTION_MODULE_NOT_PINNED:' + name)
    return {'source_contract': NATIVE_SOURCE_PROTOCOL,
            'pinned_python_file_count': len(observed),
            'pin_sha256': hashlib.sha256(found.read_bytes()).hexdigest()}


def save_new(path, obj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        f.write('\n')


def read_plan(experiment):
    p=Path(experiment).expanduser().resolve()/'experiment.json'
    data=json.loads(p.read_text(encoding='utf-8'))
    if data.get('protocol')!='SCIENTIFIC_E2E_GENERATIONAL_FIRST_RUN_V1':
        raise RuntimeError('UNSUPPORTED_EXPERIMENT_MANIFEST')
    if str(p.parent)!=data['experiment_root']:
        raise RuntimeError('EXPERIMENT_MOVED_REQUIRES_EXPLICIT_RECONCILIATION')
    return data


def source_digest(mods, root):
    j=mods.J(root)
    rows=j._events()
    return {'events':len(rows),'head_sha256':mods.sha(mods.canon(rows[-1])) if rows else None}


def operational_verify(mods,root):
    j=mods.J(root);s=j.verify()
    bad=[{'id':k,'state':v['state']} for k,v in s.model_calls.items()
         if v['state']!='SAVED']
    if bad: raise RuntimeError('UNRESOLVED_MODEL_CALLS_REQUIRE_MANUAL_REVIEW:'+str(bad[:5]))
    return j,s


def init(args):
    m=modules()
    dest=Path(args.out).expanduser().resolve()
    if dest.exists(): raise RuntimeError('EXPERIMENT_ROOT_ALREADY_EXISTS')
    if args.cohorts<2 or args.cohorts>12:
        raise RuntimeError('BOOTSTRAP_COHORT_COUNT_MUST_BE_2_TO_12; NOT A GENERATION QUOTA')
    if bool(args.source_root)==bool(args.problem_file):
        raise RuntimeError('CHOOSE_EXACTLY_ONE_OF_SOURCE_ROOT_OR_PROBLEM_FILE')
    if args.source_root:
        src=m.J(Path(args.source_root).expanduser());s=src.verify()
        p0=s.program['problem']
        source={'kind':'EXISTING_ROOT_P0_ONLY','source_root':str(src.root),**source_digest(m,src.root)}
    else:
        fp=Path(args.problem_file).expanduser().resolve()
        p0=fp.read_text(encoding='utf-8').strip()
        source={'kind':'OPERATOR_SUPPLIED_P0_TEXT','path':str(fp),
                'sha256':hashlib.sha256(fp.read_bytes()).hexdigest()}
    if not p0.strip() or len(p0)>12000:raise RuntimeError('P0_EMPTY_OR_TOO_LONG')
    if p0!=p0.strip():raise RuntimeError('P0_HAS_EDGE_WHITESPACE; ORIGINAL_TEXT_WOULD_BE_CHANGED_BY_FRESH_READER')
    dest.mkdir(parents=True)
    p0file=dest/'P0_EXACT.txt';p0file.write_text(p0+'\n',encoding='utf-8')
    cohorts=[]
    for idx in range(1,args.cohorts+1):
        root=dest/f'G0_FRESH_{idx:02d}'
        receipt=m.prepare(str(root),str(p0file))
        cohorts.append({'id':f'G0_FRESH_{idx:02d}','root':str(root),
            'origin':'INDEPENDENT_UNSEEDED_FRESH_COHORT','receipt':receipt['status']})
        j,s=operational_verify(m,root)
        if s.assets or s.work or s.sources or s.model_calls or s.controller_decisions:
            raise RuntimeError('FRESH_ROOT_NOT_EMPTY')
    base=dest/'SYN_BASE'
    j=m.J(base)
    j.init(p0,origin='SYN_COORDINATOR_EMPTY_NO_PRIOR_AI',
           criteria='Pre-experiment reviewable new scientific hypothesis or rigorously scoped conclusion; pause is not proof of impossibility.')
    j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
    j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
    if j.verify().assets or j.verify().work:raise RuntimeError('SYN_BASE_NOT_EMPTY')
    plan={'protocol':'SCIENTIFIC_E2E_GENERATIONAL_FIRST_RUN_V1',
          'experiment_root':str(dest),'source':source,
          'original_p0_sha256':hashlib.sha256(p0.encode('utf-8')).hexdigest(),
          'bootstrap_cohort_count_operator_chosen_not_ai':args.cohorts,
          'cohorts':cohorts,'syn_base':str(base),
          'scientific_selection':'AUTONOMOUS_CONTROLLER; NO FORCED_FUSE_OR_WORK',
          'not_a_science_certification':True,
          'fresh_prior_ai_sources':0}
    save_new(dest/'experiment.json',plan)
    print(json.dumps({'status':'READY_NO_PAID','experiment':str(dest),
                      'cohorts':[x['root'] for x in cohorts], 'syn_base':str(base),
                      'p0_sha256':plan['original_p0_sha256']},indent=2,ensure_ascii=False))


def assert_fresh_prompts(m,j,s):
    """Inspect saved provider requests, not just Work labels."""
    checked=0
    for wid,w in s.work.items():
        if w['mode']!='FRESH':continue
        if w['asset_input_ids'] or w.get('source_ids'):
            raise RuntimeError('FRESH_INHERITED_INPUT_IN_WORK:'+wid)
        for cid,call in s.model_calls.items():
            if call['actor']!='WORKER' or call.get('work_id')!=wid or call['state']!='SAVED':continue
            request=json.loads(j.raw(call['request_blob']))
            u=json.loads(request['messages'][1]['content'])
            pin=u.get('pinned_input',{})
            if pin.get('parent_assets') or pin.get('authorized_historical_records'):
                raise RuntimeError('FRESH_SERIALIZED_PARENT_OR_HISTORY_LEAK:'+cid)
            if any(v.get('kind')!='PRIMARY' for v in pin.get('source_entries',[])):
                raise RuntimeError('FRESH_SERIALIZED_SOURCE_LEAK:'+cid)
            if u.get('working_problem_state') or u.get('scientific_literature_feedback') or u.get('v4_claim_problem_scientific_handoff'):
                raise RuntimeError('FRESH_SERIALIZED_INFORMED_CONTEXT_LEAK:'+cid)
            checked+=1
    return checked


def _run_v4_synthesis_segments(mods,j,args,used):
    results=[];last_reason=None
    while used<args.max_new_calls:
        budget=min(args.slice_budget,args.max_new_calls-used)
        params=SimpleNamespace(call_budget=budget,checkpoint_iterations=args.checkpoint_iterations,
            max_parallel=args.max_parallel,max_tokens=args.max_tokens,
            model=args.model,science_cpu_seconds=args.science_cpu_seconds,
            science_wall_seconds=args.science_wall_seconds)
        result=mods.spe.run_feedback(str(j.root),params)
        used+=result['total_paid_new_calls']
        last_reason=result['stop_reason']
        snap=j.verify()
        checkpoint={'spent_this_segment':result['total_paid_new_calls'],
              'new_calls_cumulative':used,'stop_reason':last_reason,
              'decisions':len(snap.controller_decisions),'assets':len(snap.assets),
              'work_statuses':{k:v['status'] for k,v in snap.work.items()},
              'last_disposition':snap.program_reviews[-1]['scientific_status'] if snap.program_reviews else None}
        print(json.dumps({'checkpoint':checkpoint},ensure_ascii=False),flush=True)
        results.append(checkpoint)
        if any(v['state'] not in ('SAVED',) for v in snap.model_calls.values()):
            raise RuntimeError('NEW_UNCERTAIN_CALL_STOP_AND_REVIEW')
        if snap.program_reviews and snap.program_reviews[-1]['scientific_status'] in {
            'HOLD_WITH_RATIONALE','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}:break
        if last_reason!='CALL_BUDGET' or result['total_paid_new_calls']==0:break
    return used,last_reason,results


def cohort_context_bridge(mods):
    """Expose actual cohort dispositions to SYN; not a new Controller policy."""
    original=mods.v3._external_context
    def bridged(j,*a,**kw):
        ctx=original(j,*a,**kw)
        state=j.verify()
        cohort=[]
        for sid,src in state.sources.items():
            if not sid.startswith('SRC_COHORT_RECEIPT_') or src['kind']!='HISTORICAL_AI':
                continue
            receipt=json.loads(j.raw(src['blob']))
            cohort.append({'cohort_id':receipt['cohort'],
                 'original_scientific_status':receipt.get('scientific_status'),
                 'work_dispositions':receipt.get('work_dispositions',{}),
                 'imported_asset_ids':[row['new_asset_id'] for row in receipt.get('imported_ids',[])],
                 'original_event_sha256':receipt.get('source_head',{}).get('head_sha256'),
                 'original_root':receipt.get('source'),
                 'assessment_caveat':'Inherited AI and actual executions; NOT new primary evidence or verified novelty'})
        ctx['independent_cohort_history']=cohort
        ctx['cohort_selection_instruction']='Compare all prior cohort hypotheses, scoped negatives, and scientific HOLD reasons against P0. Do not infer failure of P0 from a cohort HOLD. FRESH cohort reports are inherited AI records, not independently certified science. You may select no new Work or new Work according to scientific value.'
        return ctx
    return original,bridged


def drive(mods,root,args,phase):
    # New clean Journal roots cannot call v3.run(): v3.run() assumes its historical
    # NVT recovery receipt. Instead use the SAME V4 + V3 runtime hooks on the
    # existing feedback research engine directly.
    verify_runtime_source(mods, root)
    if not args.paid or os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        raise RuntimeError('PAID_CALLS_REQUIRE_--paid_AND_FAKG_RESEARCH_ALLOW_PAID=YES')
    if args.max_new_calls<1 or args.slice_budget<1:raise RuntimeError('BAD_BUDGET')
    j,s=operational_verify(mods,root)
    previous_count=len(s.controller_decisions)
    if s.program_reviews and s.program_reviews[-1]['scientific_status'] in {
        'HOLD_WITH_RATIONALE','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}:
        return {'status':'ALREADY_SCIENTIFIC_TERMINAL_NO_NEW_CALLS',
                'root':str(j.root),'new_calls':0}
    used=0;results=[];last_reason=None
    if phase=='fresh':
        # A genuinely unseeded research cohort starts with the stock E2
        # Controller/Worker runtime. No unnecessary pre-research novelty
        # arbitration, no pre-assigned physical mechanism, no source leakage.
        result=mods.lc.drive(str(j.root),budget=args.max_new_calls,
            chunk=args.checkpoint_iterations,max_tokens=args.max_tokens,
            model=args.model,cpu=args.science_cpu_seconds,
            wall=args.science_wall_seconds,paid=True,parallel=args.max_parallel)
        used=result['total_paid_new_calls']
        last_reason=result['stop_reason']
    elif phase=='syn':
        # The same V4/V3 science feedback hooks, applied to a new clean SYN
        # root. Avoid v3.run(), whose historical recovery receipt is specific
        # to the legacy V4 Journal and cannot exist in this new program.
        with mods.v4.runtime(), mods.v3.v3_runtime():
            previous_external,bridged=cohort_context_bridge(mods)
            mods.v3._external_context=bridged
            try:
                used,last_reason,results=_run_v4_synthesis_segments(mods,j,args,used)
            finally:
                mods.v3._external_context=previous_external

    else:
        raise RuntimeError('UNKNOWN_RESEARCH_PHASE')
    j,s=operational_verify(mods,root)
    return {'status':'RESEARCH_SEGMENT_RECORDED','root':str(j.root),
        'new_calls_this_launch':used,'new_controller_decisions':len(s.controller_decisions)-previous_count,
        'stop_reason':last_reason,'work_statuses':{k:v['status'] for k,v in s.work.items()},
        'last_scientific_disposition':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
        'fresh_serialized_requests_checked':assert_fresh_prompts(mods,j,s),
        'head':source_digest(mods,root),'science_certification':False}


def run_cohort(args):
    m=modules();plan=read_plan(args.experiment)
    n=args.index
    if not 1<=n<=len(plan['cohorts']):raise RuntimeError('UNKNOWN_COHORT_INDEX')
    root=plan['cohorts'][n-1]['root']
    result=drive(m,root,args,'fresh')
    print(json.dumps(result,indent=2,ensure_ascii=False))


def merge(args):
    m=modules();plan=read_plan(args.experiment)
    if Path(plan['experiment_root'],'SYN_INTEGRATED').exists():
        raise RuntimeError('SYN_ALREADY_INTEGRATED; NEVER_OVERWRITE')
    current=Path(plan['syn_base']);receipts=[]
    for ix,c in enumerate(plan['cohorts'],1):
        donor=Path(c['root']);j,s=operational_verify(m,donor)
        checked=assert_fresh_prompts(m,j,s)
        if not s.controller_decisions or not any(w['mode']=='FRESH' for w in s.work.values()):
            raise RuntimeError(f'COHORT_{ix}_HAS_NOT_EXECUTED_FRESH_RESEARCH')
        if not any(call['actor']=='WORKER' and call['state']=='SAVED' and call.get('billing_mode')=='EXTERNAL'
                   for call in s.model_calls.values()):
            raise RuntimeError(f'COHORT_{ix}_NO_REAL_FRESH_MODEL_OUTPUT')
        orig_p0=j.verify().program['problem'];sj=m.J(current)
        if sj.verify().program['problem']!=orig_p0:raise RuntimeError('P0_MISMATCH')
        dest=Path(plan['experiment_root'])/('SYN_INTEGRATED' if ix==len(plan['cohorts'])
                                            else f'SYN_MERGE_{ix:02d}')
        receipt=m.transfer(str(current),str(donor),str(dest))
        receipts.append({'cohort':c['id'],'source':str(donor),
               'source_head':source_digest(m,donor),'fresh_serialized_requests_checked':checked,
               'work_dispositions':{k:{'status':w['status'],'outcome':w.get('outcome')} for k,w in s.work.items()},
               'scientific_status':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
               'all_asset_ids':list(s.assets),
               'imported_ids':receipt['imported'],
               'operator_transfer_not_scientific_discovery':True})
        current=dest
        print(json.dumps({'integrated_cohort':c['id'],
                           'imported_assets':len(receipt['imported']),
                           'destination':str(dest)},ensure_ascii=False),flush=True)
    syn=m.J(current)
    # Every imported scientific asset is in the NVT target scope. In the
    # existing scientific_problem_evolution.target_claims(), a historical
    # imported asset is otherwise OMITTED unless selected_assets is supplied.
    # This selects *all* imported assets, not a human-curated favorite.
    all_imported=list(syn.verify().assets)
    save_new(Path(current)/'FEEDBACK_PREPARE_MANIFEST.json',{
        'selected_assets':all_imported,
        'origin':'AUTOMATIC_ALL_IMPORTED_FRESH_ASSETS_NO_HUMAN_SCIENCE_SELECTION',
        'scientific_certification':False})
    syn.append('OPERATIONAL_PAUSE',{
        'reason':'E2E_ALL_IMPORTED_ASSETS_IN_SCIENTIFIC_FEEDBACK_SCOPE',
        'selected_asset_ids_hash':m.sha(m.canon(all_imported)),
        'selection_count':len(all_imported),
        'not_a_model_scientific_decision':True})
    # The transfer bridge retains all original donor Journals. Also expose
    # source text from REAL tool returns to the existing V3 evidence reader,
    # using its established INHERITED_EXECUTED_TOOL_RESULT classification.
    # Metadata and failed retrievals stay in donor Journals and are NOT
    # upgraded to inspected primary literature in this transfer.
    from collections import Counter
    classes={ 'DIRECT_FULLTEXT_EXCERPT','DIRECT_FIGURE_OR_METHOD_EXCERPT',
        'OA_FULLTEXT_TEXT','OA_FULLTEXT_CAPTION','OA_PDF_TEXT',
        'OA_SUPPLEMENT_TEXT','DIRECT_SUPPLEMENT_EXCERPT' }
    source_transfer=[]
    for c in plan['cohorts']:
        donor=m.J(c['root']);state=donor.verify()
        n=0;class_counts=Counter()
        for sid,record in state.sources.items():
            if record.get('kind')!='TOOL_RESULT':continue
            raw=donor.raw(record['blob'])
            try:data=json.loads(raw)
            except (TypeError,ValueError):continue
            if not isinstance(data,dict):continue
            result=data.get('result')
            if not isinstance(result,dict):continue
            cls=data.get('evidence_class') or result.get('evidence_class') or 'UNKNOWN'
            class_counts[cls]+=1
            if cls not in classes:continue
            tid=data.get('tool_id');tr=state.tool_results.get(tid)
            if not tr or tr.get('work_id')!=record.get('work_id') or \
                result!=json.loads(donor.raw(tr['result_blob'])):
                raise RuntimeError('INHERITED_PRIMARY_EXCERPT_NOT_EXECUTION_GROUNDED:'+str(sid))
            ident='SRC_INHERITED_TOOL_'+m.sha(m.canon({'root':str(donor.root),'sid':sid}))[:22]
            if ident in syn.verify().sources:raise RuntimeError('DUPLICATE_INHERITED_EVIDENCE')
            syn.add_source(ident,'EXTERNAL_AUDIT',{
                'kind':'INHERITED_REAL_EXECUTION_TOOL_RESULT_NOT_NEW_OBSERVATION',
                'original_root':str(donor.root),'original_tool_source_id':sid,
                'original_tool_id':tid,'original_record_sha256':m.sha(raw),
                'evidence_class':cls,'original_returned_data':data,
                'not_independently_certified':True},
                'Inherited actually executed '+cls+' source, not new inspection: '+sid)
            n+=1
        source_transfer.append({'cohort':c['id'],'direct_tool_sources_exposed':n,
             'all_tool_source_classes_in_donor':dict(class_counts),
             'metadata_and_non_direct_remain_in_donor':True})
    # Records carry VERIFIED original hashes and scientific HOLDs even for
    # donors with no assets, without treating operational transfer as discovery.
    for r in receipts:
        sid='SRC_COHORT_RECEIPT_'+r['cohort']
        syn.add_source(sid,'HISTORICAL_AI',r,
            'Operator-executed transfer of independent cohort outcome; not primary science')
    state=syn.verify()
    if len(state.controller_decisions)!=0 or len(state.work)!=0:
        raise RuntimeError('SYN_WORK_OR_CONTROLLER_RUN_BEFORE_INTEGRATION')
    report={'protocol':'SYN_INTEGRATION_RECEIPT_V1','syn_root':str(current),
         'cohort_receipts':receipts,'program_sha256':hashlib.sha256(state.program['problem'].encode()).hexdigest(),
         'imported_assets':len(state.assets),'no_ai_scientific_decision_during_transfer':True,
         'current_head':source_digest(m,current), 'source_transfer':source_transfer}
    save_new(Path(plan['experiment_root'])/'integration.json',report)
    print(json.dumps({'status':'INTEGRATED_READY_FOR_AUTONOMOUS_SYN_NO_PAID',
        'syn_root':str(current),'imported_assets':len(state.assets),
        'cohorts':len(receipts),'inherited_direct_tool_sources':sum(x['direct_tool_sources_exposed'] for x in source_transfer),'not_a_science_certification':True},indent=2,ensure_ascii=False))


def run_syn(args):
    m=modules();plan=read_plan(args.experiment)
    ir=Path(plan['experiment_root'])/'integration.json'
    if not ir.is_file():raise RuntimeError('INTEGRATE_COHORTS_BEFORE_SYN')
    syn=Path(json.loads(ir.read_text(encoding='utf-8'))['syn_root'])
    result=drive(m,syn,args,'syn')
    print(json.dumps(result,indent=2,ensure_ascii=False))


def audit_root(m,root):
    j=m.J(root);s=j.verify();events=j._events()
    hist={a for a,x in s.assets.items() if x.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
    live=[a for a,x in s.assets.items() if a not in hist]
    decisions=[]
    for e in events:
        if e['kind']!='CONTROLLER_DECISION':continue
        p=e['payload'];obj=json.loads(j.raw(p['parsed_blob']))
        decisions.append({'seq':e['seq'],'id':p['id'],'disposition':obj.get('disposition'),
             'actions':[{'operation':a.get('operation'),'asset_ids':a.get('asset_ids'),
                        'work_id':(a.get('work') or {}).get('id'),
                        'question':(a.get('work') or {}).get('question')} for a in obj.get('actions',[])]})
    assets=[]
    for aid in live:
        a=s.assets[aid];pa=a.get('parent_ids',[])
        assets.append({'id':aid,'kind':a['kind'],'work_id':a['work_id'],'parent_ids':pa,
              'parent_from_import':[p for p in pa if p in hist],
              'claim':a.get('claim'),'delta_from_parents':a.get('delta_from_parents'),
              'predictions':a.get('predictions',[]),'source_ids':a.get('source_ids',[])})
    followup_decisions=[d for d in decisions[1:] if any(ae['kind']=='ASSET_PUBLISHED' and
         decisions[0]['seq']<ae['seq']<d['seq'] for ae in events)] if decisions else []
    bad=[{'id':k,'state':c['state']} for k,c in s.model_calls.items() if c['state']!='SAVED']
    return {'root':str(j.root),'source_sha256':source_digest(m,root),
           'total_assets':len(s.assets),'imported_historical_assets':len(hist),
           'live_science_assets':assets,'controller_decisions':decisions,
           'post_live_science_controller_decisions':followup_decisions,
           'works':{k:{'mode':w.get('mode'),'operation':w.get('operation'),
                   'parents':w.get('asset_input_ids',[]),'status':w['status'],
                   'published':w.get('published',[])} for k,w in s.work.items()},
           'real_tool_result_count':len(s.tool_results),'unresolved_model_calls':bad,
           'last_scientific_disposition':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None}


def audit(args):
    m=modules();plan=read_plan(args.experiment)
    cohorts=[]
    for c in plan['cohorts']:
        data=audit_root(m,c['root'])
        j=m.J(c['root']);s=j.verify()
        data['fresh_serialized_requests_checked']=assert_fresh_prompts(m,j,s)
        cohorts.append(data)
    integ=Path(plan['experiment_root'])/'integration.json'
    syn=audit_root(m,json.loads(integ.read_text(encoding='utf-8'))['syn_root']) if integ.exists() else None
    evidence={'protocol':'SCIENTIFIC_E2E_GENERATION_AUDIT_V1',
        'original_p0_sha256':plan['original_p0_sha256'],
        'operator_chosen_initial_cohorts':plan['bootstrap_cohort_count_operator_chosen_not_ai'],
        'G0_independent_research':cohorts,'SYN_and_descendants':syn,
        'science_certified':False,
        'interpretation':'Observed lineage events, not automatic scientific novelty/quality certification.'}
    if syn:
        descendants=[a for a in syn['live_science_assets'] if a['parent_ids']]
        evidence['structural_signals']={
          'initial_syn_decision_occurred':len(syn['controller_decisions'])>0,
          'informed_worker_ever_created':any(w['mode']=='INFORMED' for w in syn['works'].values()),
          'informed_worker_executed_science':any(a['work_id'] in syn['works'] and
                    syn['works'][a['work_id']]['mode']=='INFORMED' for a in syn['live_science_assets']),
          'inherited_science_descendants':len(descendants),
          'post_descendant_controller_decision_count':len(syn['post_live_science_controller_decisions']),
          'no_level_ii_claim_from_structural_signals':True}
    dest=Path(args.out).expanduser().resolve()
    save_new(dest,evidence)
    print(json.dumps({'status':'READ_ONLY_AUDIT_SAVED','path':str(dest),
          'structural_signals':evidence.get('structural_signals'),
          'scientific_review_remains_manual':True},ensure_ascii=False,indent=2))


def preflight(args):
    m=modules();m.v3.source_code_guard()
    plan=read_plan(args.experiment)
    for c in plan['cohorts']:
        j,s=operational_verify(m,c['root'])
        if s.program['problem']!=Path(plan['experiment_root'],'P0_EXACT.txt').read_text(encoding='utf-8').strip():
            raise RuntimeError('ORIGINAL_P0_MISMATCH')
        assert_fresh_prompts(m,j,s)
    j,s=operational_verify(m,plan['syn_base'])
    integ=Path(plan['experiment_root'])/'integration.json'
    if integ.exists():
        syn=m.J(json.loads(integ.read_text(encoding='utf-8'))['syn_root'])
        syn.verify()
    print(json.dumps({'status':'PREFLIGHT_OK_NO_PAID',
          'cohorts':len(plan['cohorts']),
          'source_code_guard':'PASSED',
          'p0_unchanged':True,'fresh_serialized_inputs_checked':True,
          'integrated_syn_exists':integ.exists()},ensure_ascii=False,indent=2))


def common_run(p):
    p.add_argument('--experiment',required=True)
    p.add_argument('--paid',action='store_true')
    p.add_argument('--model',default='openai/gpt-5.6-luna')
    p.add_argument('--max-new-calls',type=int,default=24)
    p.add_argument('--slice-budget',type=int,default=12)
    p.add_argument('--checkpoint-iterations',type=int,default=12)
    p.add_argument('--max-parallel',type=int,default=2)
    p.add_argument('--max-tokens',type=int,default=16000)
    p.add_argument('--science-cpu-seconds',type=int,default=120)
    p.add_argument('--science-wall-seconds',type=int,default=160)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('init');x.add_argument('--source-root');x.add_argument('--problem-file')
    x.add_argument('--out',required=True);x.add_argument('--cohorts',type=int,default=3)
    x=sub.add_parser('preflight');x.add_argument('--experiment',required=True)
    x=sub.add_parser('run-fresh');common_run(x);x.add_argument('--index',type=int,required=True)
    x=sub.add_parser('integrate');x.add_argument('--experiment',required=True)
    x=sub.add_parser('run-syn');common_run(x)
    x=sub.add_parser('audit');x.add_argument('--experiment',required=True);x.add_argument('--out',required=True)
    args=p.parse_args()
    try:
        {'init':init,'preflight':preflight,'run-fresh':run_cohort,
         'integrate':merge,'run-syn':run_syn,'audit':audit}[args.command](args)
    except Exception as exc:
        print(json.dumps({'status':'STOPPED_NOT_A_SCIENTIFIC_HOLD',
                           'error_type':type(exc).__name__,'detail':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 3
    return 0

if __name__=='__main__':raise SystemExit(main())
