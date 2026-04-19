# Engine Protocol: The Auto-Decision Loop

This is the master protocol. Every phase references this file for the overall loop
structure, sequencing rules, and convergence logic.

## Progress Tracking (Mandatory)

Use the `TodoWrite` tool to surface a live progress tracker. Initialize at run start, mark `in_progress` when entering each phase, mark `completed` on exit. One `in_progress` at a time.

**Templates live in `references/progress-templates.md`** — pick the one for the active mode (full / medium / quick / revise / challenge) and instantiate.

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

3. If `--context` flag is present, note the file paths for extraction in Phase 0.
   See `references/phases/scope.md` "Context File Extraction" for the full protocol.

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
           INPUT QUALITY GATE ─→ score 0-4. Not a decision? Reframe or exit before any work.
                                  (runs FIRST in Phase 0, before decomposition; see scope.md)
           CONTEXT EXTRACTION ──→ context-extracted.md (if --context provided)
                                  (runs after quality gate, before decomposition; see scope.md)
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
         ├── not converged AND iteration < max AND next_iter >= 3 →
         │     AskUserQuestion "Run iter-N or stop?" (see converge.md)
         │     user picks A (continue) → loop back to Phase 2
         │     user picks B (stop, NOT REACHED) → exit inner loop
         │     user picks C (downgrade to medium) → exit, mark "N/A (user stopped)"
         ├── not converged AND iteration < max AND next_iter == 2 →
         │     loop back to Phase 2 (iter-2 is the default, no confirmation needed)
         ├── not converged AND iteration == max →
         │     AskUserQuestion "Extend or stop?" (see converge.md "Offer to Extend")
         │     user picks A (extend) → increment max by 1 (cap 5), loop to Phase 2
         │     user picks B (stop) → exit inner loop with NOT REACHED
         └── iterations = 1 (medium mode)? → skip Phase 7, go to Phase 8

OUTER (runs once):
  Phase 8:   DECIDE ───────────→ DECISION-BRIEF.md
  Phase 8.5: VALIDATE-BRIEF ───→ validation-report.json
                                  (on hard_fail, re-prompts DECIDE once)
```

## CRITICAL: Orchestration Model

**The main conversation IS the orchestrator. It NEVER delegates the full loop to a
single agent.** This is the most important architectural rule in the skill.

```
CORRECT — main conversation orchestrates:
  Main conversation → Phase 0-2 (inline)
  Main conversation → Agent("optimist") + Agent("pessimist") + ... (5 parallel)
  Main conversation → synthesis (inline)
  Main conversation → Agent("critique") + Agent("adversary") (2 parallel)
  Main conversation → sensitivity + judge (inline)
  Main conversation → Phase 8 (inline or single agent)

WRONG — delegating orchestration to a subagent:
  Main conversation → Agent("run the full loop")
    └→ that agent tries Agent("optimist") → FAILS (no grandchild agents)
    └→ falls back to writing all 5 personas sequentially in one context
    └→ personas see each other → fake diversity → fast shallow convergence
