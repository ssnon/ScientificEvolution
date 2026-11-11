"""M29.1 opt-in explicit frontier assessment at an autonomous scientific HOLD.

An assessment is required, NOT a newly invented hypothesis or experiment.
Activation is source-pinned and recorded in one native successor Journal only.
"""
from __future__ import annotations
import json
from pathlib import Path

from .core import EvidenceError, guard, sha, canon
from .m29_frontier import validate_model_frontier_assessment

MARKER = 'M291_EXPLICIT_FRONTIER_ASSESSMENT_CONTRACT_ACTIVATED'

# This is intentionally prefixed at the start of the Controller's M29.1 prompt.
# A large generic JSON template later in the legacy prompt must not hide it.
CONTROLLER_PRELUDE = '''M29.1 EXPLICIT SCIENTIFIC FRONTIER ASSESSMENT CONTRACT (source-pinned opt-in):
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


def active(j):
    """Read-only provenance gate; never activate on a legacy or sibling ROOT."""
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


def validate_for_controller(j, raw, proposed, *, disposition, state):
    """Do not infer missing science. Model must explicitly choose a status."""
    required=active(j) and disposition=='HOLD_WITH_RATIONALE'
    if required:
        guard(raw is not None,'M291_HOLD_FRONTIER_ASSESSMENT_REQUIRED')
    return validate_model_frontier_assessment(raw,state,proposed)
