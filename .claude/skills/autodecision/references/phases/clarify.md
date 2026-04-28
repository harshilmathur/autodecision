<!--
phase: 2.5
phase_name: CLARIFY
runs_in:
  - full.iteration-1    (runs ONCE per run, between HYPOTHESIZE and first SIMULATE)
  - medium.iteration-1  (runs ONCE per run, same slot)
  - NOT in iteration 2+ (hypotheses are stable by then; answers already in persona-preamble.md)
  - NOT in quick mode   (no council, no business-context gap to fill)
  - SKIPPED when config.json has "skip_clarify": true (from --skip-clarify flag)
  - SKIPPED when the clarifier returns zero questions (smart skip — grounding was thorough)
reads:
  - ~/.autodecision/runs/{slug}/config.json
  - ~/.autodecision/runs/{slug}/ground-data.md
  - ~/.autodecision/runs/{slug}/iteration-1/hypotheses.json
  - ~/.autodecision/runs/{slug}/user-inputs.md (if ELICIT produced it)
  - ~/.autodecision/runs/{slug}/context-extracted.md (if --context was provided)
writes:
  - ~/.autodecision/runs/{slug}/iteration-1/clarify-questions.json
  - ~/.autodecision/runs/{slug}/iteration-1/clarify-answers.json
  - Appends "USER-PROVIDED CONTEXT (from CLARIFY)" block to persona-preamble content
    as bundled into shared-context.md (the orchestrator rebuilds shared-context.md
    after CLARIFY so every Phase 3 persona sees the answers)
spawns:
  - 1 foreground Agent subagent (the clarifier — NOT a persona) for question generation
  - 0 subagents for answer synthesis (inline in orchestrator — mechanical merge)
gates:
  - question_cap: clarifier MUST return ≤ 5 questions (hard cap; if more, keep the highest-signal 5)
  - scope_gate: questions must be about business context (numbers, stakeholders, constraints),
    NOT about the decision itself (that's ELICIT's job) or about solutions (that's SIMULATE's job)
-->

# Phase 2.5: CLARIFY

## Purpose

Surface **persona-impacting business-context gaps** that became visible only after HYPOTHESIZE. ELICIT (Phase 1.5) asks generic questions upfront before hypotheses exist — it cannot anticipate which specifics would change a persona's analysis. By the time hypotheses are on the page, concrete gaps are obvious: "the Pessimist's churn analysis depends on a churn number we don't have," "the Regulator's jurisdiction analysis depends on which countries the decision applies to."

CLARIFY exists to close those gaps in **one bounded interactive surface** before SIMULATE fabricates specifics.

## Design constraints

This phase is narrow on purpose. Violating any of these turns the skill into a conversation instead of a decision engine:

1. **One-shot.** The clarifier runs once, returns once, the user answers once. No follow-up rounds.
2. **One batched `AskUserQuestion`.** All questions presented together, not one-by-one.
3. **≤5 questions.** Hard cap. More than 5 is CLARIFY overreaching into ELICIT or SIMULATE territory.
4. **Skippable.** `--skip-clarify` on the command line skips the whole phase. Zero-question returns auto-skip.
5. **Single subagent, not a persona council.** The clarifier reads through the decision-analyst lens and consolidates gaps. Five personas each asking questions would scatter the interactive surface and multiply question counts past the cap.

## Inputs

- `config.json` — decision statement, sub-questions, constraints, `skip_clarify` flag
- `ground-data.md` — what GROUND already found (answers already here need not be re-asked)
- `iteration-1/hypotheses.json` — the hypotheses whose analysis depends on business specifics
- `user-inputs.md` — ELICIT's output (if present) — answers already captured here need not be re-asked
- `context-extracted.md` — document extractions (if `--context` was provided) — covered data need not be re-asked

## Outputs

- `iteration-1/clarify-questions.json` — the clarifier's proposed questions
- `iteration-1/clarify-answers.json` — the user's answers, tagged by question
- Answers are also appended to `shared-context.md` under a `USER-PROVIDED CONTEXT (from CLARIFY)` block when the orchestrator rebuilds that file before Phase 3 spawns personas

## Process

### Step 0: Skip checks

Before spawning anything:

1. Read `config.json > skip_clarify`. If `true`, write `clarify-answers.json` with `{"status": "skipped", "reason": "user_flag"}` and return.
2. If mode is `quick`, skip. Quick has no council; CLARIFY has no value.
3. If iteration ≠ 1, skip. Hypotheses are stable from iter-2+, and prior-iter answers are already in `shared-context.md`.

### Step 1: Spawn the clarifier subagent

Use the Agent tool ONCE (not 5 times). The clarifier is not a persona — it is a decision-analyst reader whose only job is to surface business-context gaps. Spawn it as a foreground subagent with this prompt:

