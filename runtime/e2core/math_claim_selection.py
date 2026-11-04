"""Claim-level, Controller-authored mathematics verification selection (V1.1).

Candidates are scientific Assets, NOT automatically mathematical facts. The
Controller must identify the actual mathematical subclaim and voluntarily
choose an ordinary VERIFY evolution action. The persisted Controller decision
and exact resulting Work jointly authorize V1.1 independent review; no string
keyword classifier, review certificate, covert model request, or automatic
recategorization of a hypothesis occurs here.

The V1.0 CALCULATION/COUNTEREXAMPLE queue stays independent and unchanged.
"""
from __future__ import annotations
import hashlib
import json

PROTOCOL = 'NATIVE_MATH_CLAIM_SELECTION_V1_1'
FIELD = 'native_math_claim_decisions'
DECISIONS = frozenset({'VERIFY_NOW', 'DEFER', 'OTHER_RESEARCH_FIRST', 'NO_MATH_CLAIM'})

CONTROLLER_ADDENDUM = '''
NATIVE MATH CLAIM REVIEW SELECTION V1.1 (science choice, not a quota):
- Examine the native_math_claim_selection.candidates individually. An Asset
  labelled HYPOTHESIS, PREDICTION, NULL_MODEL etc. may contain mathematical
  subclaims with derivation or identifiability assumptions. Neither asset kind
  nor the author's confidence is a proof that these implications follow.
- For EVERY candidate, add top-level "native_math_claim_decisions":
  [{"asset_id":"EXISTING_ASSET_ID",
    "decision":"VERIFY_NOW|DEFER|OTHER_RESEARCH_FIRST|NO_MATH_CLAIM",
    "math_claims":["precise mathematical consequence or assumption, if any"],
    "rationale":"independent scientific reason, including alternatives and uncertainty",
    "work_id":"EXISTING ACTION WORK ID if VERIFY_NOW, otherwise omit"}].
- VERIFY_NOW is an actionable decision only when the SAME response creates an
  ordinary actions[] item: operation VERIFY, exactly one asset_ids entry equal
  to asset_id, INFORMED work with matching id and a scientific question that
  independently tests the selected mathematical subclaim and its conditions.
- A VERIFY_NOW row without its matching authorized action is not a completed
  selection. DEFER and OTHER_RESEARCH_FIRST can be scientifically justified;
  there is no requirement to choose VERIFY or produce mathematics every cycle.
- Independent review may refute, restrict or uphold an original claim. It does
  not certify a theorem or force the Controller to accept the review. A reviewer
  creating NEW math is itself independently reviewed. Explain priorities.
- Historical carried candidates are PREVIOUS WORK OUTPUTS, not new live work,
  and must never be passed to a FRESH worker. VERIFY is INFORMED only.
'''


def _fingerprint(asset):
    fields={key:asset.get(key) for key in ('id','kind','claim','assumptions','scope','predictions','limitations')}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()


def _recent_carried_live(j,asset):
    """Identify a directly carried live author's Asset, not 597 old AI items.

    The source record is operator-created by the existing Native population
    continuity writer. Do not infer execution from a name or an external link.
    """
    if not asset.get('carried_original_asset_id') or not asset.get('carried_from_root'):
        return False
    for sid in asset.get('source_ids',[]):
        entry=j.verify().sources.get(sid)
        if not entry or entry.get('kind')!='HISTORICAL_AI':continue
        try:body=json.loads(j.raw(entry['blob']))
        except (ValueError,KeyError,TypeError):continue
        original=body.get('original_asset')
        if not isinstance(original,dict):continue
        if (body.get('upstream_asset_id')==asset['carried_original_asset_id'] and
                body.get('upstream_root')==asset['carried_from_root'] and
                isinstance(original.get('work_id'),str) and original['work_id'] and
                original.get('origin')!='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'):
            return True
    return False


def candidate_assets(j):
    """Surface ALL candidate Asset kinds; semantic extraction is model work.

    Only current-root live Assets and directly carried, formerly live work
    from the immediate source are surfaced. Other 597+ historical AI assets
    retain ordinary Controller/VERIFY access but are not falsely called NEW.
    """
    from . import math_cycle
    s=j.verify()
    if not math_cycle.enabled(j,s):return []
    found=[]
    for aid,a in s.assets.items():
        origin='CURRENT_ROOT_LIVE_WORK' if a.get('work_id') in s.work else (
             'RECENT_PREVIOUS_ROOT_LIVE_WORK_HISTORICAL' if _recent_carried_live(j,a) else None)
        if origin is None:continue
        # Existing V1 math Assets and any newly derived claims already given
        # an automatic recursive reviewer are covered by the V1 review context;
        # do not invite redundant Controller-selected verification.
        if origin=='CURRENT_ROOT_LIVE_WORK' and (
                a.get('kind') in math_cycle.DEFAULT_KINDS or
                math_cycle.verifier_work_id(aid) in s.work):
            continue
        found.append({'asset_id':aid,'origin':origin,'kind':a.get('kind'),
            'claim':a.get('claim'),'assumptions':a.get('assumptions'),
            'scope':a.get('scope'),'predictions':a.get('predictions',[]),
            'limitations':a.get('limitations',[]),'problem_id':a.get('problem_id'),
            'author_work_id':a.get('work_id'),'parent_ids':a.get('parent_ids',[]),
            'fingerprint_sha256':_fingerprint(a),
            'science_certified':False})
    return found


