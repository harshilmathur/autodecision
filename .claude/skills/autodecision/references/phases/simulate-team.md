<!--
phase: 3
phase_name: SIMULATE (team-mode variant)
runs_in:
  - full.team.iteration-1    (5-teammate council via Agent Teams)
  - full.team.iteration-2+   (LIGHT mode — teammates persist, re-simulate only)
  - medium.team.iteration-1  (5-teammate council, single iteration)
  - NOT in non-team modes    (use phases/simulate.md instead)
  - NOT in quick mode        (quick has no council)
reads:
  - ~/.autodecision/runs/{slug}/shared-context.md (precomputed by orchestrator, enriched by CLARIFY)
  - ~/.autodecision/runs/{slug}/iteration-{N}/hypotheses.json
  - ~/.autodecision/runs/{slug}/iteration-{N}/clarify-answers.json (if CLARIFY ran)
  - agents/{short-tag}.md (teammate definition; loaded at spawn by Agent Teams framework)
writes:
  - ~/.autodecision/runs/{slug}/iteration-{N}/council/{short-tag}.json × 5 (tags from persona-council.md Canonical Persona Names)
  - ~/.autodecision/runs/{slug}/iteration-{N}/effects-chains.json (synthesis output — written inline by orchestrator)
spawns:
  - 5 teammates via Agent Teams (on iteration 1) OR reuses persistent teammates (iteration 2+)
  - Synthesis runs INLINE in orchestrator (NEVER as a teammate or subagent)
gates:
  - diversity_check: avg probability spread across shared effects > 0.10 (else "Council diversity LOW" warning)
  - depth_check: at least 3 first-order effects per persona per hypothesis
  - children_check: every 1st-order effect has ≥1 second-order child
  - alt_check: at least 3 effects with `alt_` prefix across all 5 personas
-->

# Phase 3: SIMULATE (team mode)

## Pre-SIMULATE Structural Gate — CLARIFY must have run (MUST RUN FIRST)

Before posting any simulation tasks, the orchestrator MUST verify that Phase 2.5 CLARIFY either ran or was explicitly skipped. The check:

1. Read `~/.autodecision/runs/{slug}/config.json`. Note the value of `skip_clarify`.
2. Check whether `~/.autodecision/runs/{slug}/iteration-{N}/clarify-questions.json` exists.
3. **If the file is missing AND `skip_clarify` is not `true`:** STOP. Do NOT post simulation tasks yet. Load `phases/clarify-team.md` and run Phase 2.5 CLARIFY now. Only proceed to the rest of this file after `clarify-questions.json` and `clarify-answers.json` have been written.
4. **If the file exists OR `skip_clarify` is `true`:** proceed.

Why this gate exists: CLARIFY is a new phase insertion between HYPOTHESIZE and SIMULATE. The default orchestrator mental model is "Phase 2 → Phase 3" and tends to skip over Phase 2.5. Without this structural gate, teammates simulate on fabricated assumptions about the user's business — which is the specific failure mode team mode was built to fix. A team-mode run that skips CLARIFY loses the primary value proposition of team mode over standard subagent mode.

The lead MUST pause here, verify the CLARIFY artifacts, and route to `clarify-team.md` if they are missing. Treat this as a hard gate, not a recommendation.

## Purpose

Each persona independently simulates the effects of each hypothesis, producing structured effects chains in the canonical JSON schema. **The file contract is identical to the non-team variant.** Downstream phases (CRITIQUE, CONVERGE, DECIDE) do not know whether the files were written by subagents or teammates.

This file documents only the differences from the non-team `phases/simulate.md`. Steps 2, 3, 3.5, 3.6, and 3.7 (synthesis, cross-order dedup, assumption drift check) are unchanged and are reused from `simulate.md`.

## Prerequisite check

Before proceeding, confirm the team is alive. If the team was not yet spawned (e.g., iteration 1 starting), the lead creates it now using the subagent definitions in `claude-plugin/agents/*.md`. Per Agent Teams docs:

> When spawning a teammate, you can reference a subagent type from any subagent scope: project, user, plugin, or CLI-defined. The teammate honors that definition's tools allowlist and model, and the definition's body is appended to the teammate's system prompt as additional instructions rather than replacing it.

Spawn 5 teammates with short-tag names: `optimist`, `pessimist`, `competitor`, `regulator`, `customer`. Use the lead's permission mode for all teammates (Agent Teams does not support per-teammate modes at spawn time).

## Process

### Step 1 (team-mode variant): Post simulation tasks to the shared task list

Instead of the non-team "Spawn 5 Persona Subagents (PARALLEL)" step, the lead posts 5 tasks to the shared task list:

| Task | Assignee | Deliverable |
|------|----------|-------------|
| `simulate_optimist_iter_{N}`   | optimist   | `iteration-{N}/council/optimist.json`   |
| `simulate_pessimist_iter_{N}`  | pessimist  | `iteration-{N}/council/pessimist.json`  |
| `simulate_competitor_iter_{N}` | competitor | `iteration-{N}/council/competitor.json` |
| `simulate_regulator_iter_{N}`  | regulator  | `iteration-{N}/council/regulator.json`  |
| `simulate_customer_iter_{N}`   | customer   | `iteration-{N}/council/customer.json`   |

