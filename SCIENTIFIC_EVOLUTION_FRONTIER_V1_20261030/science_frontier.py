"""Read-only, evidence-indexed science frontier views for existing E2 journals.

Never rewrites or reclassifies journal events. This is an attention/retrieval view,
not a scientific quality ranking or a novelty certification. It is intentionally
agnostic to the scientific domain (not specific to SERS).
"""
from __future__ import annotations
import hashlib, json, re
from collections import Counter, defaultdict

KIND_PRIORITY={'COUNTEREXAMPLE':5,'SCOPED_NEGATIVE':5,'NULL_MODEL':4,'PREDICTION':4,
               'HYPOTHESIS':3,'CALCULATION':3,'LITERATURE_CLAIM':2,'SUBPROBLEM':2,'FAILURE':2}
WORD=re.compile(r'[A-Za-z][A-Za-z0-9]{3,}')
STOP={'with','this','that','from','using','between','their','there','than','into','will','have',
      'been','which','does','were','under','such','only','when','also','more','model','hypothesis',
      'predictions','claim','scope','potential','different','research','evidence','observed'}

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def sha(x):return hashlib.sha256(canon(x)).hexdigest()
def size(x):return len(canon(x))
def short(x,n):
    x=str(x or '')
    return x if len(x)<=n else x[:n]+' … [EXCERPT; see original Journal by ID]'

def tags(a):
    content=str(a.get('claim',''))+' '+str(a.get('delta_from_parents',''))+' '+' '.join(map(str,a.get('predictions',[])[:2]))
    return set(w for w in WORD.findall(content.lower()) if w not in STOP)

def groups(assets):
    """Transparent, stable overlap clusters, used only for diversity of attention.

    No mechanistic truth, quality, or novelty is inferred from lexical similarity.
    """
    cluster=[];membership={}
    for aid,a in assets.items():
        terms=tags(a); best=(-1,None)
        for i,(cohort,prototype) in enumerate(cluster):
            if not terms or not prototype:continue
            sim=len(terms & prototype)/max(1,len(terms|prototype))
            if sim>best[0]:best=sim,i
        if best[0]>=0.17:
            k=best[1];cluster[k][0].append(aid)
            # No uncontrolled expansion of a cluster's prototype to generic words.
            cluster[k][1].update(sorted(terms)[:8])
        else:
            k=len(cluster);cluster.append(([aid],set(sorted(terms)[:12])))
        membership[aid]=k
    return membership,cluster

def select_assets(state, max_chars=29000):
    """Select verbatim science claims for LLM attention, not an evidence cutoff.

    Deterministic multi-lane selection: latest live, active Work parents,
    descendants/counterexamples, and cross-lineage representatives.
    Full corpus remains indexed and retrievable in the verified Journal.
    """
    assets=state.assets
    if not assets:return [],{'all_ids':[],'selected_ids':[],'omitted_ids':[],'index_sha256':sha([]),'note':'NO_ASSETS'}
    ids=list(assets); index={a:i for i,a in enumerate(ids)}
    membership,cluster=groups(assets)
    children=Counter(p for a in assets.values() for p in a.get('parent_ids',[]))
    priority=defaultdict(float);reason=defaultdict(list)
    def signal(aid,weight,label):
        if aid in assets:
            priority[aid]+=weight
            reason[aid].append(label)
    for aid,a in assets.items():
        if a.get('origin','LIVE_WORK')=='LIVE_WORK':signal(aid,70,'LIVE_WORK')
        if a.get('parent_ids'):signal(aid,10,'DERIVED')
        if len(a.get('parent_ids',[]))>=2:signal(aid,14,'MULTI_PARENT')
        if children[aid]:signal(aid,12+min(12,children[aid]),'HAS_DESCENDANTS')
        if a.get('kind') in ('COUNTEREXAMPLE','SCOPED_NEGATIVE','NULL_MODEL'):
            signal(aid,9,'STRONG_NULL_OR_NEGATIVE')
    for w in state.work.values():
        if w.get('status') in ('ACTIVE','QUEUED','DEFERRED'):
            for aid in w.get('asset_input_ids',[]):signal(aid,120,'ACTIVE_WORK_PARENT')
        for aid in w.get('published',[])[-5:]:signal(aid,30,'RECENT_WORK_OUTPUT')
    for i,aid in enumerate(ids):
        priority[aid]+=8*(i+1)/len(ids)
    # Initially favor a diverse representation, then fill with high-scoring assets.
    candidates=sorted(ids,key=lambda aid:(-priority[aid],-index[aid],aid))
    chosen=[];used=0;seen_groups=set()
    def add(aid):
        nonlocal used
        a=assets[aid]
        raw={'id':aid,'kind':a.get('kind'),'claim':a.get('claim'),'assumptions':a.get('assumptions'),
            'predictions':a.get('predictions',[]),'limitations':a.get('limitations',[]),'origin':a.get('origin','LIVE_WORK')}
        n=size(raw)
        if used+n>max_chars:return False
        chosen.append(aid);used+=n;seen_groups.add(membership[aid]);return True
    # live & active parents are important, but the chosen view remains budgeted
    for aid in candidates:
        if 'ACTIVE_WORK_PARENT' in reason[aid] or 'LIVE_WORK' in reason[aid]:add(aid)
    for aid in candidates:
        if aid not in chosen and membership[aid] not in seen_groups:add(aid)
    for aid in candidates:
        if aid not in chosen:add(aid)
    metadata={'all_ids':ids,'selected_ids':chosen,'omitted_ids':[x for x in ids if x not in chosen],
        'selected_reasons':{a:reason[a] for a in chosen},
        'claim_budget_chars':max_chars,'selected_claim_bytes':used,
        'index_sha256':sha([(a,assets[a].get('claim'),assets[a].get('parent_ids',[])) for a in ids]),
        'total_assets':len(ids), 'lexical_groups':len(cluster),'not_science_quality_or_novelty_rank':True,
        'journal_is_authoritative':True}
    return chosen,metadata

