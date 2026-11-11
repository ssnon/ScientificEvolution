"""M28 audited runtime-successor: exact Journal prefix, new source pin, no re-billing.

This is an operational branch of an existing research Journal, not a new FRESH
researcher. Existing scientific outputs are unverified historical model work.
The original experiment and its native source pin are never mutated.
"""
from __future__ import annotations
import hashlib
import json
import os
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import shutil
import sqlite3
import subprocess

from .core import EvolutionJournal, EvidenceError, canon, sha, guard
from .activation_contract import check_m28_experiment, digest as profile_digest
from .meta_scheduler import M28_RECOVERY_MARKER

PROTOCOL = 'M28_NATIVE_RESEARCH_SUCCESSOR_V1'
FILE = 'M28_NATIVE_RESEARCH_SUCCESSOR.json'
ORIGINAL_COMMIT = '9487b96'
# Exact pin of the first successor (_03); no arbitrary ref or current HEAD.
FIRST_SUCCESSOR_COMMIT = 'd931063'


def _require(ok, code):
    guard(ok, 'M28_SUCCESSOR:' + code)


def _read_json(path):
    p=Path(path)
    _require(p.is_file() and not p.is_symlink(), 'FILE_INVALID:'+str(p))
    return json.loads(p.read_text(encoding='utf8'))


def _no_symlinks(tree):
    tree=Path(tree)
    for p in (tree, *tree.rglob('*')):
        _require(not p.is_symlink(), 'SOURCE_SYMLINK:'+str(p))
        _require(p.is_file() or p.is_dir(), 'SOURCE_NONREGULAR_FILE:'+str(p))


def _read_parent_cost(exp, expected_call_ids):
    # The inherited Journal may include upstream paid calls. Only model calls
    # genuinely made IN THE CURRENT experiment have budget ledger entries.
    # Compare exact IDs, not merely totals: missing/duplicate or stale rows
    # must fail closed rather than silently undercount expenditure.
    db=exp/'.M232_DEV_BUDGET.sqlite3'
    _require(db.is_file() and not db.is_symlink(), 'ORIGINAL_BUDGET_DB_MISSING')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        rows=conn.execute('SELECT call_id,state,reserved_usd,actual_usd FROM calls').fetchall()
    ids=[x[0] for x in rows]
    _require(len(ids)==len(set(ids)) and set(ids)==set(expected_call_ids),
             'ORIGINAL_LEDGER_CALL_IDS_MISMATCH')
    _require(all(st=='SAVED' and actual is not None and
                 Decimal(str(actual)).is_finite() and Decimal(str(actual))>=0
                 for _cid,st,_reserved,actual in rows),
             'ORIGINAL_BUDGET_NOT_ALL_SETTLED')
    return sum((Decimal(str(actual)) for _cid,_st,_res,actual in rows),
               Decimal('0'))


