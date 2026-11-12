"""M29.5 optional, new-root-only science-decision provenance contract.

Guarantees provenance of prior-art comparison and explicit coverage of pending
calculation and organization choices. Does NOT certify novelty, choose science,
force execution, or silently repair/modify model authored decisions.
"""
from __future__ import annotations
import json
from pathlib import Path
from .core import EvolutionJournal, EvidenceError, guard, sha, canon

FLAG = 'm295_prior_art_and_decision_review_required'
MARKER = 'M295_SOURCE_PINNED_SCIENCE_DECISION_CONTRACT_ACTIVATED'

PRELUDE = '''M29.5 PRIOR-ART AND SCIENTIFIC CHOICE AUDIT (NEW explicitly opted-in M28 root):
The distinction between a TENTATIVE RESEARCH PROBLEM and a verified novel
scientific contribution is mandatory. Never certify novelty from a failed search.
For EVERY newly declared typed research_frontier, also supply a nonempty
new_problem.m295_interventions list identifying the separate EXPERIMENT and
CALCULATION tests inside the frontier:
[{"id":"T_unique", "kind":"EXPERIMENT|CALCULATION",
  "method_or_observation":"concrete intervention or calculation",
  "distinguishing_claim":"specific hypothesis contrast tested"}].
A single Problem can contain five such tests; do not equate tests with ROOTS.

Before registering NEW typed research_frontier or terminal HOLD, author
prior_art_assessments[] with exactly one entry per relevant frontier; each
entry must individually compare EVERY listed intervention. On a HOLD audit all
OPEN typed frontiers, including those created by Workers, not only the one
selected in research_frontier_assessment. Research may be proposed
provisionally before literature becomes accessible, but NEVER assert its
novelty or treat it as a confirmed experiment plan without evidence-backed
comparison. An older paper using the same method
may still leave a new falsifiable mechanistic contrast; separate METHOD novelty
from PROBLEM/CONTRAST novelty and value of replication or disconfirmation.

prior_art_assessments entry:
{"problem_id":"P_existing_or_new",
 "coverage_explanation":"how individual experiments/calculations were separated",
 "intervention_reviews":[
   {"id":"T_unique", "kind":"EXPERIMENT|CALCULATION",
    "status":"REVIEWED|LIMITED_SEARCH|NOT_REVIEWED",
    "contribution_class":"PRECEDED|REPLICATION|POTENTIALLY_DISTINCT|UNCERTAIN",
    "compared_sources":[{"source_id":"SRC_EXISTING_TOOL_RESULT",
      "what_prior_work_tested":"specific demonstrated prior result or scope",
      "remaining_delta":"specific distinction, not absolute novelty",
      "evidence_level":"METADATA|FULL_TEXT"}],
    "attempted_tool_ids":["TOOL_EXISTING_LITERATURE_RESEARCH"],
    "search_limitations":"scope and access limitations",
    "scientific_value":"reason for novelty, replication, rebuttal or deferral"}
 ]}.
Bind each review to the original, REGISTERED intervention ID and kind. The
registered m295_interventions item is the canonical identity: do not restate
method_or_observation or distinguishing_claim in intervention_reviews. Explain
your literature comparison and the precise scope of any differences in
scientific_value and compared_sources[].remaining_delta. A changed hypothesis,
observable, or intervention must be proposed as a NEW candidate, not silently
substituted under an existing ID. Older responses that echo those fields can
be read for audit, but their text never overwrites the registered definition.
Any echo disagreement remains an explicitly flagged unverified scope difference;
it cannot establish novelty or scientific equivalence automatically.
NOT_REVIEWED: no source/attempt, class UNCERTAIN; this item is a PROVISIONAL
candidate, not a novelty-verified experiment or confirmed scientific result. LIMITED_SEARCH: cite real past literature tool
attempt(s), class UNCERTAIN; do not infer novelty from access failure.
REVIEWED: at least one actually registered literature source and a specific
contrast (metadata-only citations support only tentative interpretation).
Do NOT invent source IDs or tool IDs; use the supplied source index and your
real Journal history. No available references? Explicitly state NOT_REVIEWED
and why; you may choose to delegate literature retrieval before HOLD.

For HOLD_WITH_RATIONALE author remaining_calculation_assessments[] covering
ALL existing/new open typed frontiers with CALCULATION=NOT_ATTEMPTED:
{"problem_id":"P...", "decision":"DEFER|REDUNDANT|NOT_FEASIBLE",
 "information_value":"what an actual calculation could discriminate",
 "reason":"science-specific reason for not executing now",
 "missing_inputs":"specific missing data/resources, or 'none'"}.
This is an assessment, not a duty to execute every calculation. Choosing to
perform such a calculation calls for an ONGOING decision with real Work instead
of a terminal HOLD.

On a meaningful choice point (multiple proposed Work actions, new typed
frontier, organizational request, or terminal HOLD), explicitly author
organization_choice_assessment:
{"choice":"SPAWN_NEW_ROOT|LOCAL_WORK|DEFER_INDEPENDENT",
 "independence_value":"whether independent replication/criticism helps",
 "overlap_or_cost":"potential overlap, synchronization, or cost",
 "rationale":"why this organization is scientifically appropriate"}.
SPAWN_NEW_ROOT requires real organization_requests; any nonempty
organization_requests requires SPAWN_NEW_ROOT. NO fixed minimum number of roots.
These are model-authored, unverified rationales, NOT science certification.
'''


