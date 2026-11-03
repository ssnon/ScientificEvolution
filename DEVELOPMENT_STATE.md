<!-- CURRENT_STATE_2026_11_03_M233 -->
# ScientificEvolution — Current Development State

**Verified documentation checkpoint:** 2026-11-03 (KST). The remote `ssnon/ScientificEvolution` branch `dev/m23-2-efficient-development` is accessible at source commit `168d0714cf1a2f94a3e6b98cbb1913677c3b4e2f` (M23.3) **before this documentation-only commit**. Local working repository: `~/ScientificEvolution_M23_2` in the operator's WSL `graphAgent311` environment. Implementation claims below are supported by user-shared test/paid-call logs and source-pinned read-only audits; private Journal bytes are not published.

**Mission and scientific boundaries.** Build a **general-purpose autonomous AI Scientist**, not a specialized FAKG/KG/SERS workflow. Human P0, independent FRESH and informed researchers, adversarial null comparisons, real tools/evidence, population synthesis, and verifiable cross-generation science remain the objective. SERS intermittency is a testbed. A Level II proposal means a review-worthy, falsifiable and physically bounded *pre-experimental* mechanism, **not** a verified discovery. See [PROJECT_VISION.md](PROJECT_VISION.md) and the dated records in [RESEARCH_EVOLUTION_LOG.md](RESEARCH_EVOLUTION_LOG.md).

## Current verified engineering state — M23.2/M23.3

| Sequence | Source commit | Change | Evidence |
| --- | --- | --- | --- |
| M23.2 context delivery | Earlier M23.2 development | `ON_DEMAND` index, `REQUEST_DETAILS` and `REQUEST_FULL_CONTEXT` to recover original science. | Observed OPP/CTRL prompt sizes changed from ~424–429K to ~312–316K tokens, still above the 272K price boundary. |
| M23.2 namespace | `fb911f0` | `COMPACT` opt-in removing redundant asset namespace/alias representation; preserves exact original ID and scientific source relations. | 146,015 JSON bytes shadow saving; 11 new tests passed, earlier full regression 150 passed/1 skipped. Live STANDARD OPP 312,050 / CTRL 316,048 versus COMPACT OPP 248,109 / CTRL 252,288 tokens. |
| M23.2 selective cache | `db1b696` | Opt-in `SELECTIVE_NO_WRITE` for PMI, OPP, CTRL; keep NVT AUTO, durable wire hash and fail-closed reuse. | 6 policy tests and full regression passed. Live PMI/OPP/CTRL cache writes all zero in SELECTIVE. |
| M23.3 metadata and references | `168d071` | `SEPARATE` opt-in moves original metadata hashes out of visible indexed model rows while preserving full Journal/DetailSession; adds `BAD_WORK` reference diagnostics without auto-correction. | 12 M23.3 tests passed. Full reported suite: 168 pass, 1 skipped. Shadow exact restore; live A/B with genuine provider usage. |

**Candidate for subsequent NEW experiments** (not a changed default and never to be applied retroactively to an old root):

```bash
M232_CONTROLLER_DETAIL_MODE=ON_DEMAND
M232_NAMESPACE_MODE=COMPACT
M232_CACHE_POLICY=SELECTIVE_NO_WRITE
M233_MODEL_METADATA_MODE=SEPARATE
```

`M232_SYN_PMI_MODE=FULL` was also held fixed in the controller-slice A/B. Exact runtime behavior must be read from the pinned source/version; an environment-variable label is not a substitute for verifying the actual saved request wire.

## Actual price and prompt observations

All dollar figures are the **reported provider charges for the specified saved requests**, not projected monthly costs or a causal meta-analysis. Different A/B arms produced different model outputs (including NVT response and cache state); do **not** add percentages or claim science equivalence from a single comparison.

