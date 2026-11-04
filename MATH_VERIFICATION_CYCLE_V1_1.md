# ScientificEvolution — Native Math Claim Selection V1.1

## Goal and version scope

V1 passed offline review-cycle tests, but in its actual pilot SYN_01 published `A_polarity_odd_resident_state_001` as a `HYPOTHESIS`, not as `CALCULATION` or `COUNTEREXAMPLE`. The content contained a conditional mathematical interpretation of local detailed balance, yet no verifier Work was registered. Its second Controller created an independent FRESH primary-literature audit instead of selecting VERIFY. A subsequent FRESH model response consisted of **two distinct JSON documents**; the Native parser correctly saved and rejected it, without executing an ungrounded tool call. All 10 paid V1 calls and the operator's V1 Source Pin stay unchanged.

V1.1 lets a Controller consider **claim-level** mathematics in any current-root live scientific Asset kind, and optionally in assets directly carried from newly completed work in the immediately prior root. This is not a keyword or asset-kind classifier. The exact mathematical subclaim must be authored by the Controller. The Controller may VERIFY, DEFER, prioritize other science, or determine no separately verifiable mathematical subclaim is present.

## Decision contract and evidence truth

For every `native_math_claim_selection.candidates` input entry, the Controller is **asked** to emit `native_math_claim_decisions` with one `asset_id`, a `decision` (`VERIFY_NOW`, `DEFER`, `OTHER_RESEARCH_FIRST`, `NO_MATH_CLAIM`), an explicit `math_claims` list, and the scientific `rationale`. The decision is part of the saved model-authored parsed `CONTROLLER_DECISION` and is *not* a machine-issued proof certificate.

`VERIFY_NOW` counts as a runnable verification selection **only** when an actually committed, single-parent `VERIFY`/`INFORMED` Work exists in the same Journal and its ID matches the model's `work_id`. Invalid, missing, conflicting or incomplete selection records are reported in `selection_audit`, not silently repaired. The model can still commit unrelated, independently useful research actions; V1.1 does not reject a whole Controller decision merely because it lacks optional selection metadata. This also makes real noncompliance observable.

A Controller-chosen VERIFY worker receives only its pinned one-parent subject and own prior steps, not prior cross-review solutions; the exact Controller-selected subclaim is labelled as **model-authored target**, not true. On terminal response, the Worker writes `MATH_REVIEW` as a normal Journal Work step. If a new mathematical Asset is published by that reviewer, it enters the V1 independent verifier queue recursively, whether its `kind` is `COUNTEREXAMPLE`, `CALCULATION`, or a hypothesis authored by a verifier. If the reviewed subject has a current-root author, a new INFORMED reassessment Work is created. If the subject was carried from a previous root, the reassessment is explicitly marked a **new current-root Work**; it does not impersonate or reactivate a historical author.

Native state and history are never rewritten; assessment is distinct from observation; tools are never asserted executed unless actual `TOOL_RECORDED` journal events prove so. The existing automatic CALCULATION/COUNTEREXAMPLE review behavior remains intact. New roots must opt in with `persistent_population.py init --math-verification`.

## Interpretation limits

The rule "all mathematical statements in every free-form paragraph will be found" is **not claimed**. Rather, candidate assets of any kind are made available, and the Controller is prompted to identify actual verifiable subclaims. A missed candidate is a measured **selection failure** to be studied, not a silent success. `native_math_claim_decisions` is advisory/for provenance; a VERIFY action is real only after it appears as a native `EVOLUTION_APPLIED` Work. Mathematical quality and the validity of reviewer-generated claims require independent human/evidence evaluation. The offline tests use explicitly MOCK decisions and MOCK Worker responses; they validate runtime wiring, not actual autonomous model competency.

Operational limits are separate from scientific judgement. A `GLOBAL_CALL_BUDGET` pause does not certify a result or mark research `HOLD`. No historical V1 Source Pin is rewritten. The V1 code must remain available in the original worktree; V1.1 uses a **separate Git worktree** and a new run root.

## No-paid tests before any paid run

```bash
cd "$HOME/ScientificEvolution_MATH_V11"
unset FAKG_RESEARCH_ALLOW_PAID
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/runtime:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
KIT="$HOME/SCIEVO_NATIVE_MATH_CYCLE_V1_1_20261104"
python "$KIT/checks/test_claim_selection_offline.py"
python "$KIT/checks/test_recursive_v1_compat.py"
python "$KIT/checks/native_claim_selection_smoke.py" "$PWD"
python "$KIT/checks/native_recursive_v1_smoke.py" "$PWD"
python -m unittest discover -s checks/v3 -p 'test_*.py'
python -m unittest discover -s checks/v4 -p 'test_*.py'
git diff --check
```

## Resume policy and next-run pilot

After tests and an explicit Git commit, use a new V1.1 root and an explicit newly generated source pin. To preserve the direct V1 pilot hypothesis as a recent *historical* scientific candidate, initialize from the read-only V1 `CYCLE_000/SYN_01` root instead of rereading the old historical SYN_02 root. This creates a new clean state and marks the V1 Work statuses as historical. Verify `candidate_assets` discovers the carried previous-root hypothesis, with no falsified current-root execution. Any experimental sampling with paid models requires a separate, explicit operator action; no paid call is made by this kit.
