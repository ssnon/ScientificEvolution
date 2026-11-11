"""M29: preserve scientifically authored, conditional follow-up problems on HOLD.

A frontier is an unexecuted hypothesis/test specification, not a measured
result, a certified claim, an automatically authorized Work, or a science STOP.
The Controller may also reject a proposed frontier as redundant/unspecifiable.
No scientific content is inferred from the model's unstructured rationale.
"""
from __future__ import annotations

from .core import EvidenceError, guard

STATUS = frozenset({'REGISTERED_NEW', 'LINKED_EXISTING',
                    'NO_ADDITIONAL_VALUE', 'CANNOT_YET_SPECIFY'})
EVIDENCE_TYPES = frozenset({'LITERATURE','CALCULATION','EXPERIMENT'})
ACQUISITION_STATES = frozenset({'NOT_ATTEMPTED','ATTEMPTED_INCONCLUSIVE',
                                'PRIMARY_TEXT_READ','CALCULATION_PERFORMED',
                                'REQUIRES_EXTERNAL_RESOURCE',
                                'ACCESS_UNAVAILABLE'})
FRONTIER_FIELDS = frozenset({'scientific_status','competing_hypotheses',
    'discriminating_intervention_or_observation','predicted_outcomes',
    'required_evidence','blocking_resources','interpretation_limits',
    'motivating_asset_ids'})

CONTROLLER_ADDENDUM = '''\nM29 EVIDENCE-TO-RESEARCH-FRONTIER HANDOFF (M28 roots only):
The original P0 is not solved merely because available observations do not
identify a mechanism. Before a scientific HOLD, distinguish (1) additional
literature/analysis/calculation that can genuinely change evidence, (2)
scientifically formulable discriminating tests whose execution is blocked by
specimens/instruments/data, and (3) already exhausted or redundant avenues.
Lack of a specified target catalyst or instrument can prevent executing an
experiment, but does NOT in itself prevent formulating a conditional testable
sub-hypothesis. Conversely, never invent materials, uncertainty levels,
measurement capability or causal outcomes. Preserve uncertainty and scope.

For any scientifically valuable NEW unresolved sub-hypothesis, use the EXISTING
new_problems[] contract to register a real descendant Problem of P0, with a
specific question and parent relation. In that new_problem include optional
research_frontier object with EXACT fields:
 {"scientific_status":"PROPOSED_NOT_EXECUTED",
  "competing_hypotheses":["H1: ...","H0: ..."],
  "discriminating_intervention_or_observation":"what contrast to measure/change",
  "predicted_outcomes":[{"if":"H1 or condition","then":"conditional prediction","limitation":"nonunique interpretation"},
                        {"if":"H0 or condition","then":"different prediction","limitation":"nonunique interpretation"}],
  "required_evidence":[{"kind":"LITERATURE|CALCULATION|EXPERIMENT",
                         "purpose":"which scientific distinction this tests",
                         "acquisition_state":"NOT_ATTEMPTED|ATTEMPTED_INCONCLUSIVE|PRIMARY_TEXT_READ|CALCULATION_PERFORMED|REQUIRES_EXTERNAL_RESOURCE|ACCESS_UNAVAILABLE"}],
  "blocking_resources":["specific missing sample/instrument/data, if any"],
  "interpretation_limits":"what positive/negative outcomes still cannot prove",
  "motivating_asset_ids":["EXISTING_ASSET_ID"]}.
Every item must have scientific specificity; do NOT create a generic task
called 'more data required'. Never mark the proposal as experimental evidence.
The Problem can be registered DURING HOLD with actions=[]; registering a Problem
does NOT authorize a new executable Worker or require continued model calls.
If an existing Problem already specifies the test, do not duplicate it.

Also AUTHOR one research_frontier_assessment object in the Controller response:
 {"status":"REGISTERED_NEW|LINKED_EXISTING|NO_ADDITIONAL_VALUE|CANNOT_YET_SPECIFY",
  "problem_ids":["P_known_or_new"],
  "rationale":"why this is a novel, existing, redundant, or not-yet-formulable scientific frontier"}.
REGISTERED_NEW references newly authored new_problems with research_frontier;
LINKED_EXISTING references existing Problem IDs; NO_ADDITIONAL_VALUE and
CANNOT_YET_SPECIFY use []. A HOLD does not require positive research frontiers,
and output format should never drive scientific activity or a false conclusion.
The runtime records only model-authored structured frontiers and accepts older
responses without this optional field; missing structure is auditably missing,
not silently fabricated.\n'''


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _texts(v, *, minimum=0):
    return (isinstance(v,list) and len(v)>=minimum and
            all(_text(x) for x in v))


