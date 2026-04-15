# Phase 4: CRITIQUE

## Purpose
Anonymized peer review. Each persona reviews the others' analyses, ranks them,
and identifies flaws. This surfaces genuine disagreements and evaluates arguments
on merit rather than source.

## Inputs
- `iteration-{N}/council/*.json` (all 5 persona files)

## Outputs
- `iteration-{N}/peer-review.json` (rankings + anonymization map)
- `iteration-{N}/critique.json` (consolidated flaws and blind spots)

## Process

### Step 1: Create Anonymization Mapping

Generate a RANDOM mapping of personas to anonymous labels A-E.
Different mapping each iteration to prevent pattern recognition.

```json
{"A": "competitor", "B": "optimist", "C": "regulator", "D": "pessimist", "E": "customer"}
```

### Step 2: Prepare Anonymized Analyses

For each persona file in `council/*.json`:
- Strip the `"persona"` field
- Replace with the anonymous label
- Combine all 5 into a single anonymized document

### Step 3: Spawn 5 Reviewer Subagents (PARALLEL)

Each subagent receives:
- All 5 analyses labeled "Analysis A" through "Analysis E"
- Instruction: "You are reviewing 5 analyses of the same decision. Review all
  analyses EXCEPT [your own label]. Rank the other 4 from strongest to weakest."
- Each reviewer does NOT know which label is theirs (the mapping ensures they
  review based on argument quality, not persona familiarity)

Each reviewer outputs:
- Ranking of the other 4 analyses (strongest to weakest)
- For each analysis: 1-2 sentence explanation of strengths/weaknesses
- Top 3 flaws, blind spots, or missing variables across ALL analyses

### Step 4: Aggregate and Write

1. Collect all 5 reviewer outputs.
2. Compute aggregate rankings (average position per analysis, lower = better).
3. Compile all identified flaws into a deduplicated list.
4. Write `peer-review.json` with mapping, individual rankings, and aggregates.
5. Write `critique.json` with:

```json
{
  "status": "complete",
  "flaws": [
    {
      "flaw_id": "f1_missing_churn",
      "description": "No analysis modeled existing customer churn from price confusion",
      "identified_by_count": 3,
      "affected_effects": ["acq_increase", "revenue_per_customer_drop"],
      "suggested_fix": "Add churn effect with sensitivity to customer communication strategy"
    }
  ],
  "missing_variables": [
    "Customer communication strategy",
    "Implementation timeline"
  ],
  "strongest_analysis": "A (competitor strategist)",
  "weakest_analysis": "D (pessimist — too generic, not grounded in data)"
}
```
