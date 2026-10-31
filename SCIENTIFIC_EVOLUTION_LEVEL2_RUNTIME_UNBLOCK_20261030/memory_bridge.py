"""Bounded model attention and provenance truth overlay (read-only on E2 state).

Entire scientific archive stays in verified E2 Journal. This file creates *model
views*; never mutates the source scientific portfolio, status, or source claims.
"""
from __future__ import annotations
import contextlib
import copy
import json
from collections import Counter
from pathlib import Path
import science_frontier as sf

# Do not bump the model-facing contract for a pure replay compatibility fix.
# Changing it would change the source payload SHA and defeat historical replay.
VERSION='RETRIEVABLE_SCIENCE_MEMORY_AND_EXECUTED_TOOL_TRUTH_V1_2_20261030'

# Limits are model-attention budgets (not quotas for hypotheses or workers).
BUDGETS={'problems':22000,'peer':10500,'previous':4500,'unreviewed':3500,
         'archive':1800,'index':5500,'frontier':9500,'candidates':11500,
         'claims':10000,'impact':8500,'all_controller':86000}


def jsize(obj):return len(json.dumps(obj,ensure_ascii=False,sort_keys=True,default=str))

def _digest(obj):return sf.sha(obj)

def _short(value,n):return sf.short(value,n)

def _attn(records,max_chars,convert):
    rows=[];used=2
    for r in records:
        row=convert(r)
        n=jsize(row)+2
        if used+n>max_chars:break
        rows.append(row);used+=n
    return rows


def bound_problems(problems, active_ids=(), budget=BUDGETS['problems']):
    """Keep the original list-of-problems schema and every exact problem ID.

    Full P0 and active problem questions have priority. Other questions are
    disclosed excerpts, never silently transformed into scientific negatives.
    """
    if not isinstance(problems,list):return problems
    active=set(active_ids)|{'P0'}
    def make(excerpt_len,active_len):
        rows=[]
        for p in problems:
            if not isinstance(p,dict):continue
            pid=p.get('id');is_active=pid in active
            row={'id':pid,'parents':p.get('parents',[]),
                 'question':_short(p.get('question'),active_len if is_active else excerpt_len)}
            if is_active:
                row['question_attention_excerpt']=len(str(p.get('question','')))>active_len
            else:
                row['question_attention_excerpt']=True
            rows.append(row)
        return rows
    for excerpt,active_length in ((145,1800),(105,1400),(75,950),(40,650),(0,350)):
        rows=make(excerpt,active_length)
        if jsize(rows)<=budget:return rows
    raise RuntimeError('PROBLEM_IDENTITIES_EXCEED_ATTENTION_BUDGET_NOT_SILENTLY_OMITTED')


def page_problem_context(problems, active_ids=(), budget=10000):
    """A bounded *view*, never a mutation or an implicit rejection of problems.

    The former loop demanded all 100+ long IDs, their parent arrays, a question
    field and an excerpt flag per row inside successively SMALLER fixed budgets.
    Its own minimum encoding could exceed those budgets. Keep P0, all active
    problems and their ancestors with descriptive context. Provide an exact
    compact ID catalog if it fits; otherwise disclose the excluded identities
    and a full cryptographic commitment to the original ledger. The verified
    Journal is authoritative. No scientific status is inferred from omission.
    """
    if not isinstance(problems,list):return problems,{}
    records=[x for x in problems if isinstance(x,dict) and isinstance(x.get('id'),str)]
    by_id={x['id']:x for x in records}
    if len(records)!=len(problems) or len(by_id)!=len(records):
        raise RuntimeError('PROBLEM_CATALOG_DUPLICATE_OR_INVALID_ID')
    required=set(active_ids)|({'P0'} if 'P0' in by_id else set())
    # Recursive parent closure; anything needed to interpret an active problem
    # is mandatory. Unknown parent IDs remain a hard error, not a fake graph.
    todo=list(required)
    while todo:
        aid=todo.pop()
        if aid not in by_id:
            raise RuntimeError('PROBLEM_CATALOG_ACTIVE_OR_PARENT_UNKNOWN:'+aid)
        for parent in by_id[aid].get('parents',[]):
            if parent not in by_id:
                raise RuntimeError('PROBLEM_CATALOG_PARENT_UNKNOWN:'+str(parent))
            if parent not in required:
                required.add(parent);todo.append(parent)
    all_ids=[x['id'] for x in records]
    registry='\n'.join(all_ids)
    positions={ident:i for i,ident in enumerate(all_ids)}
    for x in records:
        for parent in x.get('parents',[]):
            if parent not in positions:
                raise RuntimeError('PROBLEM_CATALOG_PARENT_UNKNOWN:'+str(parent))
    # A dense lossless graph encoding: row i belongs to ID line i; each
    # comma-separated integer is a parent INDEX in the very same ID catalog.
    # Empty row means no parents. The full graph is exact when this fits.
    parent_codes=';'.join(','.join(str(positions[parent]) for parent in x.get('parents',[]))
                          for x in records)
    registry_sha=_digest(all_ids)
    ledger_sha=_digest(problems)
    def record(x,full=False):
        return {'id':x['id'],'parents':x.get('parents',[]),
                'question':_short(x.get('question'),650 if full else 90),
                'question_excerpt_not_full_archive':True}
    # Required problems may be numerous; shrink their prose rather than hide
    # their identity, parentage, or status. Do not auto-select science winners.
    def select(q_len, include_registry):
        rows=[{'id':x['id'],'parents':x.get('parents',[]),
               'question':_short(x.get('question'),q_len),
               'question_excerpt_not_full_archive':True}
               for x in records if x['id'] in required]
        extras={'mode':'REFERENCE_PAGED','total_problem_count':len(records),
                'visible_problem_ids':[r['id'] for r in rows],
                'not_visible_problem_count':len(records)-len(rows),
                'full_problem_ledger_sha256':ledger_sha,
                'all_problem_ids_sha256':registry_sha,
                'hidden_problems_are_not_rejected':True,
                'verified_journal_contains_all_original_problems':True,
                'full_parent_graph_in_verified_journal':True,
                'all_problem_ids_in_this_view':include_registry}
        if include_registry:
            extras['all_problem_ids_newline_delimited']=registry
            extras['parent_indices_semicolon_delimited']=parent_codes
            extras['parent_encoding']='ID catalog lines and parent-index rows have the same order; each parent is a zero-based ID index, comma-separated for multiple parents, empty for no parents.'
        return rows,extras
    for text_limit in (650,250,90,0):
        for keep_registry in (True,False):
            rows,meta=select(text_limit,keep_registry)
            if jsize(rows)+jsize(meta)+40<=budget:
                return rows,meta
    raise RuntimeError('ACTIVE_PROBLEM_GRAPH_EXCEEDS_ATTENTION_BUDGET_PAGINATION_REQUIRED')