def validate_spec(spec, state):
    """Validate shape/references, never the scientific truth of a proposal."""
    guard(isinstance(spec,dict) and set(spec)==FRONTIER_FIELDS,
          'M29_FRONTIER_SPEC_FIELDS')
    guard(spec['scientific_status']=='PROPOSED_NOT_EXECUTED',
          'M29_FRONTIER_NOT_CERTIFIED')
    guard(_texts(spec['competing_hypotheses'],minimum=2),
          'M29_FRONTIER_COMPETITORS_REQUIRED')
    guard(_text(spec['discriminating_intervention_or_observation']),
          'M29_FRONTIER_DISCRIMINATOR_REQUIRED')
    outcomes=spec['predicted_outcomes']
    guard(isinstance(outcomes,list) and len(outcomes)>=2 and
          all(isinstance(o,dict) and set(o)=={'if','then','limitation'} and
              all(_text(o[k]) for k in ('if','then','limitation')) for o in outcomes),
          'M29_FRONTIER_CONDITIONAL_OUTCOMES_REQUIRED')
    evidence=spec['required_evidence']
    guard(isinstance(evidence,list) and bool(evidence) and
          all(isinstance(e,dict) and set(e)=={'kind','purpose','acquisition_state'} and
              e['kind'] in EVIDENCE_TYPES and _text(e['purpose']) and
              e['acquisition_state'] in ACQUISITION_STATES for e in evidence),
          'M29_FRONTIER_EVIDENCE_REQUIRED')
    guard(_texts(spec['blocking_resources']) and _text(spec['interpretation_limits']),
          'M29_FRONTIER_LIMITS_REQUIRED')
    assets=spec['motivating_asset_ids']
    guard(isinstance(assets,list) and len(assets)==len(set(assets)) and
          all(a in state.assets for a in assets), 'M29_FRONTIER_UNKNOWN_ASSET')
    return spec


def validate_model_frontier_assessment(raw, state, proposed_problems):
    """Check exactly what model authored. Omission remains omission."""
    if raw is None:
        return None
    guard(isinstance(raw,dict) and set(raw)=={'status','problem_ids','rationale'},
          'M29_FRONTIER_ASSESSMENT_FIELDS')
    status=raw['status']; ids=raw['problem_ids']
    guard(status in STATUS and _text(raw['rationale']) and
          isinstance(ids,list) and len(ids)==len(set(ids)) and
          all(_text(i) for i in ids), 'M29_FRONTIER_ASSESSMENT_INVALID')
    new={p['id']:p for p in proposed_problems if isinstance(p,dict) and
         isinstance(p.get('id'),str)}
    known=set(state.problems)
    guard(set(ids).issubset(known | set(new)), 'M29_FRONTIER_UNKNOWN_PROBLEM')
    if status=='REGISTERED_NEW':
        guard(bool(ids) and set(ids).issubset(new),
              'M29_FRONTIER_REGISTERED_NEW_IDS_REQUIRED')
        for ident in ids:
            p=new[ident]
            guard(isinstance(p.get('parents'),list) and bool(p['parents']),
                  'M29_FRONTIER_PARENT_REQUIRED')
            validate_spec(p.get('research_frontier'),state)
    elif status=='LINKED_EXISTING':
        guard(bool(ids) and set(ids).issubset(known - {'P0'}),
              'M29_FRONTIER_LINK_EXISTING_REQUIRED')
    else:
        guard(not ids,'M29_FRONTIER_NO_NEW_IDS_REQUIRED')
    return dict(raw)
