<!--
phase: 3
phase_name: SIMULATE
runs_in:
  - full.iteration-1     (5-persona council, parallel subagents)
  - full.iteration-2+    (LIGHT mode: re-simulate only — critique/adversary/sensitivity carry forward unless convergence fails)
  - medium.iteration-1   (5-persona council, single iteration)
  - quick                (single analyst variant — NO council, NO subagents)
reads:
  - ~/.autodecision/runs/{slug}/shared-context.md (precomputed by orchestrator)
  - ~/.autodecision/runs/{slug}/iteration-{N}/hypotheses.json
  - ~/.autodecision/runs/{slug}/context-extracted.md (if --context was provided — included in shared-context.md)
  - references/persona-council.md
  - references/persona-preamble.md
  - references/effects-chain-spec.md
writes:
  - ~/.autodecision/runs/{slug}/iteration-{N}/council/{tag}.json × 5 (full/medium — tags from persona-council.md Canonical Persona Names)
  - ~/.autodecision/runs/{slug}/iteration-{N}/effects-chains.json (synthesis output)
spawns:
  - 5 foreground Agent subagents in PARALLEL (full/medium); 0 in quick mode
  - Synthesis runs INLINE in orchestrator (NEVER as a separate agent)
gates:
  - diversity_check: avg probability spread across shared effects > 0.10 (else "Council diversity LOW" warning)
  - depth_check: at least 3 first-order effects per persona per hypothesis (target band 5-8)
  - pre_synthesis_discipline_gate: re-spawn personas with > 12 first-order for any hypothesis (1 retry per persona) — catches catastrophic overproduction without false-positiving on tiered analysis
  - children_check: every 1st-order effect has ≥1 second-order child
  - alt_check: at least 3 effects with `alt_` prefix across all 5 personas (creative alternatives rule)
-->

# Phase 3: SIMULATE

## Purpose
Each persona independently simulates the effects of each hypothesis, producing
structured effects chains with probabilities and assumptions.

## Inputs
- `config.json`, `ground-data.md`, `iteration-{N}/hypotheses.json`
- Previous `convergence-summary.md` (if iteration > 1)

## Outputs
- `iteration-{N}/council/{persona}.json` (5 files, one per persona)
- `iteration-{N}/effects-chains.json` (synthesized)

## Process

### Step 1: Spawn 5 Persona Subagents (PARALLEL)

Use the Agent tool to spawn 5 subagents simultaneously. Each subagent receives:

1. The persona's system prompt (from `references/persona-council.md`)
2. Instructions to read the shared context files:
   - `~/.autodecision/runs/{slug}/config.json`
   - `~/.autodecision/runs/{slug}/ground-data.md`
   - `~/.autodecision/runs/{slug}/iteration-{N}/hypotheses.json`
   - (If iteration > 1) `~/.autodecision/runs/{slug}/iteration-{N-1}/convergence-summary.md`
3. The effects chain JSON schema (from `references/effects-chain-spec.md`)
4. Instructions to write output to `~/.autodecision/runs/{slug}/iteration-{N}/council/{persona}.json`

Each subagent MUST:
- Generate effects for EVERY hypothesis in `hypotheses.json`
- Assign stable `effect_id` values (snake_case, max 30 chars)
- Assign probabilities in 0.05 increments (0.05 to 0.95)
- List all assumptions explicitly
- Generate 2nd-order effects for ALL 1st-order effects (no probability gate)
- Answer their required contrarian question
- Stay under ~2000 tokens of output

### Step 2: Wait for Completion

Wait for all 5 subagents. Handle failures:
- 5/5 complete: proceed normally
- 3-4/5 complete: proceed with available data, note missing personas
- < 3/5 complete: critical error, skip to Phase 8 with available data

### Step 2.5: Pre-Synthesis Discipline Gate (catastrophic-overproduction repair)

This gate catches catastrophic per-persona overproduction (> 12 first-order
effects for any single hypothesis) BEFORE it locks into the synthesis. The
threshold is intentionally high — at the genuinely-broken end (Japan-style
30+ wordy variants per persona) — so the gate doesn't false-positive on
tiered specialist analysis (5-8 distinct effects per hypothesis is healthy).

**Procedure:**

1. **Parse all completed council files** using the universal extractor in
   `validate-brief.py` (`_extract_first_order_per_hyp`). Handles all 3 schema
   shapes (canonical `hypotheses[]`, alt `effects_by_hypothesis{}`, dict-keyed
   `hypotheses{}` with `first_order_effects`).

