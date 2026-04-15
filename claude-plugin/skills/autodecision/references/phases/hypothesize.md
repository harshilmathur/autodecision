<!--
phase: 2
phase_name: HYPOTHESIZE
runs_in:
  - full.iteration-1     (full re-hypothesize)
  - full.iteration-2+    (LIGHT mode: re-hypothesize using convergence-summary carry-forward)
  - medium.iteration-1   (single iteration)
  - quick                (lighter — just generates a flat list, no expected effect IDs)
reads:
  - ~/.autodecision/runs/{slug}/config.json
  - ~/.autodecision/runs/{slug}/ground-data.md
  - ~/.autodecision/runs/{slug}/user-inputs.md (if exists)
  - ~/.autodecision/runs/{slug}/iteration-{N-1}/convergence-summary.md (iteration 2+)
writes:
  - ~/.autodecision/runs/{slug}/iteration-{N}/hypotheses.json
gates:
  - At least 3 hypotheses, meaningfully different (not just optimistic/neutral/pessimistic)
  - Each hypothesis carries an "expected_effect_ids" list (seeded vocabulary for SIMULATE)
-->

# Phase 2: HYPOTHESIZE

## Purpose
Generate 3-5 competing hypotheses about what will happen if the decision is made.
Hypotheses must be meaningfully different — not just optimistic/neutral/pessimistic
versions of the same outcome.

## Inputs
- `config.json` (decision, sub-questions, constraints)
- `ground-data.md` (real data from web search)
- Previous iteration's `convergence-summary.md` (if iteration > 1)

## Outputs
- `iteration-{N}/hypotheses.json`

## Process

1. Read all inputs.
2. Generate 3-5 hypotheses. Each hypothesis must:
   - Address at least 2 sub-questions from `config.json`
   - Be grounded in data from `ground-data.md` where available
   - Be DISTINCT from other hypotheses (different causal mechanism, not different magnitude)
   - Have a clear, testable statement
   - List its key assumptions explicitly

3. For iteration 2+, also read `convergence-summary.md`. Hypotheses that were
   eliminated by the critique/adversary in the prior iteration should be dropped
   or significantly revised. New hypotheses may be added if the adversary phase
   revealed unexplored scenarios.

## Hypothesis Diversity Rules

Force diversity along different AXES, not just optimism level:

- **Market dynamics axis:** "Price cut accelerates growth" vs "Price cut triggers price war"
- **Customer behavior axis:** "Customers are price-sensitive" vs "Customers are value-sensitive"
- **Competitive response axis:** "Competitor matches price" vs "Competitor differentiates"
- **Execution axis:** "We execute well" vs "Operational complexity increases"
- **Temporal axis:** "Short-term gain, long-term pain" vs "Short-term pain, long-term gain"

At least 2 of the 3-5 hypotheses must vary along DIFFERENT axes (not just the
same axis at different magnitudes).

## Shared Effect ID Vocabulary

For EACH hypothesis, generate 4-6 expected effect IDs that personas should use.
These go into `hypotheses.json` under `expected_effect_ids` and are seeded into
every persona's prompt in Phase 3 to reduce semantic dedup problems in synthesis.

Pick IDs that cover the obvious effects for each hypothesis. Personas reuse these
where applicable and only invent new IDs for genuinely novel effects.

Example:
```json
{
  "hypothesis_id": "h1_buy_vendor",
  "expected_effect_ids": ["fast_deploy", "adoption_plateau", "vendor_lock_in", "dlp_required", "budget_fit"]
}
```

## Example Output

See `references/effects-chain-spec.md` for the `hypotheses.json` schema.
