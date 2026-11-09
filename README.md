# ScientificEvolution — autonomous AI Scientist development

<!-- M28_A41_SCIENTIFIC_AUTONOMY_EVALUATION_20261109_README -->
**Latest research-development checkpoint (2026-11-09):** M28-A1/A2/A3 organizational autonomy
is implemented, and the user reported a successful **no-paid, scripted** A4-0
end-to-end run at local source `582220c`: two research ROOTs, five PRIMARY
Controller decisions, one selected cross-root import, zero paid calls.
**No actual model-driven A4-1 research or independent scientific improvement is
established.** The older M23.x section below is historical. Scientific goals:
[PROJECT_VISION.md](PROJECT_VISION.md); current experiment protocol:
[docs/M28_A41_SCIENTIFIC_AUTONOMY_EVALUATION_20261109_KO.md](docs/M28_A41_SCIENTIFIC_AUTONOMY_EVALUATION_20261109_KO.md).
<!-- /M28_A41_SCIENTIFIC_AUTONOMY_EVALUATION_20261109_README -->

**Current documentation checkpoint: 2026-11-03 (KST).** Active source branch: `dev/m23-2-efficient-development`; verified implementation head before this documentation update: `168d071` (M23.3 metadata projection and reference diagnostics). This README covers the **current development branch**, not a completed scientific result. Earlier V4 snapshot information remains below as historical context.

The mission is a **general-purpose autonomous AI Scientist**. A human supplies an unresolved scientific problem (P0); independent FRESH and informed researchers propose, challenge, calculate, obtain evidence, and generate follow-up work; population-level synthesis determines continuation, branching, or scientifically justified termination. SERS intermittency is the present test case, not the engine's fixed scientific objective. See [PROJECT_VISION.md](PROJECT_VISION.md).

## Current documents

- [DEVELOPMENT_STATE.md](DEVELOPMENT_STATE.md) — current implementation, source-pinned experiments, measured operating costs, limitations, and next engineering milestone.
- [RESEARCH_EVOLUTION_LOG.md](RESEARCH_EVOLUTION_LOG.md) — append-only research/operational evidence chronology, including rejected calls and the M23.2–M23.3 A/B comparisons.
- [PROJECT_VISION.md](PROJECT_VISION.md) — scientific north star, FRESH isolation, provenance, and development discipline.

## M23.2–M23.3 development checkpoint

The controller evaluation path uses Novelty (NVT), Problem Impact (PMI), Opportunity (OPP), and Controller (CTRL). The changes below reduce development/runtime overhead **without dropping strong-null evaluation or promoting unverified model outputs to primary evidence**:

| Feature | Tested effect / boundary |
| --- | --- |
| `ON_DEMAND` indexed context | Detail and full-context retrieval remain available; the initial large OPP/CTRL prompt was reduced from roughly 424–429K to 312–316K tokens in the earlier comparison. |
| `M232_NAMESPACE_MODE=COMPACT` | Exact ID/alias roundtrip and source-provenance checks; observed OPP/CTRL input went from 312,050/316,048 to 248,109/252,288 tokens, crossing below the observed 272K pricing threshold. |
| `M232_CACHE_POLICY=SELECTIVE_NO_WRITE` | In the measured A/B, PMI/OPP/CTRL cache-write tokens became zero while NVT retained AUTO; about 19.2% combined PMI/OPP/CTRL cost reduction was observed, with response-length variation. |
| `M233_MODEL_METADATA_MODE=SEPARATE` | Integrity hashes remain in the original Journal/detail session while indexed rows advertise their incompleteness; observed OPP/CTRL prompt tokens fell 248,575→204,084 and 252,710→207,614. |
| Reference diagnostics | Preserve the SAVED model response and reject invalid Work references; never silently convert Asset IDs into Problem or Source IDs. |

Candidate configuration **for a new source-pinned experiment only**:

```bash
export M232_CONTROLLER_DETAIL_MODE=ON_DEMAND
export M232_NAMESPACE_MODE=COMPACT
export M232_CACHE_POLICY=SELECTIVE_NO_WRITE
export M233_MODEL_METADATA_MODE=SEPARATE
```

