# Phase 6: SENSITIVITY

## Purpose
Systematically vary key assumptions and track which ones flip conclusions.
This is what turns the output from "here's our best guess" into "here's
exactly what would change our mind."

## Inputs
- `iteration-{N}/effects-chains.json`
- `iteration-{N}/adversary.json`

## Outputs
- `iteration-{N}/sensitivity.json`

## Process

### Step 1: Select Assumptions to Vary

Rank assumptions by potential impact. Select the top 3-5 for analysis:

1. Assumptions flagged as "SHAKEABLE" or "FRAGILE" by the adversary phase
2. Assumptions with wide `probability_range` (> 0.3 spread) in effects chains
3. Assumptions referenced by 3+ effects (high connectivity = high leverage)

### Step 2: Vary Each Assumption

For each selected assumption:

1. Define the **opposite case.** What if this assumption is wrong?
   - "price_sensitivity_high" → "market is value-driven, not price-sensitive"
   - "competitor_monitors_pricing" → "competitor is focused internally, ignores our move"

2. Re-estimate probabilities for every effect that depends on this assumption.
   - Keep all OTHER assumptions fixed.
   - Only change the one being tested.

3. Check if the recommendation flips:
   - Does the overall direction change (do it → don't do it)?
   - Do any "stable" effects become unstable?
   - Do any new effects emerge that weren't considered?

### Step 3: Compute Sensitivity Ratings

For each assumption:
- **HIGH:** Changing it flips the recommendation OR shifts 3+ effect probabilities by > 0.2
- **MEDIUM:** Changing it shifts 1-2 effect probabilities by > 0.2 but doesn't flip the recommendation
- **LOW:** Changing it shifts no effect probability by more than 0.1

### Step 4: Identify Decision Boundaries

For HIGH sensitivity assumptions, identify the exact boundary:
- "If customer acquisition increase is < 15% (vs assumed 30-40%), the recommendation flips from 'cut pricing' to 'hold pricing'"
- "If competitor response time is < 2 weeks (vs assumed 4-6 weeks), the price war scenario becomes dominant"

### Step 5: Update Assumption Sensitivity in Effects Chains

Write the sensitivity ratings back to the `all_assumptions` map in `effects-chains.json`:
- Update each analyzed assumption's `sensitivity` field from `null` to "HIGH"/"MEDIUM"/"LOW"

### Output

Write `sensitivity.json` — see `references/effects-chain-spec.md` for schema.

The most important output is the **decision boundaries**: specific thresholds where
the conclusion changes. These go directly into the Decision Brief.
