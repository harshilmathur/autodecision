# Engine Protocol: The Auto-Decision Loop

This is the master protocol. Every phase references this file for the overall loop
structure, sequencing rules, and convergence logic.

## Progress Tracking (Mandatory)

Use the TodoWrite tool to show the user a live progress tracker throughout the run.
This is NOT optional — the loop has many steps and the user needs to see where things
stand. Update the todo list at EVERY phase transition.

### Full Loop Progress Template

Initialize this at the start of every full loop run:

```
Phase 0: Scope — decompose decision              [pending]
Phase 1: Ground — web search for data             [pending]
Phase 1.5: Elicit — review with user              [pending]
Phase 2: Hypothesize — generate competing paths   [pending]
Phase 3: Simulate — 5 persona council (parallel)  [pending]
Phase 3b: Synthesis — merge persona outputs       [pending]
Phase 4+5: Critique + Adversary (parallel)        [pending]
Phase 6: Sensitivity — find decision boundaries   [pending]
Phase 7: Converge — judge stability               [pending]
Iteration 2: Refine — light-mode re-simulation    [pending]
Phase 8: Decide — generate Decision Brief         [pending]
Persist — journal + assumption library            [pending]
```

Mark each item `in_progress` when you START it and `completed` when you FINISH it.
Only ONE item should be `in_progress` at a time. The user sees a live checklist
that tells them exactly where the analysis stands.

### Quick Mode Progress Template

```
Phase 0: Scope — decompose decision              [pending]
Phase 1: Ground — web search for data             [pending]
Phase 3: Simulate — single-pass analysis          [pending]
Phase 8: Decide — generate Quick Brief            [pending]
```

### Medium Mode Progress Template (--iterations 1)

```
Phase 0: Scope — decompose decision              [pending]
Phase 1: Ground — web search for data             [pending]
Phase 1.5: Elicit — review with user              [pending]
Phase 2: Hypothesize — generate competing paths   [pending]
Phase 3: Simulate — 5 persona council (parallel)  [pending]
Phase 3b: Synthesis — merge persona outputs       [pending]
Phase 4+5: Critique + Adversary (parallel)        [pending]
Phase 6: Sensitivity — find decision boundaries   [pending]
Phase 8: Decide — generate Decision Brief         [pending]
Persist — journal + assumption library            [pending]
```

## Prerequisites

Before starting any decision run:

1. Create the run directory:
```bash
mkdir -p ~/.autodecision/runs/{decision-slug}
```
Derive `{decision-slug}` from the decision statement (lowercase, hyphens, max 40 chars).

2. If `~/.autodecision/` does not exist, create it:
```bash
mkdir -p ~/.autodecision/runs
```

## Iteration Modes

The loop supports configurable iteration count:

```
/autodecision "decision"                    # Default: 2 iterations (full mode)
/autodecision --iterations 1 "decision"     # Medium mode: council + 1 pass, no convergence
/autodecision --iterations 3 "decision"     # Deep mode: up to 3 iterations
/autodecision --iterations 5 "decision"     # Maximum: 5 iterations for high-stakes decisions
/autodecision:quick "decision"              # Quick: no council, no iterations
```

| Mode | Council | Iterations | Convergence | Use When |
|------|---------|------------|-------------|----------|
| Quick | No | 0 | No | Sanity check, low-stakes |
| Medium (--iterations 1) | Yes | 1 | No (baseline only) | Want persona diversity without the iteration overhead |
| Full (default, --iterations 2) | Yes | 2 | Yes | Most decisions. Good balance of depth vs speed. |
| Deep (--iterations 3-5) | Yes | 3-5 | Yes | High-stakes, high-uncertainty decisions |

Default is 2 iterations. Iteration 1 is always FULL (all phases). Iteration 2+ is LIGHT
(simulate + converge only) unless convergence fails, in which case it escalates to FULL.

For `--iterations 1` (medium mode): run all phases 0-6 once, skip Phase 7 (CONVERGE),
go directly to Phase 8 (DECIDE). The brief notes "1 iteration, no convergence check."

## The Loop

