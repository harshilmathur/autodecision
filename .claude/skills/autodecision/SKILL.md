---
name: autodecision
description: >
  Auto-Decision Engine: iterative decision simulation using autoresearch principles
  and a persona council. Decomposes decisions, generates competing hypotheses,
  simulates first/second-order effects with probabilities, critiques via anonymized
  peer review, and iterates until insights stabilize mechanically. The output is
  a possibility map — hypotheses, effects, council disagreements, adversarial
  scenarios, assumptions — with a recommendation synthesized at the end, not as
  the product.
triggers:
  - /autodecision
  - /autodecision:quick
  - /autodecision:compare
  - /autodecision:revise
  - /autodecision:challenge
  - /autodecision:summarize
  - /autodecision:publish
  - /autodecision:plan
  - /autodecision:review
  - /autodecision:export
---

# Auto-Decision Engine

Iterative decision simulation. Spend compute to think better. Five persona analysts as independent subagents, anonymized peer review, mechanical convergence — until the answer is robust.

The output is a **possibility map**: every hypothesis, every first/second-order effect, every council disagreement, every adversarial scenario, every assumption that must hold. The recommendation is one synthesis of that map, written at the end of the brief — never the product, never compressed into the lead.

## How this skill is organized

`SKILL.md` (this file) is the entry point and contract — the rules below are non-negotiable. The full loop protocol lives in `references/engine-protocol.md`; per-phase protocols live in `references/phases/*.md`; canonical structure for the brief lives in `references/brief-schema.json`. The references table at the bottom is the single source of truth for where to read each thing.

## Command Routing

`triggers:` (frontmatter above) is the canonical list. Each routes to a per-command protocol file:

- `/autodecision <decision>` (default 2 iterations) → execute `references/engine-protocol.md` end-to-end
- `/autodecision --iterations N <decision>` → 1 = medium (council, no convergence), 2 = full default, 3-5 = deep
- `/autodecision:quick <decision>` → `references/engine-protocol.md` "Quick Mode Protocol" section
- `/autodecision:compare "A" vs "B"` → quick mode on both, then side-by-side comparison
- `/autodecision:revise {slug} "{change}"` → `references/phases/revise.md`
- `/autodecision:challenge "{action}"` → `references/phases/challenge.md` (adversary-only, ~5 min)
- `/autodecision:summarize {slug}` → compress an existing brief to one page
- `/autodecision:publish {slug} [--summary]` → `references/phases/publish.md`
- `/autodecision:plan` → Phase 0 (SCOPE) interactive only
- `/autodecision:review` → read past runs, compare predictions vs outcomes
- `/autodecision:export` → bundle journal + assumptions + briefs into portable archive

## Non-Negotiable Rules