def active_problem_ids_from_payload(payload):
    active={'P0'}
    options=payload.get('v3_science_work_options',{})
    if isinstance(options,dict):
        for w in options.get('active_scientific_work',[]):
            if isinstance(w,dict) and w.get('problem_id'):active.add(w['problem_id'])
    for w in payload.get('works',[]):
        if isinstance(w,dict) and w.get('status') in ('ACTIVE','QUEUED','DEFERRED') and w.get('problem_id'):
            active.add(w['problem_id'])
    return active


def _slim_decisions(rows,n=4):
    out=[]
    for r in (rows or [])[-n:]:
        out.append({'id':r.get('id'),'disposition':r.get('disposition'),
                    'scientific_status':r.get('scientific_status'),
                    'rationale':_short(r.get('rationale') or r.get('reason'),400),
                    'actions_count':len(r.get('actions',[])), 'original_sha256':_digest(r)})
    return out


def bound_peer(v):
    """Keep the provenance and frontier of both independent peers, not their entire repeated JSON."""
    if not isinstance(v,list):return v
    rows=[]
    for peer in v:
        if not isinstance(peer,dict):continue
        out={'name':peer.get('name') or peer.get('peer'),
             'source_sha256':_digest(peer),'all_keys':list(peer),
             'scientific_detail_in_original_journal':True}
        if peer.get('decisions'):
            out['recent_decisions']=_slim_decisions(peer['decisions'],2)
        for k in ('research','assets','all_peer_assets','work_statuses','scientific_status'):
            x=peer.get(k)
            if isinstance(x,list):
                out[k+'_count']=len(x)
                out[k+'_recent']=[{'id':r.get('id') or r.get('new_id'),
                                     'original_id':r.get('original_id'),
                                     'parent_ids':r.get('parent_ids') or r.get('mapped_parent_ids')}
                                    for r in x[-6:] if isinstance(r,dict)]
            elif isinstance(x,dict):
                out[k+'_summary']=slim_object(x,2400)
            elif x is not None:out[k]=x
        rows.append(out)
    return rows


def slim_object(x,budget=5000):
    """A labeled derived excerpt, never an authoritative replacement."""
    if jsize(x)<=budget:return x
    if isinstance(x,dict):
        y={}; omitted=[]
        important=('id','state','status','objective_status','research_status','original_problem_still_open',
                   'still_unresolved_requirements','model_proposed_impact_state',
                   'model_assessment_only','science_certification')
        for k in important:
            if k in x:
                val=x[k]
                if isinstance(val,list):val=[_short(i,180) for i in val[:7]]
                if jsize({k:val})+jsize(y)<budget-350:y[k]=val
        for k,v in x.items():
            if k in y:continue
            size=jsize({k:v})
            if jsize(y)+size<=budget-350:y[k]=v
            else:omitted.append(k)
        y['_attention_omissions']={'fields':omitted,'full_sha256':_digest(x),
              'reason':'FULL_UNMODIFIED_VALUE_RETAINED_IN_MODEL_JOURNAL'}
        return y
    if isinstance(x,list):
        arr=_attn(x,max(200,budget-350),lambda z:z)
        return {'attention_rows':arr,'rows_total':len(x),'full_sha256':_digest(x),
                'unpresented_is_not_scientific_rejection':True}
    return {'original_type':type(x).__name__,'full_sha256':_digest(x),
            'excerpt':_short(x,budget-300)}