```
OUTER (runs once):
  Phase 0: SCOPE ──────────────→ config.json
  Phase 1: GROUND ─────────────→ ground-data.md
  Phase 1.5: ELICIT ───────────→ user-inputs.md (review assumptions, personas, data with user)
                                  (ELICIT runs AFTER GROUND because it shows grounding data to user)

INNER (max {iterations} times, default 2):
  Phase 2: HYPOTHESIZE ────────→ iteration-{N}/hypotheses.json
  Phase 3: SIMULATE ───────────→ iteration-{N}/council/*.json
                                  iteration-{N}/effects-chains.json
  Phase 4: CRITIQUE ───────────→ iteration-{N}/peer-review.json
                                  iteration-{N}/critique.json
  Phase 5: ADVERSARY ──────────→ iteration-{N}/adversary.json
  Phase 6: SENSITIVITY ────────→ iteration-{N}/sensitivity.json
  Phase 7: CONVERGE ───────────→ iteration-{N}/judge-score.json
                                  convergence-log.json (append)
         │
         ├── converged? → yes → exit inner loop
         ├── not converged AND iteration < max → loop back to Phase 2
         └── iterations = 1 (medium mode)? → skip Phase 7, go to Phase 8

OUTER (runs once):
  Phase 8: DECIDE ─────────────→ DECISION-BRIEF.md
```

## Phase Execution Rules

### Reading Context

- **Iteration 1:** Phases read from `config.json`, `ground-data.md`, and current iteration files.
- **Iteration 2+:** Phases ALSO read `iteration-{N-1}/convergence-summary.md` (a 500-token
  summary produced by Phase 7). Do NOT read full JSON from prior iterations — only the summary.
  This manages context window pressure.

### Writing Output

- Every phase writes its output to the run directory as structured JSON or markdown.
- Every JSON file MUST include `"status": "complete"` or `"status": "partial"` at the top level.
- If a phase fails mid-execution: write partial output with `"status": "partial"`, log the error,
  and continue to the next phase. Phase 8 (DECIDE) handles missing data gracefully.

### Shared Context File (Fix 5)

Before spawning personas, the orchestrator precomputes `shared-context.md` in
the run directory. This avoids duplicating 3-4K tokens of preamble + config +
ground data across 5 persona prompts.

Contents of `shared-context.md`:
- Decision statement + sub-questions + constraints (from config.json)
- Decision tilt (from config.json)
- User-provided domain knowledge (from user-inputs.md, if any)
- Key data points from ground-data.md (include ALL key findings, not a lossy summary)
- Hypotheses with expected effect IDs (from hypotheses.json)
- Persona preamble rules (from persona-preamble.md)

Target: ~1500 tokens. Each persona reads this ONE file instead of 3-4 files +
inline preamble. Cuts spawn time and input tokens significantly.

### Persona Subagent Protocol

In Phase 3 (SIMULATE), personas run as SEPARATE subagents via the Agent tool.
See `references/persona-council.md` for the full subagent protocol.

Key rules:
- Spawn 5 subagents in PARALLEL as FOREGROUND agents (multiple Agent tool calls
  in one message, `run_in_background: false` or omit — foreground is default).
- Each subagent reads `shared-context.md` (precomputed above) + its persona-specific
  block, and writes to `council/{persona}.json`.
- Subagents have their own context windows and CANNOT see each other's outputs.

### Synthesis (Inline, Fix 2)

After all 5 personas complete, the ORCHESTRATOR performs synthesis directly.
Do NOT spawn a separate agent for this. The synthesis agent in prior runs spent
half its time re-reasoning about structure — inline eliminates this.

1. Read all `council/*.json` files.
2. **Mechanical merge (shared IDs):** Effects using the seeded vocabulary from
   hypotheses.json merge directly — compute median probability, [min,max] range,
   council_agreement, specialist_insight tags.
3. **Novel IDs:** For effects NOT in the shared vocabulary, count them:
   - ≤ 3 novel IDs: orchestrator deduplicates inline (manageable reasoning)
   - > 3 novel IDs: spawn a single lightweight agent for just the dedup step