def _text(x):
    return isinstance(x, str) and bool(x.strip())


def _experiment(j):
    # Rootless test doubles/legacy views are not source-pinned M29.5 roots.
    # Do not require a path attribute unless an actual research root exists.
    journal_root = getattr(j, 'root', None)
    if journal_root is None:
        return None
    root = Path(journal_root)
    return root.parent.parent if root.parent.name == 'ROOTS' else None


def _flags(exp):
    p, m = exp/'persistent.json', exp/'meta_research.json'
    if not p.is_file() or not m.is_file():
        return None, None
    persistent=json.loads(p.read_text(encoding='utf8'))
    meta=json.loads(m.read_text(encoding='utf8'))
    return persistent.get(FLAG), meta.get(FLAG)


def active(j):
    exp=_experiment(j)
    if exp is None:return False
    left,right=_flags(exp)
    if left is None and right is None:return False
    guard(left is True and right is True, 'M295_MANIFEST_FLAG_DRIFT')
    pin = exp/'NATIVE_RUNTIME_SOURCE_PIN.json'
    guard(pin.is_file() and not pin.is_symlink(), 'M295_SOURCE_PIN_MISSING')
    primary=EvolutionJournal(exp/'ROOTS'/'PRIMARY')
    s=primary.verify()
    meta=json.loads((exp/'meta_research.json').read_text(encoding='utf8'))
    guard(meta.get('root')==str(exp) and
          meta.get('initial_root')==str(exp/'ROOTS'/'PRIMARY') and
          sha(s.program['problem'].encode('utf8'))==meta.get('original_P0_sha256'),
          'M295_PROGRAM_IDENTITY_MISMATCH')
    markers=[e['payload'] for e in primary._events() if e['kind']=='OPERATIONAL_PAUSE'
             and e['payload'].get('reason')==MARKER]
    guard(len(markers)==1, 'M295_MARKER_MISSING_OR_DUPLICATE')
    mark=markers[0]
    guard(mark.get('source_pin_sha256')==sha(pin.read_bytes()) and
          mark.get('original_P0_sha256')==meta['original_P0_sha256'] and
          mark.get('science_certification') is False,
          'M295_MARKER_PROVENANCE_INVALID')
    local=j.verify()
    guard(local.meta_collaboration and local.meta_research_autonomy and
          local.program['problem']==s.program['problem'],
          'M295_CHILD_PROGRAM_OR_POLICY_INVALID')
    return True


