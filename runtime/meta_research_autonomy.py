#!/usr/bin/env python3
"""M28-A1 opt-in autonomous research organization runner.

No default generation, peer count, automatic synthesis, or model call. The
operator controls limits; scientists choose organizational requests. New roots
only. Historic roots and their source pins are never patched or migrated.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from e2core.core import EvolutionJournal, EvidenceError, guard, sha, canon
from e2core.meta_autonomy import (POLICY, MODE_BLIND, MODE_TARGETED,
                                 materialize_requests, verify_receipts, recover_committed_requests)

PROTOCOL = 'SCIENTIFIC_META_RESEARCH_AUTONOMY_A1'


def _save_new(path, value):
    path = Path(path)
    guard(not path.exists(), 'META_ORG_NO_OVERWRITE_FILE')
    path.write_bytes(canon(value))


@contextmanager
def _lock(exp):
    with open(exp / '.meta-research-run.lock', 'a+b') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise EvidenceError('META_ORG_CONCURRENT_EXPERIMENT_RUN')
        yield


def _read(exp):
    exp = Path(exp).expanduser().resolve()
    meta = json.loads((exp / 'meta_research.json').read_text(encoding='utf8'))
    guard(meta.get('protocol') == PROTOCOL, 'META_ORG_WRONG_EXPERIMENT')
    guard(meta['root'] == str(exp), 'META_ORG_EXPERIMENT_MOVED')
    return exp, meta


def _roots(exp):
    folder = exp / 'ROOTS'
    return sorted(x for x in folder.iterdir() if x.is_dir() and not x.name.endswith('.STAGING'))


def init(args):
    exp = Path(args.out).expanduser().resolve()
    guard(not exp.exists(), 'META_ORG_EXPERIMENT_EXISTS')
    text = Path(args.problem_file).read_text(encoding='utf8')
    guard(bool(text) and text == text.strip() and len(text) <= 12000,
          'META_ORG_P0_INVALID_OR_EDGE_WHITESPACE')
    exp.mkdir(parents=True)
    try:
        root = exp / 'ROOTS' / 'PRIMARY'
        root.parent.mkdir()
        j = EvolutionJournal(root)
        j.init(text, origin='NEW_META_RESEARCH_AUTONOMY_RESEARCH',
               criteria='Pre-experiment reviewable scientific hypotheses or rigorously scoped conclusions. Pause is not problem completion.')
        j.append('R5_POLICY_ACTIVATED', {'policy': 'OBJECTIVE_AND_DISPOSITION_V1'})
        j.append('E3R1_POLICY_ACTIVATED', {'policy': 'PORTFOLIO_DECISIONS_V1'})
        j.append('META_RESEARCH_AUTONOMY_ACTIVATED', {'policy': POLICY})
        _save_new(exp / 'persistent.json', {'protocol': PROTOCOL,
                  'science_certification': False, 'meta_autonomy_enabled': True})
        _save_new(exp / 'meta_research.json', {'protocol': PROTOCOL, 'root': str(exp),
                  'original_P0_sha256': sha(text.encode('utf8')),
                  'initial_root': str(root), 'science_certification': False,
                  'researcher_count_not_preselected': True,
                  'mandatory_generations': False, 'mandatory_synthesis': False})
        from generational_run import pin_native_source
        pin = pin_native_source(exp)
        guard(j.verify().meta_research_autonomy, 'META_ORG_ACTIVATION_FAILED')
        print(json.dumps({'status': 'META_ORG_INITIALIZED_NO_PAID', 'root': str(root),
                          'source_pinned_files': len(pin['files'])}, ensure_ascii=False))
    except BaseException:
        # Only a brand new destination is deleted after failure. No preexisting
        # root or scientific journal is ever removed by init.
        import shutil
        shutil.rmtree(exp)
        raise


def _preflight(exp, meta):
    from generational_run import modules, verify_runtime_source
    m = modules()
    root = exp / 'ROOTS' / 'PRIMARY'
    primary = EvolutionJournal(root).verify()
    guard(primary.meta_research_autonomy, 'META_ORG_PRIMARY_NOT_ACTIVATED')
    guard(sha(primary.program['problem'].encode('utf8')) == meta['original_P0_sha256'],
          'META_ORG_P0_CHANGED')
    observations = {}
    for subroot in _roots(exp):
        j = EvolutionJournal(subroot)
        s = j.verify()
        guard(s.meta_research_autonomy and s.program['problem'] == primary.program['problem'],
              'META_ORG_CHILD_PROGRAM_MISMATCH')
        verify_runtime_source(m, subroot)
        observations[subroot.name] = {'decisions': len(s.controller_decisions),
                                      'works': len(s.work),
                                      'requests': len(s.organization_requests),
                                      'receipts': verify_receipts(exp, subroot),
                                      'disposition': (s.program_reviews[-1]['scientific_status']
                                                      if s.program_reviews else None),
                                      'saved_calls': sum(c['state'] == 'SAVED' for c in s.model_calls.values())}
    return observations


def preflight(args):
    exp, meta = _read(args.experiment)
    print(json.dumps({'status':'META_ORG_PREFLIGHT_OK_NO_PAID',
        'roots': _preflight(exp, meta)}, ensure_ascii=False, indent=2))


def materialize(args):
    exp, meta = _read(args.experiment)
    with _lock(exp):
        _preflight(exp, meta)
        results = []
        for root in _roots(exp):
            recover_committed_requests(EvolutionJournal(root))
            results.extend(materialize_requests(exp, root, args.max_roots))
        _preflight(exp, meta)
    print(json.dumps({'status': 'META_ORG_MATERIALIZATION_COMPLETE_NO_PAID',
                      'created': results}, ensure_ascii=False, indent=2))


def run(args):
    # This is a real-model interface, not part of A1's offline acceptance. A4
    # scientific performance requires separately approved, controlled runs.
    guard(args.paid and os.environ.get('FAKG_RESEARCH_ALLOW_PAID') == 'YES',
          'META_ORG_PAID_REQUIRES_TWO_EXPLICIT_GATES')
    guard(1 <= args.max_new_calls <= 10000 and 1 <= args.max_root_visits <= 100 and
          1 <= args.max_roots <= 100 and args.slice_budget >= 1,
          'META_ORG_INVALID_OPERATIONAL_CAP')
    exp, meta = _read(args.experiment)
    from generational_run import modules, drive
    m = modules()
    with _lock(exp):
        _preflight(exp, meta)
        for root in _roots(exp):
            recover_committed_requests(EvolutionJournal(root))
            materialize_requests(exp, root, args.max_roots)
        spent = 0; visits = []
        # Operationally bounded round-robin. It does not decide scientific
        # research direction, force synthesis, or terminate the program.
        seen = set()
        for _ in range(args.max_root_visits):
            candidates = [r for r in _roots(exp) if r.name not in seen]
            if not candidates or spent >= args.max_new_calls:
                break
            root = candidates[0]
            seen.add(root.name)
            s = EvolutionJournal(root).verify()
            terminal = bool(s.program_reviews and s.program_reviews[-1]['scientific_status'] in {
                'HOLD_WITH_RATIONALE', 'SCOPED_NEGATIVE', 'REVIEW_WORTHY_CANDIDATE'})
            if not terminal:
                spec = SimpleNamespace(paid=True, model=args.model,
                    max_new_calls=min(args.max_new_calls - spent, args.slice_budget),
                    slice_budget=args.slice_budget,
                    checkpoint_iterations=args.checkpoint_iterations,
                    max_parallel=args.max_parallel, max_tokens=args.max_tokens,
                    science_cpu_seconds=args.science_cpu_seconds,
                    science_wall_seconds=args.science_wall_seconds)
                result = drive(m, root, spec, 'syn')
                spent += result['new_calls_this_launch']
                visits.append({'root': str(root), 'result': result})
            else:
                visits.append({'root': str(root), 'status': 'LOCAL_SCIENTIFIC_STOP'})
            recover_committed_requests(EvolutionJournal(root))
            created = materialize_requests(exp, root, args.max_roots)
            if created:
                visits[-1]['organization_roots_created'] = created
        _preflight(exp, meta)
    print(json.dumps({'status': 'META_ORG_RUN_AT_OPERATIONAL_BOUNDARY',
        'new_model_calls': spent, 'visits': visits,
        'no_scientific_success_claim': True}, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('init');i.add_argument('--problem-file', required=True);i.add_argument('--out', required=True)
    for name in ('preflight','materialize','run'):
        a = sub.add_parser(name)
        a.add_argument('--experiment', required=True)
        if name in ('materialize', 'run'):
            a.add_argument('--max-roots', type=int, default=8,
                           help='Operational safety ceiling, not a scientific researcher count')
        if name == 'run':
            a.add_argument('--paid', action='store_true')
            a.add_argument('--model', default='openai/gpt-5.6-luna')
            a.add_argument('--max-new-calls', type=int, default=16)
            a.add_argument('--max-root-visits', type=int, default=8)
            a.add_argument('--slice-budget', type=int, default=8)
            a.add_argument('--checkpoint-iterations', type=int, default=12)
            a.add_argument('--max-parallel', type=int, default=2)
            a.add_argument('--max-tokens', type=int, default=16000)
            a.add_argument('--science-cpu-seconds', type=int, default=120)
            a.add_argument('--science-wall-seconds', type=int, default=160)
    a = p.parse_args()
    try:
        return {'init': init, 'preflight': preflight,
                'materialize': materialize, 'run': run}[a.cmd](a) or 0
    except (EvidenceError, RuntimeError, FileNotFoundError, ValueError, KeyError) as e:
        print(json.dumps({'status': 'META_ORG_OPERATIONAL_ERROR_NOT_SCIENTIFIC_HOLD',
            'error_type': type(e).__name__, 'reason': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