def catalog(state,selected, limit_chars=14000):
    """Compact representation of the full portfolio; never invent missing assets."""
    assets=state.assets; membership,clusters=groups(assets);selected=set(selected)
    rows=[]; n=0
    # Each group gets a lead, oldest source and most recent asset, when affordable.
    for k,(members,_) in enumerate(clusters):
        candidates=[m for m in members if m in selected]
        representative=(candidates[-1] if candidates else members[-1])
        a=assets[representative]
        entry={'group':k,'members':len(members),'representative_id':representative,
               'kind':a.get('kind'),'claim_excerpt':short(a.get('claim'),180),
               'has_live':any(assets[x].get('origin','LIVE_WORK')=='LIVE_WORK' for x in members),
               'full_ids_in_journal':members if len(members)<=4 else [members[0],members[-1]]}
        if n+size(entry)>limit_chars:break
        rows.append(entry);n+=size(entry)
    statuses=Counter(a.get('kind','UNKNOWN') for a in assets.values())
    return {'representation':'STRUCTURAL_CATALOG_WITH_EXACT_JOURNAL_REFERENCES',
            'authoritative_archive':'E2_APPEND_ONLY_JOURNAL',
            'total_assets':len(assets),'kinds':dict(statuses),'all_ids_sha256':sha(list(assets)),
            'all_group_count':len(clusters),'groups_shown':rows,
            'groups_omitted':len(clusters)-len(rows),
            'full_science_available_by_original_id':True,'selection_not_rejection':True,
            'archive_truth':'MODEL_PROPOSED_UNVERIFIED_UNLESS_EXPLICIT_EXECUTED_SOURCE'}

def frontier(state, selected, max_rows=32):
    assets=state.assets;selected_set=set(selected)
    items=[]
    for w in state.work.values():
        p=w.get('asset_input_ids',[])
        items.append({'id':w['id'],'status':w['status'],'mode':w.get('mode'),
            'operation':w.get('operation'),'question':short(w.get('question'),350),
            'parent_ids':p,'published':w.get('published',[]),'steps':len(w.get('steps',[])),
            'reason_not_a_quality_certificate':True})
    history=[]
    for a in list(assets.values())[::-1]:
        if a['id'] not in selected_set:continue
        if a.get('parent_ids') or a.get('kind') in ('COUNTEREXAMPLE','NULL_MODEL','SCOPED_NEGATIVE','PREDICTION'):
            history.append({'id':a['id'],'kind':a.get('kind'),'parents':a.get('parent_ids',[]),
                            'delta':short(a.get('delta_from_parents'),290),
                            'claim':short(a.get('claim'),250),
                            'source_ids':a.get('source_ids',[])[:6]})
        if len(history)>=max_rows:break
    return {'active_work':[w for w in items if w['status'] in ('ACTIVE','QUEUED','DEFERRED')],
            'recent_scientific_changes':history,
            'total_work':len(items),'work_status_counts':dict(Counter(w['status'] for w in items)),
            'historical_not_presented_as_experimental_fact':True,
            'science_vs_operations':'Retrieval failure / invalid JSON is not a scoped scientific negative'}

def compact_state(problem_state,selected,root):
    selected=set(selected)
    c=problem_state.get('current_claim_assessments',{})
    slim={a:v for a,v in c.items() if a in selected}
    hist=problem_state.get('historical_source_assessment')
    # Previous ledger remains fully reconstructable from committed Controller prompts.
    h={'present':hist is not None,'original_ledger_sha256':sha(hist) if hist else None,
       'read_original':'historical source records and committed Controller prompts in '+str(root)}
    return {**problem_state,'current_claim_assessments':slim,
        'historical_source_assessment':h,
        'scientific_attention_scope':{'selected':sorted(selected),'model_assessments_in_scope':len(slim),
           'model_assessments_out_of_scope':len(c)-len(slim),
           'full_ledger_unchanged_in_journal':True},
        'claim_relation_changes':[v for v in problem_state.get('claim_relation_changes',[])
             if v.get('asset_id') in selected][-16:],
        'historical_problem_status_changes':problem_state.get('historical_problem_status_changes',[])[-8:]}

