"""Immutable attempt-ID reservation and opt-in legacy opportunity-prompt fidelity.

A partially completed Controller assessment can contain a saved OPP_D00007
without a committed CTRL_D00007. Because that OPP was produced under an older
request contract, it cannot be replayed for a different science input. Reserve
*any* previously used per-decision call identifier and allocate a new attempt.

No Journal events, blobs, old responses, or scientific claims are rewritten.
"""
from __future__ import annotations
import contextlib
import json
import re
from types import SimpleNamespace

# Historical V4 addendum is recovered from the authenticated SAVED model wire.
LEGACY_V4_MARKER='V4 pre-experiment scientific research opportunity comparison'


def reserved_next_id(j, baseline_candidate):
    """Return a fresh decision identifier, preserving all partially paid tries.

    This only reserves proposal attempts, NOT scientific Works or generations.
    """
    s=j.verify()
    digits=[]
    for cid in s.model_calls:
        hit=re.fullmatch(r'(?:CTRL|OPP)_D(\d+)',cid)
        if hit:digits.append(int(hit.group(1)))
    for dec in s.controller_decisions:
        hit=re.fullmatch(r'D(\d+)',dec['id'])
        if hit:digits.append(int(hit.group(1)))
    hit=re.fullmatch(r'D(\d+)',baseline_candidate)
    if not hit:raise RuntimeError('UNEXPECTED_CONTROLLER_ATTEMPT_ID:'+str(baseline_candidate))
    return 'D'+str(max(max(digits,default=0)+1,int(hit.group(1)))).zfill(5)


def archived_opportunity_prompt(j, current_prompt, ident='OPP_D00007'):
    """Restore same science-opportunity instructions if original is a proven suffix.

    A changed system prompt must *not* be used to replay an old call. This
    recovered prompt is used for a NEW attempt only.
    """
    c=j.verify().model_calls.get(ident)
    if not c or c['state']!='SAVED':
        raise RuntimeError('EXPECTED_SAVED_OPPORTUNITY_CALL_MISSING:'+ident)
    wire=json.loads(j.raw(c['request_blob']))
    msgs=wire.get('messages')
    if not isinstance(msgs,list) or len(msgs)!=2 or msgs[0].get('role')!='system':
        raise RuntimeError('ARCHIVED_OPPORTUNITY_PROMPT_BAD_WIRE:'+ident)
    archived=msgs[0].get('content')
    if not isinstance(archived,str) or not isinstance(current_prompt,str):
        raise RuntimeError('ARCHIVED_OPPORTUNITY_PROMPT_BAD_TEXT:'+ident)
    if archived==current_prompt:
        return archived,{'source_call_id':ident,'reason':'EXACT_MATCH','restored_v4_addendum':False}
    # Distinct V4 scientific guidance existed before the versioned memory layer.
    # Require a strict append-only suffix; never normalize/rewrite user science.
    if not archived.startswith(current_prompt):
        raise RuntimeError('ARCHIVED_OPPORTUNITY_PROMPT_NOT_APPEND_ONLY:'+ident)
    suffix=archived[len(current_prompt):].strip()
    if not suffix.startswith(LEGACY_V4_MARKER):
        raise RuntimeError('ARCHIVED_OPPORTUNITY_PROMPT_UNKNOWN_SUFFIX:'+ident)
    return archived,{'source_call_id':ident,'reason':'ARCHIVED_APPEND_ONLY_V4_RESTORED',
                    'restored_v4_addendum':True,
                    'current_length':len(current_prompt),'archived_length':len(archived)}


