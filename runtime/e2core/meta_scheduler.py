"""M28-A3 operational scheduler and evidence-triggered scientific re-review.

A scheduler selects CPU/model execution opportunities, NOT a scientific direction.
A previously terminal program is *not* automatically reopened as research: new
child science can permit exactly a new model-authored review; the previous
HOLD/negative/candidate remains historically recorded.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from .core import EvolutionJournal, EvidenceError, guard, canon, sha
from .meta_collaboration import latest_program_disposition, PROGRAM_STOPS

PROTOCOL = 'M28_A3_OPERATIONAL_SCHEDULER_V1'
CHECKPOINT = 'M28_A3_SCHEDULER_CHECKPOINT.json'
TERMINAL = {'HOLD_WITH_RATIONALE', 'SCOPED_NEGATIVE', 'REVIEW_WORTHY_CANDIDATE'}
MATERIAL_EVENTS = {'ASSET_PUBLISHED', 'PROBLEM_CREATED', 'WORK_FINISHED',
                   'HISTORICAL_ASSET_INDEXED', 'CHILD_RESEARCH_OBSERVED',
                   'COLLABORATION_ASSET_IMPORTED', 'PROGRAM_REASSESSMENT_REQUESTED'}


def _event_head(j):
    rows = j._events()
    guard(bool(rows), 'META_A3_EMPTY_JOURNAL')
    return sha(canon(rows[-1]))


def reassessment_pending(j):
    """Only open a new *judgement*, never treat evidence as an automatic CONTINUE."""
    s = j.verify()
    if not s.meta_collaboration or not s.program_reviews:
        return False
    previous = s.program_reviews[-1]
    if previous['scientific_status'] not in TERMINAL:
        return False
    return bool(s.program_reassessments and
                s.program_reassessments[-1]['prior_review_decision_id'] ==
                previous['reviewer_id'])


def request_evidence_reassessment(j):
    """A genuine new child scientific report after terminal may reopen deliberation.

    This does not invalidate or overwrite the old conclusion, nor execute old
    Work. It permits one new Controller judgement from the current science.
    """
    s = j.verify()
    if not s.meta_collaboration or not s.program_reviews:
        return None
    last = s.program_reviews[-1]
    if last['scientific_status'] not in TERMINAL or reassessment_pending(j):
        return None
    events = j._events()
    reviews = [e for e in events if e['kind'] == 'PROGRAM_REVIEWED'
               and e['payload']['reviewer_id'] == last['reviewer_id']]
    guard(len(reviews) == 1, 'META_A3_PROGRAM_REVIEW_EVENT_AMBIGUOUS')
    since = [e for e in events if e['seq'] > reviews[0]['seq'] and
             e['kind'] == 'CHILD_RESEARCH_OBSERVED']
    if not since:
        return None
    new_ids = sorted({e['payload']['report_id'] for e in since})
    current = sorted({v['report_id'] for v in s.child_research_reports.values()})
    # A report may have been superseded during the same run; only the *latest*
    # current reports should trigger an actionable, provenance-linked review.
    new_ids = sorted(set(new_ids).intersection(current))
    if not new_ids:
        return None
    payload = {'prior_review_decision_id': last['reviewer_id'],
               'new_report_ids': new_ids,
               'current_report_ids': current,
               'reason': 'NEW_CHILD_SCIENTIFIC_REPORT_REQUIRES_MODEL_REVIEW_NOT_AUTOMATIC_RESUMPTION',
               'science_certification': False,
               'previous_scientific_result_preserved': True}
    j.append('PROGRAM_REASSESSMENT_REQUESTED', payload)
    return payload


# An operational recovery marker is created ONLY in an independently
# source-pinned successor experiment, never in the original scientific Journal.
M28_RECOVERY_MARKER = 'M28_VERIFIED_SUCCESSOR_TERMINAL_REVIEW_RETRY_OPENED'


def controller_recovery_pending(j):
    """Allow a model-authored terminal rejudgment, not a new science claim.

    No model output is rewritten or accepted by this predicate. Only successor
    runs with a verified, explicit upstream lineage receive one new recovery
    window. Once a Controller decision commits, the window is consumed.
    """
    root = j.root
    if root.name != 'PRIMARY' or root.parent.name != 'ROOTS':
        return False
    exp = root.parent.parent
    p = exp / 'M28_NATIVE_RESEARCH_SUCCESSOR.json'
    if not p.is_file() or p.is_symlink():
        return False
    meta = json.loads((exp / 'meta_research.json').read_text(encoding='utf8'))
    persistent = json.loads((exp / 'persistent.json').read_text(encoding='utf8'))
    if (meta.get('native_successor_sha256') != sha(p.read_bytes()) or
            persistent.get('native_successor_sha256') != sha(p.read_bytes())):
        return False
    lineage = json.loads(p.read_text(encoding='utf8'))
    rows = j._events()
    prefix_n = lineage.get('parent_events')
    if type(prefix_n) is not int or prefix_n < 1 or len(rows) <= prefix_n:
        return False
    handoff = rows[prefix_n]
    if (handoff['kind'] != 'OPERATIONAL_PAUSE' or
            handoff['payload'].get('reason') != M28_RECOVERY_MARKER or
            handoff['payload'].get('parent_head_sha256') != lineage.get('parent_head_sha256') or
            sha(canon(rows[prefix_n-1])) != lineage.get('parent_head_sha256')):
        return False
    if any(e['kind'] == 'CONTROLLER_DECISION' for e in rows[prefix_n+1:]):
        return False
    s = j.verify()
    if (not s.meta_collaboration or not s.program_reviews or
            s.program_reviews[-1]['scientific_status'] != 'ONGOING' or
            not s.controller_decisions or
            any(w['status'] in {'ACTIVE', 'QUEUED'} for w in s.work.values()) or
            any(v['state'] != 'SAVED' for v in s.model_calls.values())):
        return False
    last = max(i for i,e in enumerate(rows) if e['kind'] == 'CONTROLLER_DECISION')
    return any(e['kind'] == 'OPERATIONAL_PAUSE' and
               str(e['payload'].get('reason','')).startswith(
                   ('CONTROLLER_PLAN_REJECTED:', 'CONTROLLER_INVALID_JSON')) and
               e['payload'].get('call_id') in s.model_calls and
               s.model_calls[e['payload']['call_id']]['state'] == 'SAVED'
               for e in rows[last+1:])


def root_ready(root):
    guard(not Path(root).is_symlink(), 'META_A3_SYMLINK_RESEARCH_ROOT')
    j = EvolutionJournal(root); s = j.verify()
    guard(s.meta_research_autonomy and s.meta_collaboration,
          'META_A3_NOT_OPTED_IN_ROOT')
    uncertain = [x for x,v in s.model_calls.items() if v['state'] != 'SAVED']
    guard(not uncertain, 'META_A3_UNRESOLVED_MODEL_CALL_MANUAL_REVIEW:'+
          ','.join(uncertain[:3]))
    if s.program_reviews and s.program_reviews[-1]['scientific_status'] in TERMINAL:
        return reassessment_pending(j)
    if any(w['status'] in {'ACTIVE','QUEUED'} for w in s.work.values()):
        return True
    if not s.controller_decisions:
        return True
    events = j._events()
    last = max((i for i,e in enumerate(events) if e['kind'] == 'CONTROLLER_DECISION'), default=-1)
    if any(e['kind'] in MATERIAL_EVENTS for e in events[last+1:]):
        return True
    return controller_recovery_pending(j)


def _initial_state():
    return {'protocol': PROTOCOL, 'visits_total': 0, 'last_completed_root': None,
            'in_flight': None, 'science_certification': False}


def _read_state(exp):
    f = Path(exp) / CHECKPOINT
    if not f.exists():
        return _initial_state()
    guard(f.is_file() and not f.is_symlink(), 'META_A3_CHECKPOINT_NOT_REGULAR_FILE')
    raw = f.read_bytes(); data = json.loads(raw)
    guard(raw == canon(data) and isinstance(data,dict) and
          set(data)==set(_initial_state()) and data['protocol']==PROTOCOL and
          type(data['visits_total']) is int and data['visits_total'] >= 0 and
          (data['last_completed_root'] is None or isinstance(data['last_completed_root'],str)) and
          data['science_certification'] is False, 'META_A3_CHECKPOINT_INVALID')
    flight = data['in_flight']
    guard(flight is None or (isinstance(flight, dict) and
          set(flight)=={'root','initial_journal_head','visit_number'} and
          isinstance(flight['root'],str) and
          isinstance(flight['initial_journal_head'],str) and len(flight['initial_journal_head'])==64 and
          type(flight['visit_number']) is int and
          flight['visit_number']==data['visits_total']+1),
          'META_A3_CHECKPOINT_FLIGHT_INVALID')
    return data


def _write_state(exp, state):
    """Atomic and fsynced operational checkpoint. Caller holds experiment lock."""
    exp = Path(exp)
    path = exp / CHECKPOINT
    guard(not path.is_symlink(), 'META_A3_CHECKPOINT_SYMLINK')
    fd, stage = tempfile.mkstemp(prefix='.m28-a3-scheduler-',dir=exp)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(canon(state));f.flush();os.fsync(f.fileno())
        os.replace(stage,path)
        directory = os.open(exp,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(stage):os.unlink(stage)


def _next_root(roots,last):
    """Deterministic, persisted operational fairness; no scientific priority ranking."""
    names = sorted(roots)
    if not names:return None
    if last is None:return names[0]
    return next((name for name in names if name > last),names[0])


def _recover_flight(exp, state, root_names):
    flight = state['in_flight']
    if flight is None:return state, None
    name=flight['root']
    guard(name in root_names,'META_A3_INFLIGHT_ROOT_DISAPPEARED')
    j=EvolutionJournal(Path(exp)/'ROOTS'/name)
    if _event_head(j) == flight['initial_journal_head']:
        return state, name  # no Journal progress: safely retry this visit
    # The Journal did progress: never replay a possibly completed research
    # slice solely because the scheduler process crashed before checkpoint.
    state={**state,'in_flight':None,'last_completed_root':name,
           'visits_total':state['visits_total']+1}
    _write_state(exp,state)
    return state, None


def _incomplete_controller_decisions(j):
    """Fail closed on base Controller commits left without PROGRAM_REVIEWED.

    A1/A2 recover metadata commitments, not necessarily the scientific Work
    plan itself. Do not silently resume and misrepresent partial decisions.
    """
    s=j.verify()
    reviewed={r['reviewer_id'] for r in s.program_reviews}
    objectives={r['reviewer_id'] for r in s.objective_assessments}
    evolutions={r['id'] for r in s.evolution}
    missing=[]
    for decision in s.controller_decisions:
        ident=decision['id']
        if ident not in reviewed or (s.r5_policy and ident not in objectives):
            missing.append(ident+':PROGRAM_OR_OBJECTIVE_REVIEW_MISSING')
            continue
        authored=json.loads(j.raw(decision['parsed_blob']))
        actions=authored.get('actions',[])
        if not isinstance(actions,list) or any(not isinstance(action,dict) or
            action.get('id') not in evolutions for action in actions):
            missing.append(ident+':SCIENTIFIC_WORK_PLAN_INCOMPLETE')
        if s.e3r1_policy:
            for group in authored.get('portfolio_decisions',[]):
                if not isinstance(group,dict):
                    missing.append(ident+':PORTFOLIO_PLAN_INVALID');break
                for wid in group.get('work_ids',[]):
                    history=s.work.get(wid,{}).get('portfolio_history',[])
                    if not any(item.get('reviewer_id')==ident and
                               item.get('action')==group.get('action') for item in history):
                        missing.append(ident+':PORTFOLIO_PLAN_INCOMPLETE');break
    return missing


def run_dynamic(exp,meta,args,drive,modules,synchronize,preflight,roots):
    """Execute model-authored science in repeatedly visited, independent ROOTs.

    The caller has acquired the global experiment lock and the actual paid
    execution opt-in. `drive` is the existing science engine, never a mock in
    production. Injection supports no-paid integration tests.
    """
    exp=Path(exp).resolve()
    preflight(exp,meta)
    synchronize(exp,args.max_roots)
    for root in roots(exp):
        missing=_incomplete_controller_decisions(EvolutionJournal(root))
        guard(not missing,'META_A3_INCOMPLETE_CONTROLLER_SCIENCE_PLAN_MANUAL_REVIEW:'+
              root.name+':'+','.join(missing[:3]))
        request_evidence_reassessment(EvolutionJournal(root))
    preflight(exp,meta)
    m=modules()
    spent=0;visits=[];idled=set();stop_reason='ROOT_VISIT_LIMIT'
    state=_read_state(exp)
    state,retry=_recover_flight(exp,state,{x.name for x in roots(exp)})
    for _ in range(args.max_root_visits):
        synchronize(exp,args.max_roots)
        for r in roots(exp):
            missing=_incomplete_controller_decisions(EvolutionJournal(r))
            guard(not missing,'META_A3_INCOMPLETE_CONTROLLER_SCIENCE_PLAN_MANUAL_REVIEW:'+r.name+':'+','.join(missing[:3]))
            request_evidence_reassessment(EvolutionJournal(r))
        primary = exp/'ROOTS'/'PRIMARY'
        decision=latest_program_disposition(primary)
        if decision is not None and decision['disposition'] in PROGRAM_STOPS and not reassessment_pending(EvolutionJournal(primary)):
            if decision.get('stale'):
                raise EvidenceError('META_A3_STALE_PROGRAM_REVIEW_WITHOUT_NEW_REPORT_REQUIRES_REVIEW')
            visits.append({'status':'MODEL_AUTHORED_PROGRAM_SCIENTIFIC_PAUSE_OR_RESULT',
                           'disposition':decision['disposition'],
                           'not_independently_certified':True})
            stop_reason='PROGRAM_LEVEL_MODEL_AUTHORED_SCIENTIFIC_DISPOSITION'
            break
        if spent >= args.max_new_calls:
            stop_reason='OPERATIONAL_TOTAL_CALL_BUDGET'
            break
        rootlist={x.name:x for x in roots(exp)}
        eligible={name:root for name,root in rootlist.items() if root_ready(root)}
        pending_primary=reassessment_pending(EvolutionJournal(primary))
        if pending_primary:
            eligible={'PRIMARY':primary} # only rejudge before other paid research
        eligible={name:root for name,root in eligible.items() if name not in idled}
        if not eligible:
            stop_reason='NO_ACTIONABLE_ROOT_OR_SCIENTIFIC_STATE_CHANGE'
            break
        if retry is not None and retry in eligible:
            name=retry;retry=None
        else:name=_next_root(eligible,state['last_completed_root'])
        root=eligible[name]
        if state['in_flight'] is None:
            state={**state,'in_flight':{'root':name,'initial_journal_head':_event_head(EvolutionJournal(root)),
                                      'visit_number':state['visits_total']+1}}
            _write_state(exp,state)
        elif state['in_flight']['root'] != name:
            raise EvidenceError('META_A3_INFLIGHT_ROOT_SELECTION_CONFLICT')
        spec=SimpleNamespace(paid=True,model=args.model,
             max_new_calls=min(args.slice_budget,args.max_new_calls-spent),
             slice_budget=args.slice_budget,
             checkpoint_iterations=args.checkpoint_iterations,
             max_parallel=args.max_parallel,max_tokens=args.max_tokens,
             science_cpu_seconds=args.science_cpu_seconds,
             science_wall_seconds=args.science_wall_seconds)
        outcome=drive(m,root,spec,'syn')
        used=outcome['new_calls_this_launch']
        guard(type(used) is int and 0<=used<=spec.max_new_calls,
              'META_A3_UNEXPECTED_MODEL_CALL_COUNT')
        spent+=used
        state={**state,'in_flight':None,'last_completed_root':name,
               'visits_total':state['visits_total']+1}
        _write_state(exp,state)
        visits.append({'root':str(root),'new_calls':used,'result':outcome})
        if used==0 or outcome.get('stop_reason') in {
                'SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED',
                'OPERATIONAL_ERROR_OR_NO_RESEARCH_ACTION',
                'OPERATIONAL_DEVELOPMENT_BUDGET_PAUSE'}:
            idled.add(name)
        changes=synchronize(exp,args.max_roots)
        if any(changes.values()):
            visits[-1]['organization_updates']=changes
            idled.clear()
        preflight(exp,meta)
        for r in roots(exp):request_evidence_reassessment(EvolutionJournal(r))
    return {'status':'M28_A3_EXECUTION_AT_SCIENTIFIC_OR_OPERATIONAL_BOUNDARY',
            'new_model_calls':spent,'visits':visits,'stop_reason':stop_reason,
            'scheduler_checkpoint':state,'scientific_certification':False}
