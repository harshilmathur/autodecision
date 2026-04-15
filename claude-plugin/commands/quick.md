---
name: autodecision:quick
description: Quick single-pass decision analysis (no council, no iteration)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - TodoWrite
---

# /autodecision:quick

Fast single-pass mode. SCOPE → GROUND → SIMULATE (single analyst) → DECIDE.
No personas, no peer review, no iteration. ~2 minutes.

## Invocation

```
/autodecision:quick "Should we launch in Southeast Asia?"
```

## Execution

1. Read `.claude/skills/autodecision/SKILL.md` for context
2. Read `references/engine-protocol.md` — follow "Quick Mode Protocol" section
3. Execute Phase 0 (SCOPE), Phase 1 (GROUND), Phase 3 (SIMULATE, single pass), Phase 8 (DECIDE)
4. Use the Quick Mode Brief Template from `references/output-format.md`
5. Write to `~/.autodecision/runs/{decision-slug}/`
6. Print the Quick Brief to the conversation

## When to Use

- Decisions that don't warrant 20+ LLM calls
- Quick sanity checks before committing to a full analysis
- When the user wants effects chain structure without the full council overhead
