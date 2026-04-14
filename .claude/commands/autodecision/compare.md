---
name: autodecision:compare
description: Compare two decisions side-by-side — either run fresh or compare existing runs
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - WebSearch
  - AskUserQuestion
---

# /autodecision:compare

Compare two decisions or decision variants side-by-side.

## Two Modes

### Mode 1: Fresh Comparison (run quick mode on both)
```
/autodecision:compare "Cut pricing 20%" vs "Cut pricing 10%"
/autodecision:compare "Launch in US" vs "Launch in SE Asia"
```

Runs `/autodecision:quick` on BOTH options, then produces a side-by-side comparison.
If one option is clearly better, recommend running the full loop on it.

### Mode 2: Post-Facto Comparison (compare existing runs)
```
/autodecision:compare pricing-cut-20pct-full vs market-expansion-full
/autodecision:compare --existing slug-a vs slug-b
```

Reads two existing Decision Briefs from `~/.autodecision/runs/` and produces
a structural comparison. Works for both quick and full mode runs.

## Execution

### Fresh Comparison

1. Parse the two decision statements from the input.
2. Run quick mode on Decision A (Phase 0 → 1 → 3 → 8).
3. Run quick mode on Decision B (same).
4. Read both Decision Briefs.
5. Produce comparison output (see template below).
6. Ask: "Want to run the full loop on one of these?"

### Post-Facto Comparison

1. Parse the two run slugs from the input.
2. Read both `DECISION-BRIEF.md` files from `~/.autodecision/runs/{slug}/`.
3. Read both `effects-chains.json` files for structural comparison.
4. Produce comparison output.

## Comparison Output Template

Write to `~/.autodecision/runs/comparison-{slug-a}-vs-{slug-b}.md`:

```markdown
# Decision Comparison: {Decision A} vs {Decision B}

Generated: {date}

## Summary

| Dimension | {Decision A short name} | {Decision B short name} |
|-----------|------------------------|------------------------|
| Recommendation | {action} | {action} |
| Confidence | {level} | {level} |
| Mode | {quick/full} | {quick/full} |
| Hypotheses explored | {N} | {N} |
| Effects (1st order) | {N} | {N} |
| High-consensus effects | {N} (if full) | {N} (if full) |
| Iterations | {N} | {N} |
| Converged | {yes/no} | {yes/no} |

## Risk Profile Comparison

| Risk Type | {A} | {B} |
|-----------|-----|-----|
| Execution risk | {HIGH/MED/LOW} | {HIGH/MED/LOW} |
| Competitive risk | {HIGH/MED/LOW} | {HIGH/MED/LOW} |
| Financial risk | {HIGH/MED/LOW} | {HIGH/MED/LOW} |
| Reversibility | {HIGH/MED/LOW} | {HIGH/MED/LOW} |
| Time to value | {timeframe} | {timeframe} |

## Shared Effects

Effects that appear in BOTH decisions (same or similar effect_ids):
{list with probability comparison: "acq_increase: A=0.60, B=0.45"}

## Unique to {A}

Effects or insights that only appear in Decision A:
{list}

## Unique to {B}

Effects or insights that only appear in Decision B:
{list}

## Assumption Overlap

Assumptions shared between both decisions:
{list — these are your "organizational assumptions" that recur across decisions}

## Key Tradeoffs

{What do you gain by choosing A over B? What do you lose?}
{What do you gain by choosing B over A? What do you lose?}

## Recommendation

{If one is clearly better: "Decision A is the stronger option because..."}
{If it's a genuine tradeoff: "This depends on [specific factor]. If X, choose A. If Y, choose B."}
{If the decisions are not comparable (apples vs oranges): "These are independent decisions — the comparison surfaces shared assumptions but they don't compete."}
```

## Integration with Assumption Library

If both decisions reference the same assumptions (e.g., both reference
`price_sensitivity_moderate`), note it in the comparison. Shared assumptions
across different decisions are candidates for the assumption library — they
represent organizational beliefs worth tracking and validating.
