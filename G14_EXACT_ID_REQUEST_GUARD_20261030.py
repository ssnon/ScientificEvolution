#!/usr/bin/env python3
"""G14-only, request-time, exact-ID feedback for NEW controller/worker calls.

This patch never repairs or rewrites an old model reply or relaxes validation.
It adds exact, state-verified reference IDs to future paid requests *after* the
existing attention/memory compaction, but before provider serialization.
Existing saved calls are passed through byte-identically for replay safety.
"""
from __future__ import annotations
import contextlib
import copy
import json
import os
import sys
from pathlib import Path

WORK_ID = 'W_P0_charge_multichannel_model_001'
BAD_PARENT = 'A_CARRY_f1ddae09f1c863fc3ee9c6fb'
GOOD_PARENT = 'A_CARRY_f1ddae09f1c863fc3ee9c6f'
BAD_REVIEW = 'A_CARRY_1ce713be6e14f0895a2fecc4'
GOOD_REVIEW = 'A_CARRY_1ce713be6e14f0895a2fecc'
EXPECTED_HEAD = {'events': 1101, 'head_sha256':
    'e86ce5d8bef7de3cc77aaf35b6f03cf20cde0fde01c920adec95ed2db500c3cf'}
EARLIER_UNREGISTERED = ('A_bounded_charge_tensor_intervention_001',
    'A_charge_tensor_power_bound_002', 'A_redox_thermodynamic_telegraph_manifold_003',
    'A_charge_conserving_redox_event_004')


def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str), flush=True)


def assert_state(state, *, require_initial=False, require_active=False):
    """Never infer that a similar-looking ID is a valid asset."""
    assert GOOD_PARENT in state.assets and BAD_PARENT not in state.assets, 'PARENT_STATE_CHANGED'
    assert GOOD_REVIEW in state.assets and BAD_REVIEW not in state.assets, 'REVIEW_STATE_CHANGED'
    w = state.work.get(WORK_ID)
    assert w and w['mode'] == 'INFORMED', 'TARGET_WORK_MISSING_OR_NOT_INFORMED'
    if require_active: assert w['status'] == 'ACTIVE', 'TARGET_WORK_NOT_ACTIVE'
    allowed = list(dict.fromkeys([*w['asset_input_ids'], *w['published']]))
    assert GOOD_PARENT in allowed, 'PARENT_NOT_AUTHORIZED'
    assert BAD_PARENT not in allowed, 'BAD_PARENT_AUTHORIZED'
    if require_initial:
        assert not any(x in state.assets for x in EARLIER_UNREGISTERED), 'PREVIOUS_PROPOSAL_NOW_REGISTERED'
    return allowed


def inspect(exp, require_head=True):
    import population_run as pop
    import persistent_population as pp
    import autonomous_population as aut
    path = Path(exp).expanduser().resolve(strict=True)
    assert (path/'autonomous.json').is_file(), 'AUTONOMOUS_PLAN_MISSING'
    assert (path/'persistent.json').is_file(), 'PERSISTENT_PLAN_MISSING'
    mods = pop.gen.modules()
    aut.meta_check(mods,path)
    cycle = pp.latest_cycle(path)
    assert cycle and cycle['index']==14 and cycle['stage']=='POPULATION', 'WRONG_CYCLE_STAGE'
    root = Path(cycle['population_root']).resolve(strict=True)
    assert root == path / 'CYCLE_014' / 'POPULATION', 'WRONG_POPULATION_ROOT'
    j,state = pop.root_status(mods,root)
    before = pp.digest(mods,j)
    if require_head:
        assert before == EXPECTED_HEAD, 'JOURNAL_HEAD_CHANGED_REVIEW_FIRST:'+str(before)
    assert not [k for k,v in state.model_calls.items() if v['state']!='SAVED'], 'UNRESOLVED_CALLS'
    allowed = assert_state(state,require_initial=True,require_active=True)
    # Read-only provenance verification of the three rejected Controller attempts.
    invalid=[]
    for n in (3,4,5):
        cid=f'CTRL_D{n:05d}'
        c=state.model_calls.get(cid)
        assert c and c['state']=='SAVED', 'MISSING_REJECTED_CONTROLLER:'+cid
        wire=json.loads(j.raw(c['response_blob']))
        msg=wire['choices'][0]['message']['content']
        if isinstance(msg,dict):parsed=msg
        else:
            import e2core.provider as provider
            parsed=provider.strict_envelope(msg)
        assert isinstance(parsed,dict), 'REJECTED_CONTROLLER_PARSE_FAILED'
        bad=[r for r in parsed.get('reviews',[]) if isinstance(r,dict) and r.get('id')==BAD_REVIEW]
        assert len(bad)==1, 'WRONG_REJECTION_CAUSE:'+cid
        invalid.append(cid)
    assert pp.digest(mods,j)==before, 'READ_CHANGED_JOURNAL'
    return {'status':'G14_EXACT_ID_REQUEST_GUARD_READY_NO_PAID',
        'cycle':14, 'stage':'POPULATION', 'head':before,
        'controller_rejection_calls':invalid,
        'invalid_controller_asset_id':BAD_REVIEW,'exact_controller_asset_id':GOOD_REVIEW,
        'invalid_worker_parent_id':BAD_PARENT,'exact_worker_parent_id':GOOD_PARENT,
        'authorized_worker_parent_ids':allowed,
        'unregistered_proposals':list(EARLIER_UNREGISTERED),
        'new_paid_calls':0,'journal_modified':False,
        'operator_stop_present':(path/'STOP_REQUESTED').exists()},root


