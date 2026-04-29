---
description: Interactive setup wizard — decompose and scope a decision before running the full loop
agent: build
---

# /autodecision-plan

Interactive setup wizard. Walks the user through decomposing a decision into sub-questions and constraints before running the full loop.

Optional input: $ARGUMENTS (the decision statement — if provided, skip the first question)

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md`
3. `.claude/skills/autodecision/references/phases/scope.md` — the scope protocol

## Execute

Walk the user through Phase 0 (SCOPE) interactively via the `question` tool. All questions use structured multiple-choice where possible; use "Type your own answer" for open inputs.

### 1. Decision statement

If `$ARGUMENTS` is empty, ask:
> "What decision are you trying to make? (Phrase as a question, e.g., 'Should we cut pricing by 20%?')"

### 2. Input quality gate

Score the decision statement on the 4-point rubric from `phases/scope.md`:
- Is it a decision or an exploration? (Needs to be a decision.)
- Is it specific? (No ambiguity about what action is being considered.)
- Is it scoped? (Clear boundaries, not "should we change our strategy?")
- Is it high-stakes enough to warrant 20+ LLM calls?

If score < 3, use `question` to offer reframings. Do not let a weak decision through.

### 3. Sub-question decomposition

Help the user identify 2–5 sub-questions. Offer template-driven starters if a template fits:
- `pricing`, `expansion`, `build-vs-buy`, `hiring` — use `question` to offer these.
- If a template matches, load `references/templates/{template}.md` and pre-populate.
- Otherwise, ask the user to list 2–5 sub-questions with guidance prompts (e.g., "What's the biggest uncertainty about this decision?").

### 4. Constraints

Ask about:
- Budget / capital constraints
- Timeline / deadline
- Non-negotiables (regulatory, contractual, strategic)
- Reversibility (how hard to undo if wrong?)

### 5. Decision tilt (optional)

Ask: "What are you optimizing for? Growth, risk minimization, speed, or balanced?" — this biases the personas during ELICIT in the full loop. Record it in `config.json` but do NOT let it override persona independence during simulation.

### 6. Write config.json

Write `~/.autodecision/runs/{slug}/config.json` per `phases/scope.md` schema. Include:
- `decision_statement`
- `input_quality: {score, rubric_scores, needs_reframe}`
- `sub_questions: [...]`
- `constraints: {budget, timeline, non_negotiables, reversibility}`
- `tilt: "growth" | "risk" | "speed" | "balanced"`
- `template: {name} | null`
- `created_at: {ISO timestamp}`

### 7. Next step

Tell the user:
> "Ready to run the full analysis. Use `/autodecision \"{decision_statement}\"` to start."

If a template was selected, suggest: `/autodecision --template {name} "{decision_statement}"`.

## Rules

- This command does NOT spawn any subagents.
- It does NOT invoke `websearch` — save grounding for Phase 1 in the full loop.
- It only writes `config.json`. The rest of the run directory is created when `/autodecision` is invoked against the same slug.