```

When the main conversation spawns a persona agent, that agent has its own context
window and genuinely cannot see the other personas' work. When a single agent
authors all 5 personas sequentially, it sees its own prior output — diversity
collapses, convergence is fake, and the analysis is shallow.

**The practical rule:** Follow the phases step by step in the main conversation.
Use the Agent tool to spawn tasks (persona analysis, critique, adversary, decide).
NEVER spawn a single agent to "run everything" or "do phases 3-8."

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

### Output Validation (Mandatory)

After EVERY phase that writes JSON, apply the validation rules from
`references/validation.md`. Read that file once at run start.

Key validations:
- Probabilities must be floats in 0.05 increments (auto-fix "70%" → 0.70)
- Effect IDs and assumption keys must be lowercase snake_case (auto-fix case/format)
- All JSON field types must match spec (auto-fix string-to-int, null-to-empty-array)
- Timeframes must match the enum (auto-fix common variants)
- Descriptions must not contain underscores (auto-fix snake_case → human readable)
- Cross-references must be valid (assumption keys, parent effect IDs)

Auto-fix what's fixable. Log warnings. Never block the run for a single failure.

### Quality Gates (Post-Phase Checks)

After certain phases, the orchestrator checks output quality before proceeding.
These catch shallow analysis that would otherwise produce a fast but worthless brief.

**After Phase 3 (SIMULATE) — Diversity Check:**
After all 5 persona files are written, before synthesis:
1. Count effects per persona per hypothesis.
   - **Floor:** If any persona has fewer than 3 first-order effects for any
     hypothesis, the analysis is too shallow. Log a warning.
   - **Ceiling:** If any persona has more than 8 first-order effects for any
     hypothesis, the persona may be over-producing. Log a WARN. > 12 is the
     upstream cause of the synthesis_dedup_skipped HARD_FAIL — too many
     redundant inventions sit as council_agreement = 1 islands and pull avg
     agreement below 1.5.
   - **Healthy band: 5-8 first-order effects per persona per hypothesis** —
     allows tiered effect modeling (e.g. 4 acquirer-motive variants each with
     its own probability, 3 cash-structure tiers) AND specialist insights that
     don't fit a single-effect-per-concept frame. Tightening below this floor
     killed legitimate tiered analysis in real runs (v0.4.0 sell-vs-raise
     brief had 7 effects in one hypothesis from 4 motive tiers + 3 cash tiers,
     all with high agreement). The validator's `per_persona_overproduction`
     check (HARD_FAIL > 12, WARN > 8) catches the genuinely-broken redundant-
     invention pattern (Japan-style 30+ wordy variants per persona) without
     false-positiving on tiered specialist analysis.
2. Check probability spread. For each effect that 3+ personas generated, compute
   the range (max - min probability). If the AVERAGE range across all shared
   effects is < 0.10, the personas are not genuinely disagreeing — the council
   added no value. Log: "Council diversity LOW — average probability spread {N}.
   Consider re-running with independent subagents."
3. Check for creative alternatives. Count effects with `alt_` prefix across all
   personas. The new spec (persona-preamble.md rule 8) makes alts OPTIONAL, not
   mandatory — personas should write alts only when they have genuine non-obvious
   insight. Healthy band: 3-15 alts per run (across 5 personas × 5 hypotheses, so
   25 maximum if every persona had one for every hypothesis). 0 alts is a quality
   warning ("council surfaced zero creative alternatives — possible groupthink").
   25 alts is also a quality warning ("personas forced alts on every hypothesis —
   likely weak alternatives padding the singleton bucket"). Both are quality
   issues, not blocking errors.

**After Synthesis — Depth Check:**
After effects-chains.json is written:
1. Count total unique first-order effects across all hypotheses. If fewer than
   10 total, the analysis is shallow.
2. Count hypotheses. If fewer than 3, the hypothesis space is underexplored.
3. Check that every first-order effect has at least one second-order child.

**After Phase 7 (CONVERGE) — False Convergence Check:**
If convergence is reached at iteration 1 (which should never happen by design)
or if ALL convergence parameters are at perfect scores (effects_delta = 0,
assumption_stability = 100%, flips = 0, contradictions = 0), something is wrong.
Perfect convergence usually means the personas didn't genuinely disagree.
Log: "WARNING: Perfect convergence may indicate low council diversity."

These checks are informational — they don't block the run but they get noted
in the Decision Brief header so the reader knows if the analysis is weaker
than usual.

### Shared Context File

Before spawning personas, the orchestrator precomputes `shared-context.md` in
the run directory. This avoids duplicating 3-4K tokens of preamble + config +
ground data across 5 persona prompts.

Contents of `shared-context.md`:
- Decision statement + sub-questions + constraints (from config.json)
- Decision tilt (from config.json)
- User-provided domain knowledge (from user-inputs.md, if any)
- Document context (from context-extracted.md, if --context was provided — see below)
- Key data points from ground-data.md (include ALL key findings, not a lossy summary)
- Hypotheses with expected effect IDs (from hypotheses.json) — format these as a
  per-hypothesis block (not one flat list across all hypotheses) so personas
  can scan seeded IDs in context. Per `persona-preamble.md` rule 3, personas
  should prefer seeded IDs when the concept matches; the `seeded_vocab_ignored`
  validator (WARN < 50%, HARD_FAIL < 20% adoption) catches runs where personas
  systematically ignored the shared vocabulary. Format example:

  ```
  ## Seeded effect vocabulary (prefer these where applicable)

  ### h1_short_label
  - `seeded_id_1` — one-line concept hint
  - `seeded_id_2` — ...

  ### h2_short_label
  - ...
  ```

  Aggressive "USE THESE FIRST" all-caps framing penalized novel insight in
  real runs — personas suppressed legitimate specialist contributions (§368
  tax mechanics, novel hypothesis branches) because the spec read as "always
  pick seeded." The softer "prefer when applicable" framing keeps the synthesis
  benefit without killing creative range.
- Persona preamble rules (from persona-preamble.md)
- **FOR ITERATION 2+ ONLY** — append these three blocks before spawning:
  - **Mandatory canonical schema example.** Iter-2+ council files MUST match
    iter-1's JSON shape — same field names, same nesting, no alt schemas. Personas
    in the wild have switched mid-run to `effects_by_hypothesis`, dict-keyed
    `hypotheses`, `first_order_effects` (instead of `effects`), `id` (instead of
    `hypothesis_id`), and dropped the `assumptions` field entirely. The last one
    crashes the Judge's assumption_stability metric to 0% silently. Include the
    following literal example in shared-context.md, prefaced with "Your iter-2
    council file MUST match this canonical shape":

    ```json
    {
      "status": "complete",
      "persona": "optimist",
      "iteration": 2,
      "hypotheses": [
        {
          "hypothesis_id": "h1_short_label",
          "effects": [
            {
              "effect_id": "stable_id_carried_from_iter1",
              "description": "Human-readable description",
              "order": 1,
              "probability": 0.65,
              "timeframe": "0-3 months",
              "assumptions": ["assumption_key_1", "assumption_key_2"],
              "children": [
                {
                  "effect_id": "second_order_id",
                  "description": "...",
                  "order": 2,
                  "probability": 0.50,
                  "timeframe": "3-6 months",
                  "assumptions": [],
                  "parent_effect_id": "stable_id_carried_from_iter1",
                  "children": []
                }
              ]
            }
          ]
        }
      ]
    }
    ```

    Do NOT switch to `effects_by_hypothesis`, dict-keyed `hypotheses`,
    `first_order_effects`, `first_order`, `second_order`, or use `id` instead of
    `hypothesis_id`. Always include the `assumptions` array on every effect, even
    if empty (`[]`). The validator's `assumptions_field_missing` content_check
    HARD_FAILs if < 10% of first-order effects have non-empty assumptions.
  - **Previous iteration effect_ids:** the full list of `effect_id` values from
    `iteration-{N-1}/effects-chains.json > effects[].effect_id` with the rule
    "reuse these IDs for conceptually identical effects, only create new IDs for
    genuinely new effects."
  - **Previous iteration all_assumptions map:** the full `key: description` pairs
    from `iteration-{N-1}/effects-chains.json > all_assumptions` with the rule
    "reuse keys verbatim for conceptually identical assumptions, only create new
    keys for genuinely new assumptions. Do NOT rename for style or phrasing
    preference — that fakes instability and breaks the Judge."
- **OUTPUT FORMATTING RULE (mandatory, include verbatim):**
  "CRITICAL: All output that will appear in the Decision Brief must use human-readable
  language, NEVER snake_case identifiers. Write 'Merchant friction persists' not
  'merchant_friction_persists'. Write 'Capital attach rate' not 'capital_attach_rate'.
  The effect_id field in JSON is internal only — the description field is what appears
  in the brief. If you write an underscore in any user-facing text, you have made an error."

**Document context block (if `--context` was provided).** Include after user-provided
domain knowledge and before hypotheses:

```
## Document Context (from user-provided files)

