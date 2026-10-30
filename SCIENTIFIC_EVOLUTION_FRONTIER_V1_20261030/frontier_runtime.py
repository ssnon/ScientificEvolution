"""Opt-in runtime overlay for scientific context/portfolio; no change to E2 source.

The runtime guard still checks original source hashes. Patch only model-facing
DERIVED context and a strictly authorized archive-lookup tool for INFORMED Work.
"""
from __future__ import annotations
import contextlib, json, os
from collections import Counter
from pathlib import Path
import science_frontier as sf

VIEW_VERSION='FRONTIER_CONTEXT_AND_POPULATION_SCIENCE_V1_20261030'


def _scope(j):
    s=j.verify()
    selected,report=sf.select_assets(s)
    return s,selected,report


def _research_context(base,s,selected,selection):
    selected_set=set(selected)
    base['assets']=[x for x in base.get('assets',[]) if x['id'] in selected_set]
    base['scientific_portfolio_index']=sf.catalog(s,selected)
    base['scientific_archive_manifest']={'all_asset_ids':list(s.assets),
        'archive_scope':'ALL_REGISTERED_ASSETS_PRESERVED_NOT_ALL_FULL_TEXT_REPRINTED',
        'omitted_full_text_is_not_rejected_science':True,
        'original_journal_root':'SEE_CURRENT_MODEL_JOURNAL',
        'source_ledger_sha256':sf.sha([(k,v.get('kind'),v.get('blob')) for k,v in s.sources.items()])}
    base['scientific_evidence_inventory']={'all_registered_potential_evidence_ids':[k for k,v in s.sources.items()
        if v.get('kind') in ('TOOL_RESULT','EXTERNAL_AUDIT')],
        'attention_evidence_is_only_a_subset':True,
        'absence_from_current_model_evidence_is_not_evidence_of_absence':True}
    base['scientific_portfolio_frontier']=sf.frontier(s,selected)
    base['provisional_level_ii_candidate_dossiers']=sf.candidate_dossiers(s,selected,limit=7)
    base['scientific_attention_contract']={
        'version':VIEW_VERSION,'all_assets_in_original_journal':len(s.assets),
        'selected_claim_ids':selected, 'unpresented_asset_count':len(selection['omitted_ids']),
        'complete_portfolio_hash':selection['index_sha256'],
        'unpresented_not_rejected':True,
        'no_forced_fuse_or_new_work':True,
        'context_is_incomplete_as_to_full_claim_text':True,
        'original_is_authoritative':'Use exact asset/source IDs for any claimed parent or evidence; originals remain in Journal',
        'science_caveat':'This attention view is not an independent assessment of novelty or physical plausibility'}
    if sf.size(base.get('research_capability_state'))>7000:
        base['research_capability_state']=sf.redact_model_context(base['research_capability_state'],7000)
    if sf.size(base.get('portfolio_context'))>7000:
        base['portfolio_context']=sf.redact_model_context(base['portfolio_context'],7000)
    if sf.size(base.get('prior_program_reviews'))>6000:
        reviews=base['prior_program_reviews']
        base['prior_program_reviews']=[{'reviewer_id':r.get('reviewer_id'),'scientific_status':r.get('scientific_status'),
            'rationale_excerpt':sf.short(r.get('rationale'),400), 'raw_sha256':sf.sha(r)} for r in reviews]
    if sf.size(base.get('objective_assessments'))>6000:
        base['objective_assessments']=[{'objective_status':r.get('objective_status'),
            'research_status':r.get('research_status'),'reason_excerpt':sf.short(r.get('reason'),500),
            'raw_sha256':sf.sha(r)} for r in base['objective_assessments']]
    return base


def _compact_view(view, root, max_claims=28):
    """Compact a meta council VIEW; raw source remains in its verified Journal."""
    if not isinstance(view,dict) or not view.get('root') or not Path(view['root']).is_dir():return view
    import population_run as pop
    mods=pop.gen.modules()
    j=mods.J(view['root']);s=j.verify()
    selected,report=sf.select_assets(s,29000)
    # Council sees a shorter but diverse, traceable mechanism frontier, not just newest data.
    rows=sf.catalog(s,selected,limit_chars=8000)
    history=sf.frontier(s,selected,max_rows=18)
    v=dict(view)
    v['historical_assets']=[{'id':aid,'kind':s.assets[aid].get('kind'),
        'claim_excerpt':sf.short(s.assets[aid].get('claim'),175),
        'parent_ids':s.assets[aid].get('parent_ids',[])} for aid in selected if
        s.assets[aid].get('origin','LIVE_WORK')!='LIVE_WORK'][:max_claims]
    v['live_assets']=[{'id':a.get('id'),'kind':a.get('kind'),
        'claim_excerpt':sf.short(a.get('claim'),280),
        'delta_excerpt':sf.short(a.get('delta_from_parents'),240),
        'parent_ids':a.get('parent_ids',[]),
        'source_ids':a.get('source_ids',[])[:6]}
        for a in view.get('live_assets',[])][-24:]
    v['scientific_archive_index']=rows
    v['scientific_frontier']=history
    v['model_facing_view_disclosure']={'original_root':view['root'],
       'original_head':view.get('head'), 'all_asset_count':len(s.assets),
       'full_catalog_sha256':report['index_sha256'],
       'context_selection_is_not_scientific_rejection':True,
       'original_source_and_work_results_remain_available':True}
    # recent decisions remain, but avoid repeating large JSON blobs indefinitely.
    v['recent_controller_decisions']=[{'id':r.get('id'),'disposition':r.get('disposition'),
       'rationale_excerpt':sf.short(r.get('rationale'),600),
       'actions':r.get('actions',[])[:8]} for r in view.get('recent_controller_decisions',[])][-5:]
    return v