| A/B | Stage(s) | Baseline cost | Opt-in cost | Observed reduction |
| --- | --- | ---: | ---: | ---: |
| STANDARD vs COMPACT namespace | OPP + CTRL | $0.32061840 | $0.12962655 | ~59.6% |
| AUTO vs SELECTIVE cache | PMI + OPP + CTRL | $0.17772920 | $0.14362940 | ~19.2% |
| FULL vs SEPARATE metadata | OPP + CTRL | $0.10507260 | $0.08639800 | ~17.8% |

The namespace test crossed the observed 272K prompt pricing boundary for both OPP and CTRL, so the cost change is larger than the prompt-token change alone. The cache A/B confirmed `cache_write_tokens=0` for PMI/OPP/CTRL while retaining NVT AUTO, but NVT cache hits differed across independent runs. The M23.3 A/B observed OPP **248,575 → 204,084** and CTRL **252,710 → 207,614** prompt tokens; the FULL and SEPARATE total 4-stage bills were **$0.2129135** and **$0.1352338**, but that 36.5% total bill reduction is **not attributable solely to metadata** because FULL NVT wrote 253,510 cache tokens while SEPARATE NVT read 253,510 cached tokens.

Before the paid metadata A/B, read-only Shadow projection saved **103,192 bytes from each** OPP and CTRL payload with `full_roundtrip_exact=true`, preserving the original hashes and detail recovery. The live `SEPARATE` requests marked **537 indexed assets and 238 indexed problems**; the earlier shadow sample had **538 indexed assets and 238 indexed problems**. The byte result is not a token-price estimate; the live provider token counts are the appropriate measured quantity.

## Execution truth and scientific comparison of M23.3 A/B

- **Source equality:** Separate fresh experiment roots `M233_META_FULL_20261103_01` and `M233_META_SEPARATE_20261103_01`, each with 546 inherited assets, 239 problems, base Journal 1,457 events, same scientific fingerprint `076b59287d7fe3c6579a9adc43dea90ae9e6997a1333c1ca68b37e30d4c854aa` and base head `81f533d5e8f8d8b743bd37e72de1f40b905c2989e33c6d17b303338a3e1cdd75`. No independent direct tool transfer was reported at bootstrap; inherited `EXTERNAL_AUDIT` records remain distinct from operator-verified new PRIMARY evidence.
- **FULL:** four calls `SAVED`, **zero committed Controller decisions or Work**. The controller chose `ONGOING`, P0, an INFORMED `DEVELOP` finite-exposure CTMC-HMM adversarial benchmark. It was **rejected** with `CONTROLLER_PLAN_REJECTED:UNKNOWN_WORK_SOURCES`: `SRC_INHERITED_TOOL_0283f27646701431bec6599` is not registered even though `A_CARRY_0283f27646701431bec6599` is a registered Asset. Identical ID suffix suggests an Asset/Source namespace mix-up, but does not prove the intended correct Source; no automatic remapping or phantom Source creation is authorized.
- **SEPARATE:** four calls `SAVED`, **one Controller decision and one INFORMED `DEVELOP` Work committed** (`W_INFORMED_CTMC_HMM_IDENTIFIABILITY_001`, P0). Status `ONGOING`, objective `UNRESOLVED`, research `CONTINUING`. Work input listed five historical assets and an empty direct `source_ids` list. **The Worker had not executed the planned benchmark** in this A/B; a committed Work is not a validated computation.
- **Scientific overlap:** both model-authored plans independently selected the same *type* of research: exact finite-exposure CTMC-HMM/Poisson observation-law checks, matched strong nulls (occupancy, selective field, orientation, photochemistry, thermal, contact, detector), held-out discrimination, physically bounded nuisance parameters and explicit scoped negative conditions. Both reject a causal or novelty claim from model-class separation alone. Different NVT responses and different assets mean this **does not certify causal scientific equivalence or long-run quality**.
- **FRESH watchpoint:** an unselected SEPARATE Opportunity suggestion was labeled FRESH yet listed parent Asset IDs. This was **not committed as a FRESH Work**, but future Population evaluation must verify actual FRESH isolation rather than trust an advisory label.

## Validation failures preserved, never converted into science