def _verify_origin_source_pin(repo, original_pin, commit):
    _require(commit in {ORIGINAL_COMMIT,FIRST_SUCCESSOR_COMMIT},
             'UNSUPPORTED_PARENT_SOURCE_COMMIT')
    _require(original_pin.get('protocol')=='M16_NATIVE_EXECUTION_SOURCE_V1',
             'ORIGINAL_SOURCE_PIN_PROTOCOL')
    _require(original_pin.get('repository')==str(repo), 'ORIGINAL_REPOSITORY_MISMATCH')
    files=original_pin.get('files')
    _require(isinstance(files,dict) and bool(files), 'ORIGINAL_SOURCE_PIN_EMPTY')
    for rel,expected in files.items():
        _require(isinstance(rel,str) and rel.startswith(('runtime/','AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/'))
                 and '..' not in Path(rel).parts, 'ORIGINAL_SOURCE_PATH_INVALID')
        try:
            raw=subprocess.check_output(['git','show',commit+':'+rel],cwd=repo,
                                        stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            raise EvidenceError('M28_SUCCESSOR:ORIGINAL_COMMIT_FILE_MISSING:'+rel) from e
        _require(hashlib.sha256(raw).hexdigest()==expected,
                 'ORIGINAL_SOURCE_NOT_EXACT_GIT_COMMIT:'+rel)
    return len(files)


def verify_successor_prefix(exp):
    """Verify the immutable upstream event prefix and explicit operational handoff.

    May run after new model calls; no assumption about future event count.
    Does not rewrite events or assert that copied science is correct.
    """
    exp=Path(exp).expanduser().resolve()
    lineage_path=exp/FILE
    lineage=_read_json(lineage_path)
    _require(lineage.get('protocol')==PROTOCOL, 'LINEAGE_PROTOCOL')
    persistent=_read_json(exp/'persistent.json')
    meta=_read_json(exp/'meta_research.json')
    digest=sha(lineage_path.read_bytes())
    _require(persistent.get('native_successor_sha256')==digest and
             meta.get('native_successor_sha256')==digest, 'LINEAGE_MANIFEST_HASH_MISMATCH')
    _require(meta.get('root')==str(exp) and meta.get('initial_root')==str(exp/'ROOTS'/'PRIMARY'),
             'LINEAGE_EXPERIMENT_IDENTITY')
    root=exp/'ROOTS'/'PRIMARY'
    j=EvolutionJournal(root)
    rows=j._events()
    n=lineage['parent_events']
    _require(type(n)==int and n>0 and len(rows)>n, 'LINEAGE_EVENT_COUNT')
    _require(sha(canon(rows[n-1]))==lineage['parent_head_sha256'], 'LINEAGE_PARENT_HEAD_CHANGED')
    _require(rows[n]['kind']=='OPERATIONAL_PAUSE' and
             rows[n]['payload'].get('reason')==M28_RECOVERY_MARKER and
             rows[n]['payload'].get('parent_head_sha256')==lineage['parent_head_sha256'],
             'LINEAGE_HANDOFF_MARKER_INVALID')
    _require(sha((root/'manifest.json').read_bytes())==lineage['parent_journal_manifest_sha256'],
             'LINEAGE_ORIGINAL_JOURNAL_MANIFEST_CHANGED')
    for name in lineage['parent_blob_names']:
        _require(isinstance(name,str) and len(name)==64 and
                 (root/'blobs'/name).is_file() and
                 hashlib.sha256((root/'blobs'/name).read_bytes()).hexdigest()==name,
                 'LINEAGE_PARENT_BLOB_MISSING_OR_CHANGED:'+name)
    budget=_read_json(exp/'M232_DEV_BUDGET.json')
    _require(abs(Decimal(str(budget['limit_usd']))-Decimal(str(lineage['successor_budget_limit_usd'])))<Decimal('0.000000001'),
             'LINEAGE_BUDGET_CHANGED')
    _require(abs(Decimal(str(lineage['original_budget_limit_usd']))-
                 Decimal(str(lineage['accounted_upstream_usd']))-
                 Decimal(str(lineage['successor_budget_limit_usd'])))<Decimal('0.00000002'),
             'LINEAGE_BUDGET_DOES_NOT_CONSERVE_TOTAL')
    _require(meta['original_P0_sha256']==lineage['original_P0_sha256'],
             'LINEAGE_P0_DIGEST_CHANGED')
    # Re-verify the A/B baseline's immutable journal head and billed calls.
    # It is accounted for in the original experiment budget, but never copied
    # into the counterfactual science input or presented to the Controller.
    baseline=lineage.get('comparison_baseline')
    if baseline is not None:
        cmp_exp=Path(baseline['experiment']).resolve()
        parent=Path(lineage['upstream_experiment']).resolve()
        _require(cmp_exp.parent==parent.parent and cmp_exp!=parent,
                 'LINEAGE_COMPARATOR_LOCATION_DRIFT')
        cmp_lineage=_read_json(cmp_exp/FILE)
        _require(cmp_lineage['upstream_experiment']==str(parent) and
                 cmp_lineage['parent_head_sha256']==baseline['parent_head_sha256'] and
                 cmp_lineage['parent_events']==lineage['parent_events'] and
                 baseline['parent_head_sha256']==lineage['parent_head_sha256'],
                 'LINEAGE_COMPARATOR_INPUT_DRIFT')
        cj=EvolutionJournal(cmp_exp/'ROOTS'/'PRIMARY')
        crows=cj._events();cs=cj.verify()
        _require(sha(canon(crows[-1]))==baseline['terminal_head_sha256'] and
                 cs.program_reviews[-1]['scientific_status']==baseline['disposition'] and
                 all(c['state']=='SAVED' for c in cs.model_calls.values()),
                 'LINEAGE_COMPARATOR_TERMINAL_DRIFT')
        ids={e['payload']['id'] for e in crows[cmp_lineage['parent_events']+1:]
             if e['kind']=='MODEL_CALL_INTENT'}
        _require(ids==set(baseline['new_call_ids']) and
                 len(ids)==len(cs.model_calls)-cmp_lineage['parent_calls_saved'],
                 'LINEAGE_COMPARATOR_CALLS_DRIFT')
        actual=_read_parent_cost(cmp_exp,ids)
        _require(abs(actual-Decimal(str(baseline['actual_usd'])))<
                 Decimal('0.00000001') and
                 abs(Decimal(str(lineage['accounted_upstream_usd']))-
                     Decimal(str(lineage['direct_parent_spent_usd']))-actual)<
                 Decimal('0.00000002'),
                 'LINEAGE_COMPARATOR_BUDGET_DRIFT')
    if lineage.get('parent_successor_lineage_sha256') is not None:
        upstream=Path(lineage['upstream_experiment'])
        upstream_lineage=_read_json(upstream/FILE)
        _require(sha((upstream/FILE).read_bytes())==
                 lineage['parent_successor_lineage_sha256'],
                 'LINEAGE_UPSTREAM_LINK_CHANGED')
        _require(upstream_lineage.get('protocol')==PROTOCOL and
                 upstream_lineage['parent_native_source_commit']==ORIGINAL_COMMIT,
                 'LINEAGE_UPSTREAM_CHAIN_UNSUPPORTED')
        _require(abs(Decimal(str(lineage['original_total_budget_usd']))-
                     Decimal(str(lineage['cumulative_upstream_accounted_usd']))-
                     Decimal(str(lineage['successor_budget_limit_usd'])))<
                 Decimal('0.00000003'), 'LINEAGE_ORIGINAL_TOTAL_BUDGET_NOT_CONSERVED')
    else:
        # The d931063 first successor remains valid with its old schema.
        _require(abs(Decimal(str(lineage['original_budget_limit_usd']))-
                     Decimal(str(lineage['accounted_upstream_usd']))-
                     Decimal(str(lineage['successor_budget_limit_usd'])))<
                 Decimal('0.00000002'), 'LINEAGE_FIRST_SUCCESSOR_BUDGET_NOT_CONSERVED')
    return {'status':'M28_NATIVE_SUCCESSOR_PREFIX_VERIFIED_NO_PAID',
            'parent_events':n, 'parent_head_sha256':lineage['parent_head_sha256'],
            'parent_calls_saved':lineage['parent_calls_saved'],
            'parent_assets':lineage['parent_assets'],
            'upstream_accounted_usd':lineage['accounted_upstream_usd'],
            'successor_budget_limit_usd':lineage['successor_budget_limit_usd'],
            'original_preserved':True}


def build_successor(parent, dest, *, dry_run=False, comparison_baseline=None):
    """Create a new, source-pinned continuation from a quiescent M28 ROOT.

    Execution must be separately authorized. This function makes NO model calls,
    writes NOTHING in parent, and aborts if any previous call is unresolved.
    """
    _require(os.environ.get('FAKG_RESEARCH_ALLOW_PAID')!='YES', 'PAID_FLAG_MUST_BE_UNSET')
    parent=Path(parent).expanduser().resolve()
    dest=Path(dest).expanduser().resolve()
    _require(parent.is_dir() and parent!=dest and not dest.exists(), 'DESTINATION_NOT_NEW_OR_PARENT_INVALID')
    _require(not dest.is_relative_to(parent) and not parent.is_relative_to(dest),
             'NESTED_EXPERIMENTS_FORBIDDEN')
    repo=Path(__file__).resolve().parents[2]
    _require(parent.parent==dest.parent, 'SUCCESSOR_REQUIRES_SAME_EXPERIMENT_PARENT_DIRECTORY')
    # One verified successive continuation is supported: _02 -> _03 -> _04.
    # The prior _03 experiment is never edited. Do not silently permit a later
    # chain depth with an unrecognized runtime source pin.
    previous_lineage = None
    if (parent/FILE).exists():
        verify_successor_prefix(parent)
        previous_lineage = _read_json(parent/FILE)
        _require(previous_lineage.get('parent_native_source_commit') == ORIGINAL_COMMIT and
                 not previous_lineage.get('parent_successor_lineage_sha256'),
                 'UNSUPPORTED_SUCCESSOR_CHAIN_DEPTH')
    parent_commit = (FIRST_SUCCESSOR_COMMIT if previous_lineage is not None
                     else ORIGINAL_COMMIT)
    _require(not (parent/'ROOTS').is_symlink() and not (parent/'ROOTS'/'PRIMARY').is_symlink(),
             'ORIGINAL_ROOT_SYMLINK')
    roots=[x.name for x in (parent/'ROOTS').iterdir() if x.is_dir()]
    _require(roots==['PRIMARY'], 'ORIGINAL_MULTIPLE_ROOTS_REQUIRES_SEPARATE_MIGRATION')
    oldroot=parent/'ROOTS'/'PRIMARY'
    _no_symlinks(oldroot)
    oldmeta=_read_json(parent/'meta_research.json')
    oldpersistent=_read_json(parent/'persistent.json')
    pinpath=parent/'NATIVE_RUNTIME_SOURCE_PIN.json'
    pin=_read_json(pinpath)
    _require(oldmeta.get('root')==str(parent) and oldmeta.get('initial_root')==str(oldroot),
             'ORIGINAL_MANIFEST_IDENTITY_MISMATCH')
    _require(oldmeta.get('protocol')=='SCIENTIFIC_META_RESEARCH_AUTONOMY_A1' and
             oldpersistent.get('protocol')==oldmeta['protocol'],
             'NOT_AN_M28_EXPERIMENT')
    _require(oldpersistent.get('activation_profile') is not None, 'ORIGINAL_PROFILE_MISSING')
    _require(oldpersistent.get('activation_profile_sha256')==
             profile_digest(oldpersistent['activation_profile']), 'ORIGINAL_PROFILE_DRIFT')
    _require(_verify_origin_source_pin(repo,pin,parent_commit)>0,
             'ORIGINAL_SOURCE_UNVERIFIED')
    j=EvolutionJournal(oldroot)
    state=j.verify()
    events=j._events()
    _require(state.meta_research_autonomy and state.meta_collaboration and
             state.program_reviews and state.program_reviews[-1]['scientific_status']=='ONGOING',
             'ORIGINAL_NOT_PENDING_TERMINAL_REVIEW')
    _require(state.controller_decisions and not state.organization_requests and
             not state.organization_materialized and
             not any(w['status']!='DONE' for w in state.work.values()),
             'ORIGINAL_HAS_ACTIVE_WORK_OR_CHILD_REQUESTS')
    _require(all(c['state']=='SAVED' for c in state.model_calls.values()),
             'UNRESOLVED_PROVIDER_CALLS_MANUAL_REVIEW')
    last_dec=max(i for i,e in enumerate(events) if e['kind']=='CONTROLLER_DECISION')
    _require(any(e['kind']=='OPERATIONAL_PAUSE' and
                 str(e['payload'].get('reason','')).startswith('CONTROLLER_PLAN_REJECTED:')
                 for e in events[last_dec+1:]),
             'NO_REJECTED_TERMINAL_PLAN_TO_RECOVER')
    _require(sha(state.program['problem'].encode('utf8'))==oldmeta['original_P0_sha256'],
             'ORIGINAL_P0_DRIFT')
    oldbudget=_read_json(parent/'M232_DEV_BUDGET.json')
    old_cap=Decimal(str(oldbudget['limit_usd']))
    if previous_lineage is None:
        expected_paid_ids = set(state.model_calls)
        cumulative_previous_cost = Decimal('0')
        initial_total_budget = old_cap
    else:
        inherited_n = previous_lineage['parent_events']
        expected_paid_ids = {e['payload']['id'] for e in events[inherited_n+1:]
                             if e['kind']=='MODEL_CALL_INTENT'}
        _require(len(expected_paid_ids)==len(state.model_calls)-
                 previous_lineage['parent_calls_saved'],
                 'INHERITED_MODEL_CALL_COUNT_MISMATCH')
        cumulative_previous_cost = Decimal(str(previous_lineage['accounted_upstream_usd']))
        initial_total_budget = Decimal(str(previous_lineage['original_budget_limit_usd']))
        _require(abs(initial_total_budget-cumulative_previous_cost-old_cap) <
                 Decimal('0.00000002'), 'PARENT_BUDGET_CHAIN_BROKEN')
    spent=_read_parent_cost(parent,expected_paid_ids)
    # A/B research: fork the SAME pre-terminal parent (_03) while counting
    # the already executed comparator (_04) against the original $10 envelope.
    # Sibling cost is verified from its exact SAVED call IDs, never estimated.
    comparator_record = None
    comparator_cost = Decimal('0')
    if comparison_baseline is not None:
        comparison_baseline=Path(comparison_baseline).expanduser().resolve()
        _require(comparison_baseline.parent==parent.parent and
                 comparison_baseline!=parent and comparison_baseline!=dest,
                 'COMPARATOR_LOCATION_INVALID')
        verify_successor_prefix(comparison_baseline)
        comparison_lineage=_read_json(comparison_baseline/FILE)
        _require(comparison_lineage['upstream_experiment']==str(parent) and
                 comparison_lineage['parent_events']==len(events) and
                 comparison_lineage['parent_head_sha256']==sha(canon(events[-1])),
                 'COMPARATOR_NOT_SAME_RESEARCH_SNAPSHOT')
        cj=EvolutionJournal(comparison_baseline/'ROOTS'/'PRIMARY')
        cs=cj.verify()
        _require(cs.program_reviews and
                 cs.program_reviews[-1]['scientific_status']=='HOLD_WITH_RATIONALE' and
                 all(v['state']=='SAVED' for v in cs.model_calls.values()),
                 'COMPARATOR_NOT_SETTLED_SCIENTIFIC_HOLD')
        compare_rows=cj._events()
        compare_ids={e['payload']['id'] for e in
                     compare_rows[comparison_lineage['parent_events']+1:]
                     if e['kind']=='MODEL_CALL_INTENT'}
        _require(len(compare_ids)==len(cs.model_calls)-
                 comparison_lineage['parent_calls_saved'],
                 'COMPARATOR_INHERITED_CALLS_MISMATCH')
        comparator_cost=_read_parent_cost(comparison_baseline,compare_ids)
        comparator_record={
            'experiment':str(comparison_baseline),
            'terminal_head_sha256':sha(canon(compare_rows[-1])),
            'parent_head_sha256':sha(canon(events[-1])),
            'new_call_ids':sorted(compare_ids),
            'actual_usd':float(comparator_cost),
            'disposition':'HOLD_WITH_RATIONALE',
            'not_independent_scientific_certification':True,
        }
    _require(old_cap>spent+comparator_cost>=0,
             'ORIGINAL_BUDGET_EXHAUSTED_OR_INVALID')
    new_cap=(old_cap-spent-comparator_cost).quantize(
        Decimal('0.00000001'),rounding=ROUND_DOWN)
    _require(new_cap>0,'NO_REMAINING_BUDGET')
    newbudget=dict(oldbudget)
    newbudget['limit_usd']=float(new_cap)
    _require(parent/'M232_DEV_BUDGET.json' != dest/'M232_DEV_BUDGET.json','DESTINATION_BUDGET_COLLISION')
    lineage={
        'protocol':PROTOCOL,
        'kind':'EXACT_EXISTING_JOURNAL_PREFIX_NEW_RUNTIME_NOT_FRESH',
        'upstream_experiment':str(parent),
        'upstream_primary_root':str(oldroot),
        'parent_events':len(events),
        'parent_head_sha256':sha(canon(events[-1])),
        'parent_journal_manifest_sha256':sha((oldroot/'manifest.json').read_bytes()),
        'parent_blob_names':sorted(x.name for x in (oldroot/'blobs').iterdir()),
        'parent_native_source_pin_sha256':sha(pinpath.read_bytes()),
        'parent_native_source_commit':parent_commit,
        'parent_successor_lineage_sha256':(
            sha((parent/FILE).read_bytes()) if previous_lineage is not None else None),
        'original_total_budget_usd':float(initial_total_budget),
        'cumulative_upstream_accounted_usd':float(cumulative_previous_cost+spent+comparator_cost),
        'comparison_baseline':comparator_record,
        'direct_parent_spent_usd':float(spent),
        'parent_calls_saved':len(state.model_calls),
        'parent_decisions':len(state.controller_decisions),
        'parent_assets':len(state.assets),
        'parent_works':len(state.work),
        'original_P0_sha256':oldmeta['original_P0_sha256'],
        'original_budget_limit_usd':float(old_cap),
        'accounted_upstream_usd':float(spent+comparator_cost),
        'successor_budget_limit_usd':float(new_cap),
        'notes':('Original experiment remains unchanged; copied accepted scientific history '
                 'is not independently validated; all rejected responses remain saved; '
                 'only new calls after operational handoff are charged to the successor.'),
        'scientific_certification':False,
    }
    if dry_run:
        print(json.dumps({'status':'M28_SUCCESSOR_CHECK_OK_NO_FILES_WRITTEN',
                          'parent_events':len(events),
                          'parent_calls_saved':len(state.model_calls),
                          'parent_assets':len(state.assets),
                          'original_budget_limit_usd':float(old_cap),
                          'upstream_accounted_usd':float(spent+comparator_cost),
                          'comparator_actual_usd':float(comparator_cost),
                          'new_budget_limit_usd':float(new_cap),
                          'destination':str(dest)},ensure_ascii=False,indent=2))
        return lineage
    # Original root is copied BEFORE any new runtime event, preserving exact bytes.
    dest.mkdir(parents=True)
    try:
        (dest/'ROOTS').mkdir()
        shutil.copytree(oldroot,dest/'ROOTS'/'PRIMARY',symlinks=False)
        newroot=dest/'ROOTS'/'PRIMARY'
        _require(sha(canon(EvolutionJournal(newroot)._events()[-1]))==lineage['parent_head_sha256'],
                 'COPIED_HEAD_MISMATCH')
        for source in (oldroot/'manifest.json',):
            _require((newroot/source.name).read_bytes()==source.read_bytes(),
                     'COPIED_ORIGINAL_MANIFEST_MISMATCH')
        lineage_blob=canon(lineage)
        (dest/FILE).write_bytes(lineage_blob)
        budget_blob=canon(newbudget)
        (dest/'M232_DEV_BUDGET.json').write_bytes(budget_blob)
        newsha=sha(budget_blob)
        native_sha=sha(lineage_blob)
        newpersistent=dict(oldpersistent)
        newpersistent['budget_config_sha256']=newsha
        newpersistent['native_successor_sha256']=native_sha
        newmeta=dict(oldmeta)
        newmeta['root']=str(dest)
        newmeta['initial_root']=str(newroot)
        newmeta['budget_config_sha256']=newsha
        newmeta['native_successor_sha256']=native_sha
        (dest/'persistent.json').write_bytes(canon(newpersistent))
        (dest/'meta_research.json').write_bytes(canon(newmeta))
        check_m28_experiment(dest,model=oldpersistent['activation_profile']['model'])
        from generational_run import pin_native_source
        pin_native_source(dest)
        successor=EvolutionJournal(newroot)
        successor.append('OPERATIONAL_PAUSE',{
            'reason':M28_RECOVERY_MARKER,
            'parent_head_sha256':lineage['parent_head_sha256'],
            'parent_events':lineage['parent_events'],
            'scientific_certification':False,
        })
        successor.verify()
        status=verify_successor_prefix(dest)
        from .meta_scheduler import controller_recovery_pending
        _require(controller_recovery_pending(successor), 'CONTROLLER_RECOVERY_NOT_RUNNABLE')
        # Old root's previous fingerprint is verified again after creation.
        _require(sha(canon(j._events()[-1]))==lineage['parent_head_sha256'],
                 'PARENT_CHANGED_DURING_FORK')
        print(json.dumps({'status':'M28_SUCCESSOR_INITIALIZED_NO_PAID',
                          'new_experiment':str(dest),**status},ensure_ascii=False,indent=2))
        return status
    except BaseException:
        # Newly created destination only; never delete/mutate an existing root.
        shutil.rmtree(dest)
        raise
