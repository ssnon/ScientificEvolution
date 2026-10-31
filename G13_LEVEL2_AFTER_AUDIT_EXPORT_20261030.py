#!/usr/bin/env python3
"""Read-only G13 post-audit scientific trace export.

Requires the original ScientificEvolution Python packages on PYTHONPATH.
Never appends an E2 event, calls a provider, changes experiment state, or
interprets an unregistered model response as a published asset.
"""
import argparse
import hashlib
import json
from pathlib import Path

PREFIX_EVENTS = 1268
PREFIX_HEAD = 'b635f827b27877889da3b2265f2495182f9e608361aea55c63cf8b61b0995fa5'
AUDIT_ID = 'SRC_AUDIT_G13_MC_100d78f17a261a93a72ce048'
TARGET_WORK = 'W_develop_finite_exposure_adversarial_model_001'
FRESH_WORK = 'W_fresh_sers_joint_evidence_audit_001'


def text_summary(text, limit=2400):
    if not isinstance(text, str):
        return None
    if len(text) <= limit:
        return text
    return text[: limit // 2] + '\n...[CONTENT TRUNCATED; ORIGINAL IN JOURNAL]...\n' + text[-limit // 2:]


def load_json(data):
    try:
        return json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


def worker_steps(j, w, min_step=1):
    results = []
    for st in w['steps']:
        if st.get('step', 0) < min_step:
            continue
        obj = load_json(j.raw(st['raw_blob']))
        record = {'step': st['step'], 'kind': st['kind']}
        if not isinstance(obj, dict):
            record['unreadable_or_nonobject_raw_sha256'] = st['raw_blob']
        elif st['kind'] == 'MODEL_RESPONSE':
            raw = obj.get('text')
            decoded = load_json(raw)
            record['call_id'] = obj.get('call_id')
            record['parse_ok'] = obj.get('parse_ok')
            record['raw_text_chars'] = len(raw) if isinstance(raw, str) else None
            if isinstance(decoded, dict):
                record['next_action'] = decoded.get('next_action')
                record['scientific_text'] = text_summary(decoded.get('scientific_text'), 15000)
                record['submitted_asset_ids'] = [a.get('id') for a in decoded.get('assets', []) if isinstance(a, dict)]
                record['submitted_problem_ids'] = [p.get('id') for p in decoded.get('new_problems', []) if isinstance(p, dict)]
                if isinstance(decoded.get('tool_request'), dict):
                    tool = decoded['tool_request']
                    record['tool_request_kind'] = tool.get('kind')
                    record['tool_request_arguments_sha256'] = hashlib.sha256(json.dumps(tool.get('arguments'), sort_keys=True, default=str).encode()).hexdigest()
            else:
                record['unparsed_model_response_excerpt'] = text_summary(raw, 3000)
        elif st['kind'] == 'OUTPUT_VALIDATION':
            for key in ('status', 'accepted', 'rejected', 'local_problem_id_mapping', 'local_asset_id_mapping'):
                if key in obj:
                    record[key] = obj[key]
        elif st['kind'] == 'TOOL_RESULT':
            result = obj.get('result') or {}
            record.update({'tool_id': obj.get('tool_id'), 'tool_status': result.get('status'),
                           'code_sha256': result.get('code_sha256'), 'exit_code': result.get('exit_code')})
        else:
            record['record_excerpt'] = text_summary(json.dumps(obj, ensure_ascii=False, default=str), 2400)
        results.append(record)
    return results


def wire_user(j, call):
    raw = load_json(j.raw(call['request_blob']))
    if not isinstance(raw, dict):
        return None
    messages = raw.get('messages') or []
    for msg in messages:
        if isinstance(msg, dict) and msg.get('role') == 'user':
            val = msg.get('content')
            return load_json(val) if isinstance(val, str) else val
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--out', default=str(Path.home() / 'G13_LEVEL2_AFTER_AUDIT_REVIEW.json'))
    args = parser.parse_args()
    import population_run as pop
    mods = pop.gen.modules()
    root = Path(args.experiment).expanduser().resolve() / 'CYCLE_013' / 'POPULATION'
    j = mods.J(root)
    s = j.verify()
    events = j._events()
    if len(events) < PREFIX_EVENTS or mods.sha(mods.canon(events[PREFIX_EVENTS-1])) != PREFIX_HEAD:
        raise RuntimeError('G13_ORIGINAL_1268_EVENT_PREFIX_CHANGED_OR_WRONG_EXPERIMENT')

    recent = events[PREFIX_EVENTS:]
    new_assets = [e['payload']['id'] for e in recent if e['kind'] == 'ASSET_PUBLISHED']
    audit_source = s.sources.get(AUDIT_ID)
    audit_record = None
    if audit_source:
        audit_record = load_json(j.raw(audit_source['blob']))
    target_call_id = 'WK_' + TARGET_WORK + '_00004'
    target_call = s.model_calls.get(target_call_id)
    target_wire = wire_user(j, target_call) if target_call else None
    disclosure = target_wire.get('independent_external_science_audit') if isinstance(target_wire, dict) else None

    fresh_calls = []
    for ident, call in s.model_calls.items():
        if call.get('actor') == 'WORKER' and call.get('work_id') == FRESH_WORK:
            user = wire_user(j, call)
            exposed = isinstance(user, dict) and ('independent_external_science_audit' in user or AUDIT_ID in json.dumps(user, ensure_ascii=False))
            fresh_calls.append({'call_id': ident, 'state': call.get('state'), 'audit_exposed': exposed})

    reviewed_works = {}
    for wid, first in ((TARGET_WORK, 4), (FRESH_WORK, 3), ('W_develop_selective_intervention_boundary_001', 19)):
        w = s.work.get(wid)
        if w:
            reviewed_works[wid] = {'status': w['status'], 'mode': w.get('mode'), 'step_count': len(w['steps']),
                                   'registered_asset_ids': list(w.get('published', [])),
                                   'steps_from_selected_position': worker_steps(j, w, first)}

    checks = {
        'registered_audit_source_kind': audit_source.get('kind') if audit_source else None,
        'registered_audit_has_original_packet': isinstance(audit_record, dict) and isinstance(audit_record.get('record'), dict),
        'target_step4_call_exists': target_call is not None,
        'target_step4_call_saved': target_call.get('state') == 'SAVED' if target_call else False,
        'target_step4_wire_contains_external_audit': isinstance(disclosure, dict),
        'target_step4_wire_references_registered_audit_id': isinstance(disclosure, dict) and disclosure.get('id') == AUDIT_ID,
        'target_step4_wire_packet_matches_registered_source': isinstance(disclosure, dict) and isinstance(audit_record, dict) and disclosure.get('packet') == {k: v for k, v in audit_record.get('record', {}).items() if k != 'redox_unregistered_candidate_notice'},
        'fresh_calls_reviewed': len(fresh_calls),
        'fresh_calls_with_audit_exposure': [c['call_id'] for c in fresh_calls if c['audit_exposed']],
        'rotational_work_in_this_population_root': 'W_challenge_rotational_feasibility_001' in s.work,
    }
    output = {
        'status': 'READ_ONLY_SCIENTIFIC_AFTER_AUDIT_EXPORT',
        'journal_path': str(root), 'original_prefix_verified': True,
        'journal_event_count': len(events), 'journal_head_sha256': mods.sha(mods.canon(events[-1])),
        'new_event_kind_counts': {k: sum(e['kind']==k for e in recent) for k in sorted({e['kind'] for e in recent})},
        'new_registered_assets': [s.assets[x] for x in new_assets],
        'registered_audit_source_id': AUDIT_ID if audit_source else None,
        'target_step4_call_id': target_call_id,
        'audit_delivery_checks': checks,
        'fresh_worker_calls': fresh_calls,
        'reviewed_works': reviewed_works,
        'current_work_statuses': {k: v['status'] for k, v in s.work.items()},
        'new_tool_metadata': [dict(e['payload']) for e in recent if e['kind']=='TOOL_RECORDED'],
        'new_controller_decisions': [{'id': e['payload'].get('id'), 'call_id': e['payload'].get('call_id'),
                                       'rationale': e['payload'].get('rationale')} for e in recent if e['kind']=='CONTROLLER_DECISION'],
        'read_only': True, 'provider_requests_sent_by_this_script': 0,
        'note': 'Scientific and provenance inspection only; cannot certify Level II or infer billing.'
    }
    # Check that the journal did not change during reading. Stop on concurrent modifications.
    end = j._events()
    if len(end) != len(events) or mods.sha(mods.canon(end[-1])) != output['journal_head_sha256']:
        raise RuntimeError('CONCURRENT_JOURNAL_CHANGE_RETRY_WHILE_STOPPED')
    destination = Path(args.out).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'status': output['status'], 'report': str(destination),
                      'journal_events': len(events), 'new_asset_ids': new_assets,
                      'audit_delivery_checks': checks,
                      'work_statuses': output['current_work_statuses'],
                      'provider_requests_sent_by_this_script': 0}, indent=2, ensure_ascii=False))

if __name__=='__main__':
    main()
