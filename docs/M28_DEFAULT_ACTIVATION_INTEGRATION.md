# ScientificEvolution — M28/M25 activation continuity: unified default execution contract

**2026-11-09 | Status: OPEN DESIGN/EXECUTION REQUIREMENT, NOT IMPLEMENTED**

## Why this exists

M23.3 had verified context/cache configuration modes, but later M23.6.2–M24 execution silently reverted to FULL settings. M25 implemented an opt-in Activation Profile, drift/fingerprint checks and budget requirements in the native Persistent Population path. The M28 meta-autonomy runner (`runtime/meta_research_autonomy.py` → `e2core.meta_scheduler.run_dynamic` → `generational_run.drive(..., phase='syn')` → V3/V4 hooks) shares scientific engine functionality but **does not enforce the same activation contract by default**. Feature *existence* is not proof of feature *activation* in a paid run.

A4-1 no-paid state reported at `4d5fa51`: original P0 hash verified (`8fc9da6e2c3889ce7c379f6571912e33b8771d1fd1192a7c7dea8a037ac7e136`), 65 Python source-pinned files, 0 saved calls, no `M232_DEV_BUDGET.json`, and unset M232/M233 feature modes; paid gate not enabled. `meta_autonomy: None` in an ad hoc probe was a **wrong metadata-file lookup**, not evidence M28 activation is off: the setting is `meta_autonomy_enabled: true` in `persistent.json` and the M28 preflight succeeded.

## Non-negotiable target

1. **Canonical configuration is the default across *all new supported research entrypoints*.** M28 and native Persistent Population must validate one authoritative activation/operational-budget profile, including newly spawned child roots and recovery. No silent fallback to earlier modes because a different CLI was used. “Default integration” means consistent validation and inheritance, **not** forcing an optimization mode or restricting scientific choices.
2. **Runtime effective activation is verified, not inferred from source.** Validate at init, preflight, paid boundary and restart; record the effective model, feature modes, hashes and budget mode so offline review can distinguish declared from actually used configuration. A code SHA pin alone does not capture environment activation.
3. **Fail closed for new paid research** on missing/mismatched profile, unknown model/rates, drift, or absent required cost guard. Keep `--paid` and `FAKG_RESEARCH_ALLOW_PAID=YES` separate approvals. Call-count limit is not a USD cap; estimated reservations are not guaranteed provider-billing caps. Confirm the provider's external spending cap separately.
4. **No historical rewriting.** Do not repin or migrate the already-created A4-1 root, M26/M27 Journals, P0, source blobs, saved responses or scientific status silently. A future source-changing implementation should be evaluated in a **new** source-pinned experiment. An explicitly controlled interim A4-1 manual profile is not evidence of integrated default behavior.
5. **Prove the contract via actual entrypoints.** No-paid regression across M28/Persistent Population `init → preflight → paid-boundary → restart → child creation`, including tests for environmental drift, missing budget, model change and child mismatch. Preserve source provenance, FRESH isolation, real tool execution truth, and science-vs-operational-stop semantics.

## Acceptance criteria before declaring default integration complete

- Same canonical profile and enforcement in both new-research entrypoints; no silent fallback.
- Actual activated modes and budget checks observable in source-pinned runtime/provenance.
- A regression recreating the M23.6.2–M24 deactivation mechanism now **fails closed**.
- Previous historical experiments unaffected; no mandatory new scientific organization, hypothesis or Work steps.
- No paid experiment is claimed completed by the implementation tests.

## Priority and scope boundary

**Do not lose this requirement as M28 evolves.** It is an outstanding integration/development-continuity requirement, not proof that the current A4-1 science is blocked or that architecture is complete. Before any paid segment, independently inspect/approve the effective feature modes, provider price, budget policy and stop conditions. Do not expand this task into a fresh manager/architecture project without an observed missing scientific execution capability. A4-1's goal remains *real scientific choices → actual evidence/computation → criticism/correction → defensible claim/negative/HOLD*.

References: `PROJECT_VISION.md`, `DEVELOPMENT_STATE.md`, `docs/M28_A41_SCIENTIFIC_AUTONOMY_EVALUATION_20261109_KO.md`, `runtime/e2core/activation_contract.py`, `runtime/meta_research_autonomy.py`, `AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/persistent_population.py`.