def register_new_root(j):
    exp=_experiment(j)
    guard(exp is not None and Path(j.root).name=='PRIMARY',
          'M295_ACTIVATE_NEW_PRIMARY_ONLY')
    left,right=_flags(exp)
    guard(left is True and right is True, 'M295_NEW_ROOT_NOT_OPTED_IN')
    guard(not any(e['kind']=='OPERATIONAL_PAUSE' and
                  e['payload'].get('reason')==MARKER for e in j._events()),
          'M295_MARKER_ALREADY_EXISTS')
    pin=exp/'NATIVE_RUNTIME_SOURCE_PIN.json'
    guard(pin.is_file() and not pin.is_symlink(), 'M295_NO_SOURCE_PIN')
    s=j.verify()
    j.append('OPERATIONAL_PAUSE',{
        'reason':MARKER,'source_pin_sha256':sha(pin.read_bytes()),
        'original_P0_sha256':sha(s.program['problem'].encode('utf8')),
        'science_certification':False, 'not_a_scientific_decision':True})
    guard(active(j),'M295_ACTIVATION_POSTCHECK_FAILED')


def literature_source_index(j):
    """Source pointers, not full documents; preserve all IDs and evidence classes."""
    s=j.verify()
    records=[]
    for sid,src in s.sources.items():
        if src.get('kind')!='TOOL_RESULT':continue
        obj=json.loads(j.raw(src['blob']))
        req=obj.get('request',{})
        if req.get('kind') not in ('literature_research','literature_lookup'):continue
        result=obj.get('result',{})
        if not isinstance(result,dict):result={}
        records.append({'source_id':sid,'work_id':src.get('work_id'),
            'evidence_class':obj.get('evidence_class',result.get('evidence_class')),
            'result_status':result.get('status'),
            'action':(req.get('arguments',{}) if isinstance(req.get('arguments'),dict) else {}).get('action'),
            'title':str(result.get('title',''))[:140],
            'pmcid':result.get('pmcid'),'doi':result.get('doi'),
            'source_sha256':obj.get('full_document_sha256')})
    return records


def _checked_source(j, state, item):
    sid=item['source_id']
    guard(sid in state.sources,'M295_PRIOR_ART_SOURCE_NOT_REGISTERED')
    src=state.sources[sid]
    guard(src['kind']=='TOOL_RESULT','M295_PRIOR_ART_SOURCE_NOT_TOOL_EVIDENCE')
    obj=json.loads(j.raw(src['blob']))
    req=obj.get('request',{})
    result=obj.get('result',{})
    guard(req.get('kind') in ('literature_lookup','literature_research') and
          isinstance(result,dict) and result.get('status')=='DELIVERED',
          'M295_PRIOR_ART_SOURCE_NOT_DELIVERED_LITERATURE')
    evidence=obj.get('evidence_class',result.get('evidence_class',''))
    if item['evidence_level']=='FULL_TEXT':
        guard(evidence=='OA_FULLTEXT_TEXT','M295_FULLTEXT_NOT_ACTUALLY_READ')
    else:
        guard(item['evidence_level']=='METADATA', 'M295_BAD_EVIDENCE_LEVEL')
    return evidence


def _checked_literature_tool(j,state,tid):
    guard(tid in state.tool_results,'M295_SEARCH_TOOL_ID_UNKNOWN')
    tool=state.tool_results[tid]
    req=json.loads(j.raw(tool['request_blob']))
    guard(req.get('kind') in ('literature_lookup','literature_research'),
          'M295_SEARCH_TOOL_NOT_LITERATURE')


def _frontier_calc_pending(problem):
    if not isinstance(problem,dict) or problem.get('status')=='CLOSED':return False
    f=problem.get('research_frontier')
    return isinstance(f,dict) and any(
        isinstance(e,dict) and e.get('kind')=='CALCULATION' and
        e.get('acquisition_state')=='NOT_ATTEMPTED'
        for e in f.get('required_evidence',[]))


