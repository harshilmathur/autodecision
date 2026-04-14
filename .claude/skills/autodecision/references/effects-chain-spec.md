# Effects Chain JSON Specification

## Core Data Structure

Every simulation output (per persona and synthesized) uses this format.

### Per-Persona Output (`council/{persona}.json`)

```json
{
  "status": "complete",
  "persona": "optimist",
  "hypotheses": [
    {
      "hypothesis_id": "h1_price_growth",
      "statement": "Price cut drives 30-40% customer acquisition growth",
      "effects": [
        {
          "effect_id": "acq_increase",
          "description": "Customer acquisition increases 30-40%",
          "order": 1,
          "probability": 0.75,
          "timeframe": "0-3 months",
          "assumptions": ["price_sensitivity_high", "market_not_saturated"],
          "children": [
            {
              "effect_id": "support_cost_rise",
              "description": "Support costs increase 25% due to larger user base",
              "order": 2,
              "probability": 0.80,
              "timeframe": "3-6 months",
              "assumptions": ["no_automation_investment"],
              "parent_effect_id": "acq_increase",
              "children": []
            },
            {
              "effect_id": "wom_acceleration",
              "description": "Word of mouth accelerates growth beyond paid channels",
              "order": 2,
              "probability": 0.45,
              "timeframe": "6-12 months",
              "assumptions": ["product_quality_maintained", "nps_above_50"],
              "parent_effect_id": "acq_increase",
              "children": []
            }
          ]
        },
        {
          "effect_id": "revenue_per_customer_drop",
          "description": "Revenue per customer drops 20% immediately",
          "order": 1,
          "probability": 0.95,
          "timeframe": "immediate",
          "assumptions": ["no_upsell_offset"],
          "children": []
        }
      ]
    }
  ]
}
```

### Synthesized Output (`effects-chains.json`)

After all 5 personas complete, the synthesis pass produces:

```json
{
  "status": "complete",
  "iteration": 1,
  "hypotheses": [
    {
      "hypothesis_id": "h1_price_growth",
      "statement": "Price cut drives 30-40% customer acquisition growth",
      "effects": [
        {
          "effect_id": "acq_increase",
          "description": "Customer acquisition increases 30-40%",
          "order": 1,
          "probability": 0.70,
          "probability_range": [0.50, 0.85],
          "council_agreement": 4,
          "timeframe": "0-3 months",
          "assumptions": ["price_sensitivity_high", "market_not_saturated"],
          "children": [...]
        }
      ]
    }
  ],
  "all_assumptions": {
    "price_sensitivity_high": {
      "description": "Target market is highly sensitive to price changes",
      "referenced_by": ["acq_increase", "wom_acceleration"],
      "sensitivity": null
    },
    "market_not_saturated": {
      "description": "There is meaningful unserved demand in the market",
      "referenced_by": ["acq_increase"],
      "sensitivity": null
    }
  }
}
```

## Field Definitions

