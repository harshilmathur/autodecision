# Phase 8: DECIDE

## Purpose
Final synthesis. Produce the Decision Brief — the primary output of the system.

## Inputs
- `config.json`, `ground-data.md`
- All iteration outputs (read only the LATEST iteration's files + `convergence-log.json`)
- `convergence-log.json` (full iteration history)

## Outputs
- `DECISION-BRIEF.md`

## Process

### Step 1: Read Final State

Read the latest iteration's:
- `effects-chains.json` (the converged or final effects map)
- `sensitivity.json` (decision boundaries and assumption rankings)
- `adversary.json` (worst cases and black swans)
- `peer-review.json` (council agreement and rankings)
- `convergence-log.json` (convergence history)

### Step 2: Classify Insights

**Stable insights:** Effects present across all iterations with probability shift < 0.1
and `council_agreement` >= 3. These survived adversarial pressure.

**Fragile insights:** Effects with HIGH sensitivity assumptions, wide probability ranges
(> 0.3), or `council_agreement` < 3. These depend on assumptions that could be wrong.

### Step 3: Generate Recommendation

Apply expected value reasoning across the hypothesis space:
- For each hypothesis, compute the expected net impact by weighting effects by probability
- Factor in worst-case scenarios from the adversary phase
- Identify the action with the best expected outcome ACROSS hypotheses
- Note which assumptions the recommendation depends on

### Step 4: Write Decision Brief

Write `DECISION-BRIEF.md` using the template from `references/output-format.md`.

### Step 5: Print Brief to User

After writing the file, print the full Decision Brief to the conversation so the
user can see it immediately.

## Handling Incomplete Data

If phases are missing (status: partial or file missing):
- Note which phases are incomplete in the Brief header
- Reduce confidence rating accordingly
- Proceed with available data — an incomplete analysis is better than no analysis

## Convergence Status in Brief

- **Converged at iteration N:** "Insights stabilized after N iterations of adversarial pressure."
- **NOT REACHED after 3 iterations:** "Convergence not reached. This decision has genuine
  unresolvable uncertainty. The effects below represent the best available analysis but
  may shift with additional iteration. Delta values: [effects_delta], [assumption_stability],
  [ranking_flips], [contradictions]."

## Quick Mode Variant

For `/autodecision:quick`, Phase 8 produces a lighter brief:
- No convergence data (single pass)
- No council agreement (no council)
- No sensitivity analysis
- No adversary scenarios
- Probabilities are point estimates only (no ranges)
- Still includes: hypotheses, effects, assumptions, recommendation
