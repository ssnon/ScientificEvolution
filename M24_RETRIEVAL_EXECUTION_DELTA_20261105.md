# M24 retrieval-resilience V1 — observed defect and bounded native repair

**Date:** 2026-11-05 KST. **Status:** Source patch prepared; paid scientific execution not yet observed on this version.

## Observed V1.2 evidence

- `W_fresh_joint_primary_audit_M240` was assigned an accessible primary-literature audit by Controller D00001. Its first Worker response contained **three distinct JSON documents** and was rejected, so no tool executed on that step. A second single-envelope Worker response successfully requested `literature_research(search, provider=openalex)`.
- That real OpenAlex request returned **HTTP 429**, `ProviderUnavailable` / `EVIDENCE_UNAVAILABLE`. The tool correctly did not turn retrieval failure into a scientific null.
- The Worker then generated `A_charge_gated_sers` and its quantitative follow-up without inspecting primary full text. These were explicitly conditional, source-less AI theoretical assets; they **did not complete the primary literature audit** even though the Work ended `RETURN`.
- `W_fresh_modular_primary_audit_M241` was still `ACTIVE` with **zero saved Worker calls or tool results** when the Population reached its operational bound. It is not evidence of failed search.
- Provenance: `SCIEVO_M24_V12_WORK_EXECUTION_TRACE_20261105.json`, read-only extraction from the V1.2 G0 Population Journal. No old source code, original P0 or saved model response is to be rewritten.

## Native repair

`runtime/e2core/research_literature.py` previously fell back from Europe PMC on transient HTTP 5xx to OpenAlex, but **not the reverse direction** on an OpenAlex 429. M24 adds one symmetrical cross-provider **search-only** fallback on 429/502/503/504/connection unavailable. It preserves all retrieval attempts, the requested provider, fallback metadata and the strict distinction between BIBLIOGRAPHIC_METADATA and primary source text.

An optional `OPENALEX_API_KEY` can be supplied via process environment, sent only as an HTTPS `Authorization: Bearer` header to the allowlisted `api.openalex.org` host; it is never inserted in URLs or Journal evidence. No key is required to try Europe PMC fallback, and the OpenRouter model key is unrelated.

The patch does NOT change FRESH isolation, Controller decisions, science policy, Math Verifier, Work finish behavior, or the provenance contract. It does not silently claim a primary paper was read, declare a mechanistic finding, or rescue old saved calls. The separate scientific question of why M240 pivoted after provider failure remains a recorded observation, not a reason to hard-code a mandatory research direction.

## Subsequent end-to-end evaluation (not an operational quota)

After this native route passes one bounded offline test and source-pinned preflight, create a **new** experiment from the V1.2 Population checkpoint (621 assets), avoiding mutation or resumption of the old completed G0 Journal. Permit autonomous PEER and Population choices; do not force literature Work, same mechanism, or a minimum tool count. Record whether requested literature tools actually return sources, whether Workers inspect primary text if useful, and whether subsequent science genuinely changes claims/strong-null comparison. Mathematical corrections must remain available and are not pre-certified. Failures must remain visible and may justify another scientific choice.

Do not count a metadata-only fallback as a primary-study inspection. If both search providers fail, retain `EVIDENCE_UNAVAILABLE`. If no meaningful integration appears, distinguish model judgment and data availability from the runtime tool path before altering research policies.