2. **Identify violations.** Any `(persona, hypothesis)` where first-order count
   > 12 is a violation. Log every count > 8 as a WARN for visibility, but only
   re-spawn on > 12 — the lower band is where legitimate tiered analysis lives.

3. **No violations → proceed to Step 3 Synthesis.**

4. **One or more violations → spawn focused re-prompts** for each violating
   persona (only the offenders) with a trim instruction: "you wrote N effects
   for hypothesis X, the cap is 12 — pick the 5-8 strongest by causal-mechanism
   distinctness, drop the rest. Tiered effects (e.g. 4 cash-tier variants of
   one outcome) count as legitimately distinct. Wordy redundant variants of the
   same concept do not."

5. **One retry per persona, then accept.** If a persona STILL has > 12 after
   the re-prompt, log a WARNING and proceed. The post-hoc validator
   (`per_persona_overproduction` HARD_FAIL > 12) will surface it in the brief.

6. **Append to `iteration-{N}/discipline-gate.log`** so the brief's Council
   Dynamics can cite the repair if it ran.

**Why the threshold is 12, not 4:**

Earlier versions of this gate triggered at > 4, which forced re-spawns on every
healthy run that did tiered analysis (the v0.4.0 sell-vs-raise brief had 7
effects in one hypothesis from 4 acquirer-motive tiers + 3 cash-structure tiers,
all with high agreement). At threshold 12, only catastrophic patterns trigger
the repair, and the validator backstops catch the borderline cases at brief-
validation time.

**Exempt modes:** quick mode (no council), challenge mode (adversary-only).
Medium and Full modes both run this gate.

### Step 3: Synthesis Pass

After all subagents complete, the orchestrator reads all `council/*.json` files and:

0. **Shape-agnostic extraction (defense in depth against schema drift).** Personas
   in the wild have shipped 4 distinct council JSON shapes (canonical
   `hypotheses[]`, alt `effects_by_hypothesis{}`, dict-keyed `hypotheses{}` with
   `first_order_effects`, dict-keyed with `first_order`). The persona-preamble
   rule 3 + iter-2 carryforward example (in `engine-protocol.md` Shared Context)
   tell personas to use the canonical shape — this synthesis step is the backstop
   for when they don't.

   For EACH council file, extract effects + assumptions using the same
   shape-agnostic logic the validator's `_extract_first_order_per_hyp` uses
   (in `scripts/validate-brief.py`). Specifically: try each shape in order
   (canonical `hypotheses[]` → flat `effects_by_hypothesis{}` → dict-keyed
   `hypotheses{}`), and for each, extract effects from any of these field names:
   `effects`, `first_order_effects`, `first_order`. Pull `assumptions` from the
   `assumptions` field if present; if absent (persona dropped the field),
   default to `[]` and log a WARN line: "Persona X iter-N hypothesis Y dropped
   assumptions field — defaulted to empty. The validator's
   assumptions_field_missing check will surface this." This way the
   synthesized `effects-chains.json` always has a structurally valid
   `assumptions` array, even when personas misbehave, and the Judge's
   assumption_stability metric stays meaningful.

1. **Collect all unique `effect_id` values** across all 5 personas, across all
   hypotheses, across BOTH first-order and second-order slots.
2. **Deduplicate by semantic similarity (within an order).** If two personas use
   different IDs for the same effect at the same order (e.g., `acq_increase` and
   `customer_growth_surge` both as 1st-order), merge them:
   - Use the ID chosen by more personas
   - If tied, use the shorter/clearer ID
3. **For each unique effect:**
   - `probability` = median of all persona estimates
   - `probability_range` = [min, max] of all persona estimates
   - `council_agreement` = count of personas who generated this effect
   - `description` = description from the persona with the highest council agreement
   - `assumptions` = union of all assumption keys across personas for this effect
4. **Merge 2nd-order effects** similarly (by `effect_id`, with parent tracking).

### Step 3.5: Cross-Order Dedup (Canonicalize the Map)

After Step 4 but before writing `effects-chains.json`, run a cross-order dedup
pass. The problem it solves: Persona A may emit `merchant_churn` as a 1st-order
effect of Hypothesis 2, while Persona B emits the same concept as a 2nd-order
child of `price_war_escalation` under Hypothesis 1. Without dedup, the brief's
Effects Map shows two entries for one real effect — inflating the map, breaking
council_agreement counts, and confusing the reader.

**Procedure:**

1. Flatten every effect across all hypotheses AND both orders into one candidate
   list: `[(hypothesis_id, order, effect_id, description, probability, ...), ...]`.
2. Group candidates by semantic similarity on `description` (>70% token overlap
   OR manually paired synonym canonicalization like
   `merchant_churn ≡ churn_merchant ≡ enterprise_churn` when domain context
   matches).
