<!--
phase: 7
phase_name: CONVERGE
runs_in:
  - full.iteration-1     (baseline scoring — iteration 1 NEVER converges by design; scores contradictions only)
  - full.iteration-2+    (mechanical scoring vs prior iteration — gates whether to loop or exit)
  - medium.iteration-1   (SKIPPED — medium mode goes straight to DECIDE with "Converged: N/A")
  - quick                (SKIPPED — no iterations)
reads:
  - current iteration: effects-chains.json + peer-review.json
  - previous iteration (iter ≥ 2): effects-chains.json + peer-review.json
runs_inline:
  - Judge runs INLINE in orchestrator (~5 sec; set operations on JSON, not an agent)
  - Inline timing enables Phase 8 concurrent start when this is the final iteration
writes:
  - ~/.autodecision/runs/{slug}/iteration-{N}/judge-score.json (4 parameters + converged boolean)
  - ~/.autodecision/runs/{slug}/iteration-{N}/convergence-summary.md (~500-token carry-forward to next iter)
  - ~/.autodecision/runs/{slug}/convergence-log.json (append-only)
gates:
  - PRIMARY (must pass): contradiction_count ≤ 1 OR decreasing AND assumption_stability > 80%
  - SECONDARY (warn but don't gate): effects_delta < 2, ranking_flips ≤ 1
  - false_convergence_check: perfect scores at iter-1 OR all-perfect-on-iter-2 → "Council diversity LOW" warning
  - max iterations reached AND not converged → offer user extension (see "Offer to Extend at Max Iterations"); cap at 5 total
-->

# Phase 7: CONVERGE

## Purpose
The Convergence Judge measures whether insights have stabilized. This is the
mechanical stop condition that replaces "feels done" with parameters.

## Inputs
- Current iteration: `effects-chains.json`, `peer-review.json`
- Previous iteration: `effects-chains.json`, `peer-review.json` (if iteration > 1)

## Outputs
- `iteration-{N}/judge-score.json`
- `iteration-{N}/convergence-summary.md`
- Append to `convergence-log.json`

## Process

### Iteration 1 (Baseline)

No previous iteration to compare. The Judge:
1. Counts internal contradictions in the current `effects-chains.json`
2. Sets effects_delta, assumption_stability, ranking_flips to N/A
3. Records the baseline state
4. Writes `convergence-summary.md` summarizing the current state
5. **Never converges** (nothing to converge against)

### Iteration 2+

The Judge compares current vs previous iteration:

**1. Effects Delta**

Compare `effects-chains.json` between iterations by `effect_id`:
- Count effects ADDED (present in current, absent in previous)
- Count effects REMOVED (present in previous, absent in current)
- Count effects with probability SHIFTED > 0.1

Total = added + removed + shifted. This is a WARNING signal, not a gate.

**2. Assumption Stability**

Compare `all_assumptions` keys between iterations:
- Count keys present in BOTH iterations
- Divide by total unique keys across both iterations
- Express as percentage

Threshold: > 80%.

**3. Ranking Flip Count**

Compare `peer-review.json` between iterations:
- For each reviewer, extract their pairwise rankings
- A "flip" = a pair of analyses where the ordering reversed
  (e.g., iteration 1: A > B, iteration 2: B > A)
- Count total flips across all reviewers

Threshold: ≤ 1.

**4. Contradiction Count**

Within the current iteration's effects:
- Identify pairs of 1st-order effects that directly contradict
  (e.g., "revenue increases" vs "revenue decreases")
- Only count effects with `council_agreement` >= 2
  (single-persona effects don't count as contradictions)

Threshold: ≤ 1.

### Convergence Decision (Weighted Composite)

The old model (ALL 4 must pass) is broken. Iteration 2 legitimately resolves
contradictions, which REQUIRES changing effects. A 22-effect delta that resolves
5 contradictions is convergence success, not failure.

**New model: PRIMARY + SECONDARY signals with a delta-weighted cap.**

**PRIMARY signals (must pass for convergence):**
- `contradiction_count` is DECREASING or at threshold (≤ 1)
- `assumption_stability` > 80%

**SECONDARY signals (inform but also hard-cap):**
- `shared_effect_shifts` — load-bearing convergence signal. Count of first-order
  effect_ids present in BOTH iterations whose probability shifted by > 0.10.
  This is what "the map stabilized" actually means.
- `delta_first_order_added_removed` — first-order effect_ids added or removed
  between iterations. Real convergence signal but distinguishes from sub-effect
  noise.
- `sub_effect_noise` — count of new/removed second-order children of stable
  first-order effects. Informational only — does NOT trip the cap. Natural
  elaboration as personas refine details around stable mechanisms.
- `ranking_flip_count` — WARNING if > 1, gate only if > 3 (complete ranking reversal)

**Hard-cap gate:** if `effective_delta > 50`, convergence is FALSE regardless of
other signals. The cap fires only on first-order signal (shared shifts +
add/remove), NOT on sub-effect noise. Earlier versions used raw `effects_delta`
which counted every 2nd-order child change — false-NOT-CONVERGED on substantively-
converged runs (real case: 27 stable shared first-order, 1 shifted, 89 new 2nd-
order children → raw delta 116 wrongly fired the cap).

**Convergence logic (canonical pseudocode — implement exactly this):**

```
# --- Compute the 3 first-order signals + 1 noise signal ---
shared_effect_shifts = 0
delta_first_order_added_removed = 0
sub_effect_noise = 0

prev_first_order_ids = {e.effect_id for e in iter-(N-1).hypotheses[*].effects
                        where e.order == 1}
curr_first_order_ids = {e.effect_id for e in iter-N.hypotheses[*].effects
                        where e.order == 1}

# Shared first-order: effect_ids in BOTH iters
for eid in prev_first_order_ids ∩ curr_first_order_ids:
    if abs(prev[eid].probability - curr[eid].probability) > 0.10:
        shared_effect_shifts += 1

# Added/removed at first-order (still convergence signal)
delta_first_order_added_removed = len(prev_first_order_ids ⊕ curr_first_order_ids)

# Sub-effect noise: 2nd-order children of effect_ids stable across iters
for eid in prev_first_order_ids ∩ curr_first_order_ids:
    prev_children = {c.effect_id for c in prev[eid].children}
    curr_children = {c.effect_id for c in curr[eid].children}
    sub_effect_noise += len(prev_children ⊕ curr_children)

# --- Compute effective_delta (excludes sub-effect noise) ---
effective_delta = shared_effect_shifts + delta_first_order_added_removed

# Subtract first-order effects from new_in_iter_N hypotheses (existing exception)
if any hypothesis in iter-N has new_in_iter_N: true:
    effective_delta -= count_of_first_order_effects_attributable_to_that_hypothesis

# --- Decide ---
if effective_delta > 50:
    NOT CONVERGED  (first-order map is still being rewritten)
elif contradiction_count <= 1 AND assumption_stability > 80%:
    CONVERGED  (even if sub_effect_noise is high — that's natural refinement)
    note sub_effect_noise and ranking_flips as warnings in the brief
elif contradiction_count is decreasing AND assumption_stability > 70%:
    TRENDING  (close to convergence, worth one more iteration if budget allows)
else:
    NOT CONVERGED
```

**Report all values in `judge-score.json`:**
- `shared_effect_shifts` (NEW, primary convergence signal)
- `delta_first_order_added_removed` (NEW)
- `sub_effect_noise` (NEW, informational)
- `effective_delta` (now = shared_shifts + add/remove, NOT the old raw delta)
- `effects_delta` (raw, kept for backward compat with prior runs and for the
  Convergence Log table — display alongside effective_delta so reader can see both)
- `contradiction_count`, `assumption_stability_pct`, `ranking_flip_count`

The brief's Convergence Log table shows all 7 values. The cap fires only on
`effective_delta`. Convergence requires PRIMARY signals (contradictions resolving
+ assumptions stabilizing) plus first-order map stabilizing — sub-effect noise
is reported but never gates.

**Why this changed:** earlier `effects_delta` was raw (all orders, no split).
A run with 27 stable shared first-order effects + 89 new 2nd-order children of
those stable parents had effects_delta = 116, fired the > 50 cap, and was wrongly
reported NOT CONVERGED even though the first-order map was substantively stable.
The split fixes this: load-bearing signal (first-order add/remove + shifts) is
what triggers the cap; second-order proliferation is reported but doesn't gate.

### User Confirmation Before Iteration 3+

After iteration 2 completes, if the Judge says NOT CONVERGED and budget allows
another iteration, the orchestrator MUST pause and ask the user before starting
iteration 3, 4, or 5. Running a third iteration doubles wall-clock time and
burns another 5 persona subagents — that's a user decision, not a Judge decision.

Ask via AskUserQuestion (once per additional iteration — before iter-3, before
iter-4, before iter-5):

> "Iteration {N-1} did not converge. Current Judge score:
> - Effects delta: {value} (effective {effective_delta} after new-hypothesis adjustment)
> - Assumption stability: {pct}% (threshold 80%)
> - Ranking flips: {value}
> - Contradictions: {value}
>
> Running iteration {N} will spend ~{minutes} more minutes and re-simulate the
> council with the current convergence summary as carry-forward. What would
> you like to do?"
>
> Options:
> A) Run iteration {N} (try for convergence)
> B) Stop here and write the brief with "Converged: NOT REACHED" flagged
> C) Downgrade to medium mode — skip remaining iterations, write brief from
>    iter-(N-1) state with "Iterations: {N-1} | Converged: N/A (user stopped)"

