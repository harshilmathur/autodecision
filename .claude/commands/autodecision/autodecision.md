---
name: autodecision
description: Run the full Auto-Decision Engine loop on a decision
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - WebSearch
  - TodoWrite
---

# /autodecision

Run the full Auto-Decision Engine: 9 phases, 5-persona council, iterative refinement
until convergence.

## Invocation

```
/autodecision "Should we cut pricing by 20%?"
/autodecision --template pricing "Should we cut pricing by 20%?"
```

## Execution

1. Read the skill definition at `.claude/skills/autodecision/SKILL.md`
2. Read `references/engine-protocol.md` for the full loop protocol
3. Execute all 9 phases in sequence, following the protocol exactly
4. Load each phase's reference file as you enter that phase
5. For Phase 3 (SIMULATE) and Phase 4 (CRITIQUE): spawn persona subagents
   via the Agent tool as specified in `references/persona-council.md`
6. Write all outputs to `~/.autodecision/runs/{decision-slug}/`
7. Print the final Decision Brief to the conversation

## Important

- Read `references/effects-chain-spec.md` before Phase 3 for JSON schemas
- Read `references/persona-council.md` before spawning subagents
- Read `references/output-format.md` before Phase 8
- The full loop takes significant compute (20+ LLM calls). Confirm with user before starting if the decision seems trivial.
