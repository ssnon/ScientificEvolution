"""Native, opt-in recursive math reviews with V1.1 Controller-selected claims.

No mathematical result is certified by this module. It schedules independent
VERIFY Work for *newly published* mathematical Assets, including mathematical
Assets authored by VERIFY Workers, and returns grounded review feedback to a
new INFORMED reassessment Work. Every action uses existing EVOLUTION_APPLIED /
WORK_STEP Journal events, so it is a real science Work, not a mock verdict.

The queue has no scientific-depth cap: it stops growing when a reviewer returns
an assessment without publishing a NEW mathematical Asset. Operational paid
budgets remain separate. Original FRESH Workers and immutable historical roots
are unaffected unless an OPERATOR opt-in source is registered in a NEW root.
"""
from __future__ import annotations
import hashlib
import json

PROTOCOL='NATIVE_MATH_VERIFICATION_CYCLE_V1'
POLICY_ID='SRC_NATIVE_MATH_VERIFICATION_CYCLE_V1'
VERIFY_REASON='NATIVE_MATH_VERIFY_V1_SUBJECT='
REASSESS_REASON='NATIVE_MATH_REASSESS_V1_SUBJECT='
DEFAULT_KINDS=frozenset({'CALCULATION','COUNTEREXAMPLE'})
VERDICTS=frozenset({'SUPPORTED','SUPPORTED_WITH_CONDITIONS','CHALLENGED','REFUTED','INDETERMINATE'})

VERIFIER_ADDENDUM='''
NATIVE INDEPENDENT MATH VERIFIER (case-specific assigned Work, not a science certificate):
- Independently derive or challenge the target parent's mathematical claim, including assumptions, boundary cases and measurement/observation model.
- An earlier claim is NOT correct because its author or other reviewers accepted it; decide independently. Tool execution is optional; do not invent computations.
- Report your verdict in an additional top-level JSON field:
  "math_review":{"verdict":"SUPPORTED|SUPPORTED_WITH_CONDITIONS|CHALLENGED|REFUTED|INDETERMINATE","reason":"specific evidence and limits","performed_checks":["..."],"unresolved":["..."]}.
- When you can assess the parent's claim without making a new independent mathematical claim, return assets:[]. Your review text and original model output are retained in the Journal and handed to the original researcher's reassessment Work.
- If you DO introduce a new mathematical claim, counterexample, derivation, or correction, publish it as a normal CALCULATION or COUNTEREXAMPLE Asset with correct authorized parent IDs. It will itself receive independent review. Do not hide novel proof claims solely in review text.
- A review, a named CALCULATION, a run of Python, or another model's agreement does not certify mathematical correctness. You may return INDETERMINATE and state what is missing.
'''

REASSESS_ADDENDUM='''
NATIVE MATH REVIEW FEEDBACK TO RESEARCHER:
- Evaluate the independent review critically rather than automatically accepting it.
- Retain, revise, reject, or restrict the original mathematical claim with precise reasons; new claims are provisional.
- If you create a new mathematical result, publish it as a CALCULATION or COUNTEREXAMPLE Asset, linked to authorized parents. That new Asset will also enter independent verification.
- You may finish without publishing a new Asset when the review did not produce a material scientific delta. No forced novelty or acceptance.
'''


def _digest(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:22]


def verifier_work_id(asset_id):
    return 'W_NMVERIFY_'+_digest(asset_id)


def reassess_work_id(asset_id):
    return 'W_NMREASSESS_'+_digest(asset_id)


def _subject(w,marker):
    val=w.get('research_rationale','')
    if not isinstance(val,str) or not val.startswith(marker):return None
    return val[len(marker):].split(' ',1)[0]


def verifier_subject(w):
    return _subject(w,VERIFY_REASON)


def reassess_subject(w):
    return _subject(w,REASSESS_REASON)


def enabled(j, state=None):
    state=state if state is not None else j.verify()
    return POLICY_ID in state.sources and state.sources[POLICY_ID]['kind']=='OPERATOR'


