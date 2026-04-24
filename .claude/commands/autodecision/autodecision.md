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
/autodecision --skip-clarify "..."          # skip Phase 2.5 CLARIFY
/autodecision --skip-elicit --skip-clarify "..."  # fully autonomous run
```

## Flags

- `--iterations N` — inner-loop iteration cap (default 2)
- `--template {pricing|expansion|build-vs-buy|hiring}` — pre-populate decomposition
- `--context file1 [file2 ...]` — attach context documents (Claude Code only)
- `--skip-elicit` — skip Phase 1.5 ELICIT (user review of assumptions, personas, data)
- `--skip-clarify` — skip Phase 2.5 CLARIFY (post-hypothesis business-context questions)

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

## Phase 8 + 8.5 — the two rules that keep getting broken

Read these before you reach Phase 8. The writer has historically shipped
structurally broken briefs by improvising here. Two hard rules:

### Rule A — Schema is the structure. You don't get to invent headers.

Before writing ONE line of DECISION-BRIEF.md:

1. Open `references/brief-schema.json`.
2. For the active mode (`full` for default `/autodecision`; `medium` for `--iterations 1`; `quick` for `:quick`; `full` for revise runs), enumerate every `header` whose `required_in` contains that mode, plus all required subsections.
3. Write that enumerated checklist into your working context — literally, one line per required header, in schema order.
4. Compose the brief against that checklist. Check each header off as you emit it.
5. Forbidden: inventing sections not in the schema, even if they seem to aid readability.
   `## Context`, `## Decision tilt`, `## The possibility map`, `## Methodology`, `## Analysis Approach`,
   `## Bottom Line`, `## Summary`, `## Adversary Findings` — all HARD_FAIL. The schema IS the
   readability contract.
6. Forbidden: collapsing the 7-field Recommendation block into prose. The literal labels
   `**Action:**`, `**Confidence:**`, `**Confidence reasoning:**`, `**Depends on:**`,
   `**Monitor:**`, `**Pre-mortem:**`, `**Review trigger:**` are required.

Full protocol: `references/phases/decide.md` Step 4a.

### Rule B — Phase 8.5 means running the named script. No substitutes.

Phase 8.5 is `python3 "{skill_dir}/scripts/validate-brief.py" --run-dir "{run_dir}" --schema "{skill_dir}/references/brief-schema.json" --mode "{mode}"`.

- Exit 0 → continue. Exit 1 → append warning footer. Exit 2 → re-prompt DECIDE once. Exit 3 → log and continue.
- If `python3 --version` fails, run the fallback self-check from `phases/decide.md` Step 5.5 (re-read the brief, verify every header from the Step 4a checklist is present, add the structural-self-check footer).

Forbidden: writing an inline Python script in a Bash heredoc that checks for headers
you just authored and declaring "N/N passed." That is self-certification, not
validation. A writer that invents its own headers and then writes a validator checking
for those same invented headers will always pass. The validator exists precisely to
catch the case where the writer drifted from the schema. If your inline script is
checking for `## Context` or `Decision tilt` or `possibility map` — none of which are
in the schema — you built a validator for your own mistake.

Full protocol: `references/phases/validate-brief.md`.

## Important

- Read `references/effects-chain-spec.md` before Phase 3 for JSON schemas
- Read `references/persona-council.md` before spawning subagents
- Read `references/validation.md` for output validation rules
- Read `references/output-format.md` before Phase 8
- Read `references/brief-schema.json` before Phase 8 — it is the canonical structure
- Update the TodoWrite progress tracker at EVERY phase transition
- The full loop takes significant compute (20+ LLM calls). Confirm with user before starting if the decision seems trivial.
