# ScientificEvolution — Development State

**Snapshot date:** 2026-10-31. **Development branch:** `dev/research-continuity-v1`.
**Historical code baseline:** `snapshot/g14-20261031`, commit
`bb9346c5fb6de38b7a5528cbfc4242c923e6e4a5`.

## Verified current architecture

* `AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/autonomous_population.py`:
  generation/peer orchestration, scientific council, continuation/handoff.
* `runtime/scientific_problem_evolution.py`: advisory novelty (NVT), impact
  (PMI), opportunity assessment, and scientific Controller decision routing.
* `runtime/e2core/engine.py`: Controller, Work, Worker and research tool steps.
* `runtime/e2core/provider.py`: durable model calls, exact-input replay and
  fail-closed paid gate. `runtime/e2core/core.py`: journal, state, lineage.
* `G14_DOI_OPEN_PDF_BRIDGE_20261030`, Frontier, Memory and historical runtime
  extensions remain in independent folders. Do not assume they are in the
  central engine simply because a prior paid run loaded them via PYTHONPATH.

## Experiment anchors (separate from Git source)

* **Frozen G14:** 1,638 Journal events, 444 inherited/registered assets,
  head `5250128f4209f479b4bbf44ff22663835d839b1de4845368ef22bc9af9459a2d`.
  G14 code and original Journal must not be mutated by M15 development.
* **M15 G0 (last user-reported status):** stage PEERS, three SYN peers,
  18 paid model calls including Council, two committed local Controllers,
  no new published scientific assets and no actual recorded research tool result.
  SYN_01 has one previously BLOCKED worker, SYN_02 has no committed Controller,
  SYN_03 has one ACTIVE Work at zero Worker steps. These are **observations**,
  not proof of a Level II result or proof that the current model cannot do science.
* M15 Continuity, NVT Scope, Resume V2, and Common Boundary packages were loaded
  from `$HOME/...` externally; they were NOT yet integrated into tracked source
  when the development branch was first pushed. Historical live roots may have
  source pins incompatible with future direct-runtime changes. Use separate
  temporary/mock roots or an explicitly validated new continuation root.

## Current engineering priority

Build one well-understood code path and test it through a whole scientific step.
First native integration at `56ae65b` (2026-10-31, MOCK_VERIFIED on WSL):
Worker-only identical-complete-JSON handling in `runtime/e2core`, six controlled
tests passed. Provider raw-call storage/replay, Controller parsing, historical
SAVED bytes, and finished Work were not changed. A code review then found that
the *legacy preamble fallback* could accept a valid first JSON object followed
by an incomplete second object or trailing garbage, or preamble-wrapped JSON
with duplicate keys. The follow-up fail-closed correction adds explicit regression coverage;
this new code must pass WSL tests before the contract is treated as verified.

## Known M15 continuity boundary (not yet native)

M15-1C's `attach_population_routing` activates its archive bridge only for the
`POPULATION` research/council stage. The current G0 `PEERS` stage deliberately
receives **no G14 rejected-proposal archive** (it still inherits registered
G14 assets through the distinct new ROOT). Thus G0 peer research does not, by
itself, demonstrate actual use of the 19 unregistered opportunities.

The overlay currently monkeypatches `State.apply`, `Engine.worker_step`,
`controller_plan`, `_worker_input`, and selected adviser/model boundaries.
Native integration must distinguish Problem ancestry, Asset ancestry,
Source provenance and *unregistered* opportunity motivation. Controller may
explicitly hand an opportunity to INFORMED work; FRESH must not receive it,
and rejected suggestions must not be reclassified as scientific assets or
source evidence. Preserve archive/source hashes and all original errors.

Next: consolidate typed Problem/Asset/Source relations and unregistered-opportunity
continuity in the core, then assess research scheduler economics. A Controller
that schedules a valuable ACTIVE Work must not be mistaken for a completed
research result. Evidence acquisition must lead to interpretation and a changed
claim/decision to count as scientific progress.

## Work protocol / status labels

* `IMPLEMENTED`: code exists, not necessarily checked on user's WSL.
* `MOCK_VERIFIED`: no-paid controlled test passed against the actual E2 engine.
* `LIVE_VERIFIED`: real run, tool output, and Journal state were inspected.
* `SCIENTIFICALLY_REVIEWED`: a substantive claim has been independently evaluated.

Change this document with significant architecture/scientific milestone commits.
Never copy secret provider inputs, private journals, token strings, or billing
information into this public repository.
