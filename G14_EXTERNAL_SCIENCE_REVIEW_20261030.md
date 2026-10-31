# G14 external scientific review (independent; pre-experiment)

**Target:** `W_P0_redox_mechanochemical_symmetry_001` (INFORMED, ACTIVE), G14 Journal head at 1,483 events (`e47a0e3af57c4438…`).  
**Status:** Operator-side independent audit, not a native `SOURCE_REGISTERED` entry, peer-reviewed finding, primary literature observation, or Level-II certification. Previously published hypotheses/assets and rejected proposals are retained unchanged.

## R1 — Observation-index discrepancy in toy projection

Worker step 8 declares the six observation coordinates as `(odd occupancy, even occupancy, signed event charge, capacitive current, common gain, thermal/junction nuisance)`. However, its actual vector is

```python
signal = [1/occ_sigma, 0.15*sqrt(n_events), 0.0, 0.0, 0.0, 0.0]
```

The **signed charge** coordinate is index 2 and is **zero**. The nonzero projected information derives from index 1 (*even occupancy*). Recalculation with the original nuisance matrix gives projected information 0.375 (50 events), 1.5 (200), and 7.5 (1,000), independent of `occ_sigma` because the index-0 signal lies in the nuisance span. Simply moving `0.15*sqrt(n_events)` from index 1 to index 2 produces 1.125, 4.5, and 22.5—still toy-model results, now driven by a **zero nuisance coupling** in the charge coordinate. Neither set demonstrates physical charge identifiability.

**Requested scientific evaluation:** Correct the mapping and determine the information under a physically justified charge-sensor noise and nuisance basis. If no such basis can be justified, return an appropriately scoped negative result.

## R2 — Integrated capacitive charge does not generically vanish as ramp rate tends to zero

For constant capacitance, `i_C = C * dV/dt`. Over a fixed voltage interval, however,

\[
Q_C = \int i_C dt = C(V_2 - V_1),
\]

which is **rate-independent**. For `C=2 pF` and a `0.2 V` sweep, integrated charge is `0.4 pC` at each of `0.01`, `0.1`, and `1 V/s`. The **instantaneous current** approaches zero, not necessarily the **integrated charge**.

A state-dependent capacitor provides an additional counterexample. If `Q_C(x,V) = C(x,V)V`, then

\[
i_C = \left(C+V\frac{\partial C}{\partial V}\right)\dot V
   + V\frac{\partial C}{\partial x}\dot x.
\]

Even at fixed voltage, a state transition may yield a non-Faradaic event charge `ΔQ_C = V ΔC`. The specific capacitive response depends on the physical charge–voltage constitutive relation; the expression above is an explicit example, not a universal model.

**Requested scientific evaluation:** Specify the integration window (voltage span, fixed time, or event aligned), whether voltage-dependent and state-dependent charging currents have been subtracted and how, the leakage bound, and what independent chemical-state measurement would discriminate Faradaic events from charging. Re-derive any rate limit on **properly calibrated residual event charge**, not the raw integrated current.

## R3 — The broad observational-equivalence statement also needs constraints

The assertion that an arbitrary Faradaic current trace can always be reproduced by single-valued `C(x,V)` and `G(x,V)` is stronger than justified if multiple waveform histories visit the same `(x,V)` with distinct currents. A more flexible history-dependent model may match finite data, but that is a different and more explicitly constrained assertion. Specify a causal nuisance function class and whether **one common parameter set** must explain multiple waveforms.

## Journal history to preserve

The model proposed `P0_bounded_current_decomposition_005` with parent IDs `A_P0_state_dependent_charge_constructive_equivalence_008` and `A_P0_bounded_rate_extrapolation_discriminator_009`. The validator rejected the *problem* as `INVALID_PROBLEM_PARENTS`, without invalidating the two accepted assets. Do not silently repair historical records. An informed researcher may propose a new valid problem with **problem IDs as parents** and reference the scientific assets separately.

## Reviewer boundary

This is **external, critic-authored feedback for one new INFORMED Worker model request** only. The researcher may agree, refute with evidence, make a corrected calculation, qualify its prior claim, independently propose a better test, or return a scoped negative. The review must not be treated as primary literature or recorded as though it were a native scientific tool result. G14 Controller and FRESH workers are not injected with this critique; the original Journal prefix and earlier assets are never rewritten.
