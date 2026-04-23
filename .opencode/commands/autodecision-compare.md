---
description: Compare two decisions side-by-side — run fresh on both (quick mode) OR compare existing runs
agent: build
---

# /autodecision-compare

Compare two decisions: $ARGUMENTS

## Parse Mode

Parse `$ARGUMENTS` to decide:

- Contains `"A" vs "B"` (quoted) and no `--existing` flag → **Fresh Comparison** (run `/autodecision-quick` on both)
- Contains `--existing slug-a vs slug-b` → **Post-Facto Comparison** (read two existing briefs)
- Ambiguous → use `question` to ask the user which mode

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md`

## Fresh Comparison

1. Parse the two decision statements from input.
2. Run `/autodecision-quick` on Decision A (inline — don't spawn, just walk the quick-mode protocol from `references/engine-protocol.md`). Write to `~/.autodecision/runs/{slug-a}-quick/`.
3. Run `/autodecision-quick` on Decision B. Write to `~/.autodecision/runs/{slug-b}-quick/`.
4. Read both `DECISION-BRIEF.md` files + both `effects-chains.json`.
5. Produce comparison output per template below.
6. After writing the comparison file, use `question` to ask: `"Want to run the full loop on one of these?"`

## Post-Facto Comparison

1. Parse the two run slugs from input.
2. Read `~/.autodecision/runs/{slug-a}/DECISION-BRIEF.md` and `~/.autodecision/runs/{slug-b}/DECISION-BRIEF.md` (and corresponding `effects-chains.json` if present).
3. Produce comparison output.
4. If either brief is missing, list available runs via `glob` on `~/.autodecision/runs/*/` and ask the user to pick.

## Output Template

Write to `~/.autodecision/runs/comparison-{slug-a}-vs-{slug-b}.md`:

```markdown
# Decision Comparison: {Decision A} vs {Decision B}

Generated: {date}

## Summary

| Dimension | {A short name} | {B short name} |
|-----------|----------------|----------------|
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
| Execution risk | HIGH/MED/LOW | HIGH/MED/LOW |
| Competitive risk | HIGH/MED/LOW | HIGH/MED/LOW |
| Financial risk | HIGH/MED/LOW | HIGH/MED/LOW |
| Reversibility | HIGH/MED/LOW | HIGH/MED/LOW |
| Time to value | {timeframe} | {timeframe} |

## Shared Effects

Effects that appear in BOTH decisions (same or similar `effect_id`s), with probability comparison:
- acq_increase: A=0.60, B=0.45
- ...

## Unique to {A}
- ...

## Unique to {B}
- ...

## Assumption Overlap

Shared assumptions across both decisions — candidates for the assumption library:
- ...

## Key Tradeoffs

What do you gain by choosing A over B? What do you lose?
What do you gain by choosing B over A? What do you lose?

## Recommendation

{If one is clearly better: "Decision A is the stronger option because..."}
{If a genuine tradeoff: "This depends on [factor]. If X, choose A. If Y, choose B."}
{If not comparable: "These are independent decisions — comparison surfaces shared assumptions but they don't compete."}
```

## Assumption-Library Integration

If both decisions reference the same assumptions (e.g., both reference `price_sensitivity_moderate`), note them in the Assumption Overlap section. Shared assumptions across different decisions are candidates for `~/.autodecision/assumptions.jsonl` entries — they represent organizational beliefs worth tracking.
