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

## Example Output

See `references/effects-chain-spec.md` for the `hypotheses.json` schema.
