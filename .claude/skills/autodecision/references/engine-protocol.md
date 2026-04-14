# Engine Protocol: The Auto-Decision Loop

This is the master protocol. Every phase references this file for the overall loop
structure, sequencing rules, and convergence logic.

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
  Phase 0.5: ELICIT ───────────→ user-inputs.md (review assumptions, personas, data with user)
  Phase 1: GROUND ─────────────→ ground-data.md

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

### Persona Subagent Protocol

In Phase 3 (SIMULATE), personas run as SEPARATE subagents via the Agent tool.
See `references/persona-council.md` for the full subagent protocol.

Key rules:
- Spawn 5 subagents in PARALLEL as FOREGROUND agents (use multiple Agent tool calls
  in one message, do NOT use run_in_background). This avoids straggler notifications
  and ensures all results are available before proceeding.
- Each subagent receives: persona system prompt + instruction to read shared context files
  and write output to `council/{persona}.json`.
- Subagents have their own context windows and CANNOT see each other's outputs.
- After all 5 complete, the ORCHESTRATOR (not a separate agent) reads all `council/*.json`
  files and performs the synthesis merge inline: compute medians, ranges, council_agreement,
  deduplicate effect_ids, and write `effects-chains.json`. This is a mechanical operation,
  not a reasoning task — do it directly.

Phase 4 (CRITIQUE) runs as a SINGLE agent pass that reviews all 5 analyses, not 5
separate reviewer subagents. One agent produces both `peer-review.json` and `critique.json`.

### Post-Simulation Pipeline (3 stages, NOT one mega-agent)

After Phase 3 personas complete and synthesis is done, the remaining phases run as
3 SEPARATE sequential agents. This prevents a single failure from losing all work,
and makes debugging possible.

**Stage A: Critique Agent**
- Runs Phase 4 (CRITIQUE): anonymized peer review + flaw identification
- Reads: `council/*.json`, `effects-chains.json`
- Writes: `peer-review.json`, `critique.json`

**Stage B: Stress-Test Agent**
- Runs Phase 5 (ADVERSARY) + Phase 6 (SENSITIVITY) + Phase 7 (CONVERGE)
- Reads: `effects-chains.json`, `critique.json`
- Writes: `adversary.json`, `sensitivity.json`, `judge-score.json`, `convergence-summary.md`
- Appends to: `convergence-log.json`

**Stage C: Decision Agent**
- If iteration 2+ needed: runs light-mode Phase 2-3 + Phase 7, then Phase 8
- If converged or final iteration: runs Phase 8 (DECIDE) only
- Reads: all iteration outputs, `convergence-log.json`, `ground-data.md`, `user-inputs.md`
- Writes: `DECISION-BRIEF.md` (+ `COMPARISON-VS-QUICK.md` if quick run exists)

Each stage writes to disk before the next starts. If Stage B fails, Stage A's
critique output is preserved and Stage B can be re-run.

The orchestrator sequences these: spawn Stage A → wait → spawn Stage B → wait →
spawn Stage C → wait → done. NOT one agent doing all 7 steps.

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

4. **Converged** = ALL 4 thresholds met.
5. **Not converged** = any threshold violated. If iteration < 3, loop back to Phase 2
   with updated assumptions from the critique and adversary phases.
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

Quick mode (`/autodecision:quick`) skips the council and iteration:

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