Each task description reads:

> Generate effects chains for iteration {N}. Read `shared-context.md` (including any `USER-PROVIDED CONTEXT (from CLARIFY)` blocks) and `iteration-{N}/hypotheses.json`. Produce output at the deliverable path. Follow the schema in `shared-context.md` (sourced from `references/effects-chain-spec.md`) exactly — strict JSON only, no prose wrappers. Notify the lead via SendMessage when the file is written.

Teammates self-claim their task using file-locked claim (Agent Teams handles this mechanically). A teammate should only claim its own named task (optimist claims `simulate_optimist_iter_{N}`, etc.).

### Step 2 (team-mode): Wait for completion

Wait for all 5 teammates to write their `council/{short-tag}.json` files. The lead should receive SendMessage completion notices; verify by listing `iteration-{N}/council/`.

Failure handling is identical to the non-team variant:
- 5/5 complete: proceed to synthesis.
- 3–4/5 complete: proceed with available data; note missing personas in the synthesis and brief.
- <3/5 complete: critical error; skip to Phase 8 with available data.

Additionally, team mode supports **direct user correction mid-run**: if the user `Shift+Down`-messages a teammate with a correction ("Pessimist, our churn is 8% not 20%"), the teammate may update its `council/{short-tag}.json` before marking the task complete. This is expected and desirable. Treat the last-written file as canonical.

### Steps 3, 3.5, 3.6, 3.7: Unchanged

Steps 3 (synthesis), 3.5 (cross-order dedup), 3.6 (finalize), and 3.7 (post-synthesis assumption drift check) run **inline in the orchestrator**, exactly as specified in `phases/simulate.md`. There is no team-mode variant for these steps. The orchestrator reads the 5 JSON files written by teammates, performs the merges, and writes `effects-chains.json`.

**Do not spawn a teammate or subagent to do synthesis.** It is a mechanical merge operation on JSON files. Delegation adds latency and risks schema drift.

## Cross-iteration behavior (team mode only)

In non-team mode, iteration 2+ respawns fresh subagents with updated `shared-context.md`. In team mode, **teammates persist across iterations** and retain their conversation history. This is a feature, not an accident — it makes effect_id and assumption-key stability natural instead of prompt-enforced.

Protocol for iteration 2+:

1. The lead does NOT respawn teammates.
2. After Phase 7 CONVERGE writes `iteration-{N-1}/convergence-summary.md`, the lead broadcasts to all 5 teammates:

   > **Iteration {N} starting.** Convergence was not reached. Summary of iteration {N-1}: {paste convergence-summary.md contents — ~500 tokens}. Your task is `simulate_{persona}_iter_{N}`, assigned in the task list.
   >
   > **Reuse rules (critical for the Judge):**
   > - Reuse prior `effect_id` values verbatim for conceptually identical effects.
   > - Reuse prior assumption keys verbatim for conceptually identical assumptions.
   > - Only create new IDs or keys for content genuinely not covered by your iter-{N-1} analysis.
   > - Do NOT rename for stylistic preference. That fakes instability.
3. Teammates self-claim their iter-{N} tasks and write new files at `iteration-{N}/council/{short-tag}.json`.
4. Because teammates have persistent context, they already know their prior IDs and keys — no need to re-inject them via `shared-context.md` (though the orchestrator should still append the `all_assumptions` block for safety).

## Quality gates

The four gates from the standard `simulate.md` (diversity, depth, children, alternatives) run unchanged after synthesis. They read from the council files and `effects-chains.json`, both of which have the same schema in team and non-team modes.

**Team-mode-specific observation:** diversity metrics can look artificially LOW if teammates messaged each other during Phase 3 and converged on shared phrasing. Team mode is meant to debate in Phase 4 (CRITIQUE), not Phase 3 — discourage inter-teammate messaging during simulation by including in each teammate's spawn prompt:

> During Phase 3, do NOT message other teammates to compare analyses. Your independence is the council's value. Reserve debate for Phase 4 CRITIQUE, where the lead will post review tasks.

## Post-run teammate state

After Phase 3 completes, teammates remain alive and idle until the lead posts the next phase's tasks (Phase 4 CRITIQUE review tasks). The user can `Shift+Down` to any teammate during the idle window to ask follow-up questions about their analysis — these conversations do not affect `council/{short-tag}.json` unless the user explicitly tells the teammate to rewrite it.

## Non-team fallback behavior

If the lead detects that Agent Teams is not available at Phase 3 start (env var unset, Claude Code too old, etc.), it falls back to `phases/simulate.md` and spawns 5 subagents via the Agent tool instead. This fallback is decided at Phase 0 SCOPE and recorded in `config.json` as `"team_mode": false, "team_fallback_reason": "..."`. Do not re-check at Phase 3 — the decision is made once at run start.
