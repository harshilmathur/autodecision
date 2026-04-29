---
description: Run the full Auto-Decision Engine loop — 10 phases, 5-persona council, iterative convergence
agent: build
---

# /autodecision — Full Loop Orchestrator

Run the full Auto-Decision Engine on: $ARGUMENTS

## ⚠️ MUST RUN AS PRIMARY, NOT AS SUBAGENT

This command runs the 10-phase loop AND spawns 5+ parallel subagents via `task`. It MUST execute as the primary (main) conversation.

Before proceeding, verify:
1. You are NOT running as a subagent. If the `task` tool is unavailable, STOP and ask the user: run `/autodecision-quick` instead, degrade to single-analyst sequential mode, or abort.
2. This command's frontmatter does NOT set `subtask: true`. (If it somehow does, stop and fix it — the orchestrator must be primary.)

## Inputs and Flag Parsing

Parse `$ARGUMENTS` for these flags:
- `--iterations N` — 1 = medium (council, no convergence), 2 = full default, 3–5 = deep (confirm with user before 3+)
- `--template NAME` — one of: `pricing`, `expansion`, `build-vs-buy`, `hiring` (pre-populate sub-questions)
- `--context FILE1 [FILE2 ...]` — attach context documents (extracted and tagged `[D#]`)
- `--skip-elicit` — skip Phase 1.5 user review
- Everything else: the decision statement

If `$ARGUMENTS` is empty or ambiguous, use the `question` tool to ask for the decision statement before doing anything else.

## Bootstrap

Before touching any phase, read these three files via the `read` tool:

1. `.claude/skills/autodecision/SKILL.md` — the contract
2. `.opencode/host-adapter.md` — OpenCode-specific overrides (tool name map: `Agent` → `task`, subagent names, websearch caveat, forbidden `subtask: true` on orchestrator)
3. `.claude/skills/autodecision/references/engine-protocol.md` — THE loop protocol. Not "on-demand" — this is the second file you read.

Then invoke the `skill` tool with `name: "autodecision"` to confirm the skill loaded cleanly. If any of these reads fail, stop and tell the user how to install the skill (see OPENCODE.md).

## Execute the Loop

Initialize the progress tracker via `todowrite` using the full-loop template from `references/progress-templates.md`. Then walk the 10 phases yourself, in THIS conversation:

**Phase 0 SCOPE** — `references/phases/scope.md`. Input quality gate; context file extraction if `--context`; template hydration if `--template`; write `config.json` to `~/.autodecision/runs/{slug}/`.

**Phase 1 GROUND** — `references/phases/ground.md`. Mandatory web search (use `websearch`; fall back to `webfetch` against a search URL if `websearch` unavailable — see host-adapter.md §5). Write `ground-data.md`.

**Phase 1.5 ELICIT** (skip if `--skip-elicit`) — `references/phases/elicit.md`. Adaptive 5-block review via the `question` tool. Write `user-inputs.md`.

**Phase 2 HYPOTHESIZE** — `references/phases/hypothesize.md`. Generate 3–5 competing hypotheses along diverse axes, seed expected effect IDs. Write `iteration-1/hypotheses.json`.

**Phase 3 SIMULATE** — `references/phases/simulate.md`. Write `shared-context.md` to the run directory. Then spawn 5 persona agents **in parallel** using `task` tool calls in a single message. Agent names (pre-declared in `.opencode/agents/`): `ad-optimist`, `ad-pessimist`, `ad-competitor`, `ad-regulator`, `ad-customer`. Each persona reads `shared-context.md` and writes to `iteration-{N}/council/{persona}.json`. YOU spawn them directly — do NOT delegate to a sub-orchestrator. After all 5 complete, synthesize inline (mechanical merge + semantic dedup + assumption map) and write `iteration-{N}/effects-chains.json`.

**Phase 4 CRITIQUE** + **Phase 5 ADVERSARY** — in parallel (one message, two `task` calls):
- `task(agent: "ad-critique", prompt: "...run directory...iteration number...")`
- `task(agent: "ad-adversary", prompt: "...run directory...iteration number...")`

**Phase 6 SENSITIVITY** — `task(agent: "ad-sensitivity", prompt: "...")`. May run concurrently with the inline Judge.

**Phase 7 CONVERGE** — `references/phases/converge.md`. **Inline** — ~5 seconds, set operations on JSON. Do NOT spawn an agent. Compute 4 parameters (effects delta, assumption stability, ranking flips, contradictions). Write `judge-score.json` and `convergence-summary.md`. Update `convergence-log.json`.

If not converged AND iterations remaining: loop back to Phase 3 in LIGHT mode (re-simulate + re-judge only; carry critique/adversary/sensitivity forward unless convergence explicitly failed). At max iterations with NOT REACHED, **offer to extend** via the `question` tool (cap 5) — never silently exit to Phase 8.

**Phase 8 DECIDE** — `references/phases/decide.md`. Write the Decision Brief. You may compose it inline (default) or spawn `ad-decide` if the orchestrator context is near-full. Either way: open `brief-schema.json` first, enumerate required headers, compose against the checklist.

**Phase 8.5 VALIDATE-BRIEF** — MANDATORY. Via `bash`:

```
python3 "$(find .claude ~/.claude ~/.config/opencode .opencode -name validate-brief.py -path '*/autodecision/*' 2>/dev/null | head -1)" --run-dir ~/.autodecision/runs/{slug} --schema "$(find .claude ~/.claude ~/.config/opencode .opencode -name brief-schema.json -path '*/autodecision/*' 2>/dev/null | head -1)" --mode "{mode}"
```

Exit 0 → continue. Exit 1 → append warning footer to brief. Exit 2 → re-prompt Phase 8 once. Exit 3 → log and continue. If `python3` unavailable, run the fallback self-check from `phases/decide.md` Step 5.5. Do NOT author inline Python validators. Do NOT self-certify.

## Phase 8 + 8.5 — the two rules that keep getting broken

**Rule A — Schema is the structure. You don't get to invent headers.**

Open `brief-schema.json` before writing a single line. Enumerate every required header for the active mode. Compose against the checklist. Forbidden: inventing sections (`## Context`, `## Methodology`, `## Bottom Line`, `## Adversary Findings`, etc.). Forbidden: collapsing the 7-field Recommendation block into prose. Full protocol: `references/phases/decide.md` Step 4a.

**Rule B — Phase 8.5 means running the named script. No substitutes.**

Writing an inline Python script in a bash heredoc that checks for your own invented headers and declares "N/N passed" is self-certification, not validation. Don't do it. If `python3` is missing, use the Step 5.5 fallback — do NOT roll your own validator.

## Persistence (Phase 8, Step 5)

After the brief validates, append a journal entry to `~/.autodecision/journal.jsonl` per `references/journal-spec.md` and update `~/.autodecision/assumptions.jsonl` per `references/assumption-library-spec.md`. Then offer publish: `"Share this? Run /autodecision-publish {slug}."`

## Reminders

- Update `todowrite` at EVERY phase transition. One `in_progress` at a time.
- Each persona runs as a SEPARATE subagent — genuine context-window independence is non-negotiable.
- Persona disagreement IS the uncertainty signal — never average it away. The `probability_range` is the data.
- Every effect carries a stable `effect_id`, probability, range, and explicit assumption keys. The Judge compares by ID across iterations — descriptions drift, IDs don't.
- The brief is for humans. No `snake_case` in prose. No backticked IDs in prose.
- The full loop takes ~15–20 min and 20+ LLM calls. If the decision seems trivial, confirm with the user before starting.
