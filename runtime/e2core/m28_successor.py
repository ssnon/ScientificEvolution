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


def _read_parent_cost(exp, state):
    db=exp/'.M232_DEV_BUDGET.sqlite3'
    _require(db.is_file() and not db.is_symlink(), 'ORIGINAL_BUDGET_DB_MISSING')
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        rows=conn.execute('SELECT state,reserved_usd,actual_usd FROM calls').fetchall()
    _require(len(rows)==len(state.model_calls), 'ORIGINAL_LEDGER_CALL_COUNT_MISMATCH')
    _require(all(st=='SAVED' and actual is not None and float(actual)>=0
                 for st,reserved,actual in rows), 'ORIGINAL_BUDGET_NOT_ALL_SETTLED')
    return sum((Decimal(str(actual)) for _st,_res,actual in rows), Decimal('0'))


def _verify_origin_source_pin(repo, original_pin):
    _require(original_pin.get('protocol')=='M16_NATIVE_EXECUTION_SOURCE_V1',
             'ORIGINAL_SOURCE_PIN_PROTOCOL')
    _require(original_pin.get('repository')==str(repo), 'ORIGINAL_REPOSITORY_MISMATCH')
    files=original_pin.get('files')
    _require(isinstance(files,dict) and bool(files), 'ORIGINAL_SOURCE_PIN_EMPTY')
    for rel,expected in files.items():
        _require(isinstance(rel,str) and rel.startswith(('runtime/','AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/'))
                 and '..' not in Path(rel).parts, 'ORIGINAL_SOURCE_PATH_INVALID')
        try:
            raw=subprocess.check_output(['git','show',ORIGINAL_COMMIT+':'+rel],cwd=repo,
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
    return {'status':'M28_NATIVE_SUCCESSOR_PREFIX_VERIFIED_NO_PAID',
            'parent_events':n, 'parent_head_sha256':lineage['parent_head_sha256'],
            'parent_calls_saved':lineage['parent_calls_saved'],
            'parent_assets':lineage['parent_assets'],
            'upstream_accounted_usd':lineage['accounted_upstream_usd'],
            'successor_budget_limit_usd':lineage['successor_budget_limit_usd'],
            'original_preserved':True}


def build_successor(parent, dest, *, dry_run=False):
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
    _require(not (parent/FILE).exists(), 'FORK_OF_SUCCESSOR_NOT_AUTOMATICALLY_SUPPORTED')
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
    _require(_verify_origin_source_pin(repo,pin)>0, 'ORIGINAL_SOURCE_UNVERIFIED')
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
    spent=_read_parent_cost(parent,state)
    _require(old_cap>spent>=0,'ORIGINAL_BUDGET_EXHAUSTED_OR_INVALID')
    new_cap=(old_cap-spent).quantize(Decimal('0.00000001'),rounding=ROUND_DOWN)
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
        'parent_native_source_commit':ORIGINAL_COMMIT,
        'parent_calls_saved':len(state.model_calls),
        'parent_decisions':len(state.controller_decisions),
        'parent_assets':len(state.assets),
        'parent_works':len(state.work),
        'original_P0_sha256':oldmeta['original_P0_sha256'],
        'original_budget_limit_usd':float(old_cap),
        'accounted_upstream_usd':float(spent),
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
                          'upstream_accounted_usd':float(spent),
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
