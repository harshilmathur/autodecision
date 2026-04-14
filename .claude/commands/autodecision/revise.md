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
/autodecision:revise zero-mdr-upi-smb "What if Capital attach rate is only 8% and Competitor A reaches PG parity in 6 months?"
/autodecision:revise zero-mdr-upi-smb "Add a hypothesis: partner with Orchestrator Co to offer free UPI through their orchestrator"
/autodecision:revise acme-corp-orchestrator-co-support "Assume RBI mandates UPI interoperability within 6 months"
/autodecision:revise acme-corp-orchestrator-co-support "Change tilt to risk minimization — IPO is in 3 months"
/autodecision:revise acme-corp-orchestrator-co-support "New data: Competitor B just quietly reconnected with Orchestrator Co"
```

## Execution

1. Read the skill definition at `.claude/skills/autodecision/SKILL.md`
2. Read `references/phases/revise.md` for the full revise protocol
3. Follow all 7 steps: LOAD → PARSE → CONFIRM → PREPARE → EXECUTE → OUTPUT → PERSIST
4. Produces TWO files: a standalone DECISION-BRIEF.md + a REVISION-DIFF.md comparing to original