def _rows_in_decision(obj):
    rows=obj.get(FIELD,[]) if isinstance(obj,dict) else []
    return rows if isinstance(rows,list) else []


def _declared_decisions(j):
    for d in j.verify().controller_decisions:
        try:obj=json.loads(j.raw(d['parsed_blob']))
        except (KeyError,TypeError,ValueError):continue
        for row in _rows_in_decision(obj):
            if isinstance(row,dict):yield d['id'],row


def _candidate_by_id(j):
    return {c['asset_id']:c for c in candidate_assets(j)}


def selected_claim_for_work(j,wid):
    """Fail closed: only a saved Controller choice PLUS matching Native VERIFY.

    The model cannot gain reviewer privileges by writing a magic phrase into a
    work rationale, or by inventing a selected Asset/Work ID in an extra field.
    """
    if not isinstance(wid,str):return None
    s=j.verify(); w=s.work.get(wid)
    if not w or w.get('mode')!='INFORMED' or w.get('operation')!='VERIFY':return None
    parents=w.get('asset_input_ids',[])
    if not isinstance(parents,list) or len(parents)!=1:return None
    candidates=_candidate_by_id(j)
    for decision_id,row in _declared_decisions(j):
        if (row.get('decision')!='VERIFY_NOW' or row.get('work_id')!=wid or
                row.get('asset_id')!=parents[0] or parents[0] not in candidates):
            continue
        claims=row.get('math_claims')
        if not isinstance(claims,list) or not claims or not all(isinstance(c,str) and c.strip() for c in claims):
            continue
        rationale=row.get('rationale')
        if not isinstance(rationale,str) or not rationale.strip():continue
        return {'asset_id':parents[0],'math_claims':claims,'decision_id':decision_id,
                'work_id':wid,'selection_rationale':rationale,
                'claim_selection_not_certificate':True}
    return None


def selection_audit(j):
    """Read-only: report omissions/mismatches, never invent Controller choices."""
    s=j.verify();cand=_candidate_by_id(j)
    records=[];covered=set()
    for d in s.controller_decisions:
        try:obj=json.loads(j.raw(d['parsed_blob']))
        except (ValueError,TypeError,KeyError):continue
        rows=obj.get(FIELD)
        if rows is None:
            records.append({'controller_id':d['id'],'status':'NO_EXPLICIT_CLAIM_SELECTION_FIELD'})
            continue
        if not isinstance(rows,list):
            records.append({'controller_id':d['id'],'status':'INVALID_SELECTION_FIELD_NOT_LIST'})
            continue
        seen=set()
        for item in rows:
            if not isinstance(item,dict):
                records.append({'controller_id':d['id'],'status':'MALFORMED_ROW'});continue
            aid=item.get('asset_id');decision=item.get('decision')
            reasons=item.get('rationale');claims=item.get('math_claims',[])
            ok=(isinstance(aid,str) and aid in cand and aid not in seen and
                isinstance(decision,str) and decision in DECISIONS and isinstance(reasons,str) and bool(reasons.strip()) and
                isinstance(claims,list) and all(isinstance(c,str) and c.strip() for c in claims))
            if isinstance(aid,str):seen.add(aid)
            status='INVALID_OR_UNKNOWN_SELECTION' if not ok else 'MODEL_DECISION_RECORDED_NOT_CERTIFICATION'
            if ok and decision=='VERIFY_NOW':
                if selected_claim_for_work(j,item.get('work_id')) and \
                        selected_claim_for_work(j,item['work_id'])['asset_id']==aid:
                    status='VALID_AUTHORIZED_VERIFY_WORK'
                else:status='VERIFY_NOW_WITHOUT_MATCHING_EXECUTABLE_WORK'
            if status in {'VALID_AUTHORIZED_VERIFY_WORK','MODEL_DECISION_RECORDED_NOT_CERTIFICATION'}:
                covered.add(aid)
            records.append({'controller_id':d['id'],'asset_id':aid,'decision':decision,'status':status,
                            'work_id':item.get('work_id'),'reason':reasons,
                            'math_claims':claims})
    return {'protocol':PROTOCOL,'candidates_total':len(cand),'candidate_ids':list(cand),
        'decision_records':records,'assets_without_valid_selection_record':sorted(set(cand)-covered),
        'automatic_science_certification':False}


def controller_context(j):
    from . import math_cycle
    if not math_cycle.enabled(j):return None
    return {'protocol':PROTOCOL,
      'candidates':candidate_assets(j),
      'selection_audit':selection_audit(j),
      'scientific_selection_by_controller':True,
      'no_automatic_hypothesis_verification':True,
      'selection_requires_ordinary_verify_evolution':True,
      'reviewers_new_mathematical_assets_reenter_verification':True,
      'instructions':'Identify actual mathematical subclaims rather than relying on Asset kind. Independent VERIFY is an autonomous scientific choice; cite assumptions, alternatives and expected information gain.'}