- M23.2 AUTO Controller produced `BAD_WORK` with an unregistered `P_CARRY_c0c1e0fd8131939f7a6da5d` Problem, whereas the similarly suffixed `A_CARRY_c0c1e0fd8131939f7a6da5d` Asset exists. M23.3 diagnostics confirmed `UNREGISTERED_WORK_PROBLEM_ID`, kept the original SAVED response and refused to substitute `P0`.
- M23.3 FULL Source-ID mismatch above remains a different, uncommitted validation failure. M23.3's Problem reference diagnostics **do not claim to have solved arbitrary Asset/Source confusion**.
- These are operational/semantic validation failures, **not scoped negative findings about SERS**, and must not be silently retried, corrected, or logged as autonomous scientific conclusions.

## Development limits, next milestone, and safeguards

**Observed success:** prompt/cost reduction, no-paid regression and exact projection roundtrip, live wire contract, and one valid Controller commitment on the M23.3 SEPARATE branch. **Not yet observed:** real execution of that Work; independently verified new primary-source inspection under this version; verified CTMC-HMM/null benchmark; independently evaluated Level II; population-wide multi-generation cost per validated scientific advance.

**Next milestone:** stop further prompt shaving as the default priority. Start a **new source-pinned autonomous Population** with the candidate opt-in config and an explicit operational provider budget; preserve the earlier A/B roots and their SAVED/rejected responses unchanged. Verify actual Worker computation, source provenance, FRESH isolation, integration by population SYN, autonomous follow-up science, and cross-generation inheritance; report cost by stage and per validated scientific delta. An operational spend pause is **not** a scientific HOLD. Never reissue an uncertain provider call automatically.

**Do not Git-commit** local research roots, raw model requests/responses, payment receipts, secrets, private papers, or Journals. Preserve exact evidence-class distinctions, Source IDs and root identity; no source fabrication, no retroactive primary certification, no operator-selected scientific winner.

---

## Archived 2026-11-02 development-state checkpoint (M23.1; preserved below)

<!-- CURRENT_STATE_2026_11_02_M231 -->
# ScientificEvolution — Current Development State

**Snapshot:** 2026-11-02 (KST); operator-reported local WSL branch `dev/m23-1-population-source-scope`, commit `6b663adfd81494a1b9b0105fea9fa6095a2709e8` (M23.1 Native source). This state is based on user-shared, read-only Journal audits, execution logs, and regression output. The original private Journals have **not** been published to GitHub. The latest accessible remote `dev/m22-peer-rejected-continuity` documentation still described M20 when this summary was prepared. Local commit existence does **not** imply it has been pushed.

**Mission:** The product is a **general-purpose autonomous AI Scientist**, not FAKG, knowledge graphs, or a SERS-specific workflow. A human provides original P0; independent researchers generate, critique, measure, calculate, and revise; a population decides how to synthesize, continue, branch, defer, or terminate. SERS is a proving ground. See [PROJECT_VISION.md](PROJECT_VISION.md). A Level II result is a *review-worthy, physically defensible, falsifiable pre-experimental hypothesis*, not an experimentally established mechanism.

## Current verified operational checkpoint — M23.1