Default recommendation: A if trending (contradictions decreasing, stability
> 70%); B if flat (no improvement iter-(N-2) → iter-(N-1)).

**Why this gate exists.** Without it, a low-quality run keeps iterating in the
hope that something stabilizes — burning time and compute on a decision whose
uncertainty is genuine and won't resolve. The user knows whether another 15
minutes is worth it; the Judge doesn't.

**Iteration 2 does NOT require mid-loop confirmation.** iter-2 is the default loop
behavior. The mid-loop gate applies only when iter-N ≥ 3 is about to start.
However, if iter-2 is the final iteration (default max) and convergence is NOT
REACHED, the "Offer to Extend" gate below fires instead.

### Offer to Extend at Max Iterations

When the final iteration completes (iteration == max) and convergence is NOT REACHED,
the orchestrator MUST NOT silently exit to Phase 8. Instead, pause and offer the user
the option to extend.

This is the most common failure mode: the default 2 iterations don't converge, and
the system writes "Convergence: NOT REACHED" in the brief without ever asking whether
the user would have been willing to spend another 5 minutes for a better answer.

Ask via AskUserQuestion:

> "Iteration {max} complete — convergence NOT REACHED.
>
> Judge scores:
> - Effects delta: {value} (effective: {effective_delta})
> - Assumption stability: {pct}% (threshold: 80%)
> - Ranking flips: {value}
> - Contradictions: {value}
>
> The analysis has not stabilized. Running another iteration (~5-7 min) may
> resolve remaining instability, or the disagreement may be genuine.
>
> What would you like to do?"
>
> Options:
> A) Run 1 more iteration (extends to iteration {max + 1})
> B) Stop here — write the brief with "Converged: NOT REACHED"