### Effect Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `effect_id` | string | YES | Stable identifier. Snake_case. Survives across iterations. The Judge compares by this ID. Examples: `acq_increase`, `competitor_price_war`, `burn_rate_rise`. |
| `description` | string | YES | Human-readable description. May change wording between iterations (that's fine, the `effect_id` is the stable key). |
| `order` | integer | YES | 1 = first-order (direct consequence of decision). 2 = second-order (consequence of a first-order effect). |
| `probability` | float | YES | Per-persona: that persona's estimate (0.0-1.0). Synthesized: median across all personas who generated this effect. |
| `probability_range` | [float, float] | Synthesized only | [min, max] across all persona estimates. Only present in `effects-chains.json`, not individual persona files. |
| `council_agreement` | integer | Synthesized only | Count of personas (out of 5) who independently generated this effect. Only in `effects-chains.json`. |
| `specialist_insight` | boolean | Synthesized only | `true` if council_agreement is 1 AND the generating persona's domain expertise is directly relevant to this effect. See Specialist Insight Rules below. |
| `source_persona` | string | Synthesized only | Which persona generated this effect. Only set when `council_agreement` is 1 or 2. Helps trace specialist insights. |
| `timeframe` | string | YES | When this effect manifests. Use: "immediate", "0-3 months", "3-6 months", "6-12 months", "12+ months". |
| `assumptions` | [string] | YES | Array of assumption keys this effect depends on. Keys must match entries in `all_assumptions`. |
| `parent_effect_id` | string | 2nd-order only | The `effect_id` of the first-order effect that triggers this second-order effect. |
| `children` | [Effect] | YES | Array of second-order effects triggered by this effect. Empty array `[]` if none. |

### Assumption Object (in `all_assumptions`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | YES | Human-readable description of the assumption. |
| `referenced_by` | [string] | YES | Array of `effect_id`s that depend on this assumption. |
| `sensitivity` | string or null | After Phase 6 | "HIGH" / "MEDIUM" / "LOW" based on sensitivity analysis. null before Phase 6 runs. |

### Hypothesis Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hypothesis_id` | string | YES | Stable identifier. Format: `h{N}_{short_descriptor}`. Example: `h1_price_growth`. |
| `statement` | string | YES | One-sentence hypothesis statement. |
| `effects` | [Effect] | YES | Array of first-order effects (with nested children for second-order). |

## Specialist Insight Rules

An effect with `council_agreement` = 1 is NOT automatically low-value. If the single
persona who generated it has domain expertise directly relevant to the effect, it is
a **specialist insight** — something the majority correctly missed because it's outside
their lens, but the specialist correctly caught.

Tag `specialist_insight: true` when ALL of these are true:
1. `council_agreement` = 1
2. The generating persona's optimization domain matches the effect's domain:
   - **Regulator** generated a compliance, legal, regulatory, or contractual effect
   - **Competitor** generated a competitive dynamics, market response, or industry effect
   - **Customer** generated a user experience, adoption, or retention effect
   - **Optimist** generated a creative alternative or non-obvious opportunity
   - **Pessimist** generated a hidden cost, failure mode, or downside scenario

3. The effect is actionable (not vague speculation)

**Display rule:** Specialist insights appear in the HIGH-CONFIDENCE section of the
Decision Brief (not the exploratory section), tagged with `[SPECIALIST: {persona}]`.
They are treated as important findings that only one expert was equipped to see,
not as low-consensus noise.

**Examples from test runs:**
- Regulator finding MFN clause exposure (1/5) → SPECIALIST (domain match)
- Regulator finding PCI scope expansion (1/5) → SPECIALIST (domain match)
- Optimist finding productization upside (1/5) → SPECIALIST (creative alternative)
- Pessimist finding shadow AI risk (1/5) → NOT specialist (all personas should see this)

## `effect_id` Rules

The `effect_id` is the most important field in the system. It enables mechanical
convergence detection.

1. **Assigned in Phase 3 (SIMULATE)** by each persona independently.
2. **Stable across iterations.** If "customer acquisition increases" appears in iteration 1
   as `acq_increase`, it MUST keep the same ID in iteration 2 even if the description
   or probability changes.
3. **Snake_case, descriptive, max 30 chars.** Examples: `acq_increase`, `competitor_match`,
   `burn_rate_rise`, `regulatory_block`, `churn_spike`.
4. **Personas may generate the same effect with different IDs.** The synthesis pass deduplicates
   by semantic similarity: if two effects have different IDs but describe the same outcome,
   the synthesis pass merges them under one ID (preferring the ID used by more personas).
5. **New effects get new IDs.** If Phase 5 (ADVERSARY) introduces a new effect not seen in
   prior iterations, it gets a new `effect_id` and the Judge counts it as an "added" effect
   in the delta calculation.

## Probability Rules

1. **Range: 0.01 to 0.99.** Never assign 0.0 or 1.0. Nothing is certain.
2. **Granularity: 0.05 increments.** Use 0.05, 0.10, 0.15... not 0.07 or 0.13. This reduces
   false precision.
3. **Median for synthesis.** The synthesized probability is the median of all persona estimates.
   Not the mean (which is pulled by outliers).
4. **Range is [min, max].** The disagreement range is the actual min and max across personas,
   not a confidence interval.
5. **Wide range = high uncertainty.** If `probability_range` spans > 0.3, flag this effect
   as "high uncertainty" in the Decision Brief.
6. **Council agreement threshold.** Effects with `council_agreement` < 3 (fewer than 3 of 5
   personas generated them) should be flagged as "low consensus" in the Decision Brief.

## Config Schema (`config.json`)

```json
{
  "status": "complete",
  "decision_statement": "Should we cut pricing by 20%?",
  "sub_questions": [
    "How will customers react to the price change?",
    "How will competitors respond?",
    "What happens to unit economics?",
    "What are the second-order market effects?"
  ],
  "constraints": [
    "Must maintain positive unit economics within 12 months",
    "Cannot lose more than 5% of existing customers"
  ],
  "grounding": "GROUNDED",
  "template_used": null,
  "created_at": "2026-04-14T12:00:00Z"
}
```

## Hypotheses Schema (`hypotheses.json`)

```json
{
  "status": "complete",
  "hypotheses": [
    {
      "hypothesis_id": "h1_price_growth",
      "statement": "Price cut drives significant customer acquisition growth that offsets revenue loss",
      "sub_questions_addressed": ["sq1_customer_reaction", "sq3_unit_economics"],
      "key_assumptions": ["price_sensitivity_high", "market_not_saturated"]
    },
    {
      "hypothesis_id": "h2_price_war",
      "statement": "Price cut triggers competitor response leading to race-to-bottom",
      "sub_questions_addressed": ["sq2_competitor_response", "sq4_market_effects"],
      "key_assumptions": ["competitor_monitors_pricing", "competitor_has_margin_room"]
    },
    {
      "hypothesis_id": "h3_minimal_impact",
      "statement": "Price cut has minimal impact because market is not price-sensitive",
      "sub_questions_addressed": ["sq1_customer_reaction"],
      "key_assumptions": ["market_is_value_driven", "switching_costs_high"]
    }
  ]
}
```

## Judge Score Schema (`judge-score.json`)

```json
{
  "status": "complete",
  "iteration": 2,
  "parameters": {
    "effects_delta": 1,
    "assumption_stability_pct": 85,
    "ranking_flip_count": 0,
    "contradiction_count": 0
  },
  "thresholds_met": {
    "effects_delta": true,
    "assumption_stability": true,
    "ranking_flip_count": true,
    "contradiction_count": true
  },
  "converged": true,
  "notes": "All thresholds met. Effects stable. One assumption updated from adversary phase but did not shift any probability by more than 0.1."
}
```

## Peer Review Schema (`peer-review.json`)

```json
{
  "status": "complete",
  "anonymization_mapping": {
    "A": "competitor",
    "B": "optimist",
    "C": "regulator",
    "D": "pessimist",
    "E": "customer"
  },
  "reviews": [
    {
      "reviewer": "optimist",
      "reviewed_labels": ["A", "C", "D", "E"],
      "ranking": ["A", "E", "C", "D"],
      "reasoning": "Analysis A has the strongest competitive dynamics modeling..."
    }
  ],
  "aggregate_rankings": [
    {"persona": "competitor", "label": "A", "average_rank": 1.5},
    {"persona": "customer", "label": "E", "average_rank": 2.0},
    {"persona": "regulator", "label": "C", "average_rank": 2.75},
    {"persona": "pessimist", "label": "D", "average_rank": 3.25},
    {"persona": "optimist", "label": "B", "average_rank": 3.5}
  ]
}
```

## Sensitivity Schema (`sensitivity.json`)

```json
{
  "status": "complete",
  "analyses": [
    {
      "assumption_key": "price_sensitivity_high",
      "original_value": "Target market is highly sensitive to price changes",
      "varied_to": "Target market has moderate price sensitivity (value-driven, not price-driven)",
      "effects_impacted": [
        {
          "effect_id": "acq_increase",
          "original_probability": 0.70,
          "revised_probability": 0.25,
          "shift": -0.45
        }
      ],
      "conclusion_flipped": true,
      "sensitivity_rating": "HIGH"
    }
  ],
  "assumption_sensitivity_ranking": [
    {"key": "price_sensitivity_high", "rating": "HIGH", "effects_impacted_count": 3},
    {"key": "competitor_monitors_pricing", "rating": "MEDIUM", "effects_impacted_count": 2},
    {"key": "no_upsell_offset", "rating": "LOW", "effects_impacted_count": 1}
  ]
}
```
