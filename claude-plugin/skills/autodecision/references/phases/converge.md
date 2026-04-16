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
- `effects_delta` — WARNING if high. **Hard-cap gate:** if `effects_delta > 50`,
  convergence is FALSE regardless of other signals. A delta that high means the
  map is still being rewritten, not refined. Exception: if iter-N explicitly
  labeled any added hypothesis with `new_in_iter_N: true`, subtract effects
  attributable to that hypothesis from the delta before comparing to 50. This
  prevents "productive refinement" from masking genuine churn (the bug we hit
  at delta=126 in the pricing rerun).
- `ranking_flip_count` — WARNING if > 1, gate only if > 3 (complete ranking reversal)

**Convergence logic:**
```
effective_delta = effects_delta
if any hypothesis is flagged new_in_iter_N:
    effective_delta -= count_of_effects_attributable_to_that_hypothesis

if effective_delta > 50:
    NOT CONVERGED  (map is still rewriting itself)
elif contradiction_count <= 1 AND assumption_stability > 80%:
    CONVERGED (even if effective_delta is moderate, e.g., 5-50)
    note effective_delta and ranking_flips as warnings in the brief
elif contradiction_count is decreasing AND assumption_stability > 70%:
    TRENDING (close to convergence, worth one more iteration if budget allows)
else:
    NOT CONVERGED
```

**Report all 4 values regardless** — and add `effective_delta` alongside
`effects_delta` in `judge-score.json` so the brief's Convergence Log shows both
the raw delta and what was excluded. The brief shows the full picture. But
convergence is determined by contradictions resolving + assumptions stabilizing
AND the map actually stabilizing.

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
