# ScientificEvolution — Project Vision

## Purpose

Build a **general-purpose autonomous AI Scientist**. A human supplies an unresolved
scientific problem (P0), not a scripted sequence of next hypotheses. Independent
researchers explore, propose, calculate, acquire evidence, challenge, and revise
hypotheses. A population of researchers decides what research to continue, compare,
branch, hand off, or terminate. The goal is a scientifically substantive result,
not a large number of model calls, assets, generations, or successful JSON parses.

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