4. Write `effects-chains.json`.

### Post-Synthesis Pipeline (Parallel, Fixes 3+4+7)

The actual dependency graph is thinner than the old sequential pipeline assumed.
Critique and Adversary are INDEPENDENT — adversary red-teams effects-chains.json
without needing critique findings. This enables parallelism.

```
Personas (5, parallel) → Synthesis (inline)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              Critique agent      Adversary agent        ← PARALLEL (Fix 4)
              reads: council/*,   reads: effects-chains
              effects-chains      (NOT critique.json)
                    │                   │
                    ▼                   ▼
              peer-review.json    adversary.json
              critique.json             │
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    ┌─────────┴──────────┐
                    ▼                    ▼
              Sensitivity agent    Judge (INLINE, Fix 3)
              reads: effects +     reads: effects +
              adversary            peer-review
                    │                    │
                    ▼                    ▼
              sensitivity.json     judge-score.json
                                   convergence-summary.md
                    │                    │
                    └─────────┬──────────┘
                              ▼
                        Phase 8 DECIDE agent
```

**Execution sequence:**

```
Step 1: Spawn Critique + Adversary in PARALLEL (2 foreground agents, 1 message)
Step 2: Wait for both
Step 3: Spawn Sensitivity agent
         SIMULTANEOUSLY run Judge INLINE (Fix 3 — set operations on 2 JSON files,
         not an agent. Diff effect_ids, count changes, compute convergence. ~5 sec.)
Step 4: Wait for Sensitivity (Judge is already done)
Step 5: If final iteration OR convergence reached:
          Start Phase 8 DECIDE (Fix 7 — can start before judge writes
          convergence-summary if judge is inline and already done)
        If NOT final and NOT converged:
          Loop back to Phase 2 for next iteration
```

**Fix 7 detail (Phase 8 concurrent start):** Since the Judge is now inline (~5 sec),
Phase 8 can start immediately after Sensitivity completes — the judge-score.json and
convergence-summary.md are already written. This is only safe WHEN the judge is
inline (instant). If for any reason the judge runs as an agent, wait for it first.

Only apply concurrent start when this is DEFINITELY the final iteration (iteration
count = max, or convergence was achieved). If another iteration might be needed,
wait for the Judge to decide.

### Projected Timing

| Phase | Old | New | Fix |
|-------|-----|-----|-----|
| Synthesis | ~180s (agent) | ~10s | Fix 2: inline |
| Critique + Adversary | ~300s (sequential) | ~180s | Fix 4: parallel |
| Judge | ~60s (agent) | ~5s | Fix 3: inline |
| Phase 8 start | waits for judge | immediate | Fix 7: concurrent |
| Per-persona input prep | ~30s x 5 | ~5s x 5 | Fix 5: shared context |
| **Total post-personas** | **~24 min** | **~13 min** | |

### Iteration Modes

**Iteration 1: FULL.** Run all phases 2-7 (hypothesize, simulate, critique, adversary,
sensitivity, converge). This is the deep analysis pass.

**Iteration 2+: LIGHT by default.** Run only phases 2-3 (hypothesize, simulate) and
phase 7 (converge). The critique, adversary, and sensitivity from iteration 1 carry
forward — they don't need to be repeated unless convergence FAILS. If convergence fails
at iteration 2, run full phases 4-6 in iteration 3.

### Convergence Protocol

Phase 7 (CONVERGE) runs the Judge. The Judge:

1. Reads current iteration's `effects-chains.json` and `peer-review.json`.
2. If iteration > 1, reads previous iteration's `effects-chains.json` and `peer-review.json`.
3. Computes 4 mechanical parameters:

| Parameter | Threshold | Measurement |
|-----------|-----------|-------------|
| Effects delta | < 2 | Count of top-level 1st-order effects (by `effect_id`) added, removed, or whose `probability` shifted by >0.1 vs previous iteration. Across ALL hypotheses. |
| Assumption stability | > 80% | % of assumption keys present in both iterations' assumption sets. |
| Ranking flip count | ≤ 1 | In peer review, each persona ranks the other 4 analyses. A "flip" = any pairwise ordering reversal vs previous iteration. |
| Contradiction count | ≤ 1 | Effects where one persona's 1st-order effect directly contradicts another's (e.g., "revenue increases" vs "revenue decreases"). |