def enable_on_clean_root(j):
    s=j.verify()
    if enabled(j,s):return False
    if s.work or s.model_calls or s.controller_decisions:
        raise RuntimeError('MATH_CYCLE_OPTIN_REQUIRES_CLEAN_ROOT_NO_LIVE_WORK')
    j.add_source(POLICY_ID,'OPERATOR',{
        'protocol':PROTOCOL,'reason':'OPERATOR_SELECTED_NATIVE_MATH_VERIFICATION_ROLE',
        'scope':'NEW_LIVE_MATHEMATICAL_ASSETS_ONLY',
        'review_new_verifier_claims':True,'no_scientific_certification':True,
        'default_asset_kinds':sorted(DEFAULT_KINDS),
        'no_fixed_verification_depth':True,
        'no_forced_suggested_science':True},
        'Native opt-in: independently review new mathematical claims, including reviewer claims')
    return True


def is_new_math_target(s,asset_id,j=None):
    a=s.assets[asset_id]
    # Historical carried claims are not a fresh research action; a Controller
    # may explicitly assign them to VERIFY in ordinary science. We auto-queue
    # only a real newly published Asset in the current root.
    if not a.get('work_id'):return False
    creator=s.work.get(a['work_id'])
    if not creator:return False
    selected=False
    if j is not None:
        from .math_claim_selection import selected_claim_for_work
        selected=bool(selected_claim_for_work(j,creator['id']))
    return (a['kind'] in DEFAULT_KINDS or
            bool(verifier_subject(creator)) or bool(reassess_subject(creator)) or selected)


def on_assets_published(j,asset_ids):
    """Idempotent event-sourced auto-queue after successful ASSET_PUBLISHED.

    Only concrete IDs accepted in the Journal are provided. The model cannot
    forge a Review target by mentioning a nonexistent local asset ID.
    """
    s=j.verify()
    if not enabled(j,s):return []
    scheduled=[]
    for aid in asset_ids:
        s=j.verify()
        if aid not in s.assets or not is_new_math_target(s,aid,j=j):continue
        wid=verifier_work_id(aid)
        if wid in s.work:continue
        a=s.assets[aid]
        work={'id':wid,'problem_id':a['problem_id'],'mode':'INFORMED',
              'source_ids':[],
              'question':('Independently audit the mathematical validity and scope of '
                  'the supplied parent Asset. Re-derive the claim from its stated '
                  'assumptions, seek boundary cases or counterexamples when helpful, '
                  'and make a justified retain/restrict/reject/uncertain assessment. '
                  'Any NEW mathematical claim you publish is separately reviewable. '
                  'Do not presume the claim correct or incorrect; do not certify it.'),
              'research_rationale':VERIFY_REASON+aid+' Original scientific author is not the verifier.'}
        j.evolve('E_NMVERIFY_'+_digest(aid),'VERIFY',[aid],work,
                 'INDEPENDENT_REVIEW_OF_NEW_REGISTERED_MATHEMATICAL_CLAIM_NOT_CERTIFICATION')
        scheduled.append(wid)
    return scheduled