def compact_snapshot(context,cycle):
    ctx=dict(context)
    base=dict(ctx.get('inherited_base') or {})
    if base.get('root'):
        v=_compact_view({'root':base['root'],'head':base.get('head'),
                         'historical_assets':base.get('all_inherited_assets',[]),'live_assets':[]},base['root'])
        base['all_inherited_assets'] = v.get('historical_assets',[])
        base['portfolio_index']=v.get('scientific_archive_index')
        base['entire_original_catalog_sha256'] = v.get('model_facing_view_disclosure',{}).get('full_catalog_sha256')
        base['all_assets_still_in_verified_base_root']=True
        ctx['inherited_base']=base
    if ctx.get('current_research'):
        ctx['current_research']=_compact_view(ctx['current_research'],ctx['current_research']['root'])
    if ctx.get('independent_peers'):
        ctx['independent_peers']=[{'name':x['name'],'research':_compact_view(x['research'],x['research']['root'])}
             for x in ctx['independent_peers']]
    recent=[]
    for x in ctx.get('population_history_recent',[]):
        y=dict(x)
        # Past populations remain in their original verified ROOTs.
        y['assets_count']=len(y.get('assets',[]))
        y['assets']=[{'id':a.get('id'),'kind':a.get('kind'),
                     'claim_excerpt':sf.short(a.get('claim'),180),
                     'parent_ids':a.get('parent_ids',[])} for a in y.get('assets',[])][-12:]
        recent.append(y)
    ctx['population_history_recent']=recent
    ctx['population_scientific_selection_contract']={
        'version':VIEW_VERSION,
        'science_selection_instruction':('Compare materially different experimental predictions, mathematical deltas, '
          'strong nulls, evidence access outcomes, active work and dormant inherited alternatives. '
          'Choose research or HOLD autonomously. Neither inherited diversity nor FUSE is a quota.'),
        'evidence_access_failure_is_not_scientific_refutation':True,
        'scientific_progress_is_not_asset_count':True,
        'proposal_vs_certification':'Level-II is a review-worthy physical hypothesis; model review is not a proof',
        'no_fixed_stage_or_work_requirement':True,
        'journal_records_not_modified':True}
    return ctx


def archive_tool(original,self,req,context):
    if req.get('kind')!='scientific_archive':return original(self,req,context)
    s=self.j.verify();wid=context.get('work_id');w=s.work.get(wid)
    if not w or w.get('mode')!='INFORMED':
        return {'status':'REJECTED','error_code':'FRESH_OR_UNSCOPED_ARCHIVE_ACCESS_BLOCKED'}
    args=req.get('arguments') or {}
    if args.get('action')!='parent_asset' or not isinstance(args.get('id'),str):
        return {'status':'REJECTED','error_code':'ARCHIVE_QUERY_INVALID'}
    aid=args['id']
    # An informed Worker can inspect its pinned parents and their ancestors,
    # not arbitrary private sibling research or unrelated frontier documents.
    allowed=set(w.get('asset_input_ids',[]))|set(w.get('published',[]))
    todo=list(allowed)
    while todo:
        a=todo.pop()
        for pid in s.assets[a].get('parent_ids',[]):
            if pid not in allowed:allowed.add(pid);todo.append(pid)
    if aid not in allowed:
        return {'status':'REJECTED','error_code':'ASSET_OUTSIDE_INFORMED_PARENT_LINEAGE'}
    a=s.assets[aid]
    records=[]
    for sid in a.get('source_ids',[]):
        src=s.sources.get(sid)
        if src and src['kind']=='HISTORICAL_AI':
            record=json.loads(self.j.raw(src['blob']))
            records.append({'source_id':sid,'source_kind':'HISTORICAL_AI_UNVERIFIED',
                            'content':record,'original_blob_sha256':src['blob']})
    return {'status':'DELIVERED','asset':a,'historical_sources':records,
       'scientific_certification':False,'not_primary_experimental_evidence':True,
       'original_journal_root':str(self.j.root)}


