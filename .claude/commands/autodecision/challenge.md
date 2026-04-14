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
/autodecision:challenge "We're going to drop UPI fees to zero next month"
/autodecision:challenge "We'll acquire Competitor B at $800M with a bank JV"
/autodecision:challenge "We're hiring 50 engineers in Bangalore over the next quarter"
```

## Execution

Read `references/phases/challenge.md` for the full protocol.
