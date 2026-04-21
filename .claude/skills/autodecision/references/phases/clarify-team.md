<!--
phase: 2.5
phase_name: CLARIFY
runs_in:
  - full.team       (after HYPOTHESIZE, before SIMULATE — team mode only)
  - medium.team     (same)
  - quick           (SKIPPED — quick mode has no council)
  - non-team modes  (SKIPPED — phase does not exist outside team mode)
reads:
  - ~/.autodecision/runs/{slug}/shared-context.md
  - ~/.autodecision/runs/{slug}/iteration-{N}/hypotheses.json
writes:
  - ~/.autodecision/runs/{slug}/iteration-{N}/clarify-questions.json
  - ~/.autodecision/runs/{slug}/iteration-{N}/clarify-answers.json
  - appends a new block to ~/.autodecision/runs/{slug}/shared-context.md
gates:
  - Skippable with --skip-clarify
  - Skippable when no teammate raises a question within the 60s window
-->

# Phase 2.5: CLARIFY (team mode only)

## Purpose

Surface persona-specific clarifying questions about the user's business context **before** personas simulate effects. This catches the failure mode where subagents fabricate assumptions (wrong churn rate, wrong price sensitivity, wrong named competitor) because they have no mid-run channel to ask the user.

CLARIFY exists only in team mode because non-team subagents cannot pause to ask questions — they are spawned fire-and-forget via the Agent tool and return JSON.

## Inputs

- `shared-context.md` (already precomputed by orchestrator)
- `iteration-{N}/hypotheses.json` (just written by Phase 2)

## Outputs

- `iteration-{N}/clarify-questions.json` — full transcript of what each teammate asked
- `iteration-{N}/clarify-answers.json` — what the user answered, tagged per recipient
- Appends a new `USER-PROVIDED CONTEXT (from CLARIFY)` block to `shared-context.md` using the format from `references/persona-preamble.md` lines 107–113 extended

## Skip Conditions

Skip CLARIFY entirely when:

- User passed `--skip-clarify` on the command line.
- User passed `--skip-elicit` (already signaled they want to run without interactive gates).
- A decision template was used **and** grounding returned substantive data for every sub-question (high-context run).
- All 5 teammates reply with zero questions in Step 2.

When skipped, write a placeholder `clarify-questions.json` with `"status": "skipped"` and the reason, and proceed to Phase 3.

## Process

### Step 1: Lead broadcasts the question-elicitation prompt

After Phase 2 writes `hypotheses.json`, the lead broadcasts to all 5 teammates (single message, `broadcast` mode):

> **CLARIFY — Phase 2.5.** Read `shared-context.md` and `iteration-{N}/hypotheses.json`. Before you simulate, identify 1–3 clarifying questions about the user's business context you would need answered to avoid fabricating assumptions.
>
> Constraints:
> - Each question must be concrete and answerable in one sentence (e.g., *"What is your current monthly churn rate?"*, not *"How do customers feel?"*).
> - Each question must be specific to your persona's lens — the Pessimist asks about downside indicators, the Competitor asks about named rivals, etc.
> - Reply with JSON only: `{"persona": "<short-tag>", "questions": ["...", "..."]}`. Maximum 3 questions per persona.
> - If you have zero questions, reply with `{"persona": "<short-tag>", "questions": []}`.
>
> Respond within 60 seconds. Do NOT start analysis yet — wait for the consolidated answers.

### Step 2: Collect replies

Wait up to 60 seconds for SendMessage replies from all 5 teammates. Collect into a raw buffer. Teammates that don't reply within the window are treated as zero-question.

Write `clarify-questions.json`:

```json
{
  "status": "complete",
  "iteration": N,
  "window_seconds": 60,
  "replies": {
    "optimist":   {"questions": ["..."]},
    "pessimist":  {"questions": ["..."]},
    "competitor": {"questions": ["..."]},
    "regulator":  {"questions": ["..."]},
    "customer":   {"questions": ["..."]}
  }
}
```