def before_worker_model(j,wid,worker_system,payload):
    s=j.verify()
    if not enabled(j,s):return worker_system,payload
    w=s.work[wid]
    aid=verifier_subject(w)
    selected=None
    if not aid:
        from .math_claim_selection import selected_claim_for_work
        selected=selected_claim_for_work(j,wid)
        if selected:aid=selected['asset_id']
    if aid:
        # Silo the reviewer's input: no cross-review mathematical solutions or
        # entire population summaries; only its pinned subject and own feedback.
        keep=('pinned_input','own_prior_steps','research_capability_state',
              'research_action','m235_own_lineage_feedback',
              'm236_parent_reference_contract','m236_metadata_repair_context',
              'm23_asset_publication_source_contract')
        restricted={k:payload[k] for k in keep if k in payload}
        pin=restricted.get('pinned_input',{})
        parents=pin.get('parent_assets',[])
        if not (len(parents)==1 and parents[0]['id']==aid and
                pin.get('work',{}).get('mode')=='INFORMED'):
            raise RuntimeError('MATH_VERIFIER_WRONG_PINNED_PARENT')
        restricted['native_math_review']={
            'protocol':PROTOCOL,'subject_asset_id':aid,
            'controller_selected_claim':selected,
            'independent_target_only':True,'reviewer_oracle_not_supplied':True,
            'new_math_claims_require_new_assets':True,'no_scientific_certification':True}
        return worker_system+'\n'+VERIFIER_ADDENDUM,restricted
    aid=reassess_subject(w)
    if aid:
        reviewers=[]
        for source_wid,source_work in s.work.items():
            for st in source_work.get('steps',[]):
                if st['kind']!='MATH_REVIEW':continue
                record=json.loads(j.raw(st['raw_blob']))
                if record.get('target_asset_id')==aid:
                    reviewers.append((source_wid,record))
        if not reviewers:raise RuntimeError('REASSESS_REVIEW_NOT_DURABLY_RECORDED')
        reviewer_wid,raw=reviewers[-1]
        feedback={
            'protocol':PROTOCOL,'subject_asset_id':aid,
            'review_record':raw,
            'reviewer_work_id':reviewer_wid,
            'not_a_math_certificate':True,
            'new_reviewer_assets_also_reviewed_independently':True}
        return worker_system+'\n'+REASSESS_ADDENDUM,{**payload,'native_math_review_feedback':feedback}
    return worker_system,payload


def on_verifier_final(j,wid,parsed,call_id):
    """Record review as a WORK_STEP while the verifier Work is ACTIVE.

    Calling code must invoke this only on a VALID terminal model response,
    after metadata-delivery validation. No machine-written scientific verdict.
    """
    s=j.verify();w=s.work[wid]
    aid=verifier_subject(w)
    selected=None
    if not aid:
        from .math_claim_selection import selected_claim_for_work
        selected=selected_claim_for_work(j,wid)
        if selected:aid=selected['asset_id']
    if not aid or not enabled(j,s):return None
    if any(step['kind']=='MATH_REVIEW' for step in w['steps']):return None
    verdict=parsed.get('math_review')
    if (isinstance(verdict,dict) and verdict.get('verdict') in VERDICTS and
            isinstance(verdict.get('reason'),str) and verdict['reason'].strip()):
        review=dict(verdict)
        review['format']='MODEL_AUTHORED_STRUCTURED_REVIEW'
    else:
        review={'verdict':'UNSTRUCTURED_MODEL_REVIEW','reason':parsed.get('scientific_text','')[:1500],
                'format':'RESPONSE_NOT_STRUCTURED_NO_MATH_CERTIFICATION'}
    reviewed={'protocol':PROTOCOL,'target_asset_id':aid,'verifier_work_id':wid,
        'verifier_model_call_id':call_id,'review':review,
        'controller_selected_claim':selected,
        'new_assets_by_verifier':list(w.get('published',[])),
        'scientific_text':parsed.get('scientific_text',''),
        'result':'PROVISIONAL_REVIEW_RECORDED_NOT_SCIENCE_CERTIFIED',
        'model_output_verbatim_in_prior_MODEL_RESPONSE':True,
        'scientific_certification':False}
    # Work-step uses the exact original Journal; no out-of-band endorsement.
    j.step(wid,'MATH_REVIEW',reviewed)
    # Return the critique to the source researcher. If the source is another
    # verifier or a reappraisal, its NEW math assertions already enter the
    # recursive verification queue; do not spawn a redundant reappraisal tree.
    s=j.verify();origin=s.work.get(s.assets[aid].get('work_id'))
    selected_origin=False
    if origin is not None:
        from .math_claim_selection import selected_claim_for_work
        selected_origin=bool(selected_claim_for_work(j,origin['id']))
    # A directly carried historical claim has no executable original author
    # in the current root. Start a NEW, clearly labelled INFORMED reassessment
    # instead of pretending to resume its historical Work.
    inherited_author=(origin is None and bool(s.assets[aid].get('carried_from_root')))
    if ((origin is None and not inherited_author) or
            (origin is not None and (verifier_subject(origin) or
                 reassess_subject(origin) or selected_origin))):
        return reviewed
    rid=reassess_work_id(aid)
    if rid in s.work:return reviewed
    rev_assets=list(s.work[wid].get('published',[]))
    authorized=[aid]+[x for x in rev_assets if x in s.assets]
    item=s.assets[aid]
    work={'id':rid,'problem_id':item['problem_id'],'mode':'INFORMED','source_ids':[],
          'question':('Reassess the source mathematical claim after independent '
               'verification feedback. Examine the reviewer reasoning critically; '
               'retain, revise, reject, or limit the original claim according to '
               'the evidence. If making a new mathematical claim, publish it as '
               'a new science Asset so that it too is independently reviewed. '
               'No required agreement and no imposed scientific conclusion.'),
          'research_rationale':REASSESS_REASON+aid+
              (' NEW_CURRENT_ROOT_REASSESSMENT_OF_HISTORICAL_CLAIM.' if inherited_author
               else ' Response to recorded native independent review.')}
    j.evolve('E_NMREASSESS_'+_digest(aid),'DEVELOP',authorized,work,
             'SOURCE_AUTHOR_REASSESSMENT_OF_INDEPENDENT_REVIEW_NOT_AUTOMATIC_ACCEPTANCE')
    return reviewed


