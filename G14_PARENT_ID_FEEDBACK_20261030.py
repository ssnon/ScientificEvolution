#!/usr/bin/env python3
"""G14 scoped, science-neutral Worker parent-ID validation feedback.

Only alters NEW model-facing advisory context for one G14 Population Work.
Never changes saved model replies, published assets, E2 source/Journals or
scientific assessments. Unregistered proposals are not silently recovered.
"""
from __future__ import annotations
import contextlib
import json
import os
import sys
from pathlib import Path

WORK_ID = 'W_P0_charge_multichannel_model_001'
BAD_PARENT = 'A_CARRY_f1ddae09f1c863fc3ee9c6fb'
TRUE_PARENT = 'A_CARRY_f1ddae09f1c863fc3ee9c6f'
EXPECTED_HEAD = {'events': 1071, 'head_sha256':
    'f02e43ec2b3a3c1fe475d6da8995eedb95bc0f6bcc62470ff941e049f4cde4e3'}
REJECTED_PROPOSALS = (
    'A_bounded_charge_tensor_intervention_001',
    'A_charge_tensor_power_bound_002',
)


def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str), flush=True)


def inspect(experiment: str, *, required_head=True):
    """Read-only state audit. Refuse unexpected cycles, edits or unresolved calls."""
    import population_run as pop
    import persistent_population as pp
    import autonomous_population as aut

    exp = Path(experiment).expanduser().resolve(strict=True)
    if not (exp / 'autonomous.json').is_file() or not (exp / 'persistent.json').is_file():
        raise RuntimeError('NOT_AN_AUTONOMOUS_POPULATION_ROOT')
    mods = pop.gen.modules()
    aut.meta_check(mods, exp)
    cycle = pp.latest_cycle(exp)
    if cycle is None or cycle['index'] != 14 or cycle['stage'] != 'POPULATION':
        raise RuntimeError('G14_NOT_IN_POPULATION_STAGE')
    pop_root = Path(cycle['population_root']).resolve(strict=True)
    if pop_root != exp / 'CYCLE_014' / 'POPULATION':
        raise RuntimeError('UNEXPECTED_POPULATION_ROOT')
    j, state = pop.root_status(mods, pop_root)
    head = pp.digest(mods, j)
    if required_head and head != EXPECTED_HEAD:
        raise RuntimeError('G14_POPULATION_HEAD_CHANGED_REVIEW_FIRST:' + str(head))
    if any(call['state'] != 'SAVED' for call in state.model_calls.values()):
        raise RuntimeError('UNRESOLVED_MODEL_INTENT_MANUAL_REVIEW_REQUIRED')
    w = state.work.get(WORK_ID)
    if w is None or w['status'] != 'ACTIVE' or w['mode'] != 'INFORMED':
        raise RuntimeError('TARGET_WORK_NOT_ACTIVE_INFORMED')
    allowed = list(dict.fromkeys([*w['asset_input_ids'], *w['published']]))
    if (BAD_PARENT in state.assets or TRUE_PARENT not in state.assets
            or TRUE_PARENT not in allowed):
        raise RuntimeError('PARENT_ID_DIAGNOSIS_NO_LONGER_APPLICABLE')
    if any(asset_id in state.assets for asset_id in REJECTED_PROPOSALS):
        raise RuntimeError('PREVIOUS_REJECTED_ASSET_IS_NOW_REGISTERED')
    originals = []
    for st in w['steps']:
        if st['kind'] != 'MODEL_RESPONSE':
            continue
        resp = json.loads(j.raw(st['raw_blob']))
        raw = resp.get('text')
        if not isinstance(raw, str):
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in payload.get('assets', []):
            if item.get('id') in REJECTED_PROPOSALS:
                originals.append({'step': st['step'], 'id': item['id'],
                                  'submitted_parent_ids': item.get('parent_ids')})
    if {item['id'] for item in originals} != set(REJECTED_PROPOSALS):
        raise RuntimeError('SAVED_REJECTED_PROPOSALS_NOT_FOUND')
    if any(BAD_PARENT not in item['submitted_parent_ids'] for item in originals):
        raise RuntimeError('EXPECTED_EXACT_TYPO_MISSING')
    if len(originals) != 2:
        raise RuntimeError('UNEXPECTED_REJECTED_PROPOSAL_COUNT')
    if pp.digest(mods, j) != head:
        raise RuntimeError('READ_ONLY_INSPECTION_CHANGED_JOURNAL')
    return {'status': 'G14_EXACT_PARENT_FEEDBACK_READY_NO_PAID',
            'cycle': 14, 'stage': cycle['stage'], 'work_id': WORK_ID,
            'head': head, 'invalid_parent': BAD_PARENT, 'exact_parent': TRUE_PARENT,
            'allowed_exact_work_parent_ids': allowed,
            'previous_rejected_proposals': originals,
            'operator_stop_present': (exp / 'STOP_REQUESTED').exists(),
            'provider_requests_sent': 0, 'journal_modified': False,
            'previous_assets_not_recovered': True}, pop_root