def validate_decision(j,state,raw,prepared_problems):
    """Validate authored choices in memory before CONTROLLER_DECISION is committed.

    Does not launch literature tools, alter the Journal, or infer science.
    """
    if not active(j):return None
    new={p['id']:p for p in prepared_problems if isinstance(p,dict) and
         isinstance(p.get('id'),str)}
    newfront={pid for pid,p in new.items() if isinstance(p.get('research_frontier'),dict)}
    hold=raw['disposition']=='HOLD_WITH_RATIONALE'
    frontier=raw.get('research_frontier_assessment',{}) if hold else {}
    linked=[]
    if isinstance(frontier,dict) and frontier.get('status')=='LINKED_EXISTING':
        linked=[pid for pid in frontier.get('problem_ids',[]) if pid in state.problems and
                isinstance(state.problems[pid].get('research_frontier'),dict)]
    # A terminal HOLD is a program-wide scientific decision and must cover
    # ALL open typed frontiers. During ONGOING, a scientist may ALSO voluntarily
    # review an existing open typed frontier. Such an extra review is evidence,
    # not an unauthorized new Problem or a reason to reject the decision.
    open_existing={pid for pid,p in state.problems.items()
                   if p.get('status')!='CLOSED' and
                   isinstance(p.get('research_frontier'),dict)}
    required=newfront|set(linked)
    if hold:
        required.update(open_existing)
    for pid in newfront:
        tests=new[pid].get('m295_interventions')
        guard(isinstance(tests,list) and bool(tests),
              'M295_NEW_FRONTIER_INTERVENTIONS_REQUIRED')
        ids=[]
        for t in tests:
            guard(isinstance(t,dict) and
                  set(t)=={'id','kind','method_or_observation','distinguishing_claim'} and
                  _text(t['id']) and t['kind'] in {'EXPERIMENT','CALCULATION'} and
                  _text(t['method_or_observation']) and
                  _text(t['distinguishing_claim']),
                  'M295_INTERVENTION_INVENTORY_INVALID')
            ids.append(t['id'])
        guard(len(ids)==len(set(ids)), 'M295_INTERVENTION_INVENTORY_DUPLICATE')
    prior=raw.get('prior_art_assessments')
    if required:
        guard(isinstance(prior,list),'M295_PRIOR_ART_ASSESSMENTS_REQUIRED')
    elif prior is None:
        prior=[]
    guard(isinstance(prior,list),'M295_PRIOR_ART_NOT_ARRAY')
    ids=[p.get('problem_id') for p in prior if isinstance(p,dict)]
    supplied=set(ids) if all(isinstance(x,str) for x in ids) else set()
    # HOLD: full exact open-frontier coverage. ONGOING: new-frontier coverage
    # remains mandatory, while an EXTRA review is accepted only for an existing
    # OPEN typed frontier. Unknown/closed/non-frontier IDs remain rejected.
    coverage_ok=(supplied==required if hold else
                 required.issubset(supplied) and
                 supplied.issubset(newfront|open_existing))
    guard(len(ids)==len(prior) and len(supplied)==len(ids) and coverage_ok,
          'M295_PRIOR_ART_COVERAGE_MISMATCH')
    registration_status={}
    review_scope_binding={}
    for p in prior:
        guard(set(p)=={'problem_id','coverage_explanation','intervention_reviews'} and
              _text(p['coverage_explanation']) and
              isinstance(p['intervention_reviews'],list) and
              bool(p['intervention_reviews']),
              'M295_PRIOR_ART_SCHEMA')
        pid=p['problem_id']
        known_problem=new.get(pid, state.problems.get(pid,{}))
        inventory=known_problem.get('m295_interventions')
        proposed=p['intervention_reviews']
        check_ids=[i.get('id') for i in proposed if isinstance(i,dict)]
        guard(len(check_ids)==len(proposed) and
              len(check_ids)==len(set(check_ids)),
              'M295_INTERVENTION_REVIEW_DUPLICATES')
        if inventory is not None:
            guard(set(check_ids)=={i['id'] for i in inventory},
                  'M295_INTERVENTION_PRIOR_ART_COVERAGE_MISMATCH')
        # Older existing frontiers can lack the M29.5 intervention inventory.
        # Their volunteered ONGOING review is accepted as explicitly model-
        # authored, but its SEMANTIC completeness is NOT mechanically verified.
        # Newly authored frontiers always carry a mandatory exact inventory.
        levels=[]
        scope_states={}
        for item in proposed:
            # An intervention is identified by its immutable, registered ID
            # and kind. Repeating its full scientific description in a review
            # invited paraphrase errors, without adding a new identity check.
            compact={'id','kind','status','contribution_class','compared_sources',
                     'attempted_tool_ids','search_limitations','scientific_value'}
            legacy=compact|{'method_or_observation','distinguishing_claim'}
            fields=set(item) if isinstance(item,dict) else set()
            guard(fields in (compact,legacy) and
                item['kind'] in {'EXPERIMENT','CALCULATION'} and
                all(_text(item[k]) for k in ('id','search_limitations','scientific_value')) and
                (fields!=legacy or all(_text(item[k]) for k in (
                    'method_or_observation','distinguishing_claim'))) and
                item['status'] in {'REVIEWED','LIMITED_SEARCH','NOT_REVIEWED'} and
                item['contribution_class'] in {'PRECEDED','REPLICATION',
                    'POTENTIALLY_DISTINCT','UNCERTAIN'},
                'M295_PRIOR_ART_ITEM_FIELDS_INVALID')
            if inventory is not None:
                declared=next(x for x in inventory if x['id']==item['id'])
                guard(item['kind']==declared['kind'],
                      'M295_INTERVENTION_REVIEW_KIND_CHANGED')
                # Legacy echo is non-authoritative commentary, NOT a mutation
                # of the registered hypothesis. Never infer semantic sameness
                # from a text-similarity score or a model assertion.
                drift=[k for k in ('method_or_observation','distinguishing_claim')
                       if fields==legacy and item[k]!=declared[k]]
                if drift and item['contribution_class']!='UNCERTAIN':
                    raise EvidenceError('M295_SCOPE_DRIFT_CANNOT_SUPPORT_NOVELTY_CLASS')
                scope_states[item['id']]={
                    'binding':'REGISTERED_ID_AND_KIND',
                    'authoritative_registered_intervention':dict(declared),
                    'echo_status':('LEGACY_ECHO_DIFFERS_UNVERIFIED' if drift else
                                   'LEGACY_ECHO_EXACT' if fields==legacy else
                                   'CANONICAL_ID_REFERENCE_NO_ECHO'),
                    'echo_disagreement_fields':drift,
                    'semantic_equivalence_not_certified':True}
            else:
                # Older Problems can lack the M29.5 inventory. Preserve their
                # fallible reviews without falsely claiming full coverage.
                guard(fields==legacy,'M295_LEGACY_WITHOUT_INVENTORY_NEEDS_SCOPE')
                scope_states[item['id']]={
                    'binding':'LEGACY_NO_REGISTERED_INVENTORY',
                    'echo_status':'MODEL_AUTHORED_SCOPE_UNVERIFIED',
                    'semantic_equivalence_not_certified':True}
            comps=item['compared_sources'];attempts=item['attempted_tool_ids']
            guard(isinstance(comps,list) and isinstance(attempts,list) and
                  len(attempts)==len(set(attempts)),
                  'M295_PRIOR_ART_REFERENCES_INVALID')
            for t in attempts:_checked_literature_tool(j,state,t)
            for c in comps:
                guard(isinstance(c,dict) and set(c)=={'source_id',
                    'what_prior_work_tested','remaining_delta','evidence_level'} and
                    _text(c['what_prior_work_tested']) and _text(c['remaining_delta']),
                    'M295_PRIOR_ART_COMPARISON_FIELDS')
                _checked_source(j,state,c)
            guard(len({c['source_id'] for c in comps})==len(comps),
                  'M295_PRIOR_ART_DUPLICATE_SOURCE')
            if item['status']=='REVIEWED':
                guard(bool(comps),'M295_REVIEWED_REQUIRES_REAL_SOURCE')
            elif item['status']=='LIMITED_SEARCH':
                guard(bool(attempts) and item['contribution_class']=='UNCERTAIN',
                      'M295_LIMITED_SEARCH_REQUIRES_TRACE_AND_UNCERTAINTY')
            else:
                guard(not comps and not attempts and item['contribution_class']=='UNCERTAIN',
                      'M295_NOT_REVIEWED_CANNOT_ASSERT_NOVELTY')
            if item['contribution_class']!='UNCERTAIN':
                guard(item['status']=='REVIEWED',
                      'M295_NOVELTY_CLASS_WITHOUT_PRIOR_ART')
                guard(any(c['evidence_level']=='FULL_TEXT' for c in comps),
                      'M295_NONUNCERTAIN_REQUIRES_FULLTEXT_COMPARISON')
            levels.append('CANDIDATE_PRIOR_ART_COMPARED_UNCERTIFIED'
                          if item['status']=='REVIEWED'
                          else 'PROVISIONAL_NOVELTY_UNVERIFIED')
        registration_status[pid]={
           item['id']:level for item,level in zip(proposed,levels)}
        review_scope_binding[pid]=scope_states

    # Scope calculation review to all OPEN typed frontiers, not just the one
    # selected in research_frontier_assessment (which might omit old obligations).
    problems={**state.problems,**new}
    pending={pid for pid,p in problems.items() if _frontier_calc_pending(p)}
    calcs=raw.get('remaining_calculation_assessments')
    if hold:
        guard(isinstance(calcs,list),'M295_HOLD_CALC_ASSESSMENT_REQUIRED')
    elif calcs is None:calcs=[]
    guard(isinstance(calcs,list),'M295_CALC_ASSESSMENT_NOT_ARRAY')
    calcids=[c.get('problem_id') for c in calcs if isinstance(c,dict)]
    guard(len(calcids)==len(calcs) and len(set(calcids))==len(calcids) and
          (set(calcids)==pending if hold else not calcids),
          'M295_PENDING_CALC_COVERAGE_MISMATCH')
    for c in calcs:
        guard(set(c)=={'problem_id','decision','information_value','reason','missing_inputs'} and
              c['decision'] in {'DEFER','REDUNDANT','NOT_FEASIBLE'} and
              all(_text(c[k]) for k in ('information_value','reason','missing_inputs')),
              'M295_PENDING_CALC_JUSTIFICATION_INVALID')

    org_requests=raw.get('organization_requests',[])
    meaningful=hold or bool(newfront) or len(raw.get('actions',[]))>=2 or bool(org_requests)
    org=raw.get('organization_choice_assessment')
    if meaningful:guard(isinstance(org,dict),'M295_ORG_CHOICE_REQUIRED')
    if org is not None:
        guard(isinstance(org,dict) and
              set(org)=={'choice','independence_value','overlap_or_cost','rationale'} and
              org.get('choice') in {'SPAWN_NEW_ROOT','LOCAL_WORK','DEFER_INDEPENDENT'} and
              all(_text(org.get(k)) for k in ('independence_value','overlap_or_cost','rationale')),
              'M295_ORG_CHOICE_FIELDS')
        guard((org['choice']=='SPAWN_NEW_ROOT')==bool(org_requests),
              'M295_ORG_CHOICE_REQUEST_CONTRADICTION')
    return {'prior_art_assessments':prior,
            'intervention_registration_status':registration_status,
            'intervention_review_scope_binding':review_scope_binding,
            'remaining_calculation_assessments':calcs,
            'organization_choice_assessment':org,
            'scientific_certification':False,
            'novelty_not_guaranteed':True}
