#!/usr/bin/env python3
"""Exact no-paid no-mutation guard for this G14/SYN_01 continuation."""
import argparse
import json
from pathlib import Path
import population_run as pop
import persistent_population as pp

EXPECTED_HEAD = '695187b5ab98889dc8808a9160667b0479e14925a341db00b2a030d7ace6e59f'
TARGET_WORK = 'W_unique_targeted_sers_prior_art_001'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--experiment',required=True)
    opts=ap.parse_args()
    exp=Path(opts.experiment).expanduser().resolve()
    mods=pop.gen.modules()
    cycle=pp.latest_cycle(exp)
    if cycle is None or cycle['index']!=14 or cycle['stage']!='PEERS':
        raise RuntimeError('G14_NOT_AT_EXPECTED_PEER_STAGE')
    peer=Path(cycle['peers']['SYN_01'])
    j,s=pop.root_status(mods,peer)
    initial=pp.digest(mods,j)
    if initial['events']!=1058 or initial['head_sha256']!=EXPECTED_HEAD:
        raise RuntimeError('SYN01_JOURNAL_NOT_MATCH_EXPECTED_CHECKPOINT:'+str(initial))
    if s.work[TARGET_WORK]['status']!='ACTIVE' or s.work[TARGET_WORK]['mode']!='FRESH':
        raise RuntimeError('FRESH_RESEARCH_WORK_NOT_ACTIVE')
    if len(s.work[TARGET_WORK]['steps'])!=8:
        raise RuntimeError('NEXT_WORKER_STEP_NOT_EXPECTED_9')
    if len(s.assets)!=413:
        raise RuntimeError('ASSET_COUNT_CHANGED')
    if any(x['state']!='SAVED' for x in s.model_calls.values()):
        raise RuntimeError('UNSAVED_MODEL_CALL_BILLING_UNCERTAIN')
    if not (exp/'STOP_REQUESTED').exists():
        raise RuntimeError('REQUIRE_STOP_MARKER_WHILE_CHECKING')
    other,os=pop.root_status(mods,cycle['peers']['SYN_02'])
    if os.work or os.controller_decisions or os.model_calls:
        raise RuntimeError('SYN02_INDEPENDENT_RESEARCH_ALREADY_STARTED')
    if pp.digest(mods,j)!=initial:
        raise RuntimeError('PRECHECK_MUTATED_JOURNAL')
    print(json.dumps({'status':'G14_PDF_EVIDENCE_EXTENSION_READY_NO_PAID',
        'cycle':14,'stage':cycle['stage'],'target_peer':'SYN_01',
        'target_work':TARGET_WORK,'target_next_worker_step':9,
        'note_next_default_peer':'SYN_02 likely first: scheduler favors fewer saved calls',
        'root_head':initial,'syn02_still_independent_and_unstarted':True,
        'operator_stop_preserved':True,'journal_unchanged':True,
        'provider_requests_sent':0},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as ex:
        print(json.dumps({'status':'G14_PDF_EXTENSION_PREFLIGHT_BLOCKED_NO_PAID',
            'error':str(ex),'provider_requests_sent':0}))
        raise SystemExit(3)
