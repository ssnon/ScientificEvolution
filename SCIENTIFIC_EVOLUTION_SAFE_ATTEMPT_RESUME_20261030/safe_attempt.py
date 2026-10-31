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


def safety_report(j, current_prompt, expected_previous='OPP_D00007'):
    """Read-only proof of attempt reservation and V4 advisor preservation."""
    state=j.verify()
    un=[{'call_id':cid,'state':call['state']} for cid,call in state.model_calls.items()
         if call['state']!='SAVED']
    committed={d['id'] for d in state.controller_decisions}
    old=expected_previous[4:] # D00007
    if un:raise RuntimeError('UNRESOLVED_PROVIDER_OUTCOME:'+str(un[:3]))
    if expected_previous not in state.model_calls:
        raise RuntimeError('EXPECTED_PARTIAL_ASSESSMENT_NOT_FOUND:'+expected_previous)
    if old in committed or ('CTRL_'+old) in state.model_calls:
        raise RuntimeError('EXPECTED_PARTIAL_ASSESSMENT_ALREADY_COMMITTED_OR_CONTROLLER_CALLED:'+old)
    new_id=reserved_next_id(j,old)
    if new_id==old:raise RuntimeError('PARTIALLY_SAVED_OPP_ID_NOT_RESERVED')
    prompt,meta=archived_opportunity_prompt(j,current_prompt,expected_previous)
    c=state.model_calls[expected_previous]
    return {'status':'SAFE_NEW_ATTEMPT_READONLY','abandoned_partial_opportunity':expected_previous,
            'abandoned_model_call_sha256':c['request_blob'],
            'reserved_new_controller_attempt':new_id,
            'reserved_new_opportunity_call':'OPP_'+new_id,
            'new_attempt_is_not_a_scientific_generation':True,
            'old_opportunity_response_never_reinterpreted':True,
            'opportunity_prompt_provenance':meta,
            'restored_system_prompt_is_recorded_historical_v4':prompt==json.loads(j.raw(c['request_blob']))['messages'][0]['content'],
            'unresolved_model_calls':[],
            'journal_modified':False,'provider_requests_sent':0}


@contextlib.contextmanager
def activate(mods,j):
    """Reserve already used decision IDs; let the REAL V4 runtime own its prompt.

    The real generation driver enters V4.runtime() and V3.v3_runtime().
    Read-only checks enter V4.runtime() briefly to verify provenance fidelity.
    No manual prompt replacement is necessary or permitted.
    """
    import e2core.engine as eng
    original_next=eng.Engine._next_controller_id
    # V4 runtime restores all its hooks on exit, so this does not perturb the
    # nested actual research runtime or the later FRESH/INFORMED contract.
    with mods.v4.runtime():
        report=safety_report(j,mods.spe.OPPORTUNITY_PROMPT)
    if report['opportunity_prompt_provenance']['reason'] != 'EXACT_MATCH':
        raise RuntimeError('V4_RUNTIME_PROMPT_DIFFERS_FROM_SAVED_G13_PROMPT')
    def unique(self):
        return reserved_next_id(self.j,original_next(self))
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
