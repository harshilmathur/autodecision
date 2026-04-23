---
description: Review past decisions, compare predictions vs outcomes, record actuals
agent: build
---

# /autodecision-review

Review past decision runs. List decisions, read briefs, and compare predictions vs actual outcomes.

Run on: $ARGUMENTS

## Usage

```
/autodecision-review                                                  # List all past decisions
/autodecision-review {slug}                                           # Show a specific brief
/autodecision-review {slug} --outcome "Acquisition increased 25%, competitor matched in 3 weeks"
```

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md`
3. `.claude/skills/autodecision/references/journal-spec.md` — journal schema

## Modes

### List Mode (no arguments)

1. Read `~/.autodecision/journal.jsonl` via `read` tool.
2. If the file doesn't exist or is empty, print: `"No decisions logged yet. Run /autodecision to analyze a decision."`
3. Otherwise parse each line (JSONL — one JSON object per line) and display as a table:

```
| # | Decision | Date | Mode | Converged | Confidence | Recommendation | Outcome |
|---|----------|------|------|-----------|------------|----------------|---------|
| 1 | Should we cut pricing by 20%? | 2026-04-14 | full | yes (iter 2) | HIGH | Don't cut, run A/B promo | — |
| 2 | ... | ... | quick | — | MEDIUM | ... | correct |
```

### Detail Mode (with slug)

1. Find the entry in `journal.jsonl` by matching `decision_id == {slug}`.
2. Read the full `DECISION-BRIEF.md` from `{run_path}` (as recorded in the journal entry).
3. Display the brief to the conversation.
4. If the entry has an `outcome` field set, also display the accuracy comparison.

### Outcome Recording (with `--outcome`)

1. Parse `{slug}` and the outcome text from `$ARGUMENTS`.
2. Find the entry in `journal.jsonl` by `decision_id`.
3. Read the `DECISION-BRIEF.md` for that run.
4. For each top effect (from the brief's Effects Map section): was it **CORRECT** (happened as predicted), **PARTIALLY CORRECT** (happened but magnitude/timing differed), or **WRONG** (didn't happen)?
5. For each load-bearing assumption: did it **HOLD**, **BREAK**, or remain **UNTESTED**?
6. Was the recommendation followed? Was it correct in hindsight? (Use `question` to ask the user these two.)
7. Compute `accuracy_score`: (# CORRECT + 0.5 × # PARTIALLY CORRECT) / (# effects evaluated).
8. Update the journal entry:
   - Read the existing JSONL entry.
   - Append/update its `outcome` field with: timestamp, free-text, effect verdicts, assumption verdicts, recommendation_followed (bool), correct_in_hindsight (bool), accuracy_score (float).
   - Rewrite `journal.jsonl` with the updated entry. (JSONL is append-only conceptually, but in-place updates are acceptable when recording outcomes — preserve other lines unchanged.)
9. Display a comparison table:

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
Recommendation followed: {yes/no}
In hindsight: {correct/wrong}

Overall accuracy: 4/7 effects correct, 2 partially, 1 wrong
```

### Calibration Summary (after 5+ outcomes recorded)

When 5+ decisions have outcomes recorded, append a calibration section at the end of list mode:

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

This is the long-term payoff of the journal — understanding where the system's estimates are trustworthy and where they're systematically biased.

## Rules

- `journal.jsonl` is the source of truth. Never read the brief alone to answer "what was recommended" — that field lives in the journal.
- Outcome recording is in-place: keep other lines unchanged, update the matching entry's `outcome` field.
- Human output: no `snake_case` in prose, no backticked `effect_id`s — show the brief's `description` text instead.