def guidance(state,actor,work_id):
    allowed=assert_state(state)
    if actor=='CONTROLLER':
        return {
            'type':'EXACT_ASSET_ID_VALIDATION_FEEDBACK_NOT_SCIENCE',
            'authoritative_for_identifiers':'CURRENT_VERIFIED_JOURNAL',
            'previous_validation_error':'BAD_ASSET_REVIEW',
            'saved_rejection_attempts':['CTRL_D00003','CTRL_D00004','CTRL_D00005'],
            'submitted_nonexistent_review_id':BAD_REVIEW,
            'exact_existing_review_id':GOOD_REVIEW,
            'validation_rule':'Review only exact existing asset IDs. The rejected plans were NOT committed; do not assume their reviews or actions took effect. If a review remains scientifically justified, copy its id exactly from the verified state; reviews are optional when not scientifically useful.',
            'scientific_autonomy_unchanged':True,
        }
    if actor=='WORKER' and work_id==WORK_ID:
        assert_state(state,require_active=True)
        return {
            'type':'EXACT_AUTHORIZED_PARENT_ID_VALIDATION_FEEDBACK_NOT_SCIENCE',
            'authoritative_for_identifiers':'CURRENT_VERIFIED_JOURNAL',
            'previous_validation_error':'BAD_ASSET_PARENTS',
            'submitted_nonexistent_parent_id':BAD_PARENT,
            'exact_existing_authorized_parent_id':GOOD_PARENT,
            'complete_authorized_parent_ids':allowed,
            'currently_unregistered_previous_proposals':[x for x in EARLIER_UNREGISTERED if x not in state.assets],
            'previous_proposals_now_registered':[x for x in EARLIER_UNREGISTERED if x in state.assets],
            'validation_rule':'For parent_ids copy exact IDs from complete_authorized_parent_ids or accepted assets published earlier by this Work. Earlier rejected asset proposals do not exist in the Journal. Reassess their science autonomously; resubmission is optional, and not certification.',
            'scientific_autonomy_unchanged':True,
        }
    return None


def augment(state,actor,work_id,system,payload):
    """Return new payload and prompt; never alter the caller's objects."""
    g=guidance(state,actor,work_id)
    if g is None:return system,payload
    assert isinstance(payload,dict) and isinstance(system,str), 'UNEXPECTED_PROVIDER_INPUT_TYPE'
    result=copy.copy(payload)
    result['g14_exact_identifier_validation_feedback']=g
    # This instruction is appended at the final provider request boundary,
    # after the previous memory-context compaction has already happened.
    suffix=('\nEXACT IDENTIFIER CONTRACT (machine-reported provenance, not a science decision): '
            'The g14_exact_identifier_validation_feedback field contains the exact authoritative '
            'IDs and prior schema errors. Do not invent, append characters to, or silently repair '
            'parent_ids or review ids. Do not treat unregistered proposals as existing assets. '
            'Choose science and any new hypotheses freely; schema validation remains strict.\n')
    return system+suffix,result


@contextlib.contextmanager
def activate(population_root):
    """Add metadata only for FUTURE G14 Population model calls.

    Installed BEFORE evolution_pdf->evolution_memory starts, so the existing
    memory layer performs its compaction first and delegates to this wrapper.
    """
    from e2core.provider import DurableModel
    root=Path(population_root).resolve(strict=True)
    original=DurableModel.call
    def with_ids(self,ident,actor,work_id,system,payload):
        if Path(self.j.root).resolve()!=root:
            return original(self,ident,actor,work_id,system,payload)
        # An already SAVED/INTENT model call must see its ORIGINAL request.
        state=self.j.verify()
        if ident in state.model_calls:
            return original(self,ident,actor,work_id,system,payload)
        if not ((actor=='CONTROLLER' and str(ident).startswith('CTRL_')) or
                (actor=='WORKER' and work_id==WORK_ID)):
            return original(self,ident,actor,work_id,system,payload)
        new_system,new_payload=augment(state,actor,work_id,system,payload)
        return original(self,ident,actor,work_id,new_system,new_payload)
    try:
        DurableModel.call=with_ids
        yield
    finally:
        DurableModel.call=original