@contextlib.contextmanager
def activate(mods,aut):
    """Install only for a run segment; restore every symbol even on failure."""
    import e2core.engine as engine
    spe=mods.spe;v3=mods.v3
    # Both v3 and spe keep imported references to the original function.
    original=(v3._external_context,spe.target_claims,spe.classified_evidence,
              spe.working_problem_state,engine.Engine._tool,engine.WORKER_PROMPT,
              aut.snapshot,aut.S_PROMPT,spe.NOVELTY_PROMPT,spe.IMPACT_PROMPT)
    orig_external,orig_target,orig_evidence,orig_state,orig_tool,orig_prompt,orig_snapshot,orig_steer,orig_novelty,orig_impact=original
    def external(j,tool_capabilities=None):
        s,selected,selection=_scope(j)
        base=orig_external(j,tool_capabilities)
        return _research_context(base,s,selected,selection)
    def target(context,j):
        # Existing target_claims contract (selected inherited + current live) is
        # preserved; it simply receives a science-diverse, bounded view.
        return orig_target(context,j)
    def evidence(j):
        s,selected,selection=_scope(j)
        relevant={sid for aid in selected for sid in s.assets[aid].get('source_ids',[])}
        rows,report=sf.cap_evidence(orig_evidence(j),relevant)
        # Insert source omissions only in read-only working-problem context,
        # not as fake evidence IDs that could pass novelty validation.
        return rows
    def problem_state(j):
        s,selected,selection=_scope(j)
        v=orig_state(j)
        result=sf.compact_state(v,selected,str(j.root))
        result['scientific_archive_scope']={'version':VIEW_VERSION,
            'all_asset_count':len(s.assets),'attention_selected_count':len(selected),
            'original_index_sha256':selection['index_sha256'],
            'unpresented_claims_are_neither_rejected_nor_evaluated':True}
        return result
    def tool(self,req,context):return archive_tool(orig_tool,self,req,context)
    def snapshot(modules,experiment,cycle,stage,peer=None):
        full=orig_snapshot(modules,experiment,cycle,stage,peer)
        return compact_snapshot(full,cycle)
    try:
        v3._external_context=external
        spe.target_claims=target
        spe.classified_evidence=evidence
        spe.working_problem_state=problem_state
        spe.NOVELTY_PROMPT=orig_novelty+('\nATTENTION-SCOPE CONTRACT: The claims and evidence provided are a disclosed subset of a larger '
          'archived research portfolio. Absence from this scope cannot establish novelty, no prior art, '
          'a negative empirical finding, or impossibility. Evaluate only the supplied exact IDs, '
          'mark uninspected items as uncertain, and return succinct complete JSON. No minimum number of claim rows.\n')
        spe.IMPACT_PROMPT=orig_impact+('\nSCOPED SCIENTIFIC REASSESSMENT: Review claim-to-P0 effects only for specifically '
          'supplied target claim IDs with material consequences. Do not reconstruct every historical claim; '
          'all omitted historical science remains unchanged in the authoritative Journal. '
          'Keep the original P0 unresolved absent adequate support; avoid repetitive paraphrases. '
          'Return one compact, syntactically complete JSON object. No mandatory number of rows.\n')
        engine.Engine._tool=tool
        engine.WORKER_PROMPT=orig_prompt+('\nINFORMED-only archive retrieval option: '
          '{"kind":"scientific_archive","arguments":{"action":"parent_asset","id":"EXACT_AUTHORIZED_PARENT_ID"}}. '
          'This returns unverified historical AI assets in the pinned parent lineage; it cannot be used by FRESH. '
          'Archive lookup is not a new experimental observation. Never claim otherwise.\n')
        aut.snapshot=snapshot
        aut.S_PROMPT=orig_steer+('\nPORTFOLIO INTERPRETATION: Attention selection is not science rejection. '
          'Use available lineage clusters, different research-deliverable types and active work. '
          'An old mechanism can be revisited only when it adds a material prediction, falsifier, calculation or new evidence. '
          'Do not endlessly repeat failed access routes without explaining the expected new information; '
          'access failures do not prove the scientific hypothesis false. '
          'No mandatory FUSE, mutation, Work count or scientific progress.\\n')
        yield
    finally:
        (v3._external_context,spe.target_claims,spe.classified_evidence,
         spe.working_problem_state,engine.Engine._tool,engine.WORKER_PROMPT,
         aut.snapshot,aut.S_PROMPT,spe.NOVELTY_PROMPT,spe.IMPACT_PROMPT)=original