- **Local source:** `~/ScientificEvolution_M23_1`, branch `dev/m23-1-population-source-scope`, source commit `6b663adfd81494a1b9b0105fea9fa6095a2709e8`. The operator reported a clean Git worktree after this commit.
- **New source-pinned experiment:** `~/ScientificEvolution_runs/M23_1_FROM_M23_RECOVERY_POPULATION_20261102_01`; new `BASE_000` bootstrapped from the previous M23 Recovery `CYCLE_000/POPULATION` root. The bootstrap carried **519 provisional/historical assets**. `P0_unchanged: true`; `cycles_created: 0`; no new paid calls; both persistent and autonomous preflight succeeded.
- **M23.1 change:** `runtime/e2core/engine.py` now exposes the exact *current-root* registered source namespace to the Controller and diagnoses unknown IDs from previously rejected, SAVED Controller plans. `autonomous_population.py` explicitly distinguishes *current-root executable Work* from peer-root historical ACTIVE/QUEUED Work in Council context. The hard `UNKNOWN_WORK_SOURCES` validator, Source provenance, FRESH isolation, and prior Journals are not relaxed or rewritten.
- **No-paid verification:** `M231_NO_PAID_TESTS_PASS`; read-only regression recognized all four historical rejected Controller attempts and the actual invalid Source IDs, with no fabricated Work or Source record. The regression test and preflight establish **contract correctness in tested paths**, **not** an observed new Population Controller/Worker or a science result under M23.1.
- **Source carry nuance:** bootstrap reported `inherited_direct_tool_sources: 0`, which counts direct, source-root TOOL_RESULT transfers, not all previously registered historical EXTERNAL_AUDIT records. `BASE_000/carry_receipt.json` distinguishes `previously_registered_external_sources_carried`, `inherited_direct_tool_sources`, and historical peer tool carry. Verify those separately; do not claim all source content was lost from the zero count alone.

## Immediate predecessor — M23 Recovery, verified by operator logs

- The earlier M23 Population had 508 assets, 73 SAVED and one UNCERTAIN (`CTRL_D00015`, `HTTPError`) model calls. `MODEL_CALL_INTENT` event 1642 and `MODEL_CALL_UNCERTAIN` event 1643 were *not* rewritten or retried. Full original events 1–1645 and their source-root identity remain preserved.
- A new read-only-verified checkpoint root contains the fully committed events 1–1641, all 508 original assets, and `UNCERTAIN_PROVIDER_RECOVERY_RECEIPT.json`; this was a clean **branch before the uncertain call**, not proof that it was delivered, billed, or scientifically resolved.
- An autonomous new experiment bootstrapped from that checkpoint. Both independent SYNs chose `YIELD_TO_POPULATION`; one challenged charge-state identifiability against finite-exposure multichannel and flexible-nuisance nulls, with a proposed redox-versus-field factorial intervention. These are model-authored, conditional scientific analyses, *not* independent experimental validation or Level II.
- `POPULATION_COMBINED_NO_PAID` imported 11 genuinely new peer assets, yielding **519 provisional assets**. The ensuing population Controller authored four `ONGOING` plans, all rejected with `UNKNOWN_WORK_SOURCES`; current-root Work count and committed Controller decision count were both zero. The 519 assets were pooled successfully, but **synthesis-to-execution was not completed**. After four rejected attempts the run ended operationally with `SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED`, not a scientific HOLD.
- Read-only Source audit found exact nonregistered names `SRC_INHERITED_TOOL_7ffa92aad6062a5d970805a`, `SRC_INHERITED_TOOL_7ffa92aad6062a5d970805a8`, and `SRC_INHERITED_TOOL_c5ddf5d6f1cbba5bfaa9aac`. Other sources were truly registered. M23.1 exposes only actual allowed current-root IDs and retains exact rejected model proposals; it does not fabricate aliases or citations.

## Historical evolution beyond M20

- **M21:** General OA PDF route and actual independent PEER work. Both yielded, but several model-authored asset submissions were rejected due to parent/authorization mistakes. A format/retrieval/registration failure is not a scientific negative.
- **M22:** Verified, provenance-preserving handoff of rejected peer proposals as unregistered opportunities, without falsely publishing them as claims or importing them into blind FRESH. Later M22 live Population research and source-citation problems demonstrated that transfer infrastructure alone does not guarantee scientific progress.
- **M23:** Root-scoped, proof-checked reference/source continuity. The active Population progressed to a real citation-chain primary-source audit and follow-on review Work before the unresolved HTTP uncertainty halted that original run; scientific novelty or P0 resolution was not certified.
- **M23 Recovery:** Independent finite-exposure/null critique, peer YIELD and population merge succeeded; the Controller could not commit a new Work because of unknown Source IDs.
- **M23.1:** Native context/diagnostic contract corrected in a separate worktree, local regression and fresh bootstrap passed; **live paid research under this version is still unobserved**.