1. **NEVER simulate in a vacuum.** Phase 1 (GROUND) is mandatory. If WebSearch yields nothing, mark the run UNGROUNDED in the brief header — do not proceed silently.
2. **Phase 1.5 (ELICIT) runs after GROUND, before the loop**, unless `--skip-elicit`. The single biggest quality lever — never default-off.
3. **Each persona runs as a SEPARATE Agent subagent.** Genuine context-window independence. Sequential authoring in one context destroys diversity. Non-negotiable.
4. **The main conversation IS the orchestrator.** Walk the phases yourself. Spawn agents for parallelizable tasks (5 personas, critique + adversary). NEVER spawn one agent to "run the loop" — that agent can't spawn grandchildren and the council collapses. See `engine-protocol.md` "Orchestration Model."
5. **The 5 canonical personas are the default.** Optimist, Pessimist, Competitor, Regulator, Customer. ELICIT may modify (rename, specify a competitor), add (e.g., "Investor" for fundraising), or remove (e.g., Regulator when irrelevant) personas. Custom personas follow the same structure: optimization objective, blind spot, contrarian question, no-hedging rule. Names defined in `references/persona-council.md` "Canonical Persona Names."
6. **Every effect carries a stable `effect_id`, a probability, a `probability_range`, and explicit assumption keys.** The Judge compares by ID across iterations — descriptions drift, IDs don't. No implicit assumptions. **Assumption keys are as stable as effect_ids**: iteration 2+ personas receive the full `all_assumptions` map from iter-1's `effects-chains.json` and MUST reuse keys verbatim for conceptually-identical assumptions. Renaming `market_has_demand` to `market_demand_exists` between iterations fakes instability and breaks the Judge's `assumption_stability` metric. See `phases/simulate.md` "Assumption Key Stability."
7. **Persona disagreement IS the uncertainty signal.** The probability range is the data — never average it away.
8. **Generate 2nd-order effects for ALL 1st-order effects.** No probability gate. Tail risks matter most.
9. **Anonymize during peer review.** Personas review "Analysis A", "Analysis B" — never by name. Mapping randomized per iteration.
10. **The Decision Brief is for humans.** Never emit `snake_case`, never backtick raw `effect_id`s in prose. Use the `description` field. See `references/phases/decide.md`.
11. **Phase 8.5 (VALIDATE-BRIEF) is mandatory** for full/medium/revise/quick. It means literally invoking `scripts/validate-brief.py` against the schema. Writing a custom inline Python validation script (checking for your own invented section headers, declaring "13/13 passed" against a list you authored) IS NOT Phase 8.5. It is self-certification. Self-certification against invented headers is a HARD protocol violation — it silently lets a structurally broken brief ship. If the named script cannot run (e.g., `python3` missing), fall back to the Step 5.5 self-check in `phases/decide.md` and emit the structural-self-check footer. Do NOT roll your own validator. On HARD_FAIL, re-prompt DECIDE once; if still failing, prepend `VALIDATION_FAILED` and continue. See `references/phases/validate-brief.md`.

    **Writer must not invent section headers.** The brief's H2 structure is defined by `references/brief-schema.json` and is MANDATORY. Inventing headers like `## Context`, `## Decision tilt`, `## The possibility map`, `## Methodology`, `## Analysis Approach` (any header not in the schema) is a HARD_FAIL, even if it reads well. Improving readability is the schema's job, not the writer's. Do Step 4a's pre-write checklist before composing a single line.
12. **Stop when the Judge says so.** Max iterations configurable (default 2, up to 5). The iteration folders ARE the memory — read previous iteration's `convergence-summary.md` (≤500 tokens) before starting the next, never the full JSON.
13. **Subagent nesting.** If `/autodecision` runs inside another agent, the Agent tool may be unavailable. STOP and ask the user (full protocol in `engine-protocol.md`). Never silently degrade.

## References

Read on-demand as each phase begins. Each phase file opens with a self-describing metadata block (phase number, when it runs, what it reads, what it writes, what gates it has) — always read that block first.

| Reference | File |
|-----------|------|
| Full loop protocol | `references/engine-protocol.md` |
| Progress tracker templates (per mode) | `references/progress-templates.md` |
| Persona definitions + canonical names + subagent protocol | `references/persona-council.md` |
| Shared persona prompt preamble | `references/persona-preamble.md` |
| Effects chain JSON spec | `references/effects-chain-spec.md` |
| Phase 0: Scope | `references/phases/scope.md` |
| Phase 1: Ground | `references/phases/ground.md` |
| Phase 1.5: Elicit | `references/phases/elicit.md` |
| Phase 2: Hypothesize | `references/phases/hypothesize.md` |
| Phase 3: Simulate | `references/phases/simulate.md` |
| Phase 4: Critique | `references/phases/critique.md` |
| Phase 5: Adversary | `references/phases/adversary.md` |
| Phase 6: Sensitivity | `references/phases/sensitivity.md` |
| Phase 7: Converge | `references/phases/converge.md` |
| Phase 8: Decide | `references/phases/decide.md` |
| Phase 8.5: Validate Brief | `references/phases/validate-brief.md` |
| Revise protocol | `references/phases/revise.md` |
| Challenge protocol | `references/phases/challenge.md` |
| Publish protocol | `references/phases/publish.md` |
| Output validation rules (canonical) | `references/validation.md` |
| Decision Brief template (human view) | `references/output-format.md` |
| Decision Brief schema (canonical structure) | `references/brief-schema.json` |
| Decision journal spec | `references/journal-spec.md` |
| Assumption library spec | `references/assumption-library-spec.md` |
| Templates | `references/templates/{pricing,expansion,build-vs-buy,hiring}.md` |

If anything in this file conflicts with `references/engine-protocol.md`, the protocol file wins — it is canonical for loop mechanics. This file is the entry-point contract; the protocol file is the manual.