def cap_evidence(records,selected_sources,limit_chars=17000):
    enumerated=list(enumerate(records))
    def key(item):
        pos,rec=item;cls=str(rec.get('inspection_class',''))
        return (0 if rec.get('evidence_id') in selected_sources else 1,
                0 if ('FULLTEXT' in cls or 'DIRECT' in cls or 'OA_PDF' in cls) else 1,
                -pos)
    chosen=[];n=0;skipped=[]
    for i,r in sorted(enumerated,key=key):
        view=r
        # Long real source excerpts may be surfaced in a bounded first passage
        # rather than silently omitted entirely; original source remains linked.
        if size(r)>3500 and isinstance(r.get('returned_content'),str):
            view={**r,'returned_content':short(r['returned_content'],2600),
                  'original_record_sha256':sha(r),
                  'content_truncated_for_model_attention_not_for_archive':True}
        if n+size(view)<=limit_chars:
            chosen.append(view);n+=size(view)
        else:skipped.append(r.get('evidence_id'))
    return chosen,{'full_source_count':len(records),'present_source_count':len(chosen),
       'unpresented_evidence_ids':skipped,'all_evidence_index_sha256':sha([r.get('evidence_id') for r in records]),
       'unpresented_evidence_is_not_negative_result':True,
       'original_executed_tool_receipts_remain_in_journal':True}


def redact_model_context(x,max_chars=45000):
    """Drop only oversized *derived context*, with a disclosure and archival pointer.
    Never called on authoritative Journal data or committed science assets.
    """
    if size(x)<=max_chars:return x
    if isinstance(x,dict):
        # Preserve fields more likely to affect science/operations. Avoid silent truncation.
        out={};lost=[]
        for k,v in x.items():
            if k in {'program','problems','frontier','works','active_work','status','source_head','P0_sha256'}:
                out[k]=v
            elif size(out)+size({k:v})<=max_chars-3000:
                out[k]=v
            else:lost.append({'field':k,'sha256':sha(v),'bytes':size(v)})
        out['derived_context_omissions']={'fields':lost,'reason':'MODEL_ATTENTION_WINDOW_NOT_SOURCE_DELETION',
            'original_preserved':'Journal / associated cycle files'}
        return out
    return {'original_sha256':sha(x),'bytes':size(x),'read_original':'Journal'}

def candidate_dossiers(state,selected,limit=12):
    """Parent-vs-child review packets, not automated Level-II verdicts."""
    assets=state.assets;rows=[]
    for aid in selected:
        a=assets[aid]
        if a.get('kind') not in ('HYPOTHESIS','PREDICTION','NULL_MODEL','COUNTEREXAMPLE','CALCULATION'):
            continue
        parents=[assets[p] for p in a.get('parent_ids',[]) if p in assets]
        row={'candidate_id':aid,'kind':a.get('kind'),
           'candidate_claim':short(a.get('claim'),580),
           'conditional_assumptions':short(a.get('assumptions'),300),
           'predictions':[short(p,260) for p in a.get('predictions',[])[:4]],
           'limitations':[short(p,220) for p in a.get('limitations',[])[:4]],
           'parent_claims':[{'id':p['id'],'claim':short(p.get('claim'),300)} for p in parents],
           'claimed_scientific_delta':short(a.get('delta_from_parents'),420),
           'registered_source_ids':a.get('source_ids',[]),
           'review_questions':{
               'new_causal_content':'What exact causal mechanism differs from cited parent hypotheses and established literature?',
               'strongest_null':'Which physically plausible strong null can reproduce the same predicted observables?',
               'distinct_test':'What observable/intervention falsifies this proposal under matched nuisance assumptions?',
               'physical_feasibility':'Are parameters and conditions physically defensible and supported by real calculations?',
               'novelty':'What published work already implies the same causal prediction?'},
           'level_ii_qualification':'NOT_CERTIFIED_REQUIRES_INDEPENDENT_SCIENTIFIC_REVIEW',
           'executed_tool_result_is_not_implied_by_asset_kind':True}
        rows.append(row)
    # Prefer actual derived hypotheses and predicted discriminators, yet do not
    # claim unused/omitted hypotheses are scientifically worse.
    rows.sort(key=lambda r:(len(r['parent_claims'])>0,len(r['predictions'])>0,
                             r['kind']=='HYPOTHESIS'),reverse=True)
    return rows[:limit]