## Next single scientific-engineering milestone

Run M23.1 on its *new* pinned experiment for a long, operator-supervised autonomous campaign. A `--slice-budget 8` checkpoint is a resource boundary, not a scientific termination condition. Stop on a user stop-file, unresolved provider outcome, source-pin failure, schema-exhaustion, or independently adjudicated scientific terminal judgment; monitor actual billed usage separately.

**Operational success:** after independent PEER research and pooling, the *new M23.1 Population Controller* commits a valid new Work with registered source IDs and the Worker genuinely executes it. **Continuity success:** the Worker uses inherited evidence, critiques, rejected opportunities, or calculation lineage to change a scientific action, not merely repeat text. **Scientific success:** a defensible new null bound, independent recheck, distinctive prediction/falsification route, or appropriately scoped negative emerges. None of these alone proves Level II, and an increasing asset/generation count is not a substitute.

**Source/record invariants:** no overwriting previous pinned Python/Journals, no retroactive source promotion, no re-billing uncertain model calls, no interpretation of metadata or failed tool requests as primary science, no forced candidate or imposed hypothesis. Keep local research data, paid responses, secrets, full Journals, and root archives **out of Git**. Commit documentation separately from the pinned runtime Python bytes; source-pin verification hashes Python, not Markdown.

---

## Archived earlier development snapshots — preserved below without modification

<!-- CURRENT_STATE_2026_11_01_M20 -->
# ScientificEvolution — Current Development State

**Current snapshot:** 2026-11-01 (KST). **Development branch:** `dev/research-continuity-v1`. **Native runtime baseline:** `c4331ec` (M20 evidence-aware planning). This is a status record, not experimental evidence or a scientific certificate.

**Read first:** [PROJECT_VISION.md](PROJECT_VISION.md) (scientific mission and invariants), [RESEARCH_EVOLUTION_LOG.md](RESEARCH_EVOLUTION_LOG.md) (dated real-run observations and scientific deltas). The previous 2026-10-31 development snapshot is preserved verbatim below.

<!-- M20_OA_RETRIEVAL_GATE_20261101 -->
## M20 Population continuation — OA retrieval gate (2026-11-01)

- **Actual execution:** `CYCLE_000/POPULATION`, M20 source-pinned Python at `c4331ec`; after-head 1276 events `2ee8b1e39b139982ac6a6785fdb318b95987e1b229f29ba7095056b6c033cf0c`. Population 466 -> 468 provisional assets; 8 research + 1 Council model calls; original PEER Journals unchanged; no Level II or global terminal.
- **Scientific outputs:** FRESH audit `W_M22_FRESH_PRIMARY_JOINT_SERS_AUDIT_001` ended DONE, added `A_P0_electrostatic_mechanical_feedback` (unverified hypothesis; mechanistically overlaps preexisting charge/field/geometry proposals) and `A_P0_prior_art_access_failure` (retrieval limitation, NOT a negative scientific result). No newly inspected primary full text; a model-output format repair and a rejected asset were recorded.
- **Root-cause checked in Native source:** `runtime/e2core/research_literature.py` `read_fulltext` resolves DOI strictly to a Europe PMC PMCID, then requests the Europe PMC fullTextXML. The DOI 10.1021/acs.nanolett.5b04135 was correctly resolved to OpenAlex metadata with an OA manuscript location, but a subsequent DOI-based Europe PMC lookup had no PMCID, returning `NO_OPEN_FULLTEXT_PMCID_DISCOVERED`. This is not evidence that the publication or its full text is unavailable elsewhere.
- **External human/assistant verification, SEPARATE from AI Journal evidence:** The authors' group hosts actual original PDF https://nano-optics.colorado.edu/wp-content/uploads/2020/06/Park_NanoLett_15_MainText.pdf and SI PDF https://nano-optics.colorado.edu/wp-content/uploads/2020/06/Park_NanoLett_15_SI.pdf . These were independently opened and visually inspected OUTSIDE the M20 Worker. This must NOT be reported as a new AI tool execution, `PRIMARY` Journal source, current-root paper reading, or Level II validation. The paper shows 1-s single-molecule TERS time-series Raman mode covariance/anti-correlation and relatively stable reference modes; it does not, from this inspection, independently establish the strict joint occupancy/charge measurement or causal field discrimination requested by P0.
- **Operational continuity caveat:** Council `CONTINUE_RESEARCH` cites still-active Work in SYN_01, but those are historical PEER Work IDs and NOT runnable in the current Population root; the only current-root Work ended DONE. The next Controller must create an explicitly authorized new current-root Work if continuation remains valuable. Original peer local asset IDs in free-text rationale must be resolved to canonical `A_PEER_*` IDs for actual lineage.
- **Next source version, not in-place M20 patch:** Design a DOMAIN-NEUTRAL, provenance-checked OA manuscript/PDF acquisition route with safe URL/DNS/redirect policy; citation-matched PDF identity check, bounded extraction, page/figure limitations, `OA_PDF_TEXT` evidence tier, and fake-network regression tests. Never silently turn URL metadata into verified paper content. Source-pinned M20 must remain untouched; build/test on a distinct worktree, then bootstrap a fresh native-pinned descendant of M20. Preserve strict FRESH isolation and existing Journal histories.

