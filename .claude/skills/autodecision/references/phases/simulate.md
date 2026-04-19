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
  - depth_check: 2-4 first-order effects per persona per hypothesis (floor 2, target 3, hard ceiling 4 — defer to persona-preamble.md rule 6)
  - pre_synthesis_discipline_gate: re-spawn personas with > 4 first-order for any hypothesis (1 retry per persona)
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

### Step 2.5: Pre-Synthesis Discipline Gate (NEW — runs BEFORE Step 3 Synthesis)

This gate is the load-bearing enforcement of the per-persona output budget from
`persona-preamble.md` rule 6 (3 first-order per hypothesis, hard cap 4). Without
this gate, spec wording is a soft constraint that LLMs routinely ignore — and once
overproduction is locked into council files, the only options are:
(a) accept synthesis bloat (validator HARD_FAIL on `synthesis_dedup_skipped` and
`per_persona_overproduction`), or (b) re-run the entire council manually.

The gate runs the repair loop automatically.

**Procedure:**

1. **Parse all completed council files.** For each `iteration-{N}/council/{persona}.json`:
   ```python
   counts = {}  # (persona, hypothesis_id) -> first-order effect count
   for p in personas_completed:
       data = json.load(open(f"{run_dir}/iteration-{N}/council/{p}.json"))
       for h in data["hypotheses"]:
           counts[(p, h["hypothesis_id"])] = len(h["effects"])
   ```

2. **Identify violations.** Any `(persona, hypothesis)` where count > 4 is a violation.
   Log all violations:
   ```
   pre-synthesis discipline gate:
     optimist  / h1_acquire_local_devtools: 7 first-order effects (cap 4) — VIOLATION
     pessimist / h1_acquire_local_devtools: 8 first-order effects (cap 4) — VIOLATION
     regulator / h2_greenfield_full_subsidiary: 4 first-order — OK
   ```

3. **No violations → proceed to Step 3 Synthesis.**

4. **One or more violations → spawn focused re-prompts.** For each violating persona
   (NOT all 5 — only the offenders), spawn ONE Agent subagent with a re-prompt:

   ```
   YOUR PREVIOUS OUTPUT for hypothesis {hyp_id} had {N} first-order effects.
   The hard cap per persona-preamble.md rule 6 is 4 first-order effects per
   hypothesis. Re-do JUST that hypothesis:

   1. Read your previous output at iteration-{N}/council/{persona}.json
   2. For hypothesis {hyp_id}, pick the 3-4 STRONGEST effects by causal-mechanism
      distinctness. Drop the weakest. The alt_ slot stays as your 5th.
   3. Output the FULL JSON shape (all 5 hypotheses) but with the trimmed effect
      list for {hyp_id}. Other hypotheses unchanged.
   4. Write the updated JSON to iteration-{N}/council/{persona}.json (overwrite).

   Why this matters: synthesis merges across the 5 personas by effect_id. Effects
   only one persona generated sit as council_agreement = 1 islands that drown the
   shared signal. 5 personas × 3 strong effects = ~15 raw → ~5-7 unique with
   council_agreement 3-4 (clean synthesis). Your overproduction breaks that math.

   Cap: 4 first-order. Floor: 2. Target: 3.
   ```

5. **Wait for re-prompts to complete.** Re-validate the updated council files.

6. **One retry per persona, then accept.** If a persona STILL has > 4 first-order
   for any hypothesis after the re-prompt, log a WARNING and proceed to synthesis
   with the over-stuffed file. The post-hoc validator (`per_persona_overproduction`
   in `brief-schema.json`) will then HARD_FAIL the brief. Don't loop infinitely.

7. **Append to `iteration-{N}/discipline-gate.log`** so the brief's Council Dynamics
   can cite the repair: "Optimist re-spawned for h1 (7 → 3 first-order); Pessimist
   re-spawned for h1 (8 → 4)."

**Why this is in Step 2.5, before synthesis:**

- After Step 3 Synthesis, the bad pattern is locked into `effects-chains.json` —
  re-spawning a single persona requires re-running synthesis end-to-end, which
  is expensive and error-prone.
- Per-persona re-spawn is cheap: one Agent subagent with a focused prompt
  (~500 tokens), 1 minute wall-clock.
- Re-spawning the FULL council would defeat the purpose — the genuine
  per-persona analyses are independent observations and we want to keep
  the (compliant) ones.

**Iteration-2 light mode applies the gate too.** See `engine-protocol.md`
"Iteration Modes" — iter-2 personas write fresh council files, the gate runs
on iter-2/council/*.json before iter-2 synthesis. Without this, an over-stuffed
iter-1 followed by a trimmed iter-2 (or vice versa) creates fake convergence
or fake instability via count drift.

**Exempt modes:** quick mode (no council). Medium and Full modes both run
this gate.

### Step 3: Synthesis Pass

After all subagents complete, the orchestrator reads all `council/*.json` files and:

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
