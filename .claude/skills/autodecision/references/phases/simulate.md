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

### Step 3: Synthesis Pass

After all subagents complete, the orchestrator reads all `council/*.json` files and:

1. **Collect all unique `effect_id` values** across all 5 personas.
2. **Deduplicate by semantic similarity.** If two personas use different IDs for the
   same effect (e.g., `acq_increase` and `customer_growth_surge`), merge them:
   - Use the ID chosen by more personas
   - If tied, use the shorter/clearer ID
3. **For each unique effect:**
   - `probability` = median of all persona estimates
   - `probability_range` = [min, max] of all persona estimates
   - `council_agreement` = count of personas who generated this effect
   - `description` = description from the persona with the highest council agreement
   - `assumptions` = union of all assumption keys across personas for this effect
4. **Merge 2nd-order effects** similarly (by `effect_id`, with parent tracking).
5. **Build the `all_assumptions` map** from all assumption keys referenced in any effect.
6. **Write `effects-chains.json`.**

## Effect ID Stability Across Iterations

For iteration 2+, the subagent prompt MUST include the list of `effect_id` values
from the previous iteration's `effects-chains.json`. Personas should reuse these IDs
for effects that are conceptually the same, even if descriptions change slightly.

Include in the subagent prompt:
> "IMPORTANT: The following effect_ids were established in the previous iteration.
> Reuse these IDs for the same effects. Only create new IDs for genuinely new effects.
> [list of effect_ids from previous iteration]"