4. **Convergence uses a weighted composite** (see `references/phases/converge.md` for full logic):
   - PRIMARY signals (must pass): contradiction_count decreasing or ≤ 1, assumption stability > 80%
   - SECONDARY signals (warn but don't gate): effects_delta, ranking flips
   - A high effects_delta WITH decreasing contradictions = productive refinement, not instability
5. **Not converged** = primary signals violated. If iteration < max, loop back to Phase 2.
   Partial convergence triggers targeted escalation per the failing dimension.
6. **Max iterations reached** = exit anyway. Phase 8 runs with a `Convergence: NOT REACHED`
   warning in the Decision Brief.

### Iteration 1 Special Case

Iteration 1 has no previous iteration to compare against. The Judge scores:
- Effects delta: N/A (baseline)
- Assumption stability: N/A (baseline)
- Ranking flip count: N/A (baseline)
- Contradiction count: measured (this catches internal inconsistencies in the first pass)

Iteration 1 NEVER converges (there's nothing to converge against). The inner loop
always runs at least 2 iterations.

### Convergence Summary

After scoring, the Judge writes `convergence-summary.md` (~500 tokens) containing:
- Which effects are stable (present in both iterations, probability shift < 0.1)
- Which assumptions are under pressure (challenged by critique or adversary)
- Which effects are new or removed
- The 4 parameter values

This summary is the ONLY prior-iteration context carried forward to iteration N+1.

## File Structure Per Run

```
~/.autodecision/runs/{decision-slug}/
├── config.json                     # Phase 0 output
├── ground-data.md                  # Phase 1 output
├── user-inputs.md                  # Phase 1.5 output (if ELICIT ran)
├── shared-context.md               # Precomputed before Phase 3 (preamble + config + data)
├── iteration-1/
│   ├── hypotheses.json             # Phase 2 output
│   ├── council/
│   │   ├── optimist.json           # Phase 3 subagent output
│   │   ├── pessimist.json
│   │   ├── competitor.json
│   │   ├── regulator.json
│   │   └── customer.json
│   ├── effects-chains.json         # Phase 3 synthesis output
│   ├── peer-review.json            # Phase 4 output (rankings + anonymization map)
│   ├── critique.json               # Phase 4 output (flaws found)
│   ├── adversary.json              # Phase 5 output
│   ├── sensitivity.json            # Phase 6 output
│   ├── judge-score.json            # Phase 7 output (4 parameters + converged boolean)
│   └── convergence-summary.md      # Phase 7 output (500-token carry-forward)
├── iteration-2/
│   └── ...                         # Same structure
├── convergence-log.json            # Append-only log of all judge scores
└── DECISION-BRIEF.md               # Phase 8 output
```

## Quick Mode Protocol

Quick mode (`/autodecision:quick`) skips ELICIT, the council, and iteration (speed over depth):

1. **Phase 0: SCOPE** — same as full loop. Writes `config.json`.
2. **Phase 1: GROUND** — same as full loop. Writes `ground-data.md`.
3. **Phase 3: SIMULATE** — single analyst pass (no personas, no subagents). Writes
   `effects-chains.json` directly. Probabilities are point estimates only (no range,
   since there's no council to disagree).
4. **Phase 8: DECIDE** — lighter brief. No convergence data, no council agreement,
   no sensitivity analysis. Just: hypotheses, effects with probabilities, assumptions,
   recommendation.

Quick mode writes to the same `~/.autodecision/runs/{slug}/` structure but with no
`iteration-*/council/` subdirectories and no convergence log.

## Error Recovery

If Claude loses track of where it is in the loop:

1. Read `convergence-log.json` — it shows which iterations have completed.
2. Read the most recent `iteration-{N}/` directory — check which files exist.
3. Resume from the last incomplete phase.

The file structure IS the state machine. If a file exists, that phase completed.
If it's missing, that phase needs to run.