def provenance(state, root=None, max_rows=25):
    """Actual executed tools ONLY from TOOL_RECORDED/TOOL_RESULT ledger.

    A model's text announcing a search does NOT count as an executed search.
    Historical human/model summaries do not become tool receipts.
    """
    counts=Counter()
    for v in state.tool_results.values():counts[v.get('work_id')]+=1
    failures=[];works=[]
    for w in state.work.values():
        wid=w['id'];actual=counts.get(wid,0)
        models=len([s for s in w.get('steps',[]) if s.get('kind')=='MODEL_RESPONSE'])
        asset_ids=w.get('published',[])
        suspicious=[]
        for aid in asset_ids:
            a=state.assets.get(aid,{})
            if actual==0 and a.get('kind') in ('FAILURE','SCOPED_NEGATIVE','LITERATURE_CLAIM'):
                if not a.get('source_ids'):
                    suspicious.append(aid)
                    failures.append({'work_id':wid,'asset_id':aid,'asset_kind':a.get('kind'),
                        'issue':'UNSUPPORTED_LITERATURE_OR_TOOL_STATUS_NO_EXECUTED_RECEIPT',
                        'tool_execution_not_observed':True})
        if actual or suspicious or w.get('status') in ('ACTIVE','QUEUED'):
            works.append({'work_id':wid,'status':w.get('status'),'mode':w.get('mode'),
                'actual_tool_executions':actual,'model_steps':models,
                'unsupported_status_assets':suspicious[:10]})
    return {'contract':VERSION,'actual_executed_tool_receipts':len(state.tool_results),
        'tool_count_by_work':dict(counts),'works':works[-max_rows:],
        'unverified_status_claims':failures[-max_rows:],
        'no_tool_call_may_be_inferred_from_scientific_text':True,
        'no_negative_scientific_result_from_missing_tool_execution':True,
        'actual_receipts_are_only_TOOL_RECORDED_and_registered_TOOL_RESULT':True}


def bound_base(base, state, journal_root=None):
    """Trim ALL large controller context fields before NVT, PMI, OPP and Controller."""
    v=dict(base)
    active={w.get('problem_id') for w in state.work.values()
            if w.get('status') in ('ACTIVE','QUEUED','DEFERRED')}
    for a in v.get('assets',[]):
        if a.get('origin')=='LIVE_WORK':active.add(a.get('problem_id'))
    original_problems=v.get('problems',[])
    v['problems']=bound_problems(original_problems,active)
    v['problem_attention_info']={'original_problem_count':len(original_problems),
       'all_problem_ids_sha256':_digest([x.get('id') for x in original_problems]),
       'original_full_question_ledger_sha256':_digest(original_problems),
       'all_ids_kept_in_original_problems_list':True,'omitted_question_details_not_negatives':True}
    if 'independent_peer_syn_portfolio' in v:
        v['independent_peer_syn_portfolio']=bound_peer(v['independent_peer_syn_portfolio'])
    if 'previous_population_scientific_status' in v:
        x=v['previous_population_scientific_status']
        if isinstance(x,dict):
            v['previous_population_scientific_status']={
                'source_root':x.get('source_root'),'source_sha256':_digest(x),
                'previous_review':slim_object(x.get('previous_review'),1500),
                'recent_controller_decisions':_slim_decisions(x.get('recent_controller_decisions'),3),
                'work_statuses':slim_object(x.get('work_statuses',{}),2000),
                'not_current_research_evidence':True}
    if 'unreviewed_frontier_events' in v:
        ev=v['unreviewed_frontier_events']
        if isinstance(ev,list):
            v['unreviewed_frontier_events']={'total':len(ev),'kinds':dict(Counter(x.get('kind') for x in ev)),
                'latest':ev[-12:],'full_sha256':_digest(ev),
                'unpresented_events_still_in_original_journal':True}
    if 'scientific_archive_manifest' in v:
        x=v['scientific_archive_manifest']
        if isinstance(x,dict):
            v['scientific_archive_manifest']={'all_asset_count':len(state.assets),
               'all_asset_ids_sha256':_digest(list(state.assets)),
               'source_ledger_sha256':x.get('source_ledger_sha256'),
               'original_root':str(journal_root) if journal_root else None,
               'archive_ids_not_reprinted':True}
    for name,budget in [('scientific_portfolio_index',BUDGETS['index']),
                        ('scientific_portfolio_frontier',BUDGETS['frontier']),
                        ('provisional_level_ii_candidate_dossiers',BUDGETS['candidates']),
                        ('independent_cohort_history',3000),('portfolio_context',5000),
                        ('research_capability_state',2400)]:
        if name in v:v[name]=slim_object(v[name],budget)
    v['verified_execution_provenance']=provenance(state,journal_root)
    tools_by_work=Counter(x.get('work_id') for x in state.tool_results.values())
    v['assets']=[{**a,'source_execution_status':(
         'NO_EXECUTED_TOOL_RECEIPT_FOR_SOURCELESS_STATUS_CLAIM'
         if (state.assets.get(a.get('id'),{}).get('kind') in ('FAILURE','SCOPED_NEGATIVE','LITERATURE_CLAIM')
             and not state.assets.get(a.get('id'),{}).get('source_ids')
             and tools_by_work.get(state.assets.get(a.get('id'),{}).get('work_id'),0)==0)
         else 'REFER_TO_REGISTERED_SOURCE_IDS_AND_TOOL_LEDGER')}
         for a in v.get('assets',[])]
    v['science_memory_disclosure']={'version':VERSION,'original_journal_root':str(journal_root),
        'all_asset_count':len(state.assets),'all_problem_count':len(state.problems),
        'original_portfolio_full_digest':_digest([ (x['id'],x.get('claim'),x.get('parent_ids')) for x in state.assets.values()]),
        'long_context_absence_is_not_a_scientific_negative':True,
        'no_scientific_decisions_are_made_by_the_memory_compactor':True}
    return v




