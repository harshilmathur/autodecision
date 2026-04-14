# Phase 5: ADVERSARY

## Purpose
Red-team the decision. Actively try to break the conclusions from Phase 3-4
by simulating worst-case scenarios, irrational actors, and black swans.

## Inputs
- `iteration-{N}/effects-chains.json`
- (Adversary does NOT read critique.json — it runs PARALLEL with Critique.
  Independent red-teaming finds different things than building on critique findings.
  Accept occasional duplicate findings; dedup in synthesis.)

## Outputs
- `iteration-{N}/adversary.json`

## Process

This phase does NOT use the council. It runs as a single adversarial analysis pass.

### Step 1: Worst-Case Scenarios

For each hypothesis in `effects-chains.json`, generate 1-2 worst-case scenarios:
- What if the most optimistic effects don't materialize AND the most pessimistic do?
- What if multiple negative effects compound simultaneously?
- What is the plausible worst outcome within the first 6 months?

### Step 2: Irrational Actor Analysis

For each external actor referenced in the effects (competitors, regulators, customers):
- What if they act emotionally rather than rationally?
- What if they overreact or underreact to the decision?
- What if they have information you don't?

### Step 3: Black Swan Identification

Generate 2-3 low-probability, high-impact events that would invalidate the analysis:
- Market-level events (recession, regulatory change, technology shift)
- Company-level events (key person leaves, funding falls through, security breach)
- Domain-specific events (competitor acquisition, viral negative press)

### Step 4: Assumption Stress Test

For each assumption in `effects-chains.json > all_assumptions`:
- What evidence would DISPROVE this assumption?
- How easily could this assumption become false?
- Is there a historical precedent where this assumption was wrong?

Assign each assumption a `fragility_score`: "SOLID" / "SHAKEABLE" / "FRAGILE"

### Output Format

```json
{
  "status": "complete",
  "worst_cases": [
    {
      "scenario_id": "wc1_compound_negative",
      "description": "Price cut fails to drive acquisition (price insensitivity) while triggering competitor response and increasing churn among existing enterprise customers",
      "trigger_conditions": ["price_sensitivity_low", "competitor_aggressive"],
      "affected_hypotheses": ["h1_price_growth"],
      "severity": "HIGH",
      "probability_estimate": 0.15
    }
  ],
  "irrational_actors": [
    {
      "actor": "Primary competitor",
      "rational_response": "Match price selectively for contested accounts",
      "irrational_response": "Slash prices 40% across the board as emotional overreaction",
      "probability_of_irrational": 0.20,
      "impact_if_irrational": "HIGH — triggers price war that destroys margins for both"
    }
  ],
  "black_swans": [
    {
      "event": "Competitor gets acquired by major tech company with deep pockets",
      "probability": 0.10,
      "impact": "HIGH — changes competitive dynamics entirely",
      "invalidates": ["h1_price_growth", "h3_minimal_impact"]
    }
  ],
  "assumption_stress_test": [
    {
      "assumption_key": "price_sensitivity_high",
      "fragility_score": "SHAKEABLE",
      "disproof_evidence": "If enterprise buyers purchase based on vendor relationship and integration, not price",
      "historical_precedent": "Salesforce raised prices 20% in 2023 with minimal churn"
    }
  ]
}
```
