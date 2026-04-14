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

Total = added + removed + shifted. Threshold: < 2.

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

### Convergence Decision

**Converged** = ALL 4 thresholds met.
**Not converged** = any threshold violated AND iteration < max (3).
**Max reached** = exit regardless. Note which thresholds were not met.

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
