---
name: autodecision:review
description: Review past decisions, compare predictions vs outcomes
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /autodecision:review

Review past decision runs. List decisions, read briefs, and compare predictions
vs actual outcomes.

## Invocation

```
/autodecision:review                                       # List all past decisions
/autodecision:review pricing-cut-20pct-full                # Show a specific decision's brief
/autodecision:review pricing-cut-20pct-full --outcome "Acquisition increased 25%, competitor matched in 3 weeks, enterprise churn was 3%"
```

## Execution

### List Mode (no arguments)

1. Read `~/.autodecision/journal.jsonl`
2. Display as a table:

```
| # | Decision | Date | Mode | Converged | Confidence | Recommendation | Outcome |
|---|----------|------|------|-----------|------------|----------------|---------|
| 1 | Should we cut pricing by 20%? | 2026-04-14 | full | yes (iter 2) | HIGH | Don't cut, run A/B promo | — |
```

If no journal exists: "No decisions logged yet. Run `/autodecision` to analyze a decision."

### Detail Mode (with decision slug)

1. Find the entry in `journal.jsonl` by `decision_id`
2. Read the full `DECISION-BRIEF.md` from the `run_path`
3. Display the brief
4. If `outcome` is set, also display the accuracy comparison

### Outcome Recording (with --outcome)

1. Find the entry in `journal.jsonl` by `decision_id`
2. Parse the outcome text provided by the user
3. Compare each predicted effect against the outcome:
   - For each top effect: was it **correct** (happened as predicted), **partially correct**
     (happened but magnitude/timing differed), or **wrong** (didn't happen)?
   - For each load-bearing assumption: did it **hold**, **break**, or remain **untested**?
   - Was the recommendation followed? Was it correct in hindsight?
4. Compute accuracy_score
5. Update the journal entry with outcome data
6. Display a comparison table:

```
PREDICTION vs REALITY: Should we cut pricing by 20%?

| Effect | Predicted P | What Happened | Verdict |
|--------|-------------|---------------|---------|
| Acquisition increase 20-35% | 0.60 | Increased 25% | CORRECT |
| Competitor matches price | 0.45 | Matched in 3 weeks | CORRECT (faster than expected) |
| Enterprise churn > 5% | 0.30 | Churn was 3% | PARTIALLY CORRECT (below threshold) |

Assumptions:
| Assumption | Predicted | Reality |
|-----------|-----------|---------|
| price_sensitivity_moderate | assumed true | HELD |
| segments_are_separable | FRAGILE | UNTESTED (didn't implement segmentation) |

Recommendation was: Don't cut, run A/B promo
Recommendation followed: [ask user]
In hindsight: [ask user]

Overall accuracy: 4/7 effects correct, 2 partially, 1 wrong
```

7. Use AskUserQuestion to confirm:
   - "Was the recommendation followed?"
   - "In hindsight, was the recommendation correct?"

### Calibration Summary (after 5+ outcomes recorded)

When 5+ decisions have outcomes, add a calibration section:

```
CALIBRATION SUMMARY (across N decisions):

| Predicted P Range | Times Correct | Actual Rate | Calibration |
|-------------------|---------------|-------------|-------------|
| 0.70-0.95 | 12/15 | 80% | WELL CALIBRATED |
| 0.40-0.69 | 8/14 | 57% | SLIGHTLY OVER |
| 0.10-0.39 | 3/10 | 30% | WELL CALIBRATED |

Most reliable assumption type: competitive dynamics (held 8/10 times)
Least reliable: volume projections (held 3/9 times)
```

This is the long-term payoff of the journal — understanding where the system's
estimates are trustworthy and where they're systematically biased.
