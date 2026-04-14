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

**New model: PRIMARY + SECONDARY signals.**

**PRIMARY signals (must pass for convergence):**
- `contradiction_count` is DECREASING or at threshold (≤ 1)
- `assumption_stability` > 80%

**SECONDARY signals (inform but don't gate):**
- `effects_delta` — WARNING if high, but not a gate. A high delta WITH decreasing
  contradictions means productive refinement.
- `ranking_flip_count` — WARNING if > 1, gate only if > 3 (complete ranking reversal)

**Convergence logic:**
```
if contradiction_count <= 1 AND assumption_stability > 80%:
    CONVERGED (even if effects_delta is high)
    note effects_delta and ranking_flips as warnings in the brief
elif contradiction_count is decreasing AND assumption_stability > 70%:
    TRENDING (close to convergence, worth one more iteration if budget allows)
else:
    NOT CONVERGED
```

**Report all 4 values regardless.** The brief shows the full picture. But convergence
is determined by contradictions resolving + assumptions stabilizing, not by effects
freezing.

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