def safety_report(j, current_prompt):
    """Generic, read-only attempt accounting for ANY cycle.

    Previously G13's orphan OPP_D00007 was REQUIRED for every future run.
    Preserve that call if present but don't make it a global runtime policy.
    All saved calls and decisions reserve their identifiers; a missing old
    opportunity is normal in fresh generations.
    """
    state=j.verify()
    unsaved=[{'call_id':cid,'state':call['state']} for cid,call in state.model_calls.items()
             if call['state']!='SAVED']
    if unsaved:raise RuntimeError('UNRESOLVED_PROVIDER_OUTCOME:'+str(unsaved[:3]))
    candidates=[]
    committed={d['id'] for d in state.controller_decisions}
    for cid,c in state.model_calls.items():
        m=re.fullmatch(r'OPP_(D\d+)',cid)
        if m and m.group(1) not in committed and 'CTRL_'+m.group(1) not in state.model_calls:
            candidates.append((int(m.group(1)[1:]),cid,c))
    latest=max(candidates,default=None,key=lambda x:x[0])
    baseline='D'+str(max([0]+[x[0] for x in candidates])).zfill(5)
    upcoming=reserved_next_id(j,baseline)
    metadata={'source_call_id':None,'reason':'NO_ORPHAN_OPPORTUNITY',
              'restored_v4_addendum':False}
    old_call=None;sha=None
    if latest:
        old_call=latest[1];sha=latest[2]['request_blob']
        wire=json.loads(j.raw(sha));archived=wire['messages'][0]['content']
        if archived==current_prompt:
            metadata={'source_call_id':old_call,'reason':'EXACT_MATCH','restored_v4_addendum':False}
        else:
            metadata={'source_call_id':old_call,'reason':'NEW_PROMPT_CONTRACT_NEW_ATTEMPT',
                      'restored_v4_addendum':False,'archived_system_sha256':__import__('hashlib').sha256(archived.encode()).hexdigest(),
                      'current_system_sha256':__import__('hashlib').sha256(current_prompt.encode()).hexdigest()}
    return {'status':'SAFE_NEW_ATTEMPT_READONLY',
        'abandoned_partial_opportunity':old_call,'abandoned_model_call_sha256':sha,
        'reserved_new_controller_attempt':upcoming,
        'reserved_new_opportunity_call':'OPP_'+upcoming,
        'new_attempt_is_not_a_scientific_generation':True,
        'old_opportunity_response_never_reinterpreted':True,
        'opportunity_prompt_provenance':metadata,
        'restored_system_prompt_is_recorded_historical_v4': metadata['reason']=='EXACT_MATCH',
        'unresolved_model_calls':[],'journal_modified':False,'provider_requests_sent':0}


@contextlib.contextmanager
def activate(mods,j):
    """Reuse every existing saved call verbatim, reserve new IDs generically."""
    import e2core.engine as eng
    original_next=eng.Engine._next_controller_id
    with mods.v4.runtime():
        report=safety_report(j,mods.spe.OPPORTUNITY_PROMPT)
    def unique(self):return reserved_next_id(self.j,original_next(self))
    try:
        eng.Engine._next_controller_id=unique
        yield report
    finally:
        eng.Engine._next_controller_id=original_next


@contextlib.contextmanager
def stop_after_segments(aut, experiment, count):
    """Operational-only run boundary: request STOP after count completed steps.

    Each step_once may itself make several paid calls (including steering).
    This is not a dollar ceiling or scientific reason to terminate.
    """
    from pathlib import Path
    if not isinstance(count,int) or count<1:
        raise RuntimeError('INVALID_SEGMENT_GUARD_MUST_BE_POSITIVE_INTEGER')
    root=Path(experiment).expanduser().resolve()
    original_step=aut.step_once
    performed=0
    def capped(*args,**kwargs):
        nonlocal performed
        result=original_step(*args,**kwargs)
        performed+=1
        if performed>=count and result=='CONTINUE':
            (root/'STOP_REQUESTED').touch(exist_ok=True)
            print(json.dumps({'status':'OPERATOR_COST_OBSERVATION_BOUNDARY',
                'completed_segments':performed,'stop_marker':str(root/'STOP_REQUESTED'),
                'not_scientific_hold':True},ensure_ascii=False),flush=True)
        return result
    try:
        aut.step_once=capped
        yield
    finally:
        aut.step_once=original_step