These are **opt-in settings**, not permission to resume an old paid Journal under a changed wire schema. The last M23.3 A/B was a **single Controller decision per root**, not a completed autonomous Population or Worker research run. In `SEPARATE`, one INFORMED `DEVELOP` Work was committed, but its research was **not executed**. In `FULL`, one controller plan was rejected due to an unregistered Source ID; this is not a scientific negative. P0 remains `UNRESOLVED`; no new Level II mechanism or causal SERS attribution was certified.

## No-paid local regression on the development branch

Use the verified WSL environment and the current local repository. This does not make provider calls:

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution_M23_2"
unset FAKG_RESEARCH_ALLOW_PAID OPENROUTER_API_KEY
export PYTHONPATH="$PWD/runtime:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
python -m compileall -q runtime AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029
while IFS= read -r directory; do
  python -m unittest discover -s "$directory" -p 'test_*.py' -q
done < <(find checks -type f -name 'test_*.py' -printf '%h\n' | sort -u)
```

Last operator-reported result at source `168d071`: **168 tests passed, one skipped**. This tests software contracts, not scientific validity. Research Journals, provider keys, raw responses, usage receipts, and experiment roots remain outside Git; operational spending guards are not scientific stop decisions.

---

## Historical V4 active runtime snapshot (2026-10-31)

> **Development navigation (2026-10-31):** This README documents the preserved
> V4 snapshot. For the current general-purpose AI Scientist objective and
> repository-first development practice, see [PROJECT_VISION.md](PROJECT_VISION.md).
> For the active integration branch, experiment boundaries, and verified status,
> see [DEVELOPMENT_STATE.md](DEVELOPMENT_STATE.md).

This folder is a **source-preserving checkpoint**, not a refactored or experimentally validated new AI Scientist. It records the code that implements the V2 Claim–Problem Delta → V3 Closed Loop → V4 Research Readiness path, using `e2core` from the live WSL runtime. The Clean Baseline entrypoint is included without changing its model prompts, source pins, or journal contracts.

## Scope

- `runtime/e2core/`: journal, provider, engine, tools, long campaign and package-local support modules, copied without modification.
- `runtime/scientific_problem_evolution.py`, `scientific_problem_autorun.py`, `science_frontier_campaign.py`: V2 + opportunity evaluation.
- `runtime/scientific_closed_loop_v3.py`: scientific-event and reuse extension.
- `runtime/scientific_research_readiness_v4.py`: theory/computation/empirical readiness extension.
- `runtime/scientific_v4_clean_baseline.py`: checkpointed command entrypoint.
- `checks/`: original per-version no-paid tests; `background/`: contemporaneous docs.
- `SOURCE_MANIFEST.json`: SHA256 of all captured source files.

**Excluded:** V5 arbitration and its recovery patches, historical research evaluation ROOTs, model requests/responses, provider billing data, API keys, journals, datasets, notebooks, archives and logs.

This snapshot has *not* been substituted into an ongoing paid process. An existing run should continue using its original version-pinned source paths. Use this snapshot for source review, local regression tests and later consolidation; if starting a new run from the snapshot, run preflight on a newly forked research ROOT and check source pins first.

## No-paid checks (requires the existing graphAgent311 environment)

```bash
conda activate graphAgent311
unset FAKG_RESEARCH_ALLOW_PAID
cd scientific_evolution
export PYTHONPATH="$PWD/runtime"
python -m compileall -q runtime
python -m unittest discover -s checks/v3 -p 'test_*.py' -q
python -m unittest discover -s checks/v4 -p 'test_*.py' -q
python -m unittest discover -s checks/clean -p 'test_*.py' -q
```

Note that tests validate internal contracts using controlled fixtures/mocks; they cannot replace a real WSL integration preflight and do not demonstrate Level II attainment.

## Provenance & code drift

The initial six core files and the V4 wrapper are SHA256-pinned by the running research software. Copies here retain the same bytes, verified by `SOURCE_MANIFEST.json`. When consolidation/refactoring is planned, create a **new execution branch and new root** rather than modifying the code used by an existing journal.

## Security

Never commit `$HOME/GraphAgentsDAC/evaluation`, `.env`, API keys or any file from the research ROOT. Use a separate Git worktree and inspect `git status`, `git diff --cached` before pushing.
