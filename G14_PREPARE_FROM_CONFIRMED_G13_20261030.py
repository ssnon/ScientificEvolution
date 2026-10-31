#!/usr/bin/env python3
"""Prepare G14 from the SAVED G13 NEXT_GENERATION adjudication, without API calls.

This does not make a scientific decision or run a Worker. It only performs the
same pp.create_cycle operation which autonomous_population.step_once would
perform after the recorded NEXT_GENERATION verdict. Fail closed on drift.
"""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path

EXPECTED_G13_HEAD = '29ee88999d55585a8c12329ef9eb3c0d66b563d7039be974f20a8d215bf4009b'
EXPECTED_META_DECISION = 'M_106011aa29b53d9b57b6a444431e5f'
EXPECTED_G13_EVENTS = 1348
EXPECTED_G13_ASSETS = 413


def inspect(root, mods, pop, pp, aut):
    meta_j, meta_s, _ = aut.meta_check(mods, root)
    if not meta_s.controller_decisions:
        raise RuntimeError('MISSING_META_DECISION')
    decision = meta_s.controller_decisions[-1]
    verdict = json.loads(meta_j.raw(decision['parsed_blob']))
    if decision['id'] != EXPECTED_META_DECISION or verdict.get('decision') != 'NEXT_GENERATION':
        raise RuntimeError('LAST_META_VERDICT_CHANGED')
    if aut.last_meta_outcome(mods, root):
        raise RuntimeError('GLOBAL_TERMINAL_CONFIRMED')
    if any(v['state'] != 'SAVED' for v in meta_s.model_calls.values()):
        raise RuntimeError('META_HAS_UNRESOLVED_CALLS')
    cycle = pp.latest_cycle(root)
    if not cycle or cycle['index'] != 13 or cycle['stage'] != 'COMPLETE':
        raise RuntimeError('EXPECTED_G13_COMPLETE_NOT_FOUND')
    j, s = pop.root_status(mods, cycle['population_root'])
    head = pp.digest(mods, j)
    if (head['events'] != EXPECTED_G13_EVENTS or
            head['head_sha256'] != EXPECTED_G13_HEAD or
            len(s.assets) != EXPECTED_G13_ASSETS):
        raise RuntimeError('G13_JOURNAL_DRIFT')
    if any(v['state'] != 'SAVED' for v in s.model_calls.values()):
        raise RuntimeError('G13_HAS_UNRESOLVED_CALLS')
    if any(w['status'] in ('ACTIVE','QUEUED','DEFERRED') for w in s.work.values()):
        raise RuntimeError('G13_HAS_UNFINISHED_ACTIVE_WORK')
    next_dir = root / 'CYCLE_014'
    if next_dir.exists():
        raise RuntimeError('G14_ALREADY_EXISTS_NO_OVERWRITE')
    return cycle, head, verdict


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--experiment',required=True)
    ap.add_argument('--prepare',action='store_true',help='Create new G14 BASE and SYN peers after validation')
    args = ap.parse_args()
    if os.environ.get('FAKG_RESEARCH_ALLOW_PAID') == 'YES':
        raise RuntimeError('UNSET_PAID_FLAG_FOR_OFFLINE_PREPARATION')
    root = Path(args.experiment).expanduser().resolve()
    if not (root/'STOP_REQUESTED').is_file():
        raise RuntimeError('OPERATOR_STOP_MARKER_REQUIRED')
    import population_run as pop
    import persistent_population as pp
    import autonomous_population as aut
    mods = pop.gen.modules()
    mods.v3.source_code_guard()
    with open(root/'.autonomous_population.lock','a+b') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('ANOTHER_AUTONOMOUS_RUN_ACTIVE')
        try:
            old, source_head, verdict = inspect(root,mods,pop,pp,aut)
            result = {
                'status':'G14_PREPARE_ELIGIBLE_NO_PAID' if not args.prepare else 'G14_PREPARED_FROM_SAVED_SCIENCE_DECISION_NO_PAID',
                'g13_source':old['population_root'],
                'g13_head':source_head,
                'confirmed_existing_meta_decision':EXPECTED_META_DECISION,
                'saved_science_decision':verdict['decision'],
                'next_cycle':14,
                'operator_stop_marker_preserved':True,
                'provider_requests_sent':0,
                'did_not_assign_a_scientific_hypothesis':True,
            }
            if args.prepare:
                fresh = pp.create_cycle(mods,root,14,old.get('initial_peer_count',2),old['population_root'])
                if fresh['stage'] != 'PEERS' or fresh['index']!=14:
                    raise RuntimeError('G14_CYCLE_MANIFEST_UNEXPECTED')
                base,s = pop.root_status(mods,fresh['base'])
                if s.work or s.model_calls or s.controller_decisions or len(s.assets) != EXPECTED_G13_ASSETS:
                    raise RuntimeError('G14_BASE_NOT_CLEANLY_INHERITED')
                for name,peer_path in fresh['peers'].items():
                    pj,ps=pop.root_status(mods,peer_path)
                    if ps.work or ps.model_calls or ps.controller_decisions or len(ps.assets) != EXPECTED_G13_ASSETS:
                        raise RuntimeError('G14_PEER_NOT_CLEANLY_ISOLATED:'+name)
                old_j,old_s=pop.root_status(mods,old['population_root'])
                if pp.digest(mods,old_j)!=source_head:
                    raise RuntimeError('G13_CHANGED_DURING_PREPARE')
                result.update({'g14_stage':fresh['stage'],'g14_base':fresh['base'],
                               'g14_peers':list(fresh['peers']),
                               'g14_inherited_assets':len(s.assets),
                               'no_new_science_claims_or_worker_calls':True,
                               'g13_journal_unchanged':True})
            print(json.dumps(result,indent=2,ensure_ascii=False))
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)

if __name__=='__main__':main()