def pending_math_work(j):
    s=j.verify()
    if not enabled(j,s):return []
    open_ids=[]
    from .math_claim_selection import selected_claim_for_work
    for wid,w in s.work.items():
        if not (verifier_subject(w) or reassess_subject(w) or selected_claim_for_work(j,wid)):
            continue
        if w['status'] in {'QUEUED','ACTIVE'}:
            open_ids.append(wid)
        elif w['status']=='DONE' and w.get('outcome') in {'BLOCKED'}:
            # An operationally blocked review is not a completed validation.
            open_ids.append(wid)
        elif ((verifier_subject(w) or selected_claim_for_work(j,wid)) and w['status']=='DONE' and
                not any(st['kind']=='MATH_REVIEW' for st in w.get('steps',[]))):
            open_ids.append(wid)
    return open_ids


def controller_context(j):
    s=j.verify()
    if not enabled(j,s):return None
    reviews=[]
    from .math_claim_selection import selected_claim_for_work
    for wid,w in s.work.items():
        aid=verifier_subject(w)
        if not aid:
            selection=selected_claim_for_work(j,wid)
            if selection:aid=selection['asset_id']
        if not aid:continue
        step=next((p for p in w['steps'] if p['kind']=='MATH_REVIEW'),None)
        if step:
            obj=json.loads(j.raw(step['raw_blob']))
            reviews.append({'subject_asset_id':aid,'reviewer_work_id':wid,
                'review':obj.get('review'),
                'new_assets_by_verifier':obj.get('new_assets_by_verifier',[]),
                'status':w['status'],'scientific_certification':False})
    return {'protocol':PROTOCOL,'opted_in':True,'pending_math_work_ids':pending_math_work(j),
            'completed_reviews':reviews,
            'all_new_math_assets_require_independent_review':True,
            'review_of_verifier_generated_math_assets':True,
            'no_automatic_scientific_certification':True,
            'instructions':('Reviewers can be wrong. Critically evaluate the REVIEW '
                'and any mathematically new Asset it generated. Prefer documented '
                'reasoning, executed checks, qualified scope, and independent '
                'counterarguments over unanimity. Do not treat review labels '
                'or a closed review queue as a scientific proof.')}
