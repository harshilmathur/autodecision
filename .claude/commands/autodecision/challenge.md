---
name: autodecision:challenge
description: Stress-test a proposed action — adversary-only mode, no full loop
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

# /autodecision:challenge

Stress-test a proposed action without running the full decision loop. Goes straight
to adversary + sensitivity analysis. ~5 minutes.

## Invocation

```
/autodecision:challenge "We're cutting pricing by 30% across all plans next month"
/autodecision:challenge "We're acquiring a competitor at $500M to enter a new vertical"
/autodecision:challenge "We're hiring 50 engineers over the next quarter"
```

## Execution

Read `references/phases/challenge.md` for the full protocol.
