---
name: autodecision:revise
description: Revise a previous decision with changed assumptions, new hypotheses, or new data
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
  - TodoWrite
---

# /autodecision:revise

Revise a previous decision run with changed assumptions, new hypotheses, new data,
or a different tilt. One command, one natural language input. The system parses what
changed and re-runs from the earliest affected phase.

## Invocation

```
/autodecision:revise {slug} "{what changed}"
```

## Examples

```
/autodecision:revise pricing-cut-20pct-full "What if customer acquisition only increases 10% instead of 30%?"
/autodecision:revise pricing-cut-20pct-full "Add a hypothesis: offer a freemium tier instead of cutting prices"
/autodecision:revise market-expansion-full "Assume the regulatory timeline is 6 months, not 18"
/autodecision:revise market-expansion-full "Change tilt to risk minimization — IPO is in 3 months"
/autodecision:revise market-expansion-full "New data: a competitor just entered the same market"
```

## Execution

1. Read the skill definition at `.claude/skills/autodecision/SKILL.md`
2. Read `references/phases/revise.md` for the full revise protocol
3. Follow all 7 steps: LOAD → PARSE → CONFIRM → PREPARE → EXECUTE → OUTPUT → PERSIST
4. Produces TWO files: a standalone DECISION-BRIEF.md + a REVISION-DIFF.md comparing to original
