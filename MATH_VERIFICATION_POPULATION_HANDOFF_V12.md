# ScientificEvolution — Native Math Review/Population Handoff V1.2

Status: development patch and no-paid migration protocol. Target source is V1.1 commit `85fff58c74dc75d21944d1e27d36ff4733fa63df`. This is an **operational execution semantics** change, not a new research policy or scientific certificate.

## Why

The V1.1 G0 pilot left SYN_01 with an ACTIVE `W_NMREASSESS_07adfcffdeff86558f7fc3` at its cumulative 24-call cap. SYN_02 had a separate ACTIVE adversarial benchmark. The V1.1 Persistent runtime paused PEER -> COMBINE solely because `pending_math_work` was not empty. Math-review recursion may legitimately remain unresolved while independent peer research is already informative. Unfinished Work is not proof of a negative or a finished review.

## Native semantics

1. Saved provider calls and pricing continue to be counted **per actual external call**. No conversion from many paid calls to one billable call; no scientific inference from an operational call budget.
2. After the permitted PEER segment finishes, an unfinished native mathematical review is recorded as **HISTORICAL_AI pending Work**, not run or marked DONE in the Population. It does not unconditionally block COMBINE.
3. The native `combine` step imports original peer assets with unchanged scientific claims and donor ancestry, then registers `SRC_PEER_WORK_FRONTIER_SYN_01` and `SRC_PEER_WORK_FRONTIER_SYN_02`. Each source records original donor HEAD, original Work identifiers/status, original question, published asset IDs, mapped Population asset IDs, and pending math review IDs. All references derive from the verified donor Journal and checked import asset map. No synthetic external evidence is created.
4. The Population receives the exact unfinished-work checkpoint in `independent_peer_syn_portfolio` and retains autonomy to compare, continue, postpone, or abandon research directions based on scientific merit. Original PEER Work IDs are **not** runnable in the new Population root; a new Work must be independently authorized to continue any prior frontier.
5. At POPULATION -> COMPLETE, unfinished mathematical reviews remain explicit unfinished historical status for the next generation. They are **not** automatic science terminals or certificates.
6. No recursion-depth cap, quota on mathematical ideas, forced hypothesis, or change in math-review validity is introduced. Existing Native fail-closed Journal/Source/Asset validation remains unchanged.

## Existing G0 preservation and migration

The old V1.1 Source-Pinned G0 cannot run under V1.2 code without violating its exact Python-byte Source Pin. Do not alter `$HOME/ScientificEvolution_MATH_V11`, old `NATIVE_RUNTIME_SOURCE_PIN.json`, old root, or any old Journal to bypass the guard.

V1.2 adds **two native, no-paid commands**:

- `init-peer-snapshot --source-experiment OLD --out NEW` checks the old pin against the **old** Python worktree, verifies original P0, base, both peer Journals, saved-call states, model decisions, and exact donor HEADs. It then creates a separate V1.2 Source-Pinned experiment, copies only the clean original BASEs into NEW, and freezes the original peer source roots as immutable external historical donors. New G0 is placed directly at the `COMBINE` boundary. No peer research/model/tool call is re-executed, and original Work statuses are not rewritten.
- `combine-snapshot --experiment NEW` verifies exact donor heads and V1.2 source pin, then uses the **Native** peer importer to build POPULATION atomically, retaining both peer assets and explicit unfinished Work receipts. No paid model call, inference, or tool computation occurs.

The old G0's original 48 calls remain real **historical** calls. `persistent_population status` counts externally referenced historical PEER calls in the cycle total; this is not the number of new provider calls made by V1.2. The migration receipt explicitly reports `new_model_calls=0`. Subsequent POPULATION runs can be independently approved up to a new `--max-total-new-calls`, calculated from a run-local baseline, without replaying historical provider calls.

## Safety invariants

- Original P0, donor-head hashes, original V1.1 runtime pin, old Journal events/blobs, provider raw response, and original asset identities are immutable.
- No locally invented Source IDs or mathematical results may be introduced as old PEER model outputs. The two newly added `SRC_PEER_WORK_FRONTIER_*` sources are clearly labeled **operational historical status metadata**.
- The clone is aborted if any donor Journal is uncertain, P0 mismatches, original V1.1 code pin is invalid, imported asset mapping is unknown, or any frozen donor head changes.
- No modification of `e2core.core`, `e2core.engine`, `e2core.math_cycle`, `e2core.math_claim_selection`, provider, math prompts, or research scientific selection policies.
- The original V1.1 ROOT remains analyzable as its own historical experiment. V1.2's no-paid combine is a separate, traceable operational migration, not an autonomous model-selected scientific event. Population's subsequent decisions are model-selected.

## Evaluation criteria

The first milestone after no-paid migration is `POPULATION_COMBINED_NO_PAID`, with both PEER science assets imported, both `SRC_PEER_WORK_FRONTIER_*` statuses visible, old pending mathematics explicitly labeled incomplete, all old donor HEADs unchanged, and zero V1.2 model calls. This is **only an engineering continuity result**, not scientific progress.

After separately authorized paid POPULATION research, assess model-authored choices, actual retrieved source passages/calculations, noncommuting-intervention/null feasibility, critical reinterpretation of independently corrected math, and provenance-linked scientific deltas against SERS Level II criteria. A no-work or HOLD choice can be scientifically valid. Level II requires independent scrutiny, not asset count or controller approval alone.