## M20 actual Population research checkpoint (2026-11-01)

- **Execution:** M20 source-pinned Python baseline `c4331ec` (documentation at `cbb5301`); experiment `$HOME/ScientificEvolution_runs/M20_FROM_M19_POPULATION_20261101_01`, `CYCLE_000/POPULATION`; Journal head 1234 events, `5581f96d8e4cd2b70897420c3268f9bf5e8dfec56b7d110f183abbc2daf7a08e`. Native PEER → POPULATION merge already completed with 466 provisional assets (458 carry + SYN_01 seven + SYN_02 one), no scientific certification.
- **First actual pooled research:** 8 saved research-model calls, 1 saved Population Council call; Controller `D00001` chose genuinely FRESH modular primary-literature audit `W_M22_FRESH_PRIMARY_JOINT_SERS_AUDIT_001` rather than repeat an inherited qualitative charge mechanism. One current-root Work ACTIVE, last step TOOL_RESULT; no new assets, three open subordinate literature questions P0a/P0b/P0c.
- **Actual evidence:** 4 OpenAlex `literature_research` searches DELIVERED as BIBLIOGRAPHIC_METADATA; one overconstrained query returned 0 hits, the other queries returned 6 records each, many reviews/partial matches. **No full text, figure, supplement or same-experiment joint measurement was verified by this current Worker.** Retrieval outcome is not proof of novelty or scientific nonexistence.
- **Autonomous selection:** Council recognized both independent PEER portfolios (complexity-controlled observation/null tests and electrochemical/parity interventions) and chose CONTINUE_RESEARCH because the primary-source audit remained unfinished. PEER Journals unchanged; no unsaved calls, Level II or global terminal.
- **Critical boundary:** legacy PEER `ACTIVE` Works remain HISTORICAL, not executable current Population Work. The only executable current-root Work is the FRESH literature audit. Further slices should be audited for actual original full-text/figure inspection or a scientifically justified pivot, not merely more metadata searches. Distinguish canonical `A_PEER_*` Population asset IDs from original peer-local IDs in free-text Council rationale.
- **Next:** read the latest pending tool result in the existing Work, let the AI choose whether to inspect actual source bodies, challenge inherited hypotheses with new constraints, or change strategy; observe real scientific delta. A fixed slice is an operational checkpoint, not an autonomous science stop.

## Scientific north star

The objective is a **general-purpose autonomous pre-experimental AI Scientist**, not a SERS-only pipeline, knowledge-graph product, or fixed agent workflow. Given unresolved P0, independent AI researchers propose, critique, revise, calculate, acquire actual literature evidence and evaluate competing mechanisms; Population steering selects whether and how to propagate results into new independent scientific decisions, further studies and generations. Valid dispositions include a review-worthy Level II pre-experimental candidate and a rigorously scoped, independently challenged lack-of-progress decision. Neither fixed generation count nor number of model calls/assets is a scientific success criterion.

