---
description: Stress-test a proposed action — adversary-only mode, no full loop (~5 min)
agent: build
---

# /autodecision-challenge

Stress-test a proposed action without running the full decision loop. Straight to adversary + sensitivity analysis. ~5 minutes.

Run on: $ARGUMENTS

## Examples

```
/autodecision-challenge "We're cutting pricing by 30% across all plans next month"
/autodecision-challenge "We're acquiring a competitor at $500M to enter a new vertical"
/autodecision-challenge "We're hiring 50 engineers over the next quarter"
```

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md` — OpenCode overrides (`Agent` → `task`, websearch caveat)
3. `.claude/skills/autodecision/references/phases/challenge.md` — the challenge protocol

Then invoke the `skill` tool with `name: "autodecision"`.

## Execute

Initialize `todowrite` with the challenge-mode template from `references/progress-templates.md`.

Follow `phases/challenge.md`:

1. **Phase 0 light** — parse the proposed action; extract assumptions the action implies. Write `config.json` to `~/.autodecision/runs/{slug}-challenge/`.

2. **Phase 1 light GROUND** — one round of `websearch` (fallback: `webfetch`) specifically for historical precedents of similar actions. Write `ground-data.md`.

3. **Phase 5 ADVERSARY** — `task(agent: "ad-adversary", prompt: "...")`. Reads the implicit effects of the action; writes `worst_cases`, `irrational_actors`, `black_swans`, `assumption_stress_test` to `iteration-1/adversary.json`.

4. **Phase 6 SENSITIVITY** — `task(agent: "ad-sensitivity", prompt: "...")`. Top 3–5 assumptions, sensitivity ratings, decision boundaries. Writes `iteration-1/sensitivity.json`.

5. **Write Challenge Brief** — NOT a full Decision Brief. Write `~/.autodecision/runs/{slug}-challenge/CHALLENGE-BRIEF.md` with this structure (per `phases/challenge.md`):

```markdown
# Challenge Brief: {Proposed Action}

Generated: {date}

## Executive Summary

**Proposed Action:** ...
**Overall Verdict:** PROCEED / PROCEED WITH CAUTION / RECONSIDER
**Dominant Risk:** ...
**Decision Boundary:** ...

## Implicit Assumptions

Assumptions the action requires to be true:
- ...

## Worst-Case Scenarios
(from adversary.json — wc prefix)

| ID | Scenario | Severity | Probability |
|----|----------|----------|-------------|
| wc1_... | ... | HIGH | 0.15 |

## Irrational Actor Risks
(from adversary.json — ia prefix)

| Actor | Rational Response | Irrational Response | P(irrational) |
|-------|-------------------|---------------------|---------------|
| ... | ... | ... | 0.20 |

## Black Swan Invalidators
(from adversary.json — bs prefix)

| Event | Probability | Invalidates |
|-------|-------------|-------------|
| ... | 0.10 | ... |

## Assumption Stress Test

| Assumption | Fragility | Disproof Evidence |
|-----------|-----------|-------------------|
| ... | FRAGILE | ... |

## Decision Boundaries
(from sensitivity.json — HIGH-sensitivity assumptions with numeric thresholds)

- If X < N, stop.
- If Y > N, escalate.

## Recommendation

**Verdict:** PROCEED / PROCEED WITH CAUTION / RECONSIDER
**Confidence:** HIGH / MEDIUM / LOW
**Conditions:** What must be true to proceed safely.
**Monitor:** What signals would change the verdict.
**Pre-mortem:** If this action fails, the most likely cause is...

## Sources

| Tag | Type | Claim | Source |
|-----|------|-------|--------|
| [G1] | Web | ... | ... |
```

6. **Phase 8.5 validate (lightweight)** — since this is not a Decision Brief, the full `validate-brief.py` is not applicable. Do a self-check: every header above is present, every scenario_id used has a matching entry in `adversary.json`, every decision boundary is specific (numeric or named event).

7. **Persist** — append `type: "challenge"` entry to `~/.autodecision/journal.jsonl` per `journal-spec.md`.

## Reminders

- This is NOT a full loop. No 5-persona council. No iteration. No convergence.
- Spawn only `ad-adversary` and `ad-sensitivity` — that's it.
- If the user wants a complete analysis of the action, tell them to run `/autodecision` on the question form (e.g., "Should we cut pricing by 30%?") instead.