def compact_novelty_review(v,budget=BUDGETS['claims']):
    """Keep every accepted claim identity/relation/citation for next-generation replay."""
    if not isinstance(v,dict) or jsize(v)<=budget:return v
    rows=[]
    for r in v.get('claim_assessments',[]):
        if not isinstance(r,dict):continue
        keep={k:r[k] for k in ('asset_id','relation','evidence_ids','certification',
                'evidence_quality') if k in r}
        for k in ('remaining_conditional_claim','specific_differentiating_prediction',
                  'residual_hypothesis','strongest_competing_explanation','decisive_test'):
            if k in r:keep[k]=_short(r[k],240)
        rows.append(keep)
    result={'claim_assessments':rows,'rejected':v.get('rejected',[]),
            'novelty_certification':False,'original_model_review_sha256':_digest(v),
            'prose_fields_compacted_not_scientific_rejected':True,
            'assessment_records_kept':len(rows)}
    if jsize(result)>budget:
        # Referents are not discarded. Return the exact ID/relation/citation ledger,
        # with a disclosure that the verbose science remains in NVT saved wire.
        result['claim_assessments']=[{k:r[k] for k in ('asset_id','relation','evidence_ids') if k in r}
                                      for r in rows]
        result['detailed_assessments_bounded_by_attention']=True
    if jsize(result)>budget:
        raise RuntimeError('NOVELTY_ASSESSMENT_IDENTITIES_EXCEED_ATTENTION_BUDGET')
    return result


def compact_problem_impact(v,budget=BUDGETS['impact']):
    """Preserve scientific P0 status and per-claim identity under prose limits."""
    if not isinstance(v,dict) or jsize(v)<=budget:return v
    imp=v.get('problem_impact') or {}
    keep={k:imp[k] for k in ('state','original_problem_still_open',
             'still_unresolved_requirements','affected_requirements','validation_downgrade_reason') if k in imp}
    if 'reason' in imp:keep['reason']=_short(imp['reason'],850)
    if 'still_unresolved_requirements' in keep:
        keep['still_unresolved_requirements']=[_short(x,260) for x in keep['still_unresolved_requirements']]
    rows=[]
    for row in v.get('claim_to_problem',[]):
        if not isinstance(row,dict):continue
        z={k:row[k] for k in ('asset_id','relation_to_p0','evidence_ids',
                               'is_provisional_model_assessment','evidence_review_status') if k in row}
        for k in ('impact_on_solution','remaining_open_requirement'):
            if k in row:z[k]=_short(row[k],250)
        rows.append(z)
    out={'problem_impact':keep,'claim_to_problem':rows,
         'model_proposed_impact_state':v.get('model_proposed_impact_state'),
         'science_certification':False,'original_review_sha256':_digest(v),
         'model_attention_compacted_not_a_P0_conclusion':True}
    if jsize(out)>budget:
        out['claim_to_problem']=[{k:r[k] for k in ('asset_id','relation_to_p0','evidence_ids') if k in r}
                                  for r in rows]
    if jsize(out)>budget:
        raise RuntimeError('P0_STATUS_AND_CLAIM_REFERENCES_EXCEED_ATTENTION_BUDGET')
    return out

def compact_asset_attention(assets,budget=13000):
    """Prefer live derived science and multi-parent deltas to older repeated prose."""
    if not isinstance(assets,list):return assets,{}
    def score(a):
        return (2 if a.get('origin')=='LIVE_WORK' else 0) + (1 if a.get('parent_ids') else 0) + (1 if a.get('delta_from_parents') else 0)
    ordered=sorted(enumerate(assets),key=lambda it:(-score(it[1]),-it[0]))
    rows=[];used=2
    for _,a in ordered:
        row={'id':a.get('id'),'kind':a.get('kind'),'origin':a.get('origin'),
             'claim':_short(a.get('claim'),440),'predictions':[_short(q,190) for q in a.get('predictions',[])[:3]],
             'parent_ids':a.get('parent_ids',[]), 'source_ids':a.get('source_ids',[])[:12],
             'delta':_short(a.get('delta_from_parents'),250),'original_sha256':_digest(a)}
        n=jsize(row)+2
        if used+n>budget:continue
        rows.append(row);used+=n
    selected={a['id'] for a in rows}
    omitted=[a.get('id') for a in assets if a.get('id') not in selected]
    return rows,{'selected_ids':[a['id'] for a in rows],
       'unexpanded_ids':omitted,'all_ids_sha256':_digest([a.get('id') for a in assets]),
       'unexpanded_not_rejected':True,'all_original_claims_still_in_journal':True}