**Level II** means a physically defensible, meaningfully novel and falsifiable proposal with concrete predictions distinguishable from strong null mechanisms, credible prior-art comparison, experimental observables/controls and explicit uncertainty. It is not an experimentally verified discovery. Models and tools may assess these conditions, but such assessments are not external certification. A tool failure is not a scientific negative; a local HOLD is not an impossibility theorem for P0.

## M18 native Worker reliability work (2026-11-01)

**Trigger:** First M17 Population research segment (8 paid research calls, +1 Council) delivered 3 Controller decisions but 2 of 2 Worker calls were rejected with `DISTINCT_MULTIPLE_JSON_REJECTED`; both raw responses contained two standalone literature-search tool requests and a third scientific envelope. No Population tool calls, new live assets, or verified science. Council CONTINUE_RESEARCH. Current Population has one ACTIVE, unstarted Work. The independent peer-report bridge was present in all 3 Controller inputs.

**Native implementation to test:** `engine.py` now requests one model-authored format correction *within the same ACTIVE Work* after an invalid Worker response. It saves the raw original, does not auto-select any prior tool/asset, never infers scientific findings from parse failures, and still rejects a second invalid output. A one-step operational correction allowance is not a quota on scientific research. `worker_json.py` strict refusal to choose between distinct authored documents is unchanged.

**Verification status:** IMPLEMENTED when this patch is applied; LIVE_VERIFIED only after a new version-pinned ROOT is executed and inspected. Run no-paid `test_m18_worker_format_recovery.py` and prior Worker/continuity suites before committing. Existing M17 ROOT is not compatible with modified runtime Python bytes and must remain frozen; Git history preserves code revisions but does not retroactively change an immutable execution's source pin.

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
| M17 clean: `$HOME/ScientificEvolution_runs/M17_G14_NATIVE_CLEAN_20261101_01` | Both peers yielded. SYN_01: four Controller decisions, five Worker calls, three multi-JSON format failures, two metadata searches, zero new assets. SYN_02: one Controller, three Worker calls, two tool results, one unverified hypothesis. No-paid COMBINE completed: stage POPULATION, 444 base assets + 1 peer asset, five peer decisions retained, zero Population model calls, zero executable Population works. Original peer Journals unchanged. | **LIVE_EXECUTION_OBSERVED** for combination and provenance, not yet a downstream scientific delta or Level II result. |

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


## M18 live evidence and M19 continuity source change (2026-11-01)

M18 (`41b3d47`) was tested on a new, native-pinned ROOT inherited from the
actual M17 Population. Both independent SYN researchers recovered from distinct
multiple-JSON Worker outputs. SYN_01 executed a Python charge/Stark feasibility
calculation but yielded with its last Work still ACTIVE and its last step a
TOOL_RESULT. SYN_02 obtained an OA full-text result and also yielded with a
last, uninterpreted TOOL_RESULT. Two peer assets and source-level literature
records were imported into M18 Population; it has 447 provisional assets, not
447 externally certified claims. M18 Population remains frozen as historical
research after its no-paid combine.

M19 native engineering patch (pending local regression/live confirmation):
- INFORMED-only paginated source_catalog and source_lookup for precisely
  archived real-tool results; FRESH access to historical sources stays blocked.
- Every genuine Python/verified-calculation tool request and result is carried
  under exact original hashes, including REJECTED attempts distinguished from
  EXECUTED calculations. M19 bootstrap can recover M18 peer computations from
  original peer Journals only after verifying the saved peer head hash.
- Last-step TOOL_RESULT pending Worker interpretation is exposed to Council and
  Native Controller as *work still unresolved*, not as a scientific conclusion.
- A Native INFORMED source_lookup of an inherited archive creates a new local
  TOOL_RESULT citation record for the exact returned excerpt, explicitly NOT a
  second literature/experiment execution.
