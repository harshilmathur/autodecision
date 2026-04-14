---
name: autodecision:plan
description: Interactive setup wizard — decompose and scope a decision
allowed-tools:
  - Read
  - Write
  - Bash
  - WebSearch
  - AskUserQuestion
---

# /autodecision:plan

Interactive setup wizard. Helps the user decompose their decision into sub-questions
and constraints before running the full loop.

## Invocation

```
/autodecision:plan
/autodecision:plan "Should we pivot to enterprise?"
```

## Execution

1. Read `.claude/skills/autodecision/SKILL.md`
2. Read `references/phases/scope.md`
3. Walk the user through decision decomposition:
   - What is the decision statement?
   - What are the key sub-questions? (help them identify 2-5)
   - What are the constraints? (budget, timeline, non-negotiables)
   - Is there a template that fits? (pricing, expansion, build-vs-buy, hiring)
4. Write `config.json` to `~/.autodecision/runs/{decision-slug}/`
5. Ask: "Ready to run the full analysis? Use `/autodecision` to start."
