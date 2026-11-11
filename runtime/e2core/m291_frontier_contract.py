"""M29.1 opt-in explicit frontier assessment at an autonomous scientific HOLD.

An assessment is required, NOT a newly invented hypothesis or experiment.
Activation is source-pinned: M29.3 new M28 research roots or legacy opt-in successors.
"""
from __future__ import annotations
import json
from pathlib import Path

from .core import EvidenceError, guard, sha, canon
from .m29_frontier import validate_model_frontier_assessment

MARKER = 'M291_EXPLICIT_FRONTIER_ASSESSMENT_CONTRACT_ACTIVATED'

# This is intentionally prefixed at the start of the Controller's M29.1 prompt.
# A large generic JSON template later in the legacy prompt must not hide it.
CONTROLLER_PRELUDE = '''M29.1 EXPLICIT SCIENTIFIC FRONTIER ASSESSMENT CONTRACT (source-pinned M28 opt-in research):
You retain FULL scientific autonomy over the conclusion and whether to create
any new problem or Work. If (and ONLY if) you choose top-level disposition
HOLD_WITH_RATIONALE, the final JSON MUST include exactly one
research_frontier_assessment object. It MUST choose one of four honest states:
REGISTERED_NEW (real new_problems with typed scientific research_frontier),
LINKED_EXISTING (reference actual already registered subproblem IDs),
NO_ADDITIONAL_VALUE (explain scientifically why no additional nonredundant
research frontier is justified), or CANNOT_YET_SPECIFY (explain why even a
conditional discriminating sub-hypothesis cannot yet be formulated, distinguishing
lack of resources for EXECUTION from lack of information for FORMULATION).
The exact schema is: {"status":"REGISTERED_NEW|LINKED_EXISTING|NO_ADDITIONAL_VALUE|CANNOT_YET_SPECIFY",
"problem_ids":[],"rationale":"specific scientific assessment grounded in existing evidence and gaps"}.
This is a mandatory EXPLICIT ASSESSMENT, not mandatory continuation and not
mandatory creation of new scientific Problems. An absent object on HOLD will
be rejected operationally. Do NOT label an unperformed experiment as evidence;
do NOT claim that a missing instrument prevents a conditional test definition
if the scientific contrast can still be formulated. Never invent test details.
'''


def _active_successor(j):
    """Original M29.1 successor-only gate; unchanged for historical experiments."""
    root=Path(j.root)
    if root.name!='PRIMARY' or root.parent.name!='ROOTS':
        return False
    exp=root.parent.parent
    lineage_path=exp/'M28_NATIVE_RESEARCH_SUCCESSOR.json'
    if not lineage_path.is_file() or lineage_path.is_symlink():
        return False
    lineage=json.loads(lineage_path.read_text(encoding='utf8'))
    if lineage.get('m291_explicit_frontier_contract') is not True:
        return False
    # Verify immutable experiment lineage, including source pin and accounting.
    from .m28_successor import verify_successor_prefix
    verify_successor_prefix(exp)
    events=j._events(); n=lineage['parent_events']
    guard(len(events)>n+1 and events[n+1]['kind']=='OPERATIONAL_PAUSE',
          'M291_FRONTIER_ACTIVATION_EVENT_MISSING')
    marker=events[n+1]['payload']
    guard(marker.get('reason')==MARKER and
          marker.get('parent_head_sha256')==lineage['parent_head_sha256'] and
          marker.get('source_pin_sha256')==sha((exp/'NATIVE_RUNTIME_SOURCE_PIN.json').read_bytes()) and
          marker.get('science_certification') is False,
          'M291_FRONTIER_ACTIVATION_PROVENANCE_MISMATCH')
    return True


# M29.3: general-purpose fresh M28 research roots opt into the EXISTING M29.1
# scientific HOLD contract at initialization, with a source-bound durable marker.
# Source-pinned M29.1 successors keep their own original activation mechanism.
GENERAL_MARKER = 'M293_GENERAL_FRONTIER_ASSESSMENT_ACTIVATED'
GENERAL_FLAG = 'm293_explicit_frontier_assessment_required'