3. For each group with ≥ 2 candidates:
   - Pick the **canonical effect_id**: whichever ID the most personas chose; ties
     go to the shortest ID.
   - Pick the **canonical order**: if any persona emitted it as 1st-order, it's
     1st-order. Second-order is a weaker signal and loses to any 1st-order
     emission. Log the cross-order merge: `"Merged merchant_churn (2nd-order
     under price_war_escalation in competitor.json) into merchant_churn (1st-order
     of H2 in pessimist.json)."`
   - Union assumptions, union hypotheses (the effect now traces to every
     hypothesis that generated it), take probability median across all emissions,
     recompute council_agreement as count of DISTINCT personas in the merged group.
4. Write `iteration-{N}/cross-order-merges.log` with every merge so the brief's
   Council Dynamics section can cite surprises ("the Competitor persona's 2nd-order
   merchant_churn was the same effect the Pessimist made 1st-order — hidden
   consensus of 4/5 that this initial view missed").
5. Update `effects-chains.json` with the deduped list.

**Guard:** do NOT merge across genuinely different effects that share a verb.
`revenue_increases` (from acquisition) and `revenue_increases` (from upsell) are
distinct — check assumption overlap. If assumption sets are disjoint, do not merge.

### Step 3.6: Finalize

After cross-order dedup completes:

1. **Build the `all_assumptions` map** from all assumption keys referenced in any
   surviving effect.
2. **Run the Step 3.5 drift check from Assumption Key Stability above** (iter-2+ only).
3. **Write `effects-chains.json`.**

## Effect ID Stability Across Iterations

For iteration 2+, the subagent prompt MUST include the list of `effect_id` values
from the previous iteration's `effects-chains.json`. Personas should reuse these IDs
for effects that are conceptually the same, even if descriptions change slightly.

Include in the subagent prompt:
> "IMPORTANT: The following effect_ids were established in the previous iteration.
> Reuse these IDs for the same effects. Only create new IDs for genuinely new effects.
> [list of effect_ids from previous iteration]"

## Assumption Key Stability Across Iterations

**This is the same rule as effect_id stability, extended to assumption keys.** Without
it, iter-1 `market_has_demand` becomes iter-2 `market_demand_exists` and the Judge's
`assumption_stability` metric crashes from 100% to 11% for purely cosmetic reasons.
Real convergence gets masked by bookkeeping churn.

For iteration 2+, the subagent prompt MUST include the full `all_assumptions` map
from the previous iteration's `effects-chains.json` — keys AND descriptions.
Personas MUST reuse the keys verbatim for any assumption that is conceptually the
same, even if they would prefer different phrasing.

Include in the subagent prompt (after the effect_ids block):
> "IMPORTANT: The following assumption keys were established in the previous
> iteration. Reuse these keys verbatim for the same assumptions. Only create new
> keys for genuinely new assumptions the previous iteration did not surface.
>
> Previous iteration's all_assumptions map:
> [paste the full key: description mapping from iter-(N-1)/effects-chains.json]
>
> Rule: if you would write `market_demand_exists` for something the previous
> iteration called `market_has_demand`, use the previous key. Do NOT rename
> for style or preference. Rename ONLY if the meaning genuinely changed."

**Orchestrator responsibility.** Before spawning iter-2+ personas, the orchestrator:
1. Reads `iteration-(N-1)/effects-chains.json > all_assumptions`
2. Formats it as a `key: description` list
3. Injects it into the shared-context.md that every persona reads
4. Emits a warning line in the run log if any iter-N persona introduces a new key
   whose description semantically overlaps an existing key (synthesis pass
   responsibility — see Step 3.7 below).

### Step 3.7: Post-Synthesis Assumption Drift Check

After Step 3.6 Finalize but before writing `effects-chains.json`, the orchestrator
runs a drift check for iter-2+:

1. Load previous iteration's `all_assumptions` keys into `prev_keys`.
2. For every new key in this iteration's synthesized `all_assumptions`:
   - If the new key's description has >70% token overlap with an existing
     `prev_keys` entry's description, log a WARNING:
     `"Possible assumption drift: '{new_key}' may duplicate '{prev_key}'
     ('{new_desc}' vs '{prev_desc}'). Retaining '{prev_key}' for Judge stability."`
   - Merge the new key into the existing `prev_key` (rename in all effects that
     reference it, union their usages).
3. Write `iteration-{N}/assumption-drift.log` with every detected rename, for
   Judge and reviewer visibility.

The Judge's `assumption_stability` metric now reflects genuine churn, not naming.
