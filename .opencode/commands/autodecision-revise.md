---
description: Revise a previous decision with changed assumptions, new hypotheses, or new data
agent: build
---

# /autodecision-revise

Revise a previous decision run: $ARGUMENTS

## Usage

```
/autodecision-revise {slug} "{what changed}"
```

Examples:
```
/autodecision-revise pricing-cut-20pct-full "What if acquisition only increases 10% instead of 30%?"
/autodecision-revise pricing-cut-20pct-full "Add a hypothesis: offer a freemium tier instead of cutting prices"
/autodecision-revise market-expansion-full "Assume the regulatory timeline is 6 months, not 18"
/autodecision-revise market-expansion-full "New data: a competitor just entered the same market"
```

## ⚠️ Runs as primary, spawns subagents

Like `/autodecision`, this command MUST run in the primary session. It spawns the persona council for a fresh iteration. If `task` is unavailable, STOP and ask the user.

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md` — OpenCode overrides (agent names, tool map)
3. `.claude/skills/autodecision/references/phases/revise.md` — the 7-step protocol

Then invoke the `skill` tool with `name: "autodecision"`.

## Execute the 7 Steps

Initialize `todowrite` with the revise-mode template from `references/progress-templates.md`. Then follow `phases/revise.md` exactly:

1. **LOAD** — parse `{slug}` from `$ARGUMENTS`. Read `~/.autodecision/runs/{slug}/config.json`, `DECISION-BRIEF.md`, and the latest iteration's `effects-chains.json`. If slug not found, `glob` `~/.autodecision/runs/*/` and offer a pick-list via `question`.

2. **PARSE** — parse the "{what changed}" text. Classify: assumption change / new hypothesis / new data / tilt change.

3. **CONFIRM** — use `question` to confirm the parsed change with the user (4-option structured prompt per `phases/revise.md`).

4. **PREPARE** — create `~/.autodecision/runs/{slug}-revise-{N}/` (auto-increment N). Copy relevant artifacts from the parent run as starting context. Write a new `shared-context.md` with the change injected.

5. **EXECUTE** — re-run from the earliest-affected phase. Spawn persona subagents per host-adapter.md §2: `ad-optimist`, `ad-pessimist`, `ad-competitor`, `ad-regulator`, `ad-customer` — parallel, one message. Then `ad-critique` + `ad-adversary` in parallel. Then `ad-sensitivity`. Inline Judge for Phase 7.

6. **OUTPUT** — write TWO files:
   - `~/.autodecision/runs/{slug}-revise-{N}/DECISION-BRIEF.md` (standalone brief, full 16-section schema, Phase 8.5 validated)
   - `~/.autodecision/runs/{slug}-revise-{N}/REVISION-DIFF.md` (what changed vs the parent: effects added/removed, probability shifts > 0.1, recommendation delta, assumption fragility changes)

7. **PERSIST** — append a `type: "revision"` entry to `~/.autodecision/journal.jsonl` referencing the parent `decision_id`. Update `assumptions.jsonl` if the change invalidated or confirmed any tracked assumptions.

## Reminders

- Run Phase 8.5 (validate-brief.py) on the new brief, same as a full run.
- If the change is small enough that no upstream phase is affected (e.g., just a re-tilt), you may skip the council re-run and go straight to Phase 8 — but this is the exception. Confirm with the user in Step 3.
- `todowrite` updates at every step transition.