def build_feedback(state):
    """Model-facing metadata only, no authored scientific hypothesis imposed."""
    w = state.work[WORK_ID]
    allowed = list(dict.fromkeys([*w['asset_input_ids'], *w['published']]))
    if TRUE_PARENT not in allowed or BAD_PARENT in state.assets:
        raise RuntimeError('UNEXPECTED_PARENT_OR_AUTHORIZATION_IN_LIVE_STATE')
    return {
        'kind': 'PRIOR_WORKER_ASSET_PARENT_ID_VALIDATION_FEEDBACK',
        'validation_is_not_scientific_assessment': True,
        'affected_unregistered_asset_ids': list(REJECTED_PROPOSALS),
        'previously_authored_nonexistent_parent_id': BAD_PARENT,
        'exact_existing_authorized_parent_id': TRUE_PARENT,
        'exact_authorized_parent_ids_for_this_work': allowed,
        'machine_explanation': 'The invalid parent differs by one trailing b. Both previously proposed assets were rejected; their scientific claims were NOT registered.',
        'researcher_discretion': 'Continue the scientific work autonomously. If and only if the previous proposals remain justified after reviewing calculation and evidence, you may submit those assets again with exact valid parent IDs and appropriate limitations. Do not treat the rejected proposals as existing assets or verified science. No mandatory resubmission or scientific conclusion.',
        'no_original_output_rewriting': True,
    }


@contextlib.contextmanager
def activate(population_root):
    """Patch Worker *input only*, and only in the specified G14 Population Work."""
    import e2core.engine as engine
    original = engine._worker_input
    pop_root = Path(population_root).resolve(strict=True)
    def annotate(j, wid, *args, **kwargs):
        payload = original(j, wid, *args, **kwargs)
        if wid == WORK_ID and Path(j.root).resolve() == pop_root:
            state = j.verify()
            if state.work[WORK_ID]['status'] == 'ACTIVE':
                if not isinstance(payload, dict):
                    raise RuntimeError('UNEXPECTED_WORKER_INPUT_FORMAT')
                payload = dict(payload)
                payload['exact_parent_id_validation_feedback'] = build_feedback(state)
        return payload
    try:
        engine._worker_input = annotate
        yield
    finally:
        engine._worker_input = original


def selftest():
    from types import SimpleNamespace
    a = SimpleNamespace(work={WORK_ID: {
        'asset_input_ids': ['A_PEER_77447dfc52949208e332b7',
                            'A_CARRY_2edb20ad81efad97da6f699', TRUE_PARENT,
                            'A_CARRY_9a61161221ad05bc452d495'],
        'published': []}}, assets={TRUE_PARENT: {'id': TRUE_PARENT}})
    x = build_feedback(a)
    assert x['exact_existing_authorized_parent_id'] == TRUE_PARENT
    assert BAD_PARENT not in x['exact_authorized_parent_ids_for_this_work']
    assert len(x['affected_unregistered_asset_ids']) == 2
    assert x['no_original_output_rewriting'] is True
    _emit({'status': 'G14_PARENT_FEEDBACK_SELFTEST_OK', 'checks': 4,
           'provider_requests_sent': 0, 'journal_modified': False})


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['selftest']:
        selftest()
        return 0
    if not argv or argv[0] not in ('preflight', 'run'):
        raise RuntimeError('USAGE: script.py selftest | preflight --experiment EXP | run --experiment EXP --paid [other original args]')
    try:
        idx = argv.index('--experiment')
        exp = argv[idx + 1]
    except (ValueError, IndexError):
        raise RuntimeError('EXPERIMENT_REQUIRED') from None
    check, root = inspect(exp)
    if argv[0] == 'preflight':
        if not check['operator_stop_present']:
            raise RuntimeError('PREFLIGHT_REQUIRES_STOP_REQUESTED')
        _emit(check)
        return 0
    if '--paid' not in argv or os.environ.get('FAKG_RESEARCH_ALLOW_PAID') != 'YES':
        raise RuntimeError('EXPLICIT_PAID_APPROVAL_REQUIRED')
    if check['operator_stop_present']:
        raise RuntimeError('STOP_REQUESTED_REMOVE_ONLY_FOR_INTENTIONAL_PAID_RUN')
    # Existing runner controls the actual paid calls and operator pause semantics.
    # No extra intervention into Controller science, tool choices, or E2 writes.
    import evolution_pdf
    sys.argv = [str(Path(evolution_pdf.__file__).resolve()), *argv]
    with activate(root):
        return evolution_pdf.main()

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as ex:
        _emit({'status': 'G14_PARENT_FEEDBACK_OPERATIONAL_PAUSE',
               'error': type(ex).__name__, 'detail': str(ex),
               'not_a_scientific_disposition': True})
        sys.exit(3)
