"""M28-A1 opt-in meta-research organization; not a scientific success classifier.

Controller-authored organizational intentions are distinguishable from real root
creation. Materialization is replay-safe and research outputs are not merged.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from .core import EvolutionJournal, EvidenceError, guard, canon, sha

POLICY = 'META_RESEARCH_AUTONOMY_A1'
MODE_BLIND = 'ORIGINAL_P0_BLIND_INDEPENDENT'
MODE_TARGETED = 'TARGETED_INDEPENDENT_CHALLENGE'
MODES = {MODE_BLIND, MODE_TARGETED}
ORG_ID = re.compile(r'^ORG_[A-Za-z0-9_]{1,70}$')
HEX = re.compile(r'^[0-9a-f]{64}$')
ORIGIN_FILE = 'META_RESEARCH_ORIGIN.json'

CONTROLLER_ADDENDUM = '''\nM28-A1 META-RESEARCH AUTONOMY (this NEW root only):
You may propose optional organization_requests in the SAME JSON object as
ordinary actions. An empty array means no organizational change. The research
program must NOT assume any fixed researcher count, generation or merge phase.
Organization requests are research intentions, not executed research or proof.
Each request object has fields:
{"id":"ORG_unique_id", "mode":"ORIGINAL_P0_BLIND_INDEPENDENT|TARGETED_INDEPENDENT_CHALLENGE", "purpose":"scientific reason to create a genuinely separate research unit", "evidence_asset_ids":[], "target_asset_ids":[]}.
Use ORIGINAL_P0_BLIND_INDEPENDENT ONLY for an independent fresh researcher who
receives the exact original P0 and NO earlier AI hypotheses or targeted question.
Its evidence_asset_ids may justify YOUR choice, but will NOT be sent to the child;
target_asset_ids MUST be []. Use TARGETED_INDEPENDENT_CHALLENGE for a reviewer
explicitly shown existing AI claims; target_asset_ids MUST name one or more
existing assets. This is NOT blind-independent discovery. Both modes start an
independent scientific ROOT with its own decisions and tools, and do not imply
successful research, imported science, or an automatic FUSE.
A request may accompany ordinary research actions. In this opt-in ROOT only,
valid organization_requests are an alternative to an immediately runnable local
Work for an ONGOING decision: this narrowly supersedes the older E3R1
"ONGOING requires a local Work" rule. Do not create a dummy Work.
The new ROOT is materially created separately after the saved decision. Do not add
requests merely to satisfy a quota. HOLD, SCOPED_NEGATIVE and review-worthy
terminal decisions cannot simultaneously request new research units.
No additional manager call, mandatory peer, population, synthesis or generation
will be inserted by this contract. Resource limits remain operational, not science.
'''


def validate_request(state, request, decision_id, call_id, parent_root_id):
    """Canonical, schema-checked proposal. Do not judge scientific merit here."""
    guard(state.meta_research_autonomy, 'META_AUTONOMY_NOT_ACTIVATED')
    guard(isinstance(request, dict), 'META_ORG_REQUEST_NOT_OBJECT')
    keys = {'id', 'mode', 'purpose', 'evidence_asset_ids', 'target_asset_ids'}
    guard(set(request) == keys, 'META_ORG_REQUEST_UNKNOWN_OR_MISSING_FIELDS')
    rid = request.get('id')
    guard(isinstance(rid, str) and ORG_ID.fullmatch(rid), 'META_ORG_BAD_ID')
    guard(rid not in state.organization_requests, 'META_ORG_DUPLICATE_ID')
    mode = request.get('mode')
    guard(mode in MODES, 'META_ORG_MODE_UNSUPPORTED')
    purpose = request.get('purpose')
    guard(isinstance(purpose, str) and purpose.strip(), 'META_ORG_EMPTY_PURPOSE')
    refs = request.get('evidence_asset_ids')
    targets = request.get('target_asset_ids')
    guard(isinstance(refs, list) and isinstance(targets, list), 'META_ORG_BAD_ASSET_REFS')
    guard(all(isinstance(x, str) and x in state.assets for x in refs + targets),
          'META_ORG_UNKNOWN_EVIDENCE_OR_TARGET')
    guard(len(set(refs)) == len(refs) and len(set(targets)) == len(targets),
          'META_ORG_DUPLICATE_ASSET_REF')
    guard((not targets if mode == MODE_BLIND else bool(targets)),
          'META_ORG_TARGET_SCOPE_MISMATCH')
    guard(isinstance(decision_id, str) and decision_id.startswith('D') and
          call_id == 'CTRL_' + decision_id, 'META_ORG_CONTROLLER_PROVENANCE_INVALID')
    guard(isinstance(parent_root_id,str) and
          re.fullmatch(r'(?:PRIMARY|ORG_[0-9a-f]{24})',parent_root_id),
          'META_ORG_PARENT_ROOT_ID_INVALID')
    return {**request, 'decision_id': decision_id, 'call_id': call_id,
            'parent_root_id': parent_root_id, 'science_certification': False}


def _binding(parent_root, source, request):
    guard(request['parent_root_id']==parent_root.name,'META_ORG_PARENT_ROOT_CHANGED')
    s = source.verify()
    call = s.model_calls.get(request['call_id'])
    guard(call and call['state'] == 'SAVED', 'META_ORG_SAVED_CONTROLLER_REQUIRED')
    guard(any(d['id'] == request['decision_id'] and d['call_id'] == request['call_id']
              for d in s.controller_decisions), 'META_ORG_COMMITTED_DECISION_REQUIRED')
    return {'protocol': POLICY, 'parent_root': str(parent_root.resolve()),
            'decision_id': request['decision_id'], 'controller_call_id': request['call_id'],
            'controller_response_blob': call['response_blob'],
            'request': request, 'request_sha256': sha(canon(request)),
            'P0_sha256': sha(s.program['problem'].encode('utf8')),
            'child_mode': request['mode'], 'science_certification': False,
            'materialization_is_not_research': True}


def _verified_target_child(j, binding, parent):
    state = j.verify()
    req = binding['request']
    assert req['mode'] == MODE_TARGETED
    for index, aid in enumerate(req['target_asset_ids']):
        a = parent.assets[aid]
        token = sha(canon({'source': binding['parent_root'], 'asset': aid}))[:22]
        source_id = 'SRC_M28_TARGET_' + token
        dest_id = 'A_M28_TARGET_' + token
        science = {'origin_root': binding['parent_root'], 'original_asset_id': aid,
                   'original_asset': a, 'source_controller_call': binding['controller_call_id'],
                   'original_source_ids': a.get('source_ids', []),
                   'not_primary_evidence': True, 'not_blind_independent': True,
                   'origin_observation_not_certified': True}
        j.add_source(source_id, 'HISTORICAL_AI', science,
                     'Explicit targeted AI claim for independent challenge; NOT primary evidence')
        j.append('HISTORICAL_ASSET_INDEXED', {
            'id': dest_id, 'kind': a['kind'], 'problem_id': 'P0', 'parent_ids': [],
            'claim': a['claim'], 'scope': a.get('scope') or 'Targeted claim from existing research',
            'assumptions': a.get('assumptions') or 'Original assumptions not supplied',
            'predictions': a.get('predictions', []),
            'limitations': list(a.get('limitations', [])) + [
                'Targeted imported AI claim; not original-P0-blind discovery',
                'Original asset DAG references saved in source, not reconstructed as local parents'],
            'source_ids': [source_id], 'origin_root': binding['parent_root'],
            'original_asset_id': aid, 'original_parent_ids': a.get('parent_ids', []),
            'origin_work_mode': 'INFORMED_TARGETED_CHALLENGE',
        })
    guard(len(j.verify().assets) == len(req['target_asset_ids']),
          'META_ORG_TARGET_IMPORT_MISMATCH')


def _prepare_stage(stage, binding, parent):
    guard(not stage.exists(), 'META_ORG_STAGE_EXISTS')
    req = binding['request']
    j = EvolutionJournal(stage)
    j.init(parent.program['problem'],
           origin=('INDEPENDENT_UNSEEDED_FRESH_COHORT' if req['mode'] == MODE_BLIND
                   else 'TARGETED_INDEPENDENT_CHALLENGE_NOT_BLIND'),
           criteria=parent.program.get('criteria'))
    j.append('R5_POLICY_ACTIVATED', {'policy': 'OBJECTIVE_AND_DISPOSITION_V1'})
    j.append('E3R1_POLICY_ACTIVATED', {'policy': 'PORTFOLIO_DECISIONS_V1'})
    j.append('META_RESEARCH_AUTONOMY_ACTIVATED', {'policy': POLICY})
    if req['mode'] == MODE_TARGETED:
        _verified_target_child(j, binding, parent)
    verified = j.verify()
    guard(not verified.model_calls and not verified.work and not verified.controller_decisions,
          'META_ORG_CHILD_NOT_CLEAN')
    if req['mode'] == MODE_BLIND:
        guard(not verified.assets and not verified.sources and len(verified.problems) == 1,
              'META_ORG_BLIND_CHILD_CONTAMINATED')
    (stage / ORIGIN_FILE).write_bytes(canon(binding))
    return j


def _verify_child(child, binding, parent, allow_research=False):
    guard(child.is_dir() and not child.is_symlink(), 'META_ORG_CHILD_MISSING_OR_SYMLINK')
    path = child / ORIGIN_FILE
    guard(path.is_file() and path.read_bytes() == canon(binding),
          'META_ORG_BINDING_MISMATCH')
    j = EvolutionJournal(child)
    s = j.verify()
    guard(s.program['problem'] == parent.program['problem'] and
          s.program.get('criteria') == parent.program.get('criteria') and
          s.meta_research_autonomy, 'META_ORG_CHILD_PROGRAM_OR_POLICY_MISMATCH')
    if not allow_research:
        guard(not s.model_calls and not s.controller_decisions and not s.work,
              'META_ORG_UNRECEIPTED_CHILD_ALREADY_EXECUTED')
    if binding['child_mode'] == MODE_BLIND:
        guard(s.program.get('origin') == 'INDEPENDENT_UNSEEDED_FRESH_COHORT',
              'META_ORG_FAKE_BLIND_ORIGIN')
        if not allow_research:
            guard(not s.sources and not s.assets and len(s.problems) == 1,
                  'META_ORG_BLIND_FIRST_CONTEXT_CONTAMINATION')
    else:
        guard(s.program.get('origin') == 'TARGETED_INDEPENDENT_CHALLENGE_NOT_BLIND',
              'META_ORG_TARGETED_ORIGIN_MISLABELED')
    return j


def _root_name(request):
    return 'ORG_' + sha(canon({'id': request['id'], 'decision': request['decision_id'],
                               'parent_root_id': request['parent_root_id']}))[:24]


def materialize_requests(experiment, parent_root, max_roots):
    """Execute durable decisions; deterministic and crash-recoverable per request.

    Caller must hold program-level file lock to prevent concurrent append or
    publish. The parent root may not be a historical or unactivated Journal.
    """
    exp = Path(experiment).resolve()
    root = Path(parent_root).resolve()
    guard(root.is_relative_to(exp / 'ROOTS') and root.parent == exp / 'ROOTS',
          'META_ORG_PARENT_OUTSIDE_EXPERIMENT')
    source = EvolutionJournal(root)
    s = source.verify()
    guard(s.meta_research_autonomy, 'META_ORG_PARENT_NOT_OPTED_IN')
    guard(isinstance(max_roots, int) and max_roots >= 1, 'META_ORG_BAD_CAP')
    results = []
    for rid, req in list(s.organization_requests.items()):
        if rid in s.organization_materialized:
            continue
        name = _root_name(req)
        dest = exp / 'ROOTS' / name
        stage = dest.with_name(dest.name + '.STAGING')
        binding = _binding(root, source, req)
        if not dest.exists() and not stage.exists():
            active = [x for x in (exp / 'ROOTS').iterdir()
                      if x.is_dir() and not x.name.endswith('.STAGING')]
            guard(len(active) < max_roots, 'META_ORG_OPERATIONAL_ROOT_CAP')
            _prepare_stage(stage, binding, s)
        if not dest.exists():
            _verify_child(stage, binding, s)
            stage.rename(dest)
        child = _verify_child(dest, binding, s)
        guard(not stage.exists(), 'META_ORG_LEFTOVER_STAGE_REQUIRES_REVIEW')
        head = sha(canon(child._events()[-1]))
        source.append('ORGANIZATION_ROOT_MATERIALIZED', {
            'id': rid, 'relative_root': 'ROOTS/' + name,
            'child_head_sha256': head, 'binding_sha256': sha(canon(binding)),
            'science_certification': False,
            'execution_status': 'ROOT_INITIALIZED_NO_SCIENCE_EXECUTED',
        })
        s = source.verify()
        results.append({'id': rid, 'root': str(dest),
                        'mode': req['mode'], 'status': 'MATERIALIZED_NO_PAID'})
    return results


def verify_receipts(experiment, parent_root):
    exp = Path(experiment).resolve(); root = Path(parent_root).resolve()
    source = EvolutionJournal(root); s = source.verify()
    for rid, receipt in s.organization_materialized.items():
        req = s.organization_requests[rid]
        expected = 'ROOTS/' + _root_name(req)
        guard(receipt['relative_root'] == expected, 'META_ORG_RECEIPT_ROOT_CHANGED')
        child = exp / expected
        j=_verify_child(child, _binding(root, source, req), s, allow_research=True)
        initial_n=4+(2*len(req['target_asset_ids']) if req['mode']==MODE_TARGETED else 0)
        events=j._events()
        guard(len(events)>=initial_n and sha(canon(events[initial_n-1]))==receipt['child_head_sha256'],
              'META_ORG_CHILD_INITIAL_HEAD_CHANGED')
    return len(s.organization_materialized)


def organization_context(j):
    """What the same scientist already requested/executed, not source evidence."""
    s=j.verify()
    return {'enabled': bool(s.meta_research_autonomy),
            'requested': [{'id': rid, 'mode': req['mode'],
                           'purpose': req['purpose'],
                           'materialized': rid in s.organization_materialized}
                          for rid,req in s.organization_requests.items()],
            'no_mandatory_peers_or_generations': True,
            'origin_root': s.program.get('origin') if s.program else None,
            'this_context_is_not_primary_evidence': True}


def recover_committed_requests(j):
    """Finish validated organizational event append after a process crash.

    A Controller decision is committed only after controller_plan has validated
    all actions. Its original parsed model response, not regenerated text, is
    the sole source for recovery. This does not re-run or re-bill any model.
    """
    s=j.verify()
    guard(s.meta_research_autonomy,'META_ORG_RECOVERY_ON_LEGACY_FORBIDDEN')
    recovered=[]
    for dec in s.controller_decisions:
        raw=json.loads(j.raw(dec['parsed_blob']))
        requests=raw.get('organization_requests',[])
        guard(isinstance(requests,list),'META_ORG_SAVED_REQUESTS_INVALID')
        for rec in requests:
            rid=rec.get('id') if isinstance(rec,dict) else None
            existing=j.verify().organization_requests.get(rid)
            if existing is not None:
                expected=validate_request_legacy(j.verify(),rec,dec['id'],dec['call_id'],j.root.name,existing=True)
                guard(existing==expected,'META_ORG_RECOVERY_REQUEST_CHANGED')
                continue
            payload=validate_request(j.verify(),rec,dec['id'],dec['call_id'],j.root.name)
            j.append('ORGANIZATION_REQUESTED',payload)
            recovered.append(rid)
    return recovered


def validate_request_legacy(state,rec,decision_id,call_id,parent_root_id,existing=False):
    """Validate a stored request against its already recorded event."""
    if not existing:return validate_request(state,rec,decision_id,call_id,parent_root_id)
    previous=state.organization_requests.get(rec.get('id'))
    guard(previous is not None,'META_ORG_RECOVERY_EXPECTED_EXISTING')
    temp=type('StateView',(),{})()
    temp.meta_research_autonomy=state.meta_research_autonomy
    temp.organization_requests={k:v for k,v in state.organization_requests.items() if k!=rec['id']}
    temp.assets=state.assets
    return validate_request(temp,rec,decision_id,call_id,parent_root_id)
