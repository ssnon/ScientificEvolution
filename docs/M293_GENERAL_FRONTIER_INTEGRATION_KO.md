# M29.3 — General M28 frontier-assessment integration

## Problem

M29.2 repaired the actual V3/V4 Controller's delivery of M28-A1/A2 and M29, but
M29.1 was activated only in a special historical M28 successor. As a result,
new autonomous M28 ROOTs could approve `HOLD_WITH_RATIONALE` without an explicit
frontier assessment. `wire_contract_failures=0` on M29.2 correctly tested active
contracts, but did not test whether the required contract was active.

## Change

- The existing scientific contract is **not rewritten**: the scientist freely
  chooses HOLD or ONGOING, and no new problem, Work, peer or synthetic data is
  automatically created. `HOLD_WITH_RATIONALE` requires exactly one typed
  model-authored `research_frontier_assessment`: REGISTERED_NEW, LINKED_EXISTING,
  NO_ADDITIONAL_VALUE, CANNOT_YET_SPECIFY.
- Newly created M28 experiments record
  `m293_explicit_frontier_assessment_required=true` in both manifests, then an
  append-only `OPERATIONAL_PAUSE` activation event after native source pinning.
  The activation event binds the exact experiment, P0 digest and source pin.
- M29.1 `active(j)` now detects this NEW program opt-in for PRIMARY and child
  ROOTs, while preserving the original successor-only path for M29.1 `_06`.
- M28 preflight checks the opt-in and fails closed on missing/mismatched markers.
- No existing Journal or experiment is changed; old code/experiments are never
  silently repinned. An existing M29.2 ROOT with its own immutable pin **cannot
  simply be executed with M29.3 code**. Create a new M29.3 root (or build a
  separately audited continuation protocol) for further paid research.

## Scope of guarantee

The validation ensures the **presence, schema, and references** of a model-
authored frontier assessment on HOLD. It does **not** prove scientific validity,
causal identifiability, adequate evidence, independent verification or correctness
of the decision to HOLD. Other terminal statuses remain covered by their existing
R5/M28 contracts; M29.1's additional explicit frontier gate is intentionally
specific to HOLD_WITH_RATIONALE.

## Source and operating guardrails

- Existing `M292_DAC_NO3RR_FRESH_20261111_01` is read only.
- Never edit old `NATIVE_RUNTIME_SOURCE_PIN.json`, Journal events or model calls.
- Never alter source bytes in a source-pinned experiment's runtime.
- No paid API calls in patch integration or regression tests.
- Git clean worktree required. Actual V3/V4 M29.2 unified Controller function
  must already exist.
