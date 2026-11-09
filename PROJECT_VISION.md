# ScientificEvolution — Project Vision

## Purpose

Build a **general-purpose autonomous AI Scientist**. A human supplies an unresolved
scientific problem (P0), not a scripted sequence of next hypotheses or a fixed
scientific organization. The system chooses research questions, methods, actual
execution, independent criticism, and warranted conclusions. It also decides
on scientific grounds whether to use one or multiple researchers, when to branch,
collaborate, challenge, synthesize, reorganize, form further cohorts, or stop.
Neither peer count, mandatory fusion, nor generation count is a scientific policy.
The goal is a substantive, evidence-scoped result, not the number of model calls,
assets, generations, or successful JSON parses.

SERS is the current scientific proving ground, **not** a hard-coded mission for
the research engine. FAKG/Knowledge Graph infrastructure is historical context,
not the product objective.

## Scientific success and permissible outcomes

* Level II pre-experimental candidate: distinct causal or predictive content;
  physically defendable assumptions/calculations; meaningful discriminators
  against strong nulls; prior-art/evidence limitations stated; a realistic
  falsification/measurement route suitable for external scientific review.
* Scientific progress also includes a defensible counterexample, correction,
  scoped negative result, or evidence-grounded pivot; none automatically resolves
  the entire original P0.
* Novelty-advisor output, model-generated source interpretation, a recorded tool
  request, or a Python execution is not experimental validation or certification.
* It is valid to HOLD or change direction when research value is low. No fixed
  generation, worker, or step quota is a scientific success criterion.

## Pre-experimental Level II boundary and a fallible research community

The **current target is a pre-experimental, independently reviewable hypothesis or a defensible scientific negative/defer**, not an experimentally confirmed SERS mechanism. Real wet-lab experiments, new measurements, and causal proof from newly collected data are **not prerequisites** to reach the intended Level II research milestone. Pre-experimental work may nevertheless require genuine calculations/simulations, primary prior-art inspection, physical feasibility bounds and discriminating measurement designs. Known data and literature constrain the *plausibility and novelty of the proposal*; they need not already prove the proposal true.

A **Level II candidate** is a coherent scientific case, not a collection of individually impressive claims: (1) a precise, distinctive causal or predictive hypothesis; (2) internally consistent assumptions and mathematical/physical feasibility within explicitly defended regimes; (3) comparisons to strong *admissible* competing nulls, including overlap and non-identifiability boundaries; (4) honest, appropriately scoped prior-art and evidence status; and (5) feasible observations/interventions, predicted outcomes and genuine falsifiers that would make the proposed experiment worth independent human review. Novelty, feasibility and discriminating power are claims to support, not labels conferred by an agent or a prescribed threshold. Independent reviewers may reject the candidate. A rigorous scoped negative, impossibility/identifiability limit, or justified HOLD is also genuine scientific progress; it should not be cosmetically relabeled Level II.

**Individual agents are allowed to fail.** A math reviewer may miss a flaw; a literature worker may be unable to acquire a full text; a calculation may be rejected or a hypothesis falsified; a generation may pivot or make no progress. The system must preserve what was *actually* attempted, returned and learned; distinguish a failed assigned task from a potentially useful alternative scientific contribution; keep uncertainties/counterarguments available for correction; and avoid treating mere agreement, review count, asset ancestry, metadata, process-level execution or Work `DONE` as evidence of scientific truth. No mandatory positive discovery, per-agent success rate, depth quota, tool count, peer-parent link or fixed number of generations is a scientific policy.

**The system-level question** is whether independent, imperfect researchers can turn proposals, external constraints, criticisms and negative results into increasingly defensible *experiment-worthy* knowledge over time. Compare claims with actual evidence, including whether corrected limitations affected later scientific decisions; permit justified independent departures instead of enforcing convergence or forced use of any particular previous result.


<!-- ARCHITECTURE_META_AUTONOMY_20261109 -->
## 2026-11-09 clarification — scientific and meta-research autonomy

This is a **clarification of the intended mission, not a declaration that the current
runtime implements it**. The founder's original goal includes both scientific
judgment and **autonomy over the research organization and process itself**:

* The scientist chooses which research questions and methods to pursue, and whether
  to work alone or spawn independent researchers, critics, verifiers, or collaborators.
* The number of researchers, when or whether independent lines are synthesized,
  and whether to create further populations or generations must be justified by
  the research, not prescribed as compulsory stages or scientific quotas.
* It may continue, pivot, branch, defer, HOLD, or stop **on defensible scientific
  grounds** (including scoped non-identifiability, missing indispensable evidence,
  justified negative results, or low expected information value). Tool access
  failure or an uncompleted task is not automatically proof of impossibility.
* A scientific HOLD/termination must be distinguishable from a resource budget,
  permission, sandbox, or execution-time **operational pause**. Human-controlled
  cost, safety, and access boundaries remain mandatory external constraints;
  they do not determine the scientific verdict.
* The system must execute research as well as assess it, distinguish hypotheses
  from verified evidence, incorporate criticism and negative results, and revise
  its scientific methods and organization when warranted. Merely gaining more
  organizational options does not prove judgment quality or scientific ability.

`Controller`, `Worker`, `Verifier`, `PEER`, `Population`, `Generation`, `Asset`,
and the current science-evolution operators are **possible implementations**,
not definitions of an AI Scientist and not protected architectural commitments.
The current native PEERS -> COMBINE -> POPULATION cycle and operator-specified
peer count are known gaps relative to this clarified objective. This does **not**
establish that those gaps caused M26's unfinished science. Preserve provenance
truth, independent FRESH isolation where claimed, accurate tool/experiment
status, scientific corrections and uncertainty, and unmodified historic P0.

Architecture review and evidence boundary are recorded in
[`docs/AI_SCIENTIST_ARCHITECTURE_REASSESSMENT_20261109_KO.md`](docs/AI_SCIENTIST_ARCHITECTURE_REASSESSMENT_20261109_KO.md). No new architecture, automatic scientific stop,
or improved research outcome has been implemented by this documentation change.

## Invariants

* Preserve original P0 and research provenance. Append-only journals and saved
  provider responses are never silently rewritten or reinterpreted as old facts.
* Scientific FRESH independence is explicit; targeted prior-art audits are not
  represented as blind-independent hypothesis discovery.
* Problem ancestry, scientific-asset ancestry, evidence citations, unregistered
  opportunities, and certification status are separate relations.
* Research scientists, not operators or recovery scripts, choose scientific
  hypotheses and which research avenue to pursue.
* Resource/cost guardrails are operational controls, not scientific verdicts.

## Development discipline

1. Read the **current repository, architecture, and Git diff** before proposing
   changes; distinguish the live code path from frozen historical run scripts.
2. Prefer direct integration into the responsible runtime module, not accumulation
   of root-specific wrappers. Do not reimplement functionality already present.
3. State the original behavior, observed defect, proposed semantics, invariants,
   and end-to-end research effect before coding.
4. Commit and push meaningful changes; after each, inspect the resulting diff
   and tests against the overall scientist workflow.
5. Keep the scientific loop (research choice -> execution -> evidence/computation
   -> critical interpretation -> inheritance) as the dominant success criterion.

See DEVELOPMENT_STATE.md for dated implementation and experiment status.