### Step 3: Dedupe and rank

The orchestrator processes the raw buffer:

1. **Semantic dedup.** If two personas asked the same question (e.g., Optimist and Customer both asked "What is your activation rate?"), merge into a single consolidated question and tag BOTH personas as the askers.
2. **Rank by coverage.** Questions asked by 2+ personas surface first. Single-persona questions appear after.
3. **Cap.** Present at most 8 questions total to respect user time. If more exist, prioritize by coverage then by persona order (optimist, pessimist, competitor, regulator, customer).

### Step 4: Present to user via AskUserQuestion

Structure the prompt as a grouped batch:

> The council has clarifying questions before simulating. Answer any you can — skip the rest.
>
> **Asked by Pessimist and Customer:**
> 1. {consolidated question}
>
> **Asked by Competitor:**
> 2. {question}
>
> **Asked by Regulator:**
> 3. {question}
>
> ...
>
> Options:
> A) Provide answers below (free text, numbered)
> B) Skip this round — personas will work with current context (quality will suffer)

If the user picks B: note in `clarify-answers.json` with `"status": "user_skipped"` and proceed to Phase 3 with the existing `shared-context.md` unchanged.

### Step 5: Broadcast answers and enrich shared-context.md

Tag each answer with the personas that asked the underlying question. Build a `USER-PROVIDED CONTEXT (from CLARIFY)` block and append it to `shared-context.md`:

```
## USER-PROVIDED CONTEXT (from CLARIFY, iteration {N})

- [For pessimist, customer] Current monthly churn is 8% (not higher, as some council members assumed).
- [For competitor] Primary competitor is Acme Corp, not Globex — the competitive response should focus on Acme's typical playbook.
- [For regulator] The decision does not require SEC filing disclosure before shareholder vote.
- [General] Runway is 18 months at current burn.
```

Write `clarify-answers.json`:

```json
{
  "status": "complete",
  "iteration": N,
  "answers": [
    {
      "question": "What is your current monthly churn rate?",
      "asked_by": ["pessimist", "customer"],
      "answer": "8%"
    }
  ]
}
```

Broadcast a short message to all teammates:

> CLARIFY answers are now in `shared-context.md` under `USER-PROVIDED CONTEXT (from CLARIFY)`. Re-read that file before starting your Phase 3 analysis. Answers tagged `[For <your-short-tag>]` or `[General]` apply to you.

### Step 6: Proceed to Phase 3 SIMULATE

Once broadcast is complete, the lead posts Phase 3 simulation tasks to the shared task list. See `phases/simulate-team.md`.

## Timing and User Experience

CLARIFY should feel like a single 2-minute check-in, not a Q&A marathon. Target:

- Step 1 broadcast: instant
- Step 2 collection window: 60 seconds (hard cap)
- Step 3 dedup and rank: ~10 seconds (orchestrator inline work)
- Step 4 user answers: user-paced, typically 2–5 minutes
- Step 5 broadcast back: instant

Total wall-clock: ~3 minutes typical, with most of it the user writing answers.

## Integration with Revise Mode

When `/autodecision:revise` runs on a prior team-mode run, the revise protocol should:

1. Read `iteration-{N}/clarify-answers.json` from the original run to understand what was already clarified.
2. Decide whether the revision input invalidates any prior answer (e.g., if the user said churn was 8% in the original run but the revision note says "our churn is actually 20%", the new value replaces the old).
3. Re-run CLARIFY only if the revision introduces genuinely new context gaps.

## Failure Handling

- **Teammate replies with invalid JSON.** Skip that persona's questions; log a warning. Do not block.
- **Teammate times out (no reply in 60s).** Treat as zero questions. Proceed.
- **User provides partial answers.** Tag unanswered items as `"answer": "not provided"` in `clarify-answers.json`. Do not block — personas simulate with what they have.
- **All 5 teammates reply with zero questions.** Skip Steps 3–5. Write a `"status": "no_questions"` placeholder in `clarify-questions.json`. Proceed directly to Phase 3.