def compact_scientific_delta_handoff(v, budget=11000):
    """Bound nested V4 handoff without dropping any claim/evidence identity.

    Full model-authored scientific content stays in SAVED call blobs. The
    attention view preserves every identity/relation/citation, displays
    representative details, and explicitly labels unexpanded content.
    """
    if not isinstance(v,dict) or jsize(v)<=budget:return v
    result={k:v[k] for k in ('status','controller_decision','model_assessment_only',
        'original_problem_immutable','relevant_parent_asset_ids','research_instruction') if k in v}
    if 'working_problem_interpretation' in v:
        result['working_problem_interpretation']=slim_object(v['working_problem_interpretation'],1800)
    for name,keys in (
        ('novelty_claim_rows',('asset_id','relation','evidence_ids')),
        ('claim_to_original_problem',('asset_id','relation_to_p0','evidence_ids')),
        ('recent_prior_art_assessment_changes',('asset_id','change','previous_relation','current_relation'))):
        original=v.get(name,[])
        if isinstance(original,list):
            result[name]=[{k:r[k] for k in keys if k in r} for r in original if isinstance(r,dict)]
            result[name+'_all_rows_identified']=len(result[name])==len(original)
    result['original_handoff_sha256']=_digest(v)
    result['full_prose_in_original_controller_journal']=True
    # A few examples carry the explanatory content without allowing an entire
    # previous assessment to be recursively copied into every future prompt.
    candidate=v.get('novelty_claim_rows',[])
    if isinstance(candidate,list):
        details=[]
        for row in candidate:
            if not isinstance(row,dict):continue
            details.append({'asset_id':row.get('asset_id'),
                'residual_hypothesis':_short(row.get('residual_hypothesis'),220),
                'specific_differentiating_prediction':_short(row.get('specific_differentiating_prediction'),220),
                'decisive_test':_short(row.get('decisive_test'),180)})
            if len(details)>=3:break
        result['representative_scientific_details']=details
    if jsize(result)>budget:
        result.pop('representative_scientific_details',None)
    if jsize(result)>budget:
        result.pop('working_problem_interpretation',None)
        result['working_problem_interpretation_excluded_sha256']=_digest(v.get('working_problem_interpretation'))
    if jsize(result)>budget:
        raise RuntimeError('NESTED_HANDOFF_IDENTITIES_EXCEED_ATTENTION_BUDGET')
    return result


def compact_science_work_options(v,budget=13500):
    """Retain runnable Work contract; compact repeated inner advisory history."""
    if not isinstance(v,dict) or jsize(v)<=budget:return v
    out=dict(v)
    if 'v4_scientific_delta_handoff' in out:
        out['v4_scientific_delta_handoff']=compact_scientific_delta_handoff(
            out['v4_scientific_delta_handoff'],budget=11000)
    # Full active Work set is never pruned to manufacture scientific inactivity.
    active=out.get('active_scientific_work',[])
    if isinstance(active,list) and jsize(active)>20000:
        raise RuntimeError('ACTIVE_WORK_LIST_REQUIRES_EXPLICIT_PAGINATION')
    if jsize(out)>budget:
        if 'v4_research_readiness' in out:
            out['v4_research_readiness']=slim_object(out['v4_research_readiness'],1400)
    if jsize(out)>budget:
        raise RuntimeError('WORK_OPTIONS_WITH_LIVE_ACTIONS_EXCEED_ATTENTION_BUDGET')
    out['full_original_work_options_sha256']=_digest(v)
    out['source_work_options_model_advisory_not_new_evidence']=True
    return out


