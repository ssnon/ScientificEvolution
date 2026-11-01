<!-- CURRENT_STATE_2026_11_01_M17 -->
# ScientificEvolution — Current Development State

**Current snapshot:** 2026-11-01 (KST). **Development branch:** `dev/research-continuity-v1`. **Native runtime baseline:** `944d1a7` (M17 historical Work scope). This is a status record, not experimental evidence or a scientific certificate.

**Read first:** [PROJECT_VISION.md](PROJECT_VISION.md) (scientific mission and invariants), [RESEARCH_EVOLUTION_LOG.md](RESEARCH_EVOLUTION_LOG.md) (dated real-run observations and scientific deltas). The previous 2026-10-31 development snapshot is preserved verbatim below.

## Scientific north star

The objective is a **general-purpose autonomous pre-experimental AI Scientist**, not a SERS-only pipeline, knowledge-graph product, or fixed agent workflow. Given unresolved P0, independent AI researchers propose, critique, revise, calculate, acquire actual literature evidence and evaluate competing mechanisms; Population steering selects whether and how to propagate results into new independent scientific decisions, further studies and generations. Valid dispositions include a review-worthy Level II pre-experimental candidate and a rigorously scoped, independently challenged lack-of-progress decision. Neither fixed generation count nor number of model calls/assets is a scientific success criterion.

**Level II** means a physically defensible, meaningfully novel and falsifiable proposal with concrete predictions distinguishable from strong null mechanisms, credible prior-art comparison, experimental observables/controls and explicit uncertainty. It is not an experimentally verified discovery. Models and tools may assess these conditions, but such assessments are not external certification. A tool failure is not a scientific negative; a local HOLD is not an impossibility theorem for P0.

## Verified architecture and boundaries

- `runtime/e2core/{core,provider,engine,research_continuity}.py`: provenance-preserving append-only Journal, saved/replay-safe model calls, actual Controller/Work/Worker/tool execution, independent and inherited research context, typed lineage and rejected-proposal continuity.
- `runtime/scientific_problem_evolution.py`, `scientific_closed_loop_v3.py`, `scientific_research_readiness_v4.py`: novelty/impact/opportunity/readiness assessments and scientific continuation. LLM assessment is advisory, not experimental verification.
- `AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/{generational_run,persistent_population,autonomous_population,population_resume}.py`: native source-pinned experiment creation, independent peer orchestration, researcher/Population Council decisions, synthesis/combination and generation continuity.
- M16 `723e149`: new native Python-byte source pin and historical rejected-opportunity handoff; historic V3 guards remain separate.
- M17 `944d1a7`: historical G14 Work status is context only, **not executable current-root Work**. The AI may explicitly authorize a new Work to continue past science; it cannot KEEP/REACTIVATE a Work that is absent from the current Journal. User ran all 54 no-paid regressions successfully (Continuity 24, V3 9, V4 13, Clean 8).

Historical hypotheses, primary sources, executed research outputs, problem/asset ancestry and rejected suggestions remain different kinds of record. FRESH must not silently inherit earlier AI answers. Operational budget/source-pin boundaries cannot be conflated with scientific conclusions.

## Last operator-reported research status

| Root / experiment | Observed execution | Evidence status |
| --- | --- | --- |
| Frozen G14: `$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029/CYCLE_014/POPULATION` | 1,638 journal events and 444 assets in historical snapshot; original root remains frozen | Historical AI research, not Level II certified |
| M16 clean: `$HOME/ScientificEvolution_runs/M16_G14_NATIVE_CLEAN_20261031_01` | 8 saved external calls; 3 rejected Controllers due to G14 Work IDs incorrectly referenced as current-root Work | **Operational defect**, no scientific negative or committed new Work |
| M17 clean: `$HOME/ScientificEvolution_runs/M17_G14_NATIVE_CLEAN_20261101_01` | 2 committed PEER Controllers; 12 saved research-root calls plus 2 Council/meta calls (14 total). SYN_01 has an ACTIVE primary-source audit, no worker call yet. SYN_02 has 3 saved Worker calls, 2 tool records (`EVIDENCE_UNAVAILABLE`, `DELIVERED`), one new unverified hypothesis, final `BLOCKED_FORMAT` and Council `YIELD_TO_POPULATION`. Stage still PEERS. | Real model/tools and critical peer steering observed; **cross-peer scientific synthesis and improved downstream hypothesis not yet demonstrated** |