def register_general_root(j):
    """Opt in ONCE at new research initialization; never change an old Journal."""
    from .core import EvolutionJournal
    root=Path(j.root)
    guard(root.name=='PRIMARY' and root.parent.name=='ROOTS',
          'M293_ACTIVATION_ONLY_NEW_PRIMARY')
    exp=root.parent.parent
    guard(not (exp/'M28_NATIVE_RESEARCH_SUCCESSOR.json').exists(),
          'M293_SUCCESSOR_MUST_USE_ORIGINAL_LINEAGE_CONTRACT')
    persistent=json.loads((exp/'persistent.json').read_text(encoding='utf8'))
    meta=json.loads((exp/'meta_research.json').read_text(encoding='utf8'))
    guard(persistent.get(GENERAL_FLAG) is True and meta.get(GENERAL_FLAG) is True,
          'M293_ACTIVATION_MANIFESTS_NOT_OPTED_IN')
    guard(meta.get('root')==str(exp) and meta.get('initial_root')==str(root),
          'M293_ACTIVATION_IDENTITY_MISMATCH')
    pinpath=exp/'NATIVE_RUNTIME_SOURCE_PIN.json'
    guard(pinpath.is_file() and not pinpath.is_symlink(),
          'M293_NATIVE_SOURCE_PIN_REQUIRED')
    state=j.verify()
    guard(state.meta_research_autonomy and state.meta_collaboration and
          sha(state.program['problem'].encode('utf8'))==meta.get('original_P0_sha256'),
          'M293_NEW_PRIMARY_SCIENCE_PROFILE_INVALID')
    guard(not any(e['kind']=='OPERATIONAL_PAUSE' and
                  e['payload'].get('reason')==GENERAL_MARKER for e in j._events()),
          'M293_GENERAL_ACTIVATION_ALREADY_RECORDED')
    j.append('OPERATIONAL_PAUSE',{'reason':GENERAL_MARKER,
        'experiment':str(exp),
        'source_pin_sha256':sha(pinpath.read_bytes()),
        'original_P0_sha256':meta['original_P0_sha256'],
        'science_certification':False,
        'operational_contract_not_scientific_evidence':True})
    guard(active(j), 'M293_POST_ACTIVATION_VERIFICATION_FAILED')
    return GENERAL_MARKER


def _general_active(j,exp):
    from .core import EvolutionJournal
    persistent_path=exp/'persistent.json'
    meta_path=exp/'meta_research.json'
    if not persistent_path.is_file() or not meta_path.is_file():
        return False
    persistent=json.loads(persistent_path.read_text(encoding='utf8'))
    meta=json.loads(meta_path.read_text(encoding='utf8'))
    left=persistent.get(GENERAL_FLAG)
    right=meta.get(GENERAL_FLAG)
    # Ordinary pre-M29.3 roots have neither flag. Only opt-in NEW roots use
    # this branch. A half-set or falsified flag fails closed.
    if left is None and right is None:return False
    guard(left is True and right is True,'M293_FRONTIER_MANIFEST_FLAG_DRIFT')
    guard(meta.get('root')==str(exp) and
          meta.get('initial_root')==str(exp/'ROOTS'/'PRIMARY'),
          'M293_FRONTIER_ROOT_IDENTITY_DRIFT')
    pinpath=exp/'NATIVE_RUNTIME_SOURCE_PIN.json'
    guard(pinpath.is_file() and not pinpath.is_symlink(),
          'M293_FRONTIER_SOURCE_PIN_MISSING')
    primary=EvolutionJournal(exp/'ROOTS'/'PRIMARY')
    state=primary.verify()
    guard(state.meta_research_autonomy and state.meta_collaboration and
          meta.get('original_P0_sha256')==sha(state.program['problem'].encode('utf8')),
          'M293_FRONTIER_PRIMARY_PROGRAM_MISMATCH')
    markers=[r['payload'] for r in primary._events() if
             r['kind']=='OPERATIONAL_PAUSE' and
             r['payload'].get('reason')==GENERAL_MARKER]
    guard(len(markers)==1,'M293_FRONTIER_ACTIVATION_MARKER_MISSING_OR_DUPLICATED')
    marker=markers[0]
    guard(marker.get('experiment')==str(exp) and
          marker.get('source_pin_sha256')==sha(pinpath.read_bytes()) and
          marker.get('original_P0_sha256')==meta['original_P0_sha256'] and
          marker.get('science_certification') is False and
          marker.get('operational_contract_not_scientific_evidence') is True,
          'M293_FRONTIER_ACTIVATION_MARKER_DRIFT')
    # Child Controllers inherit the experiment-level termination contract;
    # child claims do not automatically decide the PRIMARY program outcome.
    local=j.verify()
    guard(local.meta_research_autonomy and local.meta_collaboration and
          local.program['problem']==state.program['problem'],
          'M293_FRONTIER_LOCAL_PROGRAM_MISMATCH')
    return True


def active(j):
    """General new M28 program or unchanged historical M29.1 successor gate."""
    root=Path(j.root)
    if root.parent.name!='ROOTS':return False
    exp=root.parent.parent
    if _general_active(j,exp):return True
    return _active_successor(j)


def validate_for_controller(j, raw, proposed, *, disposition, state):
    """Do not infer missing science. Model must explicitly choose a status."""
    required=active(j) and disposition=='HOLD_WITH_RATIONALE'
    if required:
        guard(raw is not None,'M291_HOLD_FRONTIER_ASSESSMENT_REQUIRED')
    return validate_model_frontier_assessment(raw,state,proposed)
