---
description: Quick single-pass decision analysis — no council, no iteration, ~2 min
agent: build
---

# /autodecision-quick

Fast single-pass mode. SCOPE → GROUND → SIMULATE (single analyst) → DECIDE. No personas, no peer review, no iteration. ~2 minutes.

Run on: $ARGUMENTS

## Bootstrap

Read via the `read` tool:

1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md` — OpenCode overrides (tool name map, websearch caveat)
3. `.claude/skills/autodecision/references/engine-protocol.md` — follow the **Quick Mode Protocol** section

Then invoke the `skill` tool with `name: "autodecision"` to confirm the skill loaded.

## Execute

Initialize `todowrite` with the quick-mode template from `references/progress-templates.md`. Then run:

1. **Phase 0 SCOPE** — `references/phases/scope.md`. Decompose the decision into 2–3 sub-questions. Write `config.json` to `~/.autodecision/runs/{slug}-quick/`.

2. **Phase 1 GROUND** — `references/phases/ground.md`. One round of `websearch` (or `webfetch` fallback) — cap 3–4 queries total. Write `ground-data.md`. Mark `UNGROUNDED` in the header if web access failed (after confirming with the user).

3. **Phase 3 SIMULATE (single analyst, quick mode)** — YOU do this inline, not via a subagent. One pass: generate 3–5 first-order effects with probabilities and assumptions, each with at least one 2nd-order child. Write `iteration-1/effects-chains.json` with `"persona": "quick-analyst"` and a simplified schema (see Quick Mode Protocol).

4. **Phase 8 DECIDE** — use the **Quick Brief Template** from `references/output-format.md`. Write `DECISION-BRIEF.md` to the run directory. Quick mode skips Convergence Log, skips most Appendices, keeps Executive Summary / Data Foundation / Effects Map / Key Assumptions / Recommendation / Sources.

5. **Phase 8.5 VALIDATE-BRIEF** — same as full mode, with `--mode quick`. Do NOT author inline Python.

6. **Persist** — append `type: "decision"` entry to `~/.autodecision/journal.jsonl` marked `mode: "quick"`.

7. Print the brief to the conversation. Offer: `"Want to run the full loop on this? /autodecision \"{decision}\"."`

## When to Use

- Quick sanity checks before committing to the full loop
- Trivial or low-stakes decisions
- When the user wants structure without the 15-min full council

## Not to Use For

- High-stakes decisions (run `/autodecision` instead)
- Decisions where disagreement between viewpoints would matter (full loop's 5-persona council is the point)