```
You are the CLARIFY subagent for autodecision run {slug}, iteration 1.

Read these files in order:
1. ~/.autodecision/runs/{slug}/config.json  (decision + sub-questions + constraints)
2. ~/.autodecision/runs/{slug}/ground-data.md  (already-known facts from GROUND)
3. ~/.autodecision/runs/{slug}/iteration-1/hypotheses.json  (the hypotheses that will be simulated)
4. ~/.autodecision/runs/{slug}/user-inputs.md  (already-captured from ELICIT — DO NOT re-ask)
5. ~/.autodecision/runs/{slug}/context-extracted.md  (if present — DO NOT re-ask)

Your job: surface up to 5 business-context questions whose answers would materially
change how the 5-persona council (Optimist, Pessimist, Competitor, Regulator, Customer)
simulates the hypotheses. Think about what each persona would fabricate if they had
to simulate these hypotheses right now without asking you anything. Those fabrications
are the gaps.

Hard rules:
- MAXIMUM 5 questions. If you have more, keep the 5 whose answers would shift the
  most effects across the most personas. Fewer is fine.
- Do NOT ask about the decision itself (ELICIT already covered that).
- Do NOT ask about solutions ("should we do X or Y?") — that's SIMULATE's job.
- DO ask about numbers, stakeholders, constraints, and specifics. Examples:
  - "What is your current customer churn rate?"
  - "Which jurisdictions does this decision apply to?"
  - "What is the team size and composition today?"
  - "Who are the top 2 competitors and what are their current price points?"
  - "What is your current runway in months?"
- Questions must be answerable in a sentence or two. Avoid open-ended essays.
- If a question is already answered in ground-data.md, user-inputs.md, or
  context-extracted.md, SKIP it — do not ask.
- If no genuine gaps remain (grounding was thorough), return an EMPTY questions array.
  That triggers a smart-skip and is the correct behavior when no real gaps exist.

Output strict JSON to ~/.autodecision/runs/{slug}/iteration-1/clarify-questions.json:

{
  "status": "complete",
  "questions": [
    {
      "id": "q1",
      "question": "What is your current monthly customer churn rate?",
      "why": "The Pessimist hypothesis on post-price-cut retention and the Customer
              hypothesis on satisfaction-driven retention both hinge on the baseline
              churn rate. Without it, both personas will fabricate."
    },
    {
      "id": "q2",
      "question": "...",
      "why": "..."
    }
  ]
}

STRICT JSON ONLY. No comments, no trailing commas, no prose wrappers.
Maximum 5 entries in questions. Zero is acceptable.
```

Wait for the clarifier to complete. If it times out or fails, log a warning and skip CLARIFY (proceed to SIMULATE without it). Do not block the run on a clarifier failure.

### Step 2: Smart-skip on zero questions

Read `clarify-questions.json`. If `questions` is empty:

1. Write `clarify-answers.json` with `{"status": "skipped", "reason": "no_questions"}`.
2. Log: "CLARIFY auto-skipped — clarifier found no business-context gaps given existing grounding."
3. Return. Do not present anything to the user.

### Step 3: Present the batched `AskUserQuestion`

Present all returned questions as ONE `AskUserQuestion` call, with one question per field. Include the `why` inline so the user understands why each is being asked:

```
AskUserQuestion([
  {
    "title": "Q1",
    "description": "{question} — Why: {why}",
    "header": "CLARIFY",
    "multiSelect": false,
    "options": []    // free-text
  },
  // ... up to 5
])
```

The user answers inline. If the user skips an answer (leaves it blank), treat it as "not provided" — downstream personas will fall back to hedged assumptions and note the gap in their output.

### Step 4: Write answers

Write `iteration-1/clarify-answers.json`:

```json
{
  "status": "complete",
  "answers": [
    {
      "question_id": "q1",
      "question": "What is your current monthly customer churn rate?",
      "answer": "About 8% monthly in the last 90 days — stable, not trending."
    },
    ...
  ]
}
```

Answers with empty strings MUST be kept in the array (downstream must know which questions were seen but left blank).

### Step 5: Append to shared-context.md for SIMULATE

The orchestrator rebuilds `shared-context.md` before Phase 3 spawns personas. When doing so, append a new block BEFORE the Phase 3 schema section:

```
## USER-PROVIDED CONTEXT (from CLARIFY)

Treat these as high-confidence — more reliable than web search or inference.
Every persona should use these in their simulation instead of fabricating.

- [C1] What is your current monthly customer churn rate? → About 8% monthly in the last 90 days, stable.
- [C2] Which jurisdictions does this decision apply to? → India and Singapore only at launch; UAE in a 90-day follow-up.
- ...
```

Use `[C#]` tags (C for CLARIFY) so downstream phases can cite these in the brief's Sources table alongside `[G#]`, `[D#]`, and `[U#]` tags.

If a question was left blank by the user, still include it in the block with a note:

```
- [C3] What is your current runway in months? → (not provided — personas should hedge)
```

## Quality gate

After Step 5, the orchestrator verifies:

1. If `clarify-questions.json > questions.length > 5`, that is a clarifier rule violation. Log a warning and truncate to the first 5 before presenting.
2. If the user left EVERY question blank, note in the run log that CLARIFY ran but captured no data. Continue to SIMULATE.
3. If `clarify-answers.json` is missing (write failed), log critical and continue — personas will simulate without the answers.

None of these block the run. CLARIFY is best-effort: if it breaks, SIMULATE still runs with the grounding it has.

## Why this is not a persona round

Five personas each asking 1–3 questions lands at 5–15 questions after dedup. Even batched into one `AskUserQuestion`, that scatters the interactive surface into persona-specific fragments and turns the skill into a conversation. ELICIT + CLARIFY are the only two interactive moments autodecision offers — keeping CLARIFY as a single clarifier with ≤5 questions preserves that discipline.

A single clarifier reading through the decision-analyst lens consolidates gaps across all 5 persona lenses in one pass. The trade-off — missing a persona-specific question that only one lens would surface — is accepted because the alternative (conversational drag) violates the skill's fire-and-forget design.