def bound_advisor_payload(payload,ident=None,max_chars=BUDGETS['all_controller']):
    """Bound huge repeated advisory rows for OPP/CTRL; preserve exact request digest.

    `CTRL_D...` can contain validated source opinions; their raw source remains
    in previous SAVED calls. The controller receives a referentially complete
    reduced *model view*, never a changed accepted journal record.
    """
    p=dict(payload)
    before=jsize(payload)
    # Reserve the *full* provenance receipt size before deciding whether a
    # model-facing view fits. Previously the receipt was added only after the
    # 86k-character attention check and could tip an otherwise valid view over
    # the limit. Use a conservative fixed-width placeholder for the final size
    # field, then replace it after the view is finalized. No scientific context
    # or reference is silently discarded to make room for a receipt.
    receipt={'version':VERSION,'original_payload_sha256':_digest(payload),
        'original_payload_chars':before,
        'model_attention_chars_before_receipt':max_chars,
        'view_is_derived_not_original_archive':True,
        'no_original_evidence_or_science_was_deleted':True}
    reserved=jsize({'science_memory_request_receipt':receipt})
    attention_limit=max_chars-reserved
    if attention_limit<=0:
        raise RuntimeError('MODEL_ATTENTION_BUDGET_TOO_SMALL_FOR_PROVENANCE_RECEIPT')
    field_bounds={
        'claim_prior_art_assessment':BUDGETS['claims'],
        'problem_level_impact':BUDGETS['impact'],
        'working_problem_state_before_decision':5000,
        'independent_opportunity_assessment':9000,
        'scientific_portfolio_frontier':8000,
        'scientific_portfolio_index':5500,
        'provisional_level_ii_candidate_dossiers':8000,
        'independent_peer_syn_portfolio':6500,
        'unreviewed_frontier_events':2300,
        'scientific_archive_manifest':1000,
        'previous_population_scientific_status':2800,
        'v4_scientific_delta_handoff':3500,
        'prior_program_reviews':2700,
        'objective_assessments':2700,
        'prior_art_delta':2700,
    }
    if 'claim_prior_art_assessment' in p:
        p['claim_prior_art_assessment']=compact_novelty_review(p['claim_prior_art_assessment'])
    if 'problem_level_impact' in p:
        p['problem_level_impact']=compact_problem_impact(p['problem_level_impact'])
    if 'v3_science_work_options' in p:
        p['v3_science_work_options']=compact_science_work_options(p['v3_science_work_options'])
    for k,cap in field_bounds.items():
        if k in ('claim_prior_art_assessment','problem_level_impact'):continue
        if k in p and jsize(p[k])>cap:p[k]=slim_object(p[k],cap)
    # Keep complete Controller decision IDs + action-ready Works; most cost is
    # in historic prose, not the primary Work proposal schema.
    if 'problems' in p and isinstance(p['problems'],list) and not p.get('problem_attention_info'):
        try:
            p['problems']=bound_problems(p['problems'])
        except RuntimeError as err:
            if str(err)!='PROBLEM_IDENTITIES_EXCEED_ATTENTION_BUDGET_NOT_SILENTLY_OMITTED':raise
            p['problems'],p['problem_attention_catalog']=page_problem_context(
                payload['problems'],active_problem_ids_from_payload(payload),BUDGETS['problems'])
    if jsize(p)>attention_limit:
        for k in ('scientific_portfolio_frontier','provisional_level_ii_candidate_dossiers',
                  'scientific_portfolio_index','independent_peer_syn_portfolio','assets',
                  'available_primary_sources',
                  'scientific_evidence_inventory','unreviewed_frontier_events'):
            if k in p and jsize(p)>attention_limit:
                if k=='assets' and isinstance(p[k],list):
                    p[k],p['asset_attention_detail']=compact_asset_attention(p[k],11000)
                else:p[k]=slim_object(p[k],max(1100,int(jsize(p[k])*0.4)))
    # Long-running sessions accumulate historical review prose independently of
    # Work options. Reduce *past commentary* before touching live Work IDs,
    # claim references or the original P0. Every excerpt is explicitly labeled
    # by slim_object, with the full original available in the Journal.
    if jsize(p)>attention_limit:
        for k,cap in (('prior_program_reviews',1200),
                      ('objective_assessments',1200),
                      ('research_capability_state',1000),
                      ('previous_population_scientific_status',1400),
                      ('portfolio_context',1000)):
            if k in p and jsize(p)>attention_limit and jsize(p[k])>cap:
                p[k]=slim_object(p[k],cap)
    # A very long original P0 is not trimmed; fail closed rather than transmit
    # an over-limit request or silently erase scientific context.
    # A further *referential* compaction pass is necessary on long-running
    # generations. Historical frontier prose and repeating asset-attention
    # indexes may consume a larger share than any individual field cap.
    # Never change original Journal, program P0, active Work contracts or the
    # exact claim-to-evidence IDs. The receipt below still hashes the ORIGINAL
    # (pre-compaction) payload, not this derived view.
    if jsize(p)>attention_limit:
        _original_asset_ids=[a.get('id') for a in payload.get('assets',[])] if isinstance(payload.get('assets'),list) else []
        for phase in (0,1,2):
            if jsize(p)<=attention_limit:break
            # A reduced asset index is a *view*. Full originals remain in E2.
            if isinstance(p.get('assets'),list):
                budget=(6500,3200,1200)[phase]
                slim_assets,_=compact_asset_attention(p['assets'],budget)
                p['assets']=slim_assets
                p['asset_attention_detail']={
                    'selected_ids':[a.get('id') for a in slim_assets],
                    'all_asset_ids_sha256':_digest(_original_asset_ids),
                    'all_original_assets_sha256':_digest(payload.get('assets',[])),
                    'all_original_asset_count':len(_original_asset_ids),
                    'not_in_view_count':max(0,len(_original_asset_ids)-len(slim_assets)),
                    'full_details_in_immutable_journal':True,
                    'not_in_view_does_not_mean_rejected':True,
                }
            # Only historical/repeated commentary and provenance inventories
            # are thinned; there is no filtering on a scientific hypothesis's
            # success, status or novelty judgment.
            refinements={
                'scientific_portfolio_frontier':(2500,1100,450),
                'scientific_portfolio_index':(1600,700,350),
                'provisional_level_ii_candidate_dossiers':(2300,1050,450),
                'independent_peer_syn_portfolio':(1700,800,400),
                'independent_cohort_history':(1000,600,350),
                'previous_population_scientific_status':(900,550,350),
                'scientific_evidence_inventory':(1000,550,350),
                'prior_program_reviews':(850,500,350),
                'objective_assessments':(850,500,350),
                'prior_art_delta':(1000,600,350),
                'problem_impact_delta':(950,500,350),
                'research_capability_state':(950,550,350),
                'portfolio_context':(1100,650,350),
                'working_problem_state_before_decision':(1650,850,450),
                'unreviewed_frontier_events':(800,450,300),
                'available_primary_sources':(650,350,250),
            }
            for key,caps in refinements.items():
                if jsize(p)<=attention_limit:break
                if key in p and jsize(p[key])>caps[phase]:
                    p[key]=slim_object(p[key],caps[phase])
            # All problem IDs + parent IDs are carried in the same array; the
            # entire P0 statement is retained in program.problem. Shrink
            # non-active per-problem question excerpts only if needed.
            if jsize(p)>attention_limit and isinstance(p.get('problems'),list):
                problem_cap=(17000,13000,10000)[phase]
                # Enforce the SAME TOTAL budget after accounting for catalog
                # metadata; never endlessly demand an impossible list encoding.
                was_paged='problem_attention_catalog' in p
                if was_paged:p.pop('problem_attention_catalog',None)
                if not was_paged:
                    try:
                        p['problems']=bound_problems(p['problems'],
                            active_ids=active_problem_ids_from_payload(payload),budget=problem_cap)
                    except RuntimeError as err:
                        if str(err)!='PROBLEM_IDENTITIES_EXCEED_ATTENTION_BUDGET_NOT_SILENTLY_OMITTED':raise
                        was_paged=True
                if was_paged:
                    # Always page from the original complete pre-advisor view;
                    # never treat a prior page as the full problem universe.
                    p['problems'],p['problem_attention_catalog']=page_problem_context(
                        payload['problems'],active_problem_ids_from_payload(payload),problem_cap)

    if jsize(p)>attention_limit:raise RuntimeError('MODEL_ATTENTION_BUDGET_UNSATISFIED_NO_SILENT_TRUNCATION')
    # The receipt has already been budgeted. Its exact content is invariant to
    # the original Journal or provider state and survives replay unchanged.
    receipt['model_attention_chars_before_receipt']=jsize(p)
    p['science_memory_request_receipt']=receipt
    if jsize(p)>max_chars:
        raise RuntimeError('MODEL_ATTENTION_RECEIPT_BUDGET_INVARIANT_BROKEN')
    return p



