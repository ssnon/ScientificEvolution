#!/usr/bin/env python3
"""G13 read-only Level-II science and meta-decision report.

Use with ScientificEvolution's verified modules on PYTHONPATH.
Does not call providers, write the Journal, change a cycle, or infer a scientific certificate.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

G13_PREFIX_EVENTS = 1313
G13_PREFIX_HEAD = '7fbab93817ceb7ff7e55ad5e41fafe8df1627be09dcb10c08d63d9d216cc6ae4'
INTERESTING_WORK = ('W_develop_finite_exposure_adversarial_model_001',
                    'W_fuse_charge_finite_exposure_joint_model_001')
INTERESTING_ASSET = ('A_joint_charge_intervention_factorial_identifiability_001',
                     'A_finite_exposure_continuous_smoothing_bound_003')


def jdecode(raw):
    try:
        return json.loads(raw)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None


def parse_worker_step(j, step):
    obj = jdecode(j.raw(step['raw_blob']))
    result = {'step': step.get('step'), 'kind': step.get('kind')}
    if not isinstance(obj, dict):
        result['raw_blob_sha256'] = step['raw_blob']
        return result
    if step['kind'] == 'MODEL_RESPONSE':
        parsed = jdecode(obj.get('text'))
        result.update({'call_id': obj.get('call_id'), 'parse_ok': obj.get('parse_ok')})
        if isinstance(parsed, dict):
            result.update({'scientific_text': parsed.get('scientific_text'),
                           'next_action': parsed.get('next_action'),
                           'submitted_asset_ids': [a.get('id') for a in parsed.get('assets', []) if isinstance(a, dict)],
                           'new_problem_ids': [p.get('id') for p in parsed.get('new_problems', []) if isinstance(p, dict)],
                           'tool_request_kind': (parsed.get('tool_request') or {}).get('kind') if isinstance(parsed.get('tool_request'), dict) else None})
        else:
            result['unparsed_response_excerpt'] = str(obj.get('text', ''))[:2500]
    elif step['kind'] == 'TOOL_RESULT':
        inner = obj.get('result') or {}
        result.update({'tool_id': obj.get('tool_id'), 'result_status': inner.get('status'),
                       'code_sha256': inner.get('code_sha256'), 'exit_code': inner.get('exit_code'),
                       'result_excerpt': json.dumps(inner, ensure_ascii=False, default=str)[:1600]})
    elif step['kind'] == 'OUTPUT_VALIDATION':
        result.update({key: obj.get(key) for key in ('status', 'accepted', 'rejected')})
    else:
        result['metadata'] = obj
    return result


def asset_packet(state, aid):
    a = state.assets[aid]
    parents = []
    for pid in a.get('parent_ids', []):
        p = state.assets.get(pid)
        parents.append({'id': pid, 'found_in_journal': p is not None,
                        'kind': p.get('kind') if p else None,
                        'claim': p.get('claim') if p else None,
                        'delta_from_parents': p.get('delta_from_parents') if p else None,
                        'predictions': p.get('predictions', []) if p else []})
    return {'registered_asset': a, 'parents': parents,
            'source_kinds': {sid: state.sources[sid]['kind'] if sid in state.sources else 'NOT_REGISTERED'
                             for sid in a.get('source_ids', [])},
            'qualification_questions': {
                'physical_mechanism': 'What new SERS causal mechanism does the claim posit, rather than a generic inference method?',
                'mechanistic_feasibility': 'What equations, parameter bounds, and calibrated physical constraints support it?',
                'strong_null': 'Can a non-charge / continuous orientation / hotspot null reproduce the joint prediction?',
                'novelty': 'Which inspected primary papers already establish the same causal claim or intervention prediction?',
                'falsifier': 'Which preregistered observable and intervention distinguish the mechanism after nuisance matching?',
            }}


def inspect_meta(mods, exp):
    root = exp / 'AUTONOMOUS_META'
    if not (root / 'manifest.json').is_file():
        return {'present': False, 'path': str(root)}
    j = mods.J(root)
    s = j.verify()
    rows = j._events()
    choices = []
    for d in s.controller_decisions[-7:]:
        parsed = jdecode(j.raw(d['parsed_blob'])) or {}
        request = s.model_calls.get(d['call_id'])
        stage = None
        if request:
            wire = jdecode(j.raw(request['request_blob'])) or {}
            messages = wire.get('messages', [])
            for msg in messages:
                if msg.get('role') == 'user':
                    inp = jdecode(msg.get('content'))
                    if isinstance(inp, dict):
                        stage = inp.get('stage')
                    break
        choices.append({'id': d['id'], 'decision_or_assessment': parsed.get('decision', parsed.get('assessment')),
                        'rationale': parsed.get('rationale'), 'stage_in_input': stage,
                        'remaining_opportunities': parsed.get('remaining_opportunities', []),
                        'review_call_id': d['call_id']})
    return {'present': True, 'path': str(root), 'events': len(rows),
            'head_sha256': mods.sha(mods.canon(rows[-1])) if rows else None,
            'recent_decisions': choices,
            'latest_program_reviews': s.program_reviews[-4:],
            'confirmed_global_terminal': any((jdecode(j.raw(d['parsed_blob'])) or {}).get('decision') == 'CONFIRM_TERMINAL'
                                             for d in s.controller_decisions),
            'unresolved_model_calls': [cid for cid, c in s.model_calls.items() if c['state'] != 'SAVED']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment', required=True)
    p.add_argument('--out', default=str(Path.home() / 'G13_LEVEL2_FUSION_AND_GENERATION_REVIEW.json'))
    a = p.parse_args()
    import population_run as pop
    mods = pop.gen.modules()
    exp = Path(a.experiment).expanduser().resolve()
    root = exp / 'CYCLE_013' / 'POPULATION'
    j = mods.J(root)
    s = j.verify()
    events = j._events()
    if len(events) < G13_PREFIX_EVENTS or mods.sha(mods.canon(events[G13_PREFIX_EVENTS - 1])) != G13_PREFIX_HEAD:
        raise RuntimeError('G13_PREFIX_MISMATCH_OR_WRONG_EXPERIMENT: refusal to interpret')
    start_head = mods.sha(mods.canon(events[-1]))
    delta = events[G13_PREFIX_EVENTS:]
    ids = [x['payload']['id'] for x in delta if x['kind'] == 'ASSET_PUBLISHED']
    if any(i not in s.assets for i in ids):
        raise RuntimeError('ASSET_EVENT_MISSING_FROM_VERIFIED_JOURNAL')
    works = {}
    for wid in INTERESTING_WORK:
        if wid not in s.work:
            works[wid] = {'registered': False}
            continue
        w = s.work[wid]
        works[wid] = {'registered': True, 'status': w['status'], 'operation': w.get('operation'),
                      'mode': w.get('mode'), 'question': w.get('question'),
                      'research_rationale': w.get('research_rationale'), 'asset_input_ids': w.get('asset_input_ids', []),
                      'published': w.get('published', []), 'outcome': w.get('outcome'),
                      'steps': [parse_worker_step(j, t) for t in w['steps'][-7:]]}
    decisions = []
    for e in delta:
        if e['kind'] == 'CONTROLLER_DECISION':
            x = e['payload']; obj = jdecode(j.raw(x['parsed_blob'])) or {}
            decisions.append({'id': x['id'], 'disposition': obj.get('disposition'),
                              'rationale': obj.get('rationale'), 'actions': obj.get('actions', [])})
    cycle_files = sorted(exp.glob('CYCLE_*/cycle.json'), key=lambda f: int(f.parent.name.split('_')[-1]))
    cycles = [{'index': c.parent.name, 'stage': json.loads(c.read_text(encoding='utf-8')).get('stage')}
              for c in cycle_files]
    report = {
        'status': 'READ_ONLY_G13_LEVEL2_FUSION_AND_GENERATION_REVIEW',
        'g13_root': str(root), 'events': len(events), 'head_sha256': start_head,
        'original_1313_event_prefix_verified': True,
        'new_event_kinds': dict(Counter(e['kind'] for e in delta)),
        'new_assets_since_1313': {aid: asset_packet(s, aid) for aid in ids},
        'named_candidate_assets': {aid: asset_packet(s, aid) if aid in s.assets else {'registered': False}
                                   for aid in INTERESTING_ASSET},
        'work_details': works,
        'new_controller_decisions': decisions,
        'g13_local_program_reviews': s.program_reviews[-3:],
        'g13_work_statuses': {k: v['status'] for k, v in s.work.items()},
        'cycles': cycles, 'current_cycle': cycles[-1] if cycles else None,
        'g14_created': any(x['index'] == 'CYCLE_014' for x in cycles),
        'meta': inspect_meta(mods, exp),
        'read_only': True, 'provider_requests_sent_by_this_script': 0,
        'science_certified': False,
    }
    end = j._events()
    if len(end) != len(events) or mods.sha(mods.canon(end[-1])) != start_head:
        raise RuntimeError('CONCURRENT_G13_JOURNAL_MUTATION_RETRY_WHEN_STOPPED')
    if report['meta'].get('present'):
        check = mods.J(exp / 'AUTONOMOUS_META')._events()
        if len(check) != report['meta']['events'] or mods.sha(mods.canon(check[-1])) != report['meta']['head_sha256']:
            raise RuntimeError('CONCURRENT_META_JOURNAL_MUTATION_RETRY_WHEN_STOPPED')
    output = Path(a.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'output': str(output), 'g13_events': len(events),
                      'new_asset_ids': ids, 'new_work_statuses': {k: v['status'] if v['registered'] else 'NOT_FOUND'
                                                                  for k,v in works.items()},
                      'current_cycle': report['current_cycle'], 'g14_created': report['g14_created'],
                      'global_terminal_confirmed': report['meta'].get('confirmed_global_terminal'),
                      'read_only': True, 'provider_requests_sent_by_this_script': 0}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