Default recommendation: A if TRENDING (contradictions decreasing OR assumption
stability > 60%); B if FLAT or WORSENING (no improvement between iterations).

If the user picks A:
- Increment max_iterations by 1
- The next iteration is iter-{max+1}. If iter >= 3, the "User Confirmation Before
  Iteration 3+" gate does NOT re-fire (the user just opted in via this gate)
- Loop back to Phase 2
- If the extended iteration also doesn't converge, this gate fires AGAIN
  (the user can keep extending one-at-a-time, or stop)

If the user picks B:
- Exit the inner loop
- Phase 8 writes the brief with "Convergence: NOT REACHED" in the header
- The brief's Convergence Log shows all iterations and their scores

**Maximum extension cap:** max_iterations cannot exceed 5 total (the protocol's
hard ceiling). If the user has already extended to 5 and it still hasn't converged,
skip the offer and exit with NOT REACHED. At that point the disagreement is genuine.

### Partial Convergence Escalation

When 3/4 signals are healthy but 1 is failing, don't just print "NOT REACHED."
Offer targeted escalation:

| Failing Signal | Targeted Action |
|---------------|----------------|
| effects_delta high (but contradictions resolved) | Not a real failure. Converge. |
| contradictions still high | Run a focused CRITIQUE pass on the contradicting effects only |
| assumption_stability low | Run SENSITIVITY on the shifting assumptions only |
| ranking_flips high | Re-run PEER REVIEW with explicit instruction to resolve disagreements |

If iteration budget allows (current < max), auto-run the targeted action.
If at max iterations, note which dimension failed and what would fix it.

### Convergence Summary

Write `convergence-summary.md` (~500 tokens):

```markdown
# Convergence Summary: Iteration {N}

## Stable Effects (unchanged from previous iteration)
- [effect_id]: [description] — P: [probability] — stable

## Effects Under Pressure
- [effect_id]: [description] — P shifted from [old] to [new] — triggered by [critique/adversary finding]

## Assumptions Under Pressure
- [assumption_key]: challenged by [adversary finding], fragility: [rating]

## New Effects (added this iteration)
- [effect_id]: [description] — emerged from [adversary/critique finding]

## Removed Effects
- [effect_id]: dropped because [reason]

## Judge Score
- Effects delta: [N] (threshold: < 2)
- Assumption stability: [N]% (threshold: > 80%)
- Ranking flips: [N] (threshold: ≤ 1)
- Contradictions: [N] (threshold: ≤ 1)
- **Converged: [yes/no]**
```

This summary is carried forward as the ONLY context from this iteration
to the next. Do NOT carry forward full JSON files.

### Append to Convergence Log

Append the `judge-score.json` content to `convergence-log.json`:

```json
[
  {"iteration": 1, "converged": false, "parameters": {...}, "timestamp": "..."},
  {"iteration": 2, "converged": true, "parameters": {...}, "timestamp": "..."}
]
```
