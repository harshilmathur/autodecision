<!--
phase: N/A (standalone command, not part of the main loop)
phase_name: CHALLENGE
runs_in:
  - challenge  (invoked via /autodecision:challenge — adversary-only, no council)
reads:
  - User-provided action statement (from command argument)
  - Web search results (Phase 1 grounding only)
  - Context documents (if --context provided — extracted to context-extracted.md)
writes:
  - ~/.autodecision/runs/{slug}-challenge/config.json
  - ~/.autodecision/runs/{slug}-challenge/CHALLENGE-BRIEF.md
  - journal.jsonl (append, type: "challenge")
spawns:
  - 1 adversary agent (foreground)
  - 1 sensitivity agent (foreground, parallel with adversary)
gates:
  - Must populate worst_cases[], black_swans[], irrational_actors[] (each >= 1)
  - Must identify 3-5 load-bearing assumptions with decision boundaries
-->

# Phase: CHALLENGE (Adversary-Only Mode)

## Purpose

Stress-test a proposed action. No scope decomposition, no hypotheses, no persona
council, no iteration. Just: "here's what we're doing, tell me how it fails."

Fast red-teaming for when the decision is already made and you want the risks mapped.

## Progress Template

```
Challenge: Ground — quick search for relevant data     [pending]
Challenge: Adversary — worst cases + irrational actors  [pending]
Challenge: Sensitivity — assumptions + boundaries       [pending]
Challenge: Brief — generate Challenge Brief             [pending]
```

## Step 0.5: EXTRACT CONTEXT (if --context provided)

If the user passed `--context`, run the extraction pipeline from `scope.md`
"Context File Extraction" before grounding. Write `context-extracted.md` to the
run directory. The adversary and sensitivity agents will receive these extractions
as additional context. Claims and projections from documents become primary
stress-test targets.

## Step 1: GROUND (light)

Run 2-3 targeted web searches related to the stated action:
- "{action topic} risks failures case study"
- "{action topic} common mistakes"
- "{industry} {action type} what went wrong"

Write key findings to `~/.autodecision/runs/{slug}-challenge/ground-data.md`.
This is lighter than the full GROUND phase — just enough context for the adversary.

## Step 2: ADVERSARY

Spawn a single adversary agent (foreground). Provide:
- The stated action (from user input)
- The grounding data (from step 1)
- Context document extractions (from step 0.5, if --context was provided)

The adversary produces:

**3 worst-case scenarios** where the action fails catastrophically. For each:
- Description of compound failure
- Probability estimate
- Severity (LOW / MEDIUM / HIGH / CRITICAL)
- What triggers it

**Irrational actor analysis** for each stakeholder affected by the action:
- Rational response
- Irrational response
- Probability of irrational behavior
- Impact if irrational

**3 black swans** that would invalidate the action entirely.

**Assumption extraction:** The adversary identifies the 5-8 implicit assumptions
behind the stated action and rates each SOLID / SHAKEABLE / FRAGILE.

Write to `~/.autodecision/runs/{slug}-challenge/adversary.json`.

## Step 3: SENSITIVITY

Spawn a sensitivity agent (foreground, can run parallel with adversary if both
only need ground-data). For the top 3-5 assumptions identified by the adversary:

- What if this assumption is wrong?
- What's the decision boundary (threshold where you should stop)?
- How would you test this assumption before committing?

Write to `~/.autodecision/runs/{slug}-challenge/sensitivity.json`.

NOTE: If adversary and sensitivity can run in parallel (both only read ground-data),
spawn them simultaneously. If sensitivity needs adversary output (to know which
assumptions to vary), run sequentially.

## Step 4: CHALLENGE BRIEF

Write `~/.autodecision/runs/{slug}-challenge/CHALLENGE-BRIEF.md`:

```markdown
# Challenge Brief: {stated action}

Generated: {date} | Mode: Challenge (adversary-only)

## What You're Planning

{the stated action, restated clearly}

## Top 5 Ways This Fails

| # | Scenario | Probability | Severity | Trigger |
|---|----------|-------------|----------|---------|
| 1 | {worst case} | {P} | {sev} | {what causes it} |
| 2 | ... | ... | ... | ... |

## Assumptions That Must Hold

| Assumption | Current State | Decision Boundary | How to Test |
|-----------|--------------|-------------------|-------------|
| {what you're assuming} | {SOLID/SHAKEABLE/FRAGILE} | {when to stop} | {how to validate} |

## Irrational Actor Risks

| Actor | Rational Response | Irrational Response | P(irrational) |
|-------|------------------|---------------------|---------------|

## Black Swans

| Event | Probability | Impact |
|-------|-------------|--------|

## Bottom Line

{2-3 sentences: Is this action robust? What's the single biggest risk?
What should you do before committing?}
```

Follow the human-readable output rules from `decide.md` — no snake_case, no raw IDs.

## Step 5: OFFER PUBLISH OR EXPORT

After printing the brief, offer:

> "Share this challenge brief?"
> Options:
> A) Publish — run `/autodecision:publish` (PDF → Notion, email, gist, Slack, Drive, or local)
> B) Copy to current directory
> C) Skip

If A: invoke the publish skill with the challenge slug.
If B: `cp ~/.autodecision/runs/{slug}-challenge/CHALLENGE-BRIEF.md ./{slug}-CHALLENGE-BRIEF.md`

## Persist

Append a challenge entry to journal.jsonl:
```json
{
  "decision_id": "{slug}-challenge",
  "type": "challenge",
  "action_tested": "{stated action}",
  "timestamp": "...",
  "mode": "challenge",
  "top_risk": "{highest probability worst case}",
  "assumptions_count": N,
  "fragile_count": N
}
```