# A pre-compaction advisor input from V1.1 and the V1.2/V1.3 input can
# differ only in *declared provenance contract versions*. Those exact fields
# are not science, evidence, Work, or a learned assessment. Do not normalize
# arbitrary strings, source text, prompts, or unknown future contracts.
V1_1_CONTRACT='RETRIEVABLE_SCIENCE_MEMORY_AND_EXECUTED_TOOL_TRUTH_V1_1_20261030'
V1_2_CONTRACT='RETRIEVABLE_SCIENCE_MEMORY_AND_EXECUTED_TOOL_TRUTH_V1_2_20261030'


def normalized_provenance_version_candidate(payload, prior_version):
    """Return a provenance-only candidate for EXPLICIT digest equality proof.

    The candidate never reaches the LLM. It can authorize replay only when its
    SHA256 is IDENTICAL to the archived pre-compaction input SHA256.
    """
    if prior_version!=V1_1_CONTRACT or VERSION!=V1_2_CONTRACT:
        return None,[]
    if not isinstance(payload,dict):return None,[]
    candidate=copy.deepcopy(payload);changed=[]
    for field,key in (('science_memory_disclosure','version'),
                      ('verified_execution_provenance','contract')):
        record=candidate.get(field)
        if isinstance(record,dict) and record.get(key)==V1_2_CONTRACT:
            record[key]=V1_1_CONTRACT
            changed.append(field+'.'+key)
    return (candidate,changed) if changed else (None,[])


def replay_payload_for_saved(model_gateway, ident, actor, work_id, system, payload):
    """Recover only an *exact*, source-equivalent SAVED model request.

    In V1.1/V1.2, DurableModel.call received an unbounded payload when the call
    ID was already SAVED, even though the original request had been bounded.
    The hard wire-SHA guard rightly rejected this. This function proves that
    the ORIGINAL pre-compaction science input is exactly identical to the
    archived receipt, then replays the *recorded view*, not the changed view.
    No requests are created or responses reinterpreted; the E2 provider still
    verifies the full original request hash before providing SAVED bytes.

    If the scientific payload or prompt has changed, fail closed with an ID
    that can be audited; never overwrite/rename a paid call silently.
    """
    from e2core.core import EvidenceError
    state=model_gateway.j.verify()
    record=state.model_calls.get(ident)
    if record is None:return None
    if record.get('state')!='SAVED':
        raise EvidenceError('MODEL_CALL_NOT_SAVED_MANUAL_REVIEW:'+ident+':'+str(record.get('state')))
    wire=json.loads(model_gateway.j.raw(record['request_blob']))
    messages=wire.get('messages',[])
    if len(messages)!=2:
        raise EvidenceError('ARCHIVED_MODEL_WIRE_UNEXPECTED_SHAPE:'+ident)
    archived_system=messages[0].get('content')
    try:archived_payload=json.loads(messages[1]['content'])
    except (ValueError,TypeError,KeyError):
        raise EvidenceError('ARCHIVED_MODEL_PAYLOAD_NOT_JSON:'+ident)
    # The standard E2 provider owns the final immutable wire comparison.
    # These guards explain *why* replay is safe or unsafe before invoking it.
    if (record.get('actor')!=actor or record.get('work_id')!=work_id or
        wire.get('model')!=model_gateway.model or
        wire.get('max_tokens')!=model_gateway.max_tokens or
        wire.get('temperature')!=0.7 or
        archived_system!=system):
        raise EvidenceError('MODEL_REPLAY_CONTRACT_CHANGED:'+ident)
    if archived_payload==payload:
        return payload
    receipt=archived_payload.get('science_memory_request_receipt') if isinstance(archived_payload,dict) else None
    if actor=='CONTROLLER' and ident.startswith(('OPP_','CTRL_')) and isinstance(receipt,dict):
        original_sha=receipt.get('original_payload_sha256')
        if original_sha==_digest(payload):
            # Exact pre-compaction input: replay historical bytes at no cost.
            return archived_payload
        candidate,changed=normalized_provenance_version_candidate(payload,receipt.get('version'))
        if candidate is not None and original_sha==_digest(candidate):
            # Strong proof: the only differences are two whitelisted metadata
            # version indicators. The archived input and response are replayed
            # EXACTLY; neither the archive nor the current science is rewritten.
            return archived_payload
        normalized_sha=_digest(candidate) if candidate is not None else None
        raise EvidenceError('MODEL_REPLAY_SCIENCE_INPUT_CHANGED:'+ident+
            ':archived_original_sha='+str(original_sha)[:18]+
            ':current_raw_sha='+_digest(payload)[:18]+
            ':metadata_normalized_sha='+str(normalized_sha)[:18]+
            ':normalized_fields='+','.join(changed))
    raise EvidenceError('MODEL_REPLAY_SCIENCE_INPUT_CHANGED:'+ident+
        ':archived_request_sha='+str(record['request_blob'])[:18]+
        ':current_raw_sha='+_digest(payload)[:18])


