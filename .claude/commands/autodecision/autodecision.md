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

Run the full Auto-Decision Engine: 10 phases, 5-persona council, iterative refinement
until convergence.

## ⚠️ MUST RUN INLINE — NOT AS A SUBAGENT

**This skill MUST execute in the main conversation, NOT inside a spawned agent.**
If you are a subagent (spawned by another agent or orchestrator), you CANNOT run
the full loop properly because the Agent tool is unavailable in nested contexts.
The 5-persona council requires spawning parallel subagents — which only works
from the main conversation.

**Before proceeding, check:** Am I the main conversation or a subagent?
- If main conversation: proceed normally.
- If subagent: STOP. Read `references/engine-protocol.md` "If Agent tool is
  unavailable" section and ask the user before continuing.

## Invocation

```
/autodecision "Should we cut pricing by 20%?"
/autodecision --template pricing "Should we cut pricing by 20%?"
```

## CRITICAL: You are the orchestrator

**Do NOT delegate the full loop to a single agent.** Follow each phase step by step
in THIS conversation. Spawn agents only for parallelizable tasks (personas, critique,
adversary). If you spawn one agent to "run everything," that agent can't spawn
grandchild agents and the personas collapse into sequential authoring — destroying
the council's value.

The correct pattern:
1. Run Phase 0-2 directly in this conversation
2. Spawn 5 persona agents in parallel (YOU spawn them, not a sub-orchestrator)
3. Do synthesis inline
4. Spawn critique + adversary agents in parallel (YOU spawn them)
5. Run sensitivity + judge inline
6. Run Phase 8 inline or as a single agent
7. Persist to journal

## Execution

1. Read the skill definition at `.claude/skills/autodecision/SKILL.md`
2. Read `references/engine-protocol.md` for the full loop protocol
3. Initialize the progress tracker (TodoWrite) with the full loop template
4. Execute all 10 phases in sequence, following the protocol exactly
5. Load each phase's reference file as you enter that phase
6. For Phase 3 (SIMULATE): spawn 5 persona subagents via the Agent tool
   as specified in `references/persona-council.md`. YOU spawn them directly.
7. For Phase 4+5: spawn critique + adversary agents in parallel. YOU spawn them.
8. Run quality gates after Phase 3 (diversity check) and after synthesis (depth check)
9. Write all outputs to `~/.autodecision/runs/{decision-slug}/`
10. Print the final Decision Brief to the conversation

## Important

- Read `references/effects-chain-spec.md` before Phase 3 for JSON schemas
- Read `references/persona-council.md` before spawning subagents
- Read `references/validation.md` for output validation rules
- Read `references/output-format.md` before Phase 8
- Update the TodoWrite progress tracker at EVERY phase transition
- The full loop takes significant compute (20+ LLM calls). Confirm with user before starting if the decision seems trivial.