The following data points were extracted from documents the user attached.
Treat verifiable data (revenue figures, contract terms, dates, headcount) as
high-confidence, more reliable than web search. Treat projections, estimates,
and assertions as assumptions to stress-test in your analysis.

- [D1] Revenue: $4.2M ARR as of Q1 2026 (acme-financials.csv, row 12)
- [D2] Gross margin: 72% (acme-financials.csv, row 15)
...
```

Budget: ~300-500 tokens for the document block. Read from `context-extracted.md`.

Target: ~1500 tokens in iter-1 without docs, ~1800-2000 with docs, ~2500-3000
in iter-2+ with docs (the previous-iter ID and assumption blocks add ~500-1000
tokens but are load-bearing for stability metrics).

### Shared-context anti-patterns (do NOT do these)

When constructing `shared-context.md` and `hypotheses.json`, avoid phrasings
that historically inflated effect counts:

1. **Aggregate-total parentheticals.** Do NOT add expansions like
   `"(so 25-40 first-order total across 5 hypotheses)"` alongside the
   per-hypothesis budget. The budget IS per-hypothesis (5-8, per
   `persona-preamble.md` rule 6). Aggregate-total phrasing converts a soft
   per-hypothesis range into a numerical total floor that the persona
   optimizes against.

2. **Excessive `expected_effect_ids`.** Per `phases/hypothesize.md`, seed 4-6
   effect IDs per hypothesis. Seeding 8+ signals "produce ~8 per hypothesis"
   which can drift toward redundant invention.

The post-spawn validators (`per_persona_overproduction` HARD_FAIL > 12 + WARN
> 8, `synthesis_dedup_skipped` HARD_FAIL avg agreement < 1.5) catch the
genuinely-broken redundant-invention pattern. There is no pre-spawn structured
check — earlier versions tried to enforce a hard `expected_effect_ids ≤ 4` cap
which over-constrained Phase 2 and killed legitimate seeding for hypotheses
with 5-6 obvious distinct effects.

### Persona Subagent Protocol

In Phase 3 (SIMULATE), personas run as SEPARATE subagents via the Agent tool.
See `references/persona-council.md` for the full subagent protocol.

Key rules:
- Spawn 5 subagents in PARALLEL as FOREGROUND agents (multiple Agent tool calls
  in one message, `run_in_background: false` or omit — foreground is default).
- Each subagent reads `shared-context.md` (precomputed above) + its persona-specific
  block, and writes to `council/{persona}.json`.
- Subagents have their own context windows and CANNOT see each other's outputs.

**If Agent tool is unavailable** (e.g., running inside a subagent):

Do NOT silently degrade. The council is the core value of the full loop. Without
genuine persona independence, the output is significantly weaker — personas converge,
diversity collapses, convergence is fake, and the analysis is shallow.

**Detection:** Before spawning the first persona agent, test whether the Agent tool
is available. If it fails or is not available in the current environment:

**STOP and ask the user:**

> "The Agent tool is not available in this environment (likely because /autodecision
> is running inside a subagent). This means the 5-persona council cannot run with
> genuine independence — personas would be authored sequentially in one context,
> significantly reducing analysis quality.
>
> Options:
> A) Switch to quick mode — single-pass analysis without council (~2 min, honest about its limitations)
> B) Continue with degraded council — sequential personas, weaker diversity, faster but shallower
> C) Abort — I'll re-run /autodecision from the main conversation for full quality"

If the user picks A: switch to quick mode protocol (SCOPE → GROUND → SIMULATE single pass → DECIDE).
If the user picks B: proceed with sequential fallback, note prominently in the brief header:
  "WARNING: Personas authored sequentially (Agent tool unavailable). Council diversity
  is weaker than a full-quality run. For genuine independence, run /autodecision from
  the main conversation, not inside a subagent."
If the user picks C: abort cleanly.

**NEVER proceed with degraded quality without explicit user consent.**

### Synthesis (Inline)

After all 5 personas complete, the ORCHESTRATOR performs synthesis directly.
Do NOT spawn a separate agent for this. A separate synthesis agent wastes time
re-reasoning about structure — inline merge is faster and more reliable.

1. Read all `council/*.json` files.
2. **Mechanical merge (shared IDs):** Effects using the seeded vocabulary from
   hypotheses.json merge directly — compute median probability, [min,max] range,
   council_agreement, specialist_insight tags.
3. **Novel IDs:** For effects NOT in the shared vocabulary, count them:
   - ≤ 3 novel IDs: orchestrator deduplicates inline (manageable reasoning)
   - > 3 novel IDs: spawn a single lightweight agent for just the dedup step
4. Write `effects-chains.json`.

### Post-Synthesis Pipeline (Parallel)

The actual dependency graph is thinner than the old sequential pipeline assumed.
Critique and Adversary are INDEPENDENT — adversary red-teams effects-chains.json
without needing critique findings. This enables parallelism.

```
Personas (5, parallel) → Synthesis (inline)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              Critique agent      Adversary agent        ← PARALLEL
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
              Sensitivity agent    Judge (INLINE)
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
         SIMULTANEOUSLY run Judge INLINE (set operations on 2 JSON files,
         not an agent. Diff effect_ids, count changes, compute convergence. ~5 sec.)
Step 4: Wait for Sensitivity (Judge is already done)
Step 5: If final iteration OR convergence reached:
          Start Phase 8 DECIDE (can start before judge writes
          convergence-summary if judge is inline and already done)
        If NOT final and NOT converged:
          Loop back to Phase 2 for next iteration
```

**Phase 8 concurrent start:** Since the Judge is now inline (~5 sec),
Phase 8 can start immediately after Sensitivity completes — the judge-score.json and
convergence-summary.md are already written. This is only safe WHEN the judge is
inline (instant). If for any reason the judge runs as an agent, wait for it first.

Only apply concurrent start when this is DEFINITELY the final iteration (iteration
count = max, or convergence was achieved). If another iteration might be needed,
wait for the Judge to decide.

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

4. **Convergence uses a weighted composite with a delta-weighted cap** (see `references/phases/converge.md` for full logic):
   - PRIMARY signals (must pass): contradiction_count decreasing or ≤ 1, assumption stability > 80%
   - SECONDARY signals: effects_delta, ranking flips — but `effective_delta > 50` is a hard cap (NOT converged regardless of other signals). `effective_delta = effects_delta - effects attributable to any hypothesis flagged new_in_iter_N`.
   - A moderate effective_delta (5-50) WITH decreasing contradictions = productive refinement.
5. **Not converged** = primary signals violated or effective_delta > 50. If iteration < max, loop back to Phase 2.
   Partial convergence triggers targeted escalation per the failing dimension.
6. **User confirmation before iter-3+.** If about to start iteration 3, 4, or 5, the
   orchestrator MUST pause and AskUserQuestion — running additional iterations is a
   user decision, not a Judge decision. iter-2 does not require confirmation. See
   `converge.md` "User Confirmation Before Iteration 3+" for the exact question and options.
7. **Max iterations reached and NOT converged** = offer user extension. AskUserQuestion
   with the Judge scores and option to extend by 1 iteration (cap 5 total) or stop.
   See `converge.md` "Offer to Extend at Max Iterations." If user declines (or at cap),
   Phase 8 runs with `Convergence: NOT REACHED` in the brief.

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

### Pre-DECIDE Structural Gate

Before Phase 8 (DECIDE) can start, verify the run directory contains the required
upstream files. This gate catches the failure mode where the orchestrator skips the
loop and writes a brief from memory.

```bash
# All four must exist for full/medium mode. Quick mode only needs config.json.
ls ~/.autodecision/runs/{slug}/config.json          # Phase 0
ls ~/.autodecision/runs/{slug}/ground-data.md        # Phase 1
ls ~/.autodecision/runs/{slug}/iteration-1/effects-chains.json  # Phase 3
ls ~/.autodecision/runs/{slug}/convergence-log.json  # Phase 7
```

**If ANY file is missing:** Do NOT proceed to Phase 8. Do NOT write a brief from
memory, from the context file, or from general knowledge. Instead:

1. Identify which phase failed or was skipped
2. Go back and run it
3. Only proceed to DECIDE when all upstream files exist

A brief without upstream data files is fabricated, not analyzed. The entire value
of the engine is the structured loop — scope, ground, personas, critique, adversary,
sensitivity, convergence. Without those intermediate outputs, the brief is a
consulting memo, not a Decision Brief.

**This gate is the highest-priority check.** A structurally correct brief built on
fabricated data is worse than an error message saying "Phase 3 didn't run."

## File Structure Per Run

```
~/.autodecision/runs/{decision-slug}/
├── config.json                     # Phase 0 output
├── context-extracted.md            # Phase 0 output (if --context provided)
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
├── DECISION-BRIEF.md               # Phase 8 output
└── validation-report.json          # Phase 8.5 output (mechanical brief checks)
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
5. **Phase 8.5: VALIDATE-BRIEF** — runs in `--mode quick`. Reduced section set
   (Data Foundation, Effects Map with First-Order/Second-Order, Key Assumptions,
   Recommendation with Action + Confidence). Still enforces no-snake-case-in-prose
   and recommendation-position rules.

Quick mode writes to the same `~/.autodecision/runs/{slug}/` structure but with no
`iteration-*/council/` subdirectories and no convergence log.

## Error Recovery

If Claude loses track of where it is in the loop:

1. Read `convergence-log.json` — it shows which iterations have completed.
2. Read the most recent `iteration-{N}/` directory — check which files exist.
3. Resume from the last incomplete phase.

The file structure IS the state machine. If a file exists, that phase completed.
If it's missing, that phase needs to run.