@contextlib.contextmanager
def activate(mods):
    """Attach to existing Frontier V1 AFTER its overlay; restore on every exit."""
    import frontier_runtime as fr
    from e2core.provider import DurableModel
    import e2core.engine as engine
    original_worker_prompt=engine.WORKER_PROMPT
    orig_base=fr._research_context
    orig_call=DurableModel.call
    original_target=mods.spe.target_claims
    def scoped(base,state,selected,report):
        return bound_base(orig_base(base,state,selected,report),state)
    def target(context,j):
        out=original_target(context,j)
        s=j.verify();counts=Counter(x.get('work_id') for x in s.tool_results.values())
        for row in out:
            a=s.assets.get(row.get('id'),{})
            if a.get('kind') in ('FAILURE','SCOPED_NEGATIVE','LITERATURE_CLAIM') and not a.get('source_ids') and counts.get(a.get('work_id'),0)==0:
                row['unverified_model_execution_report']=True
                row['actual_tool_receipts_for_work']=0
                row['no_negative_inference_from_unexecuted_tool']=True
        return out
    def call(self,ident,actor,work_id,system,payload):
        # Replay is an exact archived-wire operation, never a new model view.
        # A previous SAVED OPP/CTRL may already have a compacted payload;
        # skipping compaction blindly is a bug, even if all science is unchanged.
        existing=self.j.verify().model_calls.get(ident)
        if existing is not None:
            payload=replay_payload_for_saved(self,ident,actor,work_id,system,payload)
        elif ident.startswith(('OPP_','CTRL_')) and actor=='CONTROLLER':
            payload=bound_advisor_payload(payload,ident)
        return orig_call(self,ident,actor,work_id,system,payload)
    try:
        fr._research_context=scoped
        mods.spe.target_claims=target
        DurableModel.call=call
        engine.WORKER_PROMPT=(original_worker_prompt + """
EXECUTION CONTRACT: A tool invocation is dispatched ONLY if a single valid
scientific JSON response has a non-null top-level tool_request with kind and
arguments. Standalone tool-shaped JSON blocks preceding scientific_text are
NOT executed. If no actual tool receipt exists, distinguish 'NOT EXECUTED'
from tool failure; neither is experimental evidence or scientific refutation.
Do not invent retrieved passages or claim a lookup was executed just because
it was written in prose. For actual tool feedback, emit a valid tool_request.
""")
        yield
    finally:
        fr._research_context=orig_base
        mods.spe.target_claims=original_target
        DurableModel.call=orig_call
        engine.WORKER_PROMPT=original_worker_prompt


def model_tool_contract_audit(j, limit=30):
    """Inspect saved WORK_STEP model text without treating written tool JSON as executed.

    Finds the exact failure mode observed in G13: standalone tool-shaped JSON
    *before* a final scientific response with tool_request null. This is a
    derived operational audit, not a retroactive change to the model answer.
    """
    import re
    s=j.verify();items=[]
    tool_prefix=re.compile(r'^\s*\{\s*"kind"\s*:\s*"(?:literature_research|literature_lookup|python_science|source_lookup)"',re.M)
    for wid,w in s.work.items():
        actual=sum(t.get('work_id')==wid for t in s.tool_results.values())
        for n,step in enumerate(w.get('steps',[]),1):
            if step.get('kind')!='MODEL_RESPONSE':continue
            try:
                record=json.loads(j.raw(step['raw_blob']))
                raw=record.get('text','')
            except (KeyError,ValueError,TypeError):continue
            if not isinstance(raw,str) or not tool_prefix.search(raw):continue
            # Candidate JSON objects in the model text; the submitted final
            # research object is the only one that can carry tool_request.
            decoder=json.JSONDecoder();candidate=[]
            for index,ch in enumerate(raw):
                if ch!='{':continue
                try:obj,end=decoder.raw_decode(raw,index)
                except (ValueError,TypeError):continue
                if isinstance(obj,dict) and isinstance(obj.get('scientific_text'),str):
                    candidate.append(obj)
            if len(candidate)!=1:continue
            obj=candidate[0]
            if obj.get('tool_request') is not None:continue
            prefix=raw.split('"scientific_text"',1)[0]
            if not tool_prefix.search(prefix):continue
            items.append({'work_id':wid,'record_step_index':n,
                'model_wrote_tool_shaped_preamble':True,
                'parsed_science_object_tool_request':None,
                'actual_tool_receipts_in_work':actual,
                'execution_proof':'ABSENT_IN_THIS_MODEL_RESPONSE',
                'provider_or_tool_backend_was_not_called_by_this_PREAMBLE':True,
                'journal_source_preserved':True})
    return items[-limit:]
