"""Explain rejected Controller work references WITHOUT repairing model-authored plans.

Diagnostic is a mechanical read-only observation, not an authorized replacement
problem, scientific judgment, new source or salvage of a rejected paid response.
"""
from __future__ import annotations

WORK_REFERENCE_ADDENDUM = '''\nM23.3 CURRENT-ROOT WORK REFERENCE CONTRACT:
For each authored action.work.problem_id, copy an EXACT current-root
problems[].id, or an EXACT id explicitly introduced by your own new_problems
in the same response. An Asset is NOT a Problem: NEVER create a Problem ID by
changing an A_ prefix to P_. Put Asset references in action.asset_ids.
If the intended subject is the original problem, use its actual id P0.
This only restates existing native referential validation and does NOT require
choosing P0, adding a new problem, or changing scientific research priorities.
'''


def reference_failure_diagnostic(j, response, native_error):
    """Return a JSON-safe exact-ID diagnostic only for native BAD_WORK failures."""
    if str(native_error) != 'BAD_WORK' or not isinstance(response, dict):
        return None
    state = j.verify()
    registered = set(state.problems)
    assets = set(state.assets)
    proposed = response.get('new_problems', [])
    proposed_ids = {p['id'] for p in proposed
                    if isinstance(p, dict) and isinstance(p.get('id'), str)} \
        if isinstance(proposed, list) else set()
    errors = []
    for i, action in enumerate(response.get('actions', [])):
        if not isinstance(action, dict):
            continue
        work = action.get('work')
        if not isinstance(work, dict):
            continue
        problem_id = work.get('problem_id')
        if isinstance(problem_id, str) and problem_id in (registered | proposed_ids):
            continue
        candidate_asset = ('A' + problem_id[1:]
                           if isinstance(problem_id, str) and problem_id.startswith('P_')
                           else None)
        errors.append({
            'action_index': i,
            'work_id': work.get('id'),
            'authored_problem_id': problem_id,
            'registered_problem': False,
            'same_suffix_asset_exists': candidate_asset in assets,
            'same_suffix_asset_id': candidate_asset if candidate_asset in assets else None,
            'not_authorized_to_autocorrect': True,
            'model_must_choose_target_problem_independently': True,
        })
    return {
        'diagnostic_kind': 'UNREGISTERED_WORK_PROBLEM_ID' if errors else 'OTHER_BAD_WORK_CONDITION',
        'rejected_model_response_preserved': True,
        'not_scientific_disposition': True,
        'referential_errors': errors,
        'registered_problem_count': len(registered),
        'declared_new_problem_count': len(proposed_ids),
        'no_source_or_work_created_by_diagnostic': True,
    }


def annotate_rejected_work_reference(j, response, native_error, original_payload):
    """Annotate an existing native failure object, preserving every original key.

    This function is used as a pure wrapper around the two pre-existing Python
    expressions, so it cannot suppress the native BAD_WORK validator, alter
    native OPERATIONAL_PAUSE semantics, or convert a rejected plan into Work.
    """
    if not isinstance(original_payload, dict):
        raise TypeError('M233_EXPECT_NATIVE_REJECTION_DICT')
    diagnostic = reference_failure_diagnostic(j, response, native_error)
    if diagnostic is None:
        return original_payload
    if 'm233_reference_diagnostic' in original_payload:
        raise ValueError('M233_DIAGNOSTIC_KEY_COLLISION')
    return {**original_payload, 'm233_reference_diagnostic': diagnostic}