- No arbitrary mechanism selection, mandatory continuation, invented evidence,
  or mutation of M17/M18 Journals. Test and commit before creating a new
  M19 source-pinned experimental ROOT.


## M20 evidence-aware research planning — development patch (2026-11-01)

M19 `b8eafe0` engineering was committed and live tested. M19 Population
CYCLE_000 pooled 447 inherited + 8 peer assets and exposed 58 preserved
source records, including 1 unreviewed actual Python/Stark calculation.
A subsequent 16-call Population slice (2 committed Controller decisions, 2
metadata-only searches, 3 new provisional assets) chose FRESH again. Actual
Controller inputs included only evidence-class counts and pending count, not
specific archive PMCID/title/source IDs. It judged no current-root retrieval
had yet occurred while previous real full-text retrievals existed. Council
chose CONTINUE_RESEARCH. The active FRESH Work ended on FORMAT_REPAIR_REQUIRED;
no Level II result or failed scientific negative was certified.

M20 adds a bounded deterministic, non-ranking planning index. Duplicate
PMCID/DOI source records are grouped without deleting individual Journal
sources; pending tool results remain separately visible. Controller and pooled
Population Council see real archive titles and source IDs, and INFORMED
Workers see the index. FRESH Workers remain isolated. No hypothesis/mode is
forced. M19 root stays byte-pinned and MUST NOT be resumed with M20 source.
Only initialize M20 in a NEW native-pinned experiment after no-paid regression.


## M20 live two-peer research checkpoint (2026-11-01)

- **Actual pinned native source:** `c4331ecc558c1fe6237005f1ad8095db80237e5d`; experiment `$HOME/ScientificEvolution_runs/M20_FROM_M19_POPULATION_20261101_01`, `CYCLE_000`, stage **PEERS**. This is a checkpoint, not a Level II certification.
- **Carry baseline:** 458 provisional inherited assets, 58 readable inherited tool-source records in 18 planning groups (all visible), one historical Python/Stark result pending prior interpretation. This evidence index is available to Controller/INFORMED, not FRESH Worker.
- **Two newly executed peer segments:** SYN_01 +8 saved research calls; SYN_02 +8; total research-root calls now 24, Council/meta-root calls now 3. No unsaved calls reported. No Population combine or pooled synthesis yet.
- **SYN_01:** Active INFORMED `W_M20_CHALLENGE_MATCHED_SERS_NULLS_001`; published 3 new provisional assets: `A_M20_COMPLEXITY_CONTROLLED_IDENTIFIABILITY_001` (COUNTEREXAMPLE), `A_M20_COMPLEXITY_SWEEP_TEST_001` (PREDICTION), `A_M22_STARK_FEASIBILITY_BOUNDARY_001` (SUBPROBLEM). The first two restrict interpretation of finite-exposure matched diffusion/semi-Markov simulations; the third raises a conditional, unquantified Stark detectability boundary. Two new python_science tools EXECUTED, one verified_calculation REJECTED (input error); last executed result is awaiting Worker interpretation. Several other proposed assets were rejected by BAD_ASSET_PARENTS or UNAUTHORIZED_ASSET_PARENT; raw model and tool records remain preserved.
- **SYN_02:** Controller independently chose INFORMED VERIFY of previously retrieved SERS evidence. Published provisional `A_ELECTROCHEMICAL_SELF_GATE_001`, proposing charge–double-layer–barrier feedback and conditional hysteresis/ionic-strength predictions, **without a new source lookup or new tool result in the segment**. Council found substantial overlap with inherited feedback hypotheses and chose YIELD_TO_POPULATION, preserving its verification Work as historically ACTIVE/incomplete. Citation of archived source IDs is not proof the original text was newly inspected.
- **Council:** SYN_01 CONTINUE_RESEARCH; SYN_02 YIELD_TO_POPULATION. No global scientific terminal state, no independently verified Level II candidate. Next: allow scientific scheduling to continue SYN_01 until its Council autonomously yields or changes disposition, then observe native COMBINE → POPULATION and the effect on new research decisions.
