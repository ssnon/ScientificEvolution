#!/usr/bin/env python3
"""Population-level Scientific Evolution orchestration over actual E2 Journals.

Peer SYNs: identical, immutable G0 integration checkpoint -> independent models.
Population: claims, raw independent model decisions, and executed evidence -> new
  autonomous controller, no hard-coded winner, no mandatory work/merge.
Next review: fork after actual G1 science, preserve the exact ancestry and run a
  new Controller review. Append-only journal histories are never re-authored.

External model calls require both --paid and FAKG_RESEARCH_ALLOW_PAID=YES.
"""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, shutil, sys, tempfile
from pathlib import Path

import generational_run as gen
from e2core.evidence_continuity import uninterpreted_last_tool_feedback

PROTO='SCIENTIFIC_POPULATION_GENERATIONAL_V1'
DIRECT_CLASSES={
 'DIRECT_FULLTEXT_EXCERPT','DIRECT_FIGURE_OR_METHOD_EXCERPT','OA_FULLTEXT_TEXT',
 'OA_FULLTEXT_CAPTION','OA_PDF_TEXT','OA_SUPPLEMENT_TEXT','DIRECT_SUPPLEMENT_EXCERPT',
}
BLOB_KEYS={'raw_blob','blob','input_blob','request_blob','response_blob','result_blob','parsed_blob'}


def fail(message):raise RuntimeError(message)