**Provenance qualifications:** G14 provided 444 inherited assets and 2 direct historical tool sources, whose scientific content is not independently certified here. The separate 19-entry archive and G14 rejected-proposal Journal contain the *same 19 original submissions*; do not inflate these to 38 opportunities. M17 carries 19 unique rejected opportunities, not an additional archive pin. Both M17 peers inherit the common G14 historical asset base and are independent *continuing peers*, not fully seedless FRESH researchers. SYN_02's `A_charge_height_gating_001` (charge state changing adsorption height/orientation, giving SERS intermittency without desorption) was assessed by Council as substantially overlapping earlier G14 candidates; this is not a Level II result. SYN_02 evidence audit completed: OpenAlex HTTP 429; Europe PMC returned bibliographic metadata only (PMC9952515, a review), not inspected primary full text. Final Worker output contained two distinct JSON documents and was correctly rejected. No scientific negative or Level II result follows.

## Single near-term milestone: first genuine scientific evolution

1. **Read-only inspect** SYN_02 tool request/results and `BLOCKED_FORMAT`; distinguish OA full text, abstract, bibliographic metadata and access failure. Do not overinterpret `DELIVERED` or rewrite the saved model response.
2. **Resume M17 SYN_01's ACTIVE Work** on the unchanged, source-pinned runtime, giving the Worker an opportunity to actually acquire or evaluate relevant primary evidence. Council decides when the peer yields; do not manually choose a scientific winner.
3. **Observe native PEER -> COMBINE -> POPULATION**: verify direct provenance of each peer's scientific claims, disagreements and actual tool outputs. Have AI choose follow-up tasks autonomously; no compulsory FUSE.
4. **Demonstrate a causal scientific delta**: prior claim/null/prediction -> independent critique or evidence/calculation -> changed claim, narrowed scope, discriminating prediction or carefully scoped negative. Asset counts and generation numbers are not adequate substitutes.
5. **Assess Level II only when warranted** by the actual science: physical constraints, inspected prior art, strong nulls, predicted test observables, expected feasibility and independent skeptical review. No imposed mechanism or forced positive result.

Do not open an unbounded run before saved-call states, evidence-class truth and operational stops are understood. Safety or cost guardrails remain **operational**, not a research success criterion.

## Collaboration and repository truth protocol

- For each substantive planning/code turn, read `PROJECT_VISION.md`, this current state and `RESEARCH_EVOLUTION_LOG.md`, confirm the Git branch/HEAD and inspect the actual relevant source. The remote GitHub code is not equivalent to unpushed WSL work or unpublished research Journals.
- Update this document when the research phase or verified engineering state materially changes; append actual findings, failed experiments, falsifications and remaining uncertainties to the evidence log. Do not edit the immutable vision merely to justify a temporary workaround.
- Review diff and tests, commit/push meaningful code+documentation or doc-only milestones. Never commit a raw Journal, provider response, secret, billing record or local research-root archive. Use `$HOME` in operator instructions; files delivered by ChatGPT are placed directly under `$HOME` by the operator.
- If a pinned runtime Python source changes, preserve old M16/M17 experiments and bootstrap a new source-pinned root unless an explicit, independently checked migration is authorized. Do not silently re-execute an old root under changed source.
- GitHub can be reviewed during future active chat turns, but this document is **not** a promise of unattended repository monitoring between turns.

---

## Archived original 2026-10-31 snapshot (preserved unmodified)

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
The fail-closed Worker response boundary passed 9/9 controlled WSL tests after correcting a test-only audit-status expectation. Incomplete trailing JSON is classified INVALID_FORMAT and rejected; distinct complete JSON objects are classified DISTINCT_MULTIPLE_JSON_REJECTED.

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

## Native continuity integration (MOCK_VERIFIED, 2026-10-31)

The tracked core, engine, provider, Population Council and generation carry
now implement explicit typed Problem ancestry vs Asset motivation; read-only
rejected-proposal indexing; POPULATION-only inherited archive visibility;
explicit INFORMED Work handoff pinned in journal; generation carry of unregistered
proposals separate from scientific assets or evidence. The WSL no-paid regression suite passed 49/49 tests (Continuity 19, V3 9, V4 13, Clean 8). Historical V3/V4 source guards remain enforced in production; synthetic fork tests isolate their journal semantics. Population-level live scientific continuity remains UNVERIFIED. Existing
G14/M15 live roots are frozen and are NOT authorized to resume under the
new source contract. External archives require explicit hash-pinned opt-in on
a NEW experiment root. No Level II scientific claim is certified by this.