def selftest():
    from types import SimpleNamespace
    state=SimpleNamespace(assets={GOOD_PARENT:{}, GOOD_REVIEW:{}},
        work={WORK_ID:{'status':'ACTIVE','mode':'INFORMED',
        'asset_input_ids':[GOOD_PARENT,'A_PEER_77447dfc52949208e332b7'], 'published':[]}})
    assert assert_state(state)
    original={'own_prior_steps':[{'text':'unchanged'}]}
    for actor,wid in (('CONTROLLER',None),('WORKER',WORK_ID)):
        s,p=augment(state,actor,wid,'BASE_SYSTEM',original)
        assert s.startswith('BASE_SYSTEM') and s!='BASE_SYSTEM'
        assert original=={'own_prior_steps':[{'text':'unchanged'}]}
        g=p['g14_exact_identifier_validation_feedback']
        assert g['scientific_autonomy_unchanged'] and 'BAD_ASSET' in g['previous_validation_error']
        assert BAD_PARENT not in g.get('complete_authorized_parent_ids',[])
    s,p=augment(state,'WORKER','W_other','BASE_SYSTEM',original)
    assert s=='BASE_SYSTEM' and p is original
    # Exercise the provider-boundary wrapper with a fake module only; no provider.
    import tempfile, types
    sentinel=[]
    provider=types.ModuleType('e2core.provider')
    pkg=types.ModuleType('e2core');pkg.__path__=[]
    class FakeDurableModel:
        def call(self,ident,actor,wid,system,payload):
            sentinel.append((ident,system,payload));return 'CAPTURED'
    provider.DurableModel=FakeDurableModel
    old_pkg=sys.modules.get('e2core');old_mod=sys.modules.get('e2core.provider')
    sys.modules['e2core']=pkg;sys.modules['e2core.provider']=provider
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fake=SimpleNamespace(j=SimpleNamespace(root=root, verify=lambda:SimpleNamespace(
                assets=state.assets,work=state.work,model_calls={})))
            with activate(root):
                instance=FakeDurableModel()
                instance.j=fake.j
                assert instance.call('CTRL_D99999','CONTROLLER',None,'BASE_SYSTEM',original)=='CAPTURED'
                assert GOOD_REVIEW in str(sentinel[-1][2])
                assert instance.call('WK_W_P0_charge_multichannel_model_001_99999','WORKER',WORK_ID,'BASE_SYSTEM',original)=='CAPTURED'
                assert GOOD_PARENT in str(sentinel[-1][2])
                assert BAD_PARENT not in str(sentinel[-1][2]['g14_exact_identifier_validation_feedback']['complete_authorized_parent_ids'])
                # Saved calls must bypass supplementation exactly.
                fake.j.verify=lambda:SimpleNamespace(assets=state.assets,work=state.work,
                    model_calls={'CTRL_D99999':{'state':'SAVED'}})
                instance.j=fake.j
                assert instance.call('CTRL_D99999','CONTROLLER',None,'BASE_SYSTEM',original)=='CAPTURED'
                assert sentinel[-1][1]=='BASE_SYSTEM' and sentinel[-1][2] is original
                # Other roots are untouched regardless of actor.
                fake.j.root=root/'another'
                assert instance.call('CTRL_D99998','CONTROLLER',None,'BASE_SYSTEM',original)=='CAPTURED'
                assert sentinel[-1][1]=='BASE_SYSTEM'
    finally:
        if old_pkg is None:sys.modules.pop('e2core',None)
        else:sys.modules['e2core']=old_pkg
        if old_mod is None:sys.modules.pop('e2core.provider',None)
        else:sys.modules['e2core.provider']=old_mod
    emit({'status':'G14_EXACT_ID_GUARD_SELFTEST_OK','checks':7,'provider_requests_sent':0,'journal_modified':False})


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if args==['selftest']:
        selftest();return 0
    if not args or args[0] not in ('preflight','run'):
        raise RuntimeError('USAGE: script.py selftest | preflight --experiment EXP | run --experiment EXP --paid [original runner options]')
    try:exp=args[args.index('--experiment')+1]
    except (IndexError,ValueError):raise RuntimeError('EXPERIMENT_REQUIRED') from None
    report,root=inspect(exp,require_head=True)
    if args[0]=='preflight':
        if not report['operator_stop_present']:raise RuntimeError('STOP_REQUESTED_REQUIRED_FOR_READ_ONLY_PREFLIGHT')
        emit(report);return 0
    if '--paid' not in args or os.getenv('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        raise RuntimeError('EXPLICIT_PAID_APPROVAL_REQUIRED')
    if report['operator_stop_present']:
        raise RuntimeError('STOP_REQUESTED_PRESENT_REMOVE_ONLY_FOR_INTENTIONAL_PAID_RUN')
    # Preserve normal one-segment stop semantics. No code here adds calls.
    import evolution_pdf
    sys.argv=[str(Path(evolution_pdf.__file__).resolve()),*args]
    with activate(root):return evolution_pdf.main()

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        emit({'status':'G14_EXACT_ID_GUARD_OPERATIONAL_PAUSE',
              'exception_type':type(exc).__name__, 'detail':str(exc),
              'journal_modified_by_patch':False,'not_scientific_hold':True})
        sys.exit(3)