def dump(path,obj,overwrite=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if overwrite:
        tmp=path.with_name(path.name+'.tmp')
        if tmp.exists():fail('TEMP_FILE_ALREADY_EXISTS:'+str(tmp))
        with tmp.open('x',encoding='utf8') as f:
            json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
        os.replace(tmp,path)
    else:gen.save_new(path,obj)


def load(path):return json.loads(Path(path).read_text(encoding='utf8'))

def sha_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def hname(mods,tag,payload,n=20):return tag+mods.sha(mods.canon(payload))[:n]

def root_status(mods,root,allow_uncertain=False):
    j=mods.J(root);s=j.verify()
    un=[(cid,v['state']) for cid,v in s.model_calls.items() if v['state']!='SAVED']
    if un and not allow_uncertain:fail('UNRESOLVED_MODEL_CALL:'+repr(un[:5]))
    return j,s


def p0hash(state):return hashlib.sha256(state.program['problem'].encode('utf8')).hexdigest()


def clone_at_checkpoint(mods,src,dst,event_count,expected_head=None):
    """Create a distinct root with only fully verified committed prefix events.

    Never modifies original. Retains only blobs referenced in the prefix events,
    avoiding leakage of later research data into a checkpoint fork.
    """
    src=Path(src).expanduser().resolve();dst=Path(dst).expanduser().resolve()
    if dst.exists() or dst.is_relative_to(src) or not dst.parent.is_dir():fail('DEST_EXISTS_OR_UNSAFE')
    sj,ss=root_status(mods,src)
    records=sj._events()
    original_full_head=mods.sha(mods.canon(records[-1]))
    if not isinstance(event_count,int) or event_count<2 or event_count>len(records):fail('BAD_CHECKPOINT_EVENT_COUNT')
    selected=records[:event_count]
    digest=mods.sha(mods.canon(selected[-1]))
    if expected_head is not None and digest!=expected_head:fail('SOURCE_CHECKPOINT_HASH_MISMATCH')
    refs={v for e in selected for k,v in e['payload'].items()
          if k in BLOB_KEYS and isinstance(v,str)}
    stage=dst.with_name(dst.name+'.STAGING')
    if stage.exists():fail('STAGING_ALREADY_EXISTS:'+str(stage))
    stage.mkdir(parents=True)
    try:
        (stage/'events').mkdir();(stage/'blobs').mkdir()
        shutil.copy2(src/'manifest.json',stage/'manifest.json')
        for e in selected:
            name=f"{e['seq']:08d}.json"
            shutil.copy2(src/'events'/name,stage/'events'/name)
        for dig in refs:
            if not (src/'blobs'/dig).is_file():fail('MISSING_PREFIX_BLOB:'+dig)
            shutil.copy2(src/'blobs'/dig,stage/'blobs'/dig)
        # These are operation instructions, not Journal events. Verify their
        # asset IDs against the immutable checkpoint before retention.
        manifest=src/'FEEDBACK_PREPARE_MANIFEST.json'
        if manifest.is_file():shutil.copy2(manifest,stage/manifest.name)
        j,s=root_status(mods,stage)
        if p0hash(s)!=p0hash(ss):fail('CLONE_P0_CHANGED')
        if len(j._events())!=event_count:fail('CLONE_BAD_EVENT_COUNT')
        current=sj._events()
        if len(current)!=len(records) or mods.sha(mods.canon(current[-1]))!=original_full_head:
            fail('SOURCE_CHANGED_DURING_FORK')
        stage.rename(dst)
    except BaseException:
        shutil.rmtree(stage,ignore_errors=True)
        raise
    return {'root':str(dst),'events':event_count,'head_sha256':digest,'referenced_blobs':len(refs)}


def plan_at(exp):
    exp=Path(exp).expanduser().resolve();d=load(exp/'population.json')
    if d.get('protocol')!=PROTO or d.get('root')!=str(exp):fail('BAD_POPULATION_MANIFEST_OR_MOVED')
    return d


def precontroller_source(exp):
    exp=Path(exp).expanduser().resolve()
    original=load(exp/'integration.json')
    source=Path(original['syn_root']).expanduser().resolve()
    expected=original['current_head']
    return source,expected


def init(args):
    mods=gen.modules();origin=Path(args.g0_experiment).expanduser().resolve()
    integ=load(origin/'integration.json')
    source=Path(integ['syn_root']).resolve();j,s=root_status(mods,source)
    if not s.controller_decisions:fail('G0_SYN_CONTROLLER_NEVER_RAN')
    head=integ['current_head'];count=head['events'];expect=head['head_sha256']
    if mods.sha(mods.canon(j._events()[count-1]))!=expect:fail('INTEGRATION_CHECKPOINT_DOES_NOT_MATCH_ORIGINAL')
    if any(e['kind']=='MODEL_CALL_INTENT' for e in j._events()[:count]):fail('PRECONTROLLER_CHECKPOINT_CONTAINS_PAID_CALL')
    if not (s0:=clone_check_state(mods,source,count,expect))['all_g0_historical']:
        fail('NO_G0_HISTORICAL_ASSETS_AT_INTEGRATION_CHECKPOINT')
    target=Path(args.out).expanduser().resolve()
    if target.exists():fail('DEST_EXPERIMENT_EXISTS')
    target.mkdir(parents=True)
    try:
        peers=[]
        for label in ('SYN_A','SYN_B'):
            p=clone_at_checkpoint(mods,source,target/label,count,expect)
            peers.append({'name':label,**p})
        pop=clone_at_checkpoint(mods,source,target/'POP_BASE',count,expect)
        base_state=mods.J(target/'POP_BASE').verify()
        feedback=load(target/'POP_BASE'/'FEEDBACK_PREPARE_MANIFEST.json')
        if set(feedback.get('selected_assets',[]))!=set(base_state.assets):
            fail('G0_FULL_ASSET_FEEDBACK_SCOPE_NOT_PRESERVED')
        assert len(base_state.controller_decisions)==0 and not base_state.model_calls and not base_state.work
        assert all(mods.J(p['root']).verify().assets.keys()==base_state.assets.keys() for p in peers)
        manifest={'protocol':PROTO,'root':str(target),
            'g0_experiment':str(origin),'g0_integration':str(origin/'integration.json'),
            'g0_integration_sha256':sha_file(origin/'integration.json'),
            'g0_original_root':str(source),'g0_checkpoint':head,
            'P0_sha256':p0hash(base_state),'historical_G0_assets':len(base_state.assets),
            'peer_roots':{p['name']:p['root'] for p in peers},'pop_base':pop['root'],
            'population_root':str(target/'POP_G1'), 'g2_root':str(target/'G2_SYN'),
            'choice_origin':'AUTONOMOUS_AI_PEER_SYN_THEN_AUTONOMOUS_POPULATION_CONTROLLER',
            'operator_chosen_peer_count':2,'no_forced_work_or_fuse':True,
            'scientific_certification':False}
        dump(target/'population.json',manifest)
        print(json.dumps({'status':'INDEPENDENT_SYN_BRANCHES_READY_NO_PAID',
              'checkpoint':head,'G0_assets':len(base_state.assets),'peers':peers},indent=2))
    except BaseException:
        # Created only in this function and not paid; originals untouched.
        shutil.rmtree(target,ignore_errors=True)
        raise


def clone_check_state(mods,source,count,head):
    j=mods.J(source);rows=j._events()[:count]
    # Avoid materializing a transient ROOT: audit the prefix-event types and
    # the original complete Journal's imported IDs.
    return {'head_matches':mods.sha(mods.canon(rows[-1]))==head,
      'all_g0_historical':any(x['kind']=='HISTORICAL_ASSET_INDEXED' for x in rows),
      'no_model_intent':not any(x['kind']=='MODEL_CALL_INTENT' for x in rows)}


def preflight(args):
    mods=gen.modules();plan=plan_at(args.experiment);base,bs=root_status(mods,plan['pop_base'])
    if bs.model_calls or bs.work or bs.controller_decisions:fail('POP_BASE_NOT_A_PRECONTROLLER_ROOT')
    if p0hash(bs)!=plan['P0_sha256']:fail('P0_CHANGED')
    for name,root in plan['peer_roots'].items():
        j,s=root_status(mods,root)
        if p0hash(s)!=plan['P0_sha256']:fail('PEER_P0_CHANGED:'+name)
        if set(bs.assets)-set(s.assets):fail('G0_ASSET_MISSING:'+name)
        gen.assert_fresh_prompts(mods,j,s)
    for k in ['population_root','g2_root']:
        if Path(plan[k]).exists():
            j,s=root_status(mods,plan[k]);gen.assert_fresh_prompts(mods,j,s)
            if p0hash(s)!=plan['P0_sha256']:fail('DESCENDANT_P0_CHANGED:'+k)
    print(json.dumps({'status':'PREFLIGHT_OK_NO_PAID','historical_G0':len(bs.assets),
          'peer_roots':plan['peer_roots'],'population_exists':Path(plan['population_root']).exists(),
          'G2_exists':Path(plan['g2_root']).exists(),'P0_unchanged':True,'science_certified':False},indent=2))


def run_peer(args):
    plan=plan_at(args.experiment);label=args.peer
    if label not in plan['peer_roots']:fail('UNKNOWN_PEER')
    mods=gen.modules();root=plan['peer_roots'][label];j,s=root_status(mods,root)
    if p0hash(s)!=plan['P0_sha256']:fail('PEER_P0_MISMATCH')
    out=gen.drive(mods,root,args,'syn')
    print(json.dumps({'peer':label,**out},ensure_ascii=False,indent=2))


def _decision_artifact(j,s):
    from e2core.provider import content_from_wire,strict_envelope
    decisions=[]
    for d in s.controller_decisions:
        obj=load_blob_json(j,d['parsed_blob'])
        call=s.model_calls.get(d['call_id'],{})
        context={}
        if call.get('state')=='SAVED':
            try:
                request=load_blob_json(j,call['request_blob'])
                context=json.loads(request['messages'][1]['content'])
            except (ValueError,TypeError,IndexError,KeyError):
                context={'prompt_parse_error':'PRESERVED_RAW_REQUEST_IS_AUTHORITATIVE'}
        decisions.append({'id':d['id'],'decision_blob':d['parsed_blob'],
           'rationale':obj.get('rationale'),'disposition':obj.get('disposition'),
           'asset_reviews':obj.get('reviews',[]),
           'prior_art_delta':context.get('prior_art_delta'),
           'problem_impact_delta':context.get('problem_impact_delta'),
           'problem_level_impact':(context.get('problem_level_impact') or {}).get('problem_impact'),
           'actions':[{'operation':a.get('operation'),'parent_asset_ids':a.get('asset_ids',[]),
              'work_id':(a.get('work') or {}).get('id'),
              'question':(a.get('work') or {}).get('question'),
              'reason':a.get('reason')} for a in obj.get('actions',[])],
           'objective_assessment':obj.get('objective_assessment')})
    opp=[]
    for cid,c in s.model_calls.items():
        if not cid.startswith('OPP_') or c['state']!='SAVED':continue
        raw=content_from_wire(j.raw(c['response_blob']))
        parsed=strict_envelope(raw)
        opp.append({'call_id':cid,'response_sha256':c['response_blob'],
             'parsed':parsed if isinstance(parsed,dict) else {'unparsed_sha':hashlib.sha256(raw.encode()).hexdigest()}})
    return decisions,opp


def load_blob_json(j,dig):return json.loads(j.raw(dig))


def record_direct_tool_sources(mods,pop,donor,ds,peer_name):
    total=0;seen=[]
    pending={x['tool_id'] for x in uninterpreted_last_tool_feedback(donor,ds)}
    for sid,record in ds.sources.items():
        if record['kind']!='TOOL_RESULT':continue
        raw=donor.raw(record['blob']);data=json.loads(raw)
        res=data.get('result') if isinstance(data,dict) else None
        if not isinstance(res,dict):continue
        cls=data.get('evidence_class') or res.get('evidence_class')
        if cls not in DIRECT_CLASSES:continue
        tid=data.get('tool_id');original=ds.tool_results.get(tid)
        if not original or original['work_id']!=record.get('work_id') or \
           data.get('request')!=load_blob_json(donor,original['request_blob']) or \
           res!=load_blob_json(donor,original['result_blob']):
            fail('UNVERIFIED_DIRECT_TOOL_EXECUTION:'+sid)
        ident=hname(mods,'SRC_INHERITED_TOOL_',{'peer':peer_name,'root':str(donor.root),'sid':sid},22)
        pop.add_source(ident,'EXTERNAL_AUDIT',{
            'kind':'INHERITED_REAL_EXECUTION_TOOL_RESULT_NOT_NEW_OBSERVATION',
            'origin_peer':peer_name,'original_root':str(donor.root),'original_tool_source_id':sid,
            'original_tool_id':tid,'original_record_sha256':mods.sha(raw),
            'original_work_id':original['work_id'],
            'original_request_blob_sha256':original['request_blob'],
            'original_result_blob_sha256':original['result_blob'],
            'pending_worker_interpretation':tid in pending,
            'evidence_class':cls,'original_returned_data':data,'not_independently_certified':True},
            'Peer original tool return '+cls+'; not new independent inspection: '+sid)
        total+=1;seen.append(ident)
    return {'registered_direct_sources':total,'ids':seen}



def record_science_tool_results(mods, dest, donor, ds, peer_name):
    """Carry every real Python/verified-calculation attempt, with exact tool blobs.

    Saves executed computation and failed calculation as DIFFERENT evidence classes.
    No tool is run, no calculation is validated, no asset is published here.
    """
    count=0;ids=[]
    pending={x['tool_id'] for x in uninterpreted_last_tool_feedback(donor,ds)}
    for tid,record in ds.tool_results.items():
        req=load_blob_json(donor,record['request_blob'])
        result=load_blob_json(donor,record['result_blob'])
        if not isinstance(req,dict) or req.get('kind') not in {'python_science','verified_calculation'}:
            continue
        if not isinstance(result,dict) or record.get('work_id') not in ds.work:
            fail('SCIENCE_TOOL_PROVENANCE_MALFORMED:'+tid)
        actual=record['result_blob'];request=record['request_blob']
        kind=req['kind'];status=result.get('status')
        evidence_class=('EXECUTED_COMPUTATION_NOT_SCIENTIFICALLY_VALIDATED'
                        if status in {'EXECUTED','DELIVERED'}
                        else 'FAILED_CALCULATION_ATTEMPT_NOT_SCIENTIFIC_NEGATIVE')
        content={'tool_id':tid,'work_id':record['work_id'],
                 'request':req,'result':result,'evidence_class':evidence_class}
        sid=hname(mods,'SRC_INHERITED_TOOL_',
            {'peer':peer_name,'root':str(donor.root),'tool':tid},22)
        dest.add_source(sid,'EXTERNAL_AUDIT',{
            'kind':'INHERITED_SCIENCE_TOOL_EXECUTION_NOT_NEW_OBSERVATION',
            'origin_peer':peer_name,'original_root':str(donor.root),
            'original_tool_id':tid,'original_work_id':record['work_id'],
            'original_request_blob_sha256':request,
            'original_result_blob_sha256':actual,
            'original_record_sha256':mods.sha(mods.canon(content)),
            'evidence_class':evidence_class,
            'pending_worker_interpretation':tid in pending,
            'original_returned_data':content,
            'not_independently_certified':True,'is_a_new_tool_execution':False},
            'Exact prior '+kind+' '+str(status)+'; not new execution or certified science: '+tid)
        count+=1;ids.append(sid)
    return {'registered_science_tools':count,'ids':ids}


def import_peer(mods,pop,base_state,peer,root):
    donor,ds=root_status(mods,root)
    if p0hash(ds)!=p0hash(base_state):fail('PEER_P0_MISMATCH')
    if set(base_state.assets)-set(ds.assets):fail('MISSING_G0_IMPORTS_IN_PEER')
    if not ds.controller_decisions:fail('PEER_HAS_NO_COMMITTED_SYN_DECISION:'+peer)
    if not any(c['actor']=='CONTROLLER' and c['state']=='SAVED' for c in ds.model_calls.values()):
        fail('PEER_DECISION_NOT_GROUNDED_IN_PAID_CALLS')
    # For exact parent translation, all original G0 assets have identical ids.
    start_head=mods.sha(mods.canon(donor._events()[-1]))
    assets_new=[a for a in ds.assets if a not in base_state.assets]
    problems_new=[p for p in ds.problems if p not in base_state.problems]
    problem_map={p:p for p in base_state.problems}
    for pid in problems_new:
        prob=ds.problems[pid]
        mapped=hname(mods,'P_PEER_',{'peer':peer,'orig':pid},20)
        parents=[problem_map[x] for x in prob['parents']]
        p={k:v for k,v in prob.items() if k not in {'id','status','parents'}}
        p.update({'id':mapped,'parents':parents,
             'original_problem_id':pid,'peer_syn':peer})
        pop.append('PROBLEM_CREATED',p)
        problem_map[pid]=mapped
    asset_map={a:a for a in base_state.assets}
    for aid in assets_new:asset_map[aid]=hname(mods,'A_PEER_',{'peer':peer,'asset':aid},22)
    imported=[]
    # Source State assets preserve the original chronological creation order.
    for aid in assets_new:
        a=ds.assets[aid]
        if a.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK':
            fail('PEER_ADDED_UNEXPECTED_HISTORICAL_ASSET;_REVIEW_REQUIRED:'+aid)
        wid=a.get('work_id');w=ds.work.get(wid)
        if not w:fail('ASSET_WITHOUT_EXECUTED_WORK:'+aid)
        ix=a.get('origin_step',0)
        if not (isinstance(ix,int) and 1<=ix<=len(w['steps'])):fail('ASSET_WITHOUT_ORIGIN_STEP:'+aid)
        step=w['steps'][ix-1]
        if step['kind']!='MODEL_RESPONSE':fail('ASSET_NOT_AUTHORED_BY_WORKER_STEP:'+aid)
        response=load_blob_json(donor,step['raw_blob']);cid=response.get('call_id')
        call=ds.model_calls.get(cid,{})
        if call.get('state')!='SAVED' or call.get('actor')!='WORKER' or call.get('work_id')!=wid:
            fail('ASSET_ORIGIN_NOT_SAVED_WORKER_CALL:'+aid)
        source_id=hname(mods,'SRC_PEER_ASSET_',{'peer':peer,'asset':aid},20)
        original_asset_sha=mods.sha(mods.canon(a))
        original_call_sha=call['response_blob']
        record={'kind':'PEER_RESEARCH_RESULT_HISTORICAL_AI_NOT_NEW_EXECUTION',
           'peer_syn':peer,'original_root':str(donor.root),'original_asset_id':aid,
           'original_work_id':wid,'original_work_mode':w['mode'],
           'original_model_call_id':cid,'original_model_response_sha256':original_call_sha,
           'original_model_request_sha256':call['request_blob'],
           'original_worker_step_sha256':step['raw_blob'],
           'original_asset_sha256':original_asset_sha,
           'original_source_ids':a.get('source_ids',[]),'original_asset':a,
           'verification':'SAVED_WORKER_MODEL_CALL_AND_ORIGIN_STEP_MATCHED',
           'not_primary_literature':True}
        pop.add_source(source_id,'HISTORICAL_AI',record,
            'Transferred genuine AI research from '+peer+' original asset '+aid)
        pa=[asset_map[x] for x in a.get('parent_ids',[])]
        payload={'id':asset_map[aid],'kind':a['kind'],
            'problem_id':problem_map[a['problem_id']],
            'parent_ids':pa,'original_parent_ids':a.get('parent_ids',[]),
            'original_problem_id':a['problem_id'],'origin_work_mode':w['mode'],
            'claim':a['claim'],'scope':a['scope'],
            'assumptions':a['assumptions'], 'predictions':a.get('predictions',[]),
            'delta_from_parents':a.get('delta_from_parents',''),
            'limitations':list(a.get('limitations',[]))+[
                'HISTORICAL PEER MODEL OUTPUT: not independently certified'],
            'source_ids':[source_id], 'source_ref':str(donor.root)+'#'+aid,
            'source_science_sha256':original_asset_sha,
            'source_tool_sha256':mods.sha(mods.canon({'status':'TOOL_EVIDENCE_STAYS_IN_ORIGINAL_JOURNAL'})),
            'catalog_sha256':mods.sha(mods.canon({'peer':peer,'asset':aid})),
            'peer_syn':peer}
        pop.append('HISTORICAL_ASSET_INDEXED',payload)
        imported.append({'original_id':aid,'new_id':asset_map[aid],
                         'original_parent_ids':a.get('parent_ids',[]),
                         'mapped_parent_ids':pa,'model_call_id':cid})
    # Exactly recorded independent evaluations, no pseudo-Controller decisions.
    decisions,opp=_decision_artifact(donor,ds)
    source_id='SRC_PEER_DECISION_'+peer
    jrows=donor._events();head=mods.sha(mods.canon(jrows[-1]))
    peer_report={'peer_syn':peer,'original_root':str(donor.root),'head_sha256':head,
         'asset_id_translation':{k:v for k,v in asset_map.items() if k!=v},
         'events':len(jrows),'decisions':decisions,'opportunity_assessments':opp,
         'new_assets':imported,'imported_G0_assets':len(base_state.assets),
         'last_program_review':ds.program_reviews[-1] if ds.program_reviews else None,
         'pending_tool_feedback':uninterpreted_last_tool_feedback(donor,ds),
         'not_scientific_certification':True,'operator_not_choosing_winner':True}
    pop.add_source(source_id,'HISTORICAL_AI',peer_report,
           'Independently generated peer SYN model judgements; not experimental facts')
    direct=record_direct_tool_sources(mods,pop,donor,ds,peer)
    science=record_science_tool_results(mods,pop,donor,ds,peer)
    if mods.sha(mods.canon(donor._events()[-1]))!=start_head:
        fail('PEER_JOURNAL_CHANGED_DURING_IMPORT:'+peer)
    return {'peer':peer,'source':str(donor.root),'head_sha256':head,
         'new_assets_imported':len(imported),'direct_tool_sources':direct['registered_direct_sources'],
         'science_tool_sources':science['registered_science_tools'],
         'pending_tool_feedback':len(peer_report['pending_tool_feedback']),
         'decisions':len(decisions),'last_disposition':ds.program_reviews[-1]['scientific_status'] if ds.program_reviews else None,
         'asset_mapping':imported,'decision_receipt':source_id}


def combine(args):
    mods=gen.modules();plan=plan_at(args.experiment)
    poppath=Path(plan['population_root'])
    if poppath.exists():fail('POP_ALREADY_COMBINED_NO_OVERWRITE')
    for root in plan['peer_roots'].values():root_status(mods,root)
    base,bs=root_status(mods,plan['pop_base'])
    if bs.controller_decisions:fail('BASE_ALREADY_HAS_MODEL_DECISIONS')
    # Work in a private staging ROOT; never leave a partial POP_ROOT.
    stage=poppath.with_name(poppath.name+'.STAGING')
    if stage.exists():fail('POP_STAGING_EXISTS')
    shutil.copytree(plan['pop_base'],stage)
    try:
        pop,ps=root_status(mods,stage)
        peer_reports=[]
        for name,path in plan['peer_roots'].items():
            peer_reports.append(import_peer(mods,pop,bs,name,path))
        state=pop.verify();all_assets=list(state.assets)
        # All science assets, no human picks. The existing novelty system otherwise
        # omits historical imported assets not listed as selected.
        dump(stage/'FEEDBACK_PREPARE_MANIFEST.json',{
          'selected_assets':all_assets,'origin':'ALL_G0_AND_BOTH_PEER_SYN_ASSETS_NO_HUMAN_SELECTION',
          'science_certification':False},overwrite=True)
        pop.append('R5_INTEGRATION_REQUESTED',{
            'foreign_root':'TWO_INDEPENDENT_SYN_ROOTS',
            'asset_ids':all_assets,
            'event_seq':len(pop._events())+1,
            'reason':'Population-level comparison of independently executed SYN decisions and complete research outputs; no required winning candidate or mandatory new work.'})
        root_status(mods,stage)
        report={'protocol':'POPULATION_PEER_SYN_INTEGRATION_V1',
             'peer_reports':peer_reports,'root':str(poppath),
             'checkpoint_source':plan['pop_base'],
             'G0_asset_count':len(bs.assets),
             'asset_count':len(pop.verify().assets),
             'original_p0_sha256':p0hash(state),
             'no_human_selected_hypothesis':True,
             'new_model_calls':0,'science_certified':False}
        gen.save_new(stage/'population_integration.json',report)
        stage.rename(poppath)
    except BaseException:
        shutil.rmtree(stage,ignore_errors=True)
        raise
    print(json.dumps({'status':'POPULATION_SYN_READY_NO_PAID','root':str(poppath),
         'G0_assets':len(bs.assets),
         'peer_reports':[{k:r[k] for k in ['peer','decisions','new_assets_imported','direct_tool_sources','last_disposition']} for r in peer_reports]},
         indent=2,ensure_ascii=False))


@contextlib.contextmanager
def peer_context(mods,root,g2=False):
    """Pass exact provenance-labeled peer judgements to existing Controller.

    This modifies runtime prompt context only, not any research policy or model
    answer. Source data persist in Journal and remain non-certifying HISTORICAL_AI.
    """
    orig=mods.v3._external_context
    def bridged(j,*a,**kw):
        ctx=orig(j,*a,**kw)
        peer=[]
        for name in ('SYN_A','SYN_B'):
            sid='SRC_PEER_DECISION_'+name
            rec=j.verify().sources.get(sid)
            if not rec:fail('POPULATION_MISSING_PEER_RECEIPT:'+sid)
            report=load_blob_json(j,rec['blob'])
            all_decisions=report['decisions'];all_opps=report['opportunity_assessments']
            # Full originals remain replayable from the cited Journal source.
            # Prompt sees first/last two, never a quality-filtered favorite.
            shown=([all_decisions[0]]+all_decisions[-2:] if len(all_decisions)>3 else all_decisions)
            unique={d['id']:d for d in shown}
            peer.append({'peer':name,'science_origin':'INDEPENDENT_SAVED_MODEL_JUDGEMENT_NOT_LITERATURE',
                 'original_root':report['original_root'],
                 'original_head_sha256':report['head_sha256'],
                 'all_decisions_count':len(all_decisions),
                 'all_opportunity_assessments_count':len(all_opps),
                 'decisions_visible_in_prompt':list(unique.values()),
                 'opportunity_assessments_visible_in_prompt':all_opps[-2:],
                 'full_unabridged_record_at':sid,
                 'asset_id_translation_to_current_root':report['asset_id_translation'],
                 'historical_assets':[{k:x[k] for k in ['original_id','new_id','mapped_parent_ids']} for x in report['new_assets']],
                 'source_record_id':sid})
        ctx['independent_peer_syn_portfolio']=peer
        ctx['population_science_instructions']=(
          'Peer SYN decisions are independent AI research opinions, not verified literature or scientific truth. '
          'Critically compare their scientific merits, constraints, and mutually conflicting hypotheses with all inherited G0 assets. '
          'You are not obligated to create or retain any Work, FUSE or parent lineage. '
          'Choose or defer research only for substantive scientific reasons. '
          'Peer original IDs are provenance IDs, not valid new-parent IDs; use current-root mapped asset IDs when selecting parent assets. '
          'Preserve specific source-linked parent asset IDs when actually building on past science.')
        if g2:
            sid='SRC_GENERATION_REVIEW_REQUEST'
            rec=j.verify().sources.get(sid)
            if rec:
                ctx['next_generation_science_to_reconsider']=load_blob_json(j,rec['blob'])
        return ctx
    mods.v3._external_context=bridged
    try:yield
    finally:mods.v3._external_context=orig


def run_population(args,g2=False):
    plan=plan_at(args.experiment);root=plan['g2_root' if g2 else 'population_root']
    if not Path(root).is_dir():fail('POPULATION_ROOT_NOT_PREPARED')
    mods=gen.modules();j,s=root_status(mods,root)
    if p0hash(s)!=plan['P0_sha256']:fail('ROOT_P0_MISMATCH')
    with peer_context(mods,root,g2=g2):
        out=gen.drive(mods,root,args,'syn')
    print(json.dumps({'phase':'G2_REVIEW' if g2 else 'POPULATION_G1',**out},indent=2,ensure_ascii=False))


def prepare_g2(args):
    mods=gen.modules();plan=plan_at(args.experiment);poproot=Path(plan['population_root'])
    src,s=root_status(mods,poproot)
    base,_=root_status(mods,plan['pop_base'])
    gen.assert_fresh_prompts(mods,src,s)
    new_live=[aid for aid,a in s.assets.items() if aid not in base.verify().assets
              and a.get('origin')!='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK']
    if not new_live:
        print(json.dumps({'status':'NO_G1_LIVE_SCIENCE_YET_NOT_A_SCIENTIFIC_HOLD','new_assets':0},indent=2))
        return
    g2=Path(plan['g2_root'])
    if g2.exists():fail('G2_ALREADY_EXISTS')
    tail=s.program_reviews[-1]['scientific_status'] if s.program_reviews else None
    if tail in {'HOLD_WITH_RATIONALE','SCOPED_NEGATIVE','REVIEW_WORTHY_CANDIDATE'}:
        fail('G1_TERMINAL_REVIEW; NO_AUTOMATIC_REACTIVATION_OR_FORCED_G2')
    rows=src._events();report=clone_at_checkpoint(mods,poproot,g2,len(rows),mods.sha(mods.canon(rows[-1])))
    try:
        j,st=root_status(mods,g2)
        j.add_source('SRC_GENERATION_REVIEW_REQUEST','HISTORICAL_AI',{
            'kind':'OPERATIONAL_G1_TO_G2_REASSESSMENT_NOT_NEW_SCIENCE',
            'G1_original_root':str(poproot),
            'G1_original_head_sha256':report['head_sha256'],
            'new_science_asset_ids':new_live,
            'new_science_asset_sha256':{aid:mods.sha(mods.canon(s.assets[aid])) for aid in new_live},
            'has_real_synthesis_execution':len(s.controller_decisions)>0,
            'science_certified':False},
            'Checkpoint review of new G1 research; not a new source or independent discovery')
        j.append('R5_INTEGRATION_REQUESTED',{
            'foreign_root':str(poproot),'asset_ids':new_live,
            'event_seq':len(j._events())+1,
            'reason':'Offer model an autonomous new-generation reassessment of actual G1 results, without requiring further research.'})
        root_status(mods,g2)
    except BaseException:
        shutil.rmtree(g2,ignore_errors=True)
        raise
    print(json.dumps({'status':'G2_REASSESSMENT_READY_NO_PAID','G1_assets_for_reassessment':len(new_live),
                      'G2_root':str(g2)},indent=2))


def ancestry(state):
    assets=state.assets
    base={aid for aid,a in assets.items() if aid.startswith('A_ISO_') and a.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
    # The preserved G0 set is the same for all branch snapshots.
    cache={}
    def hits(aid,seen=None):
        if aid in cache:return cache[aid]
        if aid in base:return True
        if seen is None:seen=set()
        if aid in seen:return False
        parents=assets.get(aid,{}).get('parent_ids',[])
        result=any(hits(p,seen|{aid}) for p in parents)
        cache[aid]=result
        return result
    return base,hits


def audit(args):
    mods=gen.modules();plan=plan_at(args.experiment);base,bs=root_status(mods,plan['pop_base'])
    out={'protocol':'POPULATION_EVOLUTION_AUDIT_V1','G0_asset_count':len(bs.assets),
         'original_P0_sha256':plan['P0_sha256'],'independent_peer_syns':{},
         'G1':None,'G2':None,'scientific_certification':False}
    for peer,path in plan['peer_roots'].items():
        j,s=root_status(mods,path);gen.assert_fresh_prompts(mods,j,s)
        out['independent_peer_syns'][peer]={'events':len(j._events()),
            'head_sha256':mods.sha(mods.canon(j._events()[-1])),
            'controller_decisions':len(s.controller_decisions),'new_live_assets':len(s.assets)-len(bs.assets),
            'new_works':len(s.work),'last_disposition':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None}
    for phase,key in [('G1','population_root'),('G2','g2_root')]:
        root=Path(plan[key]);
        if not root.exists():continue
        j,s=root_status(mods,root);gen.assert_fresh_prompts(mods,j,s)
        base_ids,hits=ancestry(s)
        imported={aid for aid,a in s.assets.items() if a.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
        live={aid for aid in s.assets if aid not in imported}
        direct=[wid for wid,w in s.work.items() if any(pid in base_ids for pid in w['asset_input_ids'])]
        all_inherited=[wid for wid,w in s.work.items() if any(pid in imported for pid in w['asset_input_ids'])]
        descended=[aid for aid in live if hits(aid)]
        peer_desc=[aid for aid in live if any(p in imported and p not in base_ids for p in s.assets[aid]['parent_ids'])]
        decisions,_=_decision_artifact(j,s)
        out[phase]={'root':str(root),'events':len(j._events()),
          'head_sha256':mods.sha(mods.canon(j._events()[-1])),
          'historical_assets':len(imported),'new_live_assets':len(live),
          'controller_decisions':len(decisions),
          'direct_G0_parent_works':direct,
          'historical_parent_works':all_inherited,
          'G0_transitive_live_descendants':descended,
          'direct_peer_parent_live_assets':peer_desc,
          'new_work_operations':[{'id':wid,'operation':w['operation'],'mode':w['mode'],
               'parent_ids':w['asset_input_ids'],'status':w['status']}
               for wid,w in s.work.items()],
          'science_asset_claims':[{'id':aid,'kind':s.assets[aid]['kind'],
               'claim':s.assets[aid]['claim'],'parent_ids':s.assets[aid].get('parent_ids',[])} for aid in live],
          'decisions':[{'id':r['id'],'rationale':r['rationale'],'actions':r['actions'],
                        'disposition':r['disposition']} for r in decisions],
          'tool_results':len(s.tool_results),'unsaved_model_calls':[cid for cid,v in s.model_calls.items() if v['state']!='SAVED'],
          'last_disposition':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None}
    dump(args.out,out)
    print(json.dumps({'status':'READ_ONLY_POPULATION_AUDIT_SAVED','out':str(Path(args.out).resolve()),
       'peer_syn_decisions':{k:v['controller_decisions'] for k,v in out['independent_peer_syns'].items()},
       'G1_direct_G0_parent_works':len(out['G1']['direct_G0_parent_works']) if out['G1'] else None,
       'G1_live_descendants':len(out['G1']['G0_transitive_live_descendants']) if out['G1'] else None,
       'G2_controller_decisions':out['G2']['controller_decisions'] if out['G2'] else None},indent=2))


def run_args(parser):
    parser.add_argument('--experiment',required=True)
    parser.add_argument('--paid',action='store_true')
    parser.add_argument('--model',default='openai/gpt-5.6-luna')
    parser.add_argument('--max-new-calls',type=int,default=16)
    parser.add_argument('--slice-budget',type=int,default=8)
    parser.add_argument('--checkpoint-iterations',type=int,default=12)
    parser.add_argument('--max-parallel',type=int,default=2)
    parser.add_argument('--max-tokens',type=int,default=16000)
    parser.add_argument('--science-cpu-seconds',type=int,default=120)
    parser.add_argument('--science-wall-seconds',type=int,default=160)


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cmd=cli.add_subparsers(dest='command',required=True)
    a=cmd.add_parser('init');a.add_argument('--g0-experiment',required=True);a.add_argument('--out',required=True)
    a=cmd.add_parser('preflight');a.add_argument('--experiment',required=True)
    a=cmd.add_parser('run-peer');run_args(a);a.add_argument('--peer',choices=['SYN_A','SYN_B'],required=True)
    a=cmd.add_parser('combine');a.add_argument('--experiment',required=True)
    a=cmd.add_parser('run-population');run_args(a)
    a=cmd.add_parser('prepare-g2');a.add_argument('--experiment',required=True)
    a=cmd.add_parser('run-g2');run_args(a)
    a=cmd.add_parser('audit');a.add_argument('--experiment',required=True);a.add_argument('--out',required=True)
    ns=cli.parse_args()
    try:
        fn={'init':init,'preflight':preflight,'run-peer':run_peer,
            'combine':combine,'run-population':lambda n:run_population(n,False),
            'prepare-g2':prepare_g2,'run-g2':lambda n:run_population(n,True),'audit':audit}[ns.command]
        fn(ns)
    except Exception as e:
        print(json.dumps({'status':'OPERATIONAL_ERROR_NOT_A_SCIENTIFIC_HOLD',
             'error_type':type(e).__name__,'detail':str(e)},ensure_ascii=False),file=sys.stderr)
        return 3
    return 0

if __name__=='__main__':raise SystemExit(main())
