"""M28-A2 opt-in, model-selected cross-root scientific collaboration.

A child research report is *observed*, not imported. Only a saved Controller
selection permits individual historical-AI asset imports. A local terminal
review never automatically becomes a program-wide scientific disposition.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from .core import EvolutionJournal, EvidenceError, guard, canon, sha
from .meta_autonomy import _binding, _root_name, _verify_child, verify_receipts

POLICY = 'META_RESEARCH_COLLABORATION_A2'
PROGRAM_ORIGIN = 'NEW_META_RESEARCH_AUTONOMY_RESEARCH'
COL_ID = re.compile(r'^COL_[A-Za-z0-9_]{1,70}$')
PROGRAM_STOPS = {'PAUSE_WITH_RATIONALE', 'SCOPED_NEGATIVE', 'REVIEW_WORTHY_CANDIDATE'}
PROGRAM_OPTIONS = PROGRAM_STOPS | {'CONTINUE'}

CONTROLLER_ADDENDUM = '''\nM28-A2 SELECTIVE SCIENTIFIC COLLABORATION (new opt-in roots only):
Read meta_research_organization_context.child_research_reports. Each report is
verified as an actual child Journal observation but contains FALLIBLE AI claims,
not independently validated science. It is not an automatic FUSE or acceptance.
You may return collaboration_requests: [] or selected objects:
{"id":"COL_unique_id","organization_request_id":"ORG_existing_request_id",
 "report_id":"RPT_exact_latest_id","asset_ids":["A_original_child_asset_id"],
 "purpose":"scientific reason to import ONLY these child assertions for comparison"}.
Every selected asset must appear in the exact report. Import retains historical
AI provenance, including the child's original work/model/parent/source status;
it is not a primary source and is not automatically correct. You may subsequently
create ordinary INFORMED Work to challenge/develop/FUSE the imported candidates.
Declining all imports is a valid scientific choice. A collaboration-only ONGOING
Controller action is valid in this opt-in ROOT; no dummy Work required.
If THIS ROOT is the initial PRIMARY program root, you may also optionally return
program_portfolio_review: {"disposition":"CONTINUE|PAUSE_WITH_RATIONALE|SCOPED_NEGATIVE|REVIEW_WORTHY_CANDIDATE",
 "rationale":"specific scientific account of global research and alternatives",
 "considered_organization_request_ids":["ALL_materialized_child_request_ids"],
 "considered_report_ids":["latest available reports actually considered"],
 "unresolved_frontiers":["remaining evidence, methods, active research and limits"]}.
This is a distinct PROGRAM scope: a local child HOLD is not a global result,
no report is proof of P0 impossibility, and operational resource exhaustion
is not a scientific disposition. For program-wide stop, account for ALL known
children, including ones with no report and still active opportunities. The
machine checks accounting/provenance but cannot certify scientific merit.
This field is optional ONLY for disposition ONGOING (where it may be omitted or have disposition CONTINUE).
For PRIMARY, it is REQUIRED whenever top-level disposition is HOLD_WITH_RATIONALE, SCOPED_NEGATIVE, or REVIEW_WORTHY_CANDIDATE. The field is named program_portfolio_review (not a scientific asset) and its disposition MUST map to the top-level disposition: HOLD_WITH_RATIONALE -> PAUSE_WITH_RATIONALE, SCOPED_NEGATIVE -> SCOPED_NEGATIVE, REVIEW_WORTHY_CANDIDATE -> REVIEW_WORTHY_CANDIDATE. It MUST include rationale, considered_organization_request_ids, considered_report_ids, unresolved_frontiers. If no child research was requested or materialized, BOTH considered_organization_request_ids and considered_report_ids MUST be [] and must NOT be invented. Reaching a terminal decision is OPTIONAL; submitting a complete review is mandatory IF a terminal decision is chosen.
M28 scoped candidate semantics: a falsifiable pre-experiment candidate may have objective_status REVIEW_WORTHY_CANDIDATE, objective_coverage SUBPROBLEM_ONLY, research_status PAUSED_EVIDENCE or PAUSED_LOW_INFORMATION, and valid pre-existing supporting_asset_ids. This is a RESEARCH CANDIDATE, NOT P0 completion. COMPLETED is reserved for objective_coverage ORIGINAL_PROBLEM with concrete prior supporting assets. Use HOLD_WITH_RATIONALE/UNRESOLVED when evidence does not justify a candidate; never change a scientific conclusion only to fit a schema. Do not produce program-wide dispositions as a quota.
A pause is not a proof of P0 impossibility or an experiment-certified result.
'''


def _last_head(j):
    events = j._events()
    guard(bool(events), 'META_A2_EMPTY_JOURNAL')
    return sha(canon(events[-1]))


def _root_for_child(exp, j, org_id):
    root = j.root
    guard(root.parent == exp / 'ROOTS' and root.is_dir(), 'META_A2_NOT_EXPERIMENT_ROOT')
    s = j.verify()
    req = s.organization_requests.get(org_id)
    guard(s.meta_collaboration and req and org_id in s.organization_materialized,
          'META_A2_CHILD_NOT_MATERIALIZED_FROM_THIS_ROOT')
    child = exp / 'ROOTS' / _root_name(req)
    binding = _binding(root, j, req)
    _verify_child(child, binding, s, allow_research=True)
    return child, req


def _live_asset_record(j, s, asset):
    """Only authored Worker outputs; exclude all inherited/historical assets."""
    if asset.get('origin') == 'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK':
        return None
    wid = asset.get('work_id')
    w = s.work.get(wid)
    idx = asset.get('origin_step')
    if not w or type(idx) is not int or not 1 <= idx <= len(w['steps']):
        return None
    step = w['steps'][idx-1]
    if step.get('kind') != 'MODEL_RESPONSE':
        return None
    text = json.loads(j.raw(step['raw_blob']))
    call_id = text.get('call_id')
    call = s.model_calls.get(call_id)
    if not call or call.get('actor') != 'WORKER' or call.get('work_id') != wid or call.get('state') != 'SAVED':
        return None
    return {'id': asset['id'], 'asset_sha256': sha(canon(asset)),
            'kind': asset['kind'], 'claim': asset['claim'],
            'scope': asset.get('scope'), 'assumptions': asset.get('assumptions'),
            'predictions': asset.get('predictions', []),
            'limitations': asset.get('limitations', []),
            'parent_ids': asset.get('parent_ids', []),
            'source_ids': asset.get('source_ids', []),
            'work_id': wid, 'work_status': w['status'],
            'model_call_id': call_id, 'model_billing_mode': call.get('billing_mode'),
            'model_response_sha256': call.get('response_blob'),
            'not_certified': True}


def _report(parent_j, child, org_id, req):
    cj = EvolutionJournal(child)
    cs = cj.verify()
    live = []
    for a in cs.assets.values():
        rec = _live_asset_record(cj, cs, a)
        if rec is not None:
            live.append(rec)
    if not cs.controller_decisions and not live:
        return None
    review = cs.program_reviews[-1] if cs.program_reviews else None
    report = {'protocol': POLICY, 'organization_request_id': org_id,
              'child_name': child.name, 'origin_mode': req['mode'],
              'original_p0_sha256': sha(cs.program['problem'].encode('utf8')),
              'child_head_sha256': _last_head(cj),
              'latest_local_review': review,
              'work_statuses': {wid: w['status'] for wid, w in cs.work.items()},
              'saved_model_calls': sum(c.get('state') == 'SAVED' for c in cs.model_calls.values()),
              'candidate_assets': live, 'historical_seed_assets_excluded': True,
              'not_primary_evidence': True, 'not_scientific_certification': True,
              'no_automatic_synthesis': True}
    # Preserve full work/evidence summary; reject oversized observations instead
    # of silently dropping assets or claims and calling the result complete.
    guard(len(canon(report)) <= 2_000_000, 'META_A2_REPORT_TOO_LARGE_REQUIRES_REVIEW')
    return report


def _scientific_report_id(report):
    """Ignore operational-only head/call changes when deciding to notify science."""
    significant = {k: report[k] for k in (
        'organization_request_id', 'origin_mode', 'latest_local_review',
        'work_statuses', 'candidate_assets')}
    return 'RPT_' + sha(canon(significant))[:32]


def observe_children(experiment, parent_root):
    """Read-only child scan and append an exact observation only when changed.

    Caller must hold the experiment execution lock for real concurrent runs.
    """
    exp = Path(experiment).resolve()
    j = EvolutionJournal(parent_root)
    s = j.verify()
    guard(s.meta_collaboration, 'META_A2_NOT_ACTIVATED')
    verify_receipts(exp, j.root)
    created = []
    for org_id in s.organization_materialized:
        child, req = _root_for_child(exp, j, org_id)
        report = _report(j, child, org_id, req)
        if report is None:
            continue
        report_id = _scientific_report_id(report)
        previous = j.verify().child_research_reports.get(org_id)
        if previous and previous['report_id'] == report_id:
            continue
        digest = j.blob(report)
        j.append('CHILD_RESEARCH_OBSERVED', {
            'organization_request_id': org_id, 'report_id': report_id,
            'report_blob': digest, 'child_head_sha256': report['child_head_sha256'],
            'science_certification': False})
        created.append({'organization_request_id': org_id, 'report_id': report_id,
                        'candidate_assets': len(report['candidate_assets'])})
    return created


def _read_report(j, org_id):
    obs = j.verify().child_research_reports.get(org_id)
    guard(obs is not None, 'META_A2_NO_CHILD_REPORT')
    report = json.loads(j.raw(obs['report_blob']))
    guard(report['organization_request_id'] == org_id and
          _scientific_report_id(report) == obs['report_id'],
          'META_A2_REPORT_BLOB_MISMATCH')
    return obs, report


def controller_context(j):
    s = j.verify()
    reports = []
    for org_id in s.child_research_reports:
        obs, report = _read_report(j, org_id)
        reports.append({'organization_request_id': org_id,
                        'report_id': obs['report_id'],
                        'report': report,
                        'read_only_external_assertions_not_local_assets': True})
    return {'collaboration_enabled': bool(s.meta_collaboration),
            'child_research_reports': reports,
            'previous_collaboration_requests': list(s.collaboration_requests.values()),
            'collaboration_imports': list(s.collaboration_imports.values()),
            'program_portfolio_reviews': s.program_portfolio_reviews[-3:],
            'no_automatic_integration_or_global_hold': True}


def validate_selection(j, rec, decision_id, call_id):
    s = j.verify()
    guard(s.meta_collaboration, 'META_A2_NOT_ACTIVATED')
    guard(isinstance(rec, dict) and set(rec) == {
        'id','organization_request_id','report_id','asset_ids','purpose'},
        'META_A2_SELECTION_SCHEMA')
    ident = rec['id']
    guard(isinstance(ident, str) and COL_ID.fullmatch(ident) and ident not in s.collaboration_requests,
          'META_A2_SELECTION_DUPLICATE_OR_BAD_ID')
    org_id = rec['organization_request_id']
    guard(isinstance(org_id, str) and org_id in s.organization_materialized,
          'META_A2_SELECTION_UNKNOWN_CHILD')
    obs, report = _read_report(j, org_id)
    guard(rec['report_id'] == obs['report_id'], 'META_A2_STALE_REPORT_SELECTION')
    aids = rec['asset_ids']
    guard(isinstance(aids, list) and bool(aids) and len(set(aids)) == len(aids),
          'META_A2_SELECTION_EMPTY_OR_DUPLICATE')
    candidates = {a['id'] for a in report['candidate_assets']}
    guard(all(isinstance(a, str) and a in candidates for a in aids),
          'META_A2_SELECTION_NOT_ACTUAL_WORKER_ASSET')
    previously = {(r['organization_request_id'], x)
                  for r in s.collaboration_requests.values() for x in r['asset_ids']}
    guard(all((org_id, a) not in previously for a in aids),
          'META_A2_CHILD_ASSET_ALREADY_SELECTED')
    guard(isinstance(rec['purpose'], str) and rec['purpose'].strip(),
          'META_A2_SELECTION_NO_SCIENTIFIC_RATIONALE')
    guard(call_id == 'CTRL_' + decision_id, 'META_A2_SELECTION_NOT_CONTROLLER')
    return {**rec, 'decision_id': decision_id, 'call_id': call_id,
            'science_certification': False}


def validate_program_review(j, raw, decision_id, call_id):
    s = j.verify()
    guard(s.meta_collaboration and j.root.name == 'PRIMARY' and
          s.program.get('origin') == PROGRAM_ORIGIN,
          'META_A2_NOT_PRIMARY_PROGRAM')
    guard(isinstance(raw, dict) and set(raw) == {
        'disposition','rationale','considered_organization_request_ids',
        'considered_report_ids','unresolved_frontiers'},
        'META_A2_PROGRAM_REVIEW_SCHEMA')
    guard(raw['disposition'] in PROGRAM_OPTIONS, 'META_A2_PROGRAM_DISPOSITION_UNKNOWN')
    guard(isinstance(raw['rationale'], str) and raw['rationale'].strip(),
          'META_A2_PROGRAM_RATIONALE_REQUIRED')
    children = raw['considered_organization_request_ids']
    reports = raw['considered_report_ids']
    guard(isinstance(children, list) and len(children) == len(set(children)) and
          set(children) == set(s.organization_materialized),
          'META_A2_PROGRAM_MUST_ACCOUNT_FOR_ALL_CHILDREN')
    current = {x['report_id'] for x in s.child_research_reports.values()}
    guard(isinstance(reports, list) and len(reports) == len(set(reports)) and
          set(reports) == current,
          'META_A2_PROGRAM_REVIEW_STALE_OR_OMITTED_REPORT')
    guard(isinstance(raw['unresolved_frontiers'], list) and
          all(isinstance(x, str) for x in raw['unresolved_frontiers']),
          'META_A2_PROGRAM_UNRESOLVED_FRONTIERS_INVALID')
    return {**raw, 'decision_id': decision_id, 'call_id': call_id,
            'science_certification': False, 'program_level_model_judgment_only': True}


def _import_key(request, asset_id):
    return request['id'] + '#' + asset_id


def _source_and_asset_ids(child, original_asset_id):
    token = sha(canon({'child': str(child.resolve()), 'original_asset_id': original_asset_id}))[:25]
    return 'SRC_M28_COLLAB_' + token, 'A_M28_COLLAB_' + token


def import_selected(experiment, parent_root):
    """Execute only saved/committed Controller selections, never auto-import."""
    exp = Path(experiment).resolve()
    j = EvolutionJournal(parent_root)
    s = j.verify()
    guard(s.meta_collaboration, 'META_A2_NOT_ACTIVATED')
    imported = []
    for req in list(s.collaboration_requests.values()):
        guard(any(d['id']==req['decision_id'] and d['call_id']==req['call_id']
                  for d in j.verify().controller_decisions),
              'META_A2_IMPORT_REQUIRES_COMMITTED_CONTROLLER')
        org_id = req['organization_request_id']
        # Historical selection references its exact captured report, not the
        # latest child report (which may have advanced afterward).
        reports = [r for r in j._events() if r['kind'] == 'CHILD_RESEARCH_OBSERVED'
                   and r['payload']['report_id'] == req['report_id'] and
                   r['payload']['organization_request_id'] == org_id]
        guard(len(reports) == 1, 'META_A2_SELECTED_REPORT_NOT_FOUND')
        original_report = json.loads(j.raw(reports[0]['payload']['report_blob']))
        child, _ = _root_for_child(exp, j, org_id)
        cj = EvolutionJournal(child)
        cs = cj.verify()
        candidates = {a['id']: a for a in original_report['candidate_assets']}
        for asset_id in req['asset_ids']:
            key = _import_key(req, asset_id)
            if key in j.verify().collaboration_imports:
                continue
            assert asset_id in candidates
            original = cs.assets.get(asset_id)
            guard(original is not None and sha(canon(original)) == candidates[asset_id]['asset_sha256'],
                  'META_A2_CHILD_ASSET_CHANGED_OR_DISAPPEARED')
            live = _live_asset_record(cj, cs, original)
            guard(live is not None and live['asset_sha256'] == candidates[asset_id]['asset_sha256'],
                  'META_A2_CHILD_ASSET_NOT_SAVED_WORKER_OUTPUT')
            source_id, local_id = _source_and_asset_ids(child, asset_id)
            source = {'protocol': POLICY, 'origin_root': str(child),
                      'original_asset_id': asset_id, 'original_asset': original,
                      'origin_model_call_id': live['model_call_id'],
                      'origin_model_response_sha256': live['model_response_sha256'],
                      'origin_billing_mode': live['model_billing_mode'],
                      'original_parent_ids': original.get('parent_ids', []),
                      'original_source_ids': original.get('source_ids', []),
                      'original_child_head_sha256': original_report['child_head_sha256'],
                      'selected_report_id': req['report_id'],
                      'selection_decision_id': req['decision_id'],
                      'original_science_not_certified': True,
                      'this_import_not_new_execution': True}
            present_source = j.verify().sources.get(source_id)
            if present_source is None:
                j.add_source(source_id, 'HISTORICAL_AI', source,
                             'Model-selected child AI science; provenance is not empirical certification')
            else:
                guard(present_source['kind'] == 'HISTORICAL_AI' and
                      json.loads(j.raw(present_source['blob'])) == source,
                      'META_A2_SOURCE_CONFLICT')
            imported_asset = {'id': local_id, 'kind': original['kind'],
                'problem_id': 'P0', 'parent_ids': [],
                'claim': original['claim'],
                'scope': original.get('scope') or 'Claim scope as originally declared',
                'assumptions': original.get('assumptions') or 'Unverified origin assumptions',
                'predictions': list(original.get('predictions', [])),
                'limitations': list(original.get('limitations', [])) + [
                    'Selective cross-root historical AI assertion; not primary evidence',
                    'Original child asset ancestry and source IDs retained in source blob'],
                'source_ids': [source_id],
                'original_asset_id': asset_id, 'origin_root': str(child),
                'original_parent_ids': original.get('parent_ids', []),
                'origin_work_mode': 'INFORMED_CROSS_ROOT_IMPORT_NOT_LIVE_WORK'}
            present_asset = j.verify().assets.get(local_id)
            if present_asset is None:
                j.append('HISTORICAL_ASSET_INDEXED', imported_asset)
            else:
                guard(all(present_asset.get(k) == v for k,v in imported_asset.items()),
                      'META_A2_ASSET_CONFLICT')
            receipt = {'id': key, 'selection_id': req['id'],
                       'organization_request_id': org_id,
                       'original_asset_id': asset_id, 'local_asset_id': local_id,
                       'source_id': source_id, 'selected_report_id': req['report_id'],
                       'science_certification': False, 'status': 'HISTORICAL_AI_IMPORTED_NOT_ACCEPTED'}
            j.append('COLLABORATION_ASSET_IMPORTED', receipt)
            imported.append(receipt)
    return imported


def recover_committed_a2(j):
    """Recover A2 commitments from SAVED Controller responses, no model calls."""
    s = j.verify()
    if not s.meta_collaboration:
        return []
    applied = []
    for decision in s.controller_decisions:
        raw = json.loads(j.raw(decision['parsed_blob']))
        for selection in raw.get('collaboration_requests', []):
            ident = selection.get('id') if isinstance(selection, dict) else None
            existing = j.verify().collaboration_requests.get(ident)
            if existing is not None:
                guard(existing == {**selection, 'decision_id': decision['id'],
                                  'call_id': decision['call_id'], 'science_certification': False},
                      'META_A2_RECOVERY_SELECTION_CONFLICT')
                continue
            valid = validate_selection(j, selection, decision['id'], decision['call_id'])
            j.append('COLLABORATION_REQUESTED', valid)
            applied.append(ident)
        review = raw.get('program_portfolio_review')
        if review is not None:
            existing = [v for v in j.verify().program_portfolio_reviews if v['decision_id'] == decision['id']]
            if existing:
                guard(existing[-1] == {**review, 'decision_id': decision['id'],
                      'call_id': decision['call_id'], 'science_certification': False,
                      'program_level_model_judgment_only': True},
                      'META_A2_RECOVERY_PROGRAM_REVIEW_CONFLICT')
            else:
                valid = validate_program_review(j, review, decision['id'], decision['call_id'])
                j.append('PROGRAM_PORTFOLIO_REVIEWED', valid)
                applied.append('PROGRAM_' + decision['id'])
    return applied


def latest_program_disposition(primary):
    s = EvolutionJournal(primary).verify()
    if not s.meta_collaboration or not s.program_portfolio_reviews:
        return None
    review=s.program_portfolio_reviews[-1]
    latest={x['report_id'] for x in s.child_research_reports.values()}
    if (set(review['considered_report_ids']) != latest or
            set(review['considered_organization_request_ids']) !=
            set(s.organization_materialized)):
        return {**review, 'stale': True,
                'status': 'REVIEW_STALE_NEW_CHILD_SCIENCE_OR_ORGANIZATION'}
    return {**review, 'stale': False}
