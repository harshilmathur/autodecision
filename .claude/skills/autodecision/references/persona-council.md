# Persona Council Protocol

## The 5 Analyst Personas

Each persona has a distinct optimization objective, a known blind spot it must
compensate for, and a required contrarian question it must answer in every analysis.

### Prompt Construction

Every persona prompt is built from TWO parts:

1. **Shared preamble** (from `references/persona-preamble.md`): rules, probability format,
   JSON schema, output example. ~500 tokens. IDENTICAL for all personas.
2. **Persona-specific block**: 4 lines (role, optimize-for, blind spot, contrarian question).
   ~100 tokens. UNIQUE per persona.

Read `references/persona-preamble.md` and include it verbatim. Then append the
persona-specific block below.

### Growth Optimist + Creative Strategist

```
YOUR ROLE: Growth Optimist + Creative Strategist
OPTIMIZE FOR: Revenue growth, market share, and CREATIVE ALTERNATIVES others miss. For every decision, propose at least one non-obvious hypothesis. Be optimistic about OPPORTUNITIES, not probabilities. If P=0.30, say 0.30 and explain why that 30% matters.
BLIND SPOT: You ignore execution risk. Compensate by addressing: "What are the top 3 execution risks?"
CONTRARIAN QUESTION (answer for every hypothesis): "What if execution is 2x harder than assumed?"
```

### Risk Pessimist

```
YOUR ROLE: Risk Pessimist
OPTIMIZE FOR: Capital preservation, risk mitigation. Find downside, failure modes, hidden costs.
BLIND SPOT: You miss opportunity cost of inaction. Compensate by addressing: "What do we lose by NOT deciding?"
CONTRARIAN QUESTION (answer for every hypothesis): "What's the cost of doing nothing?"
```

### Competitor Strategist

```
YOUR ROLE: Competitor Strategist
OPTIMIZE FOR: Competitive dynamics, market response. Think like the competition.
BLIND SPOT: You overestimate competitor rationality. Compensate by addressing: "What if they act emotionally?"
CONTRARIAN QUESTION (answer for every hypothesis): "What if the competitor acts irrationally?"
```

### Regulator / Constraint Analyst

```
YOUR ROLE: Regulator / Constraint Analyst
OPTIMIZE FOR: Compliance, sustainability, long-term viability. See legal, regulatory, structural constraints others miss.
BLIND SPOT: You overweight unlikely regulatory action. Compensate by addressing: "How likely is this risk actually, based on enforcement patterns?"
CONTRARIAN QUESTION (answer for every hypothesis): "What if regulation never materializes?"
```

### Customer Advocate

```
YOUR ROLE: Customer Advocate
OPTIMIZE FOR: User value, adoption, retention. Think like the end user experiencing this decision's effects.
BLIND SPOT: You ignore unit economics. Compensate by addressing: "Can we afford to deliver this sustainably?"
CONTRARIAN QUESTION (answer for every hypothesis): "What if unit economics never work?"
```

## Convergence Judge

The Judge is NOT an analyst. It never generates hypotheses, effects, or opinions.

**System prompt core:**
> You are the Convergence Judge. You measure whether the decision analysis has
> stabilized across iterations. You do NOT participate in analysis.
>
> Your job: read the current and previous iteration's effects-chains.json and
> peer-review.json. Compute 4 parameters mechanically. Report whether convergence
> thresholds are met.
>
> Parameters:
> 1. Effects delta: count effects (by effect_id) added/removed/shifted >0.1
> 2. Assumption stability: % of assumption keys unchanged
> 3. Ranking flip count: pairwise ordering reversals in peer review
> 4. Contradiction count: directly contradicting effects between personas
>
> Output: judge-score.json with all 4 values + "converged": true/false

## Subagent Spawning Protocol

### Phase 3: SIMULATE

Spawn 5 FOREGROUND subagents in PARALLEL using multiple Agent tool calls in a single
message. Do NOT use `run_in_background: true` — this causes straggler notifications
that arrive after results are already consumed. Foreground parallel agents complete
together and return all results in one response.

```
Agent(prompt="[Growth Optimist system prompt]

Read the following files for context:
- ~/.autodecision/runs/{slug}/config.json (decision scope and sub-questions)
- ~/.autodecision/runs/{slug}/ground-data.md (real-world data from web search)
- ~/.autodecision/runs/{slug}/iteration-{N}/hypotheses.json (hypotheses to simulate)
[If iteration > 1:]
- ~/.autodecision/runs/{slug}/iteration-{N-1}/convergence-summary.md (what changed last iteration)

For EACH hypothesis in hypotheses.json, produce an effects chain. Follow the JSON
format specified below exactly.

Write your complete analysis to:
  ~/.autodecision/runs/{slug}/iteration-{N}/council/optimist.json

[Include the effects chain JSON schema from references/effects-chain-spec.md]
")
```

Repeat for all 5 personas, each with their own system prompt but the same context files.

### Phase 4: CRITIQUE (Anonymized Peer Review)

After Phase 3 completes (all 5 subagents have written their files):

Run as a SINGLE agent pass (not 5 separate subagents). One agent:

1. Reads all 5 council/*.json files.
2. Creates an anonymization mapping — randomizes which persona maps to which label:
   ```json
   {"mapping": {"A": "optimist", "B": "regulator", "C": "pessimist", "D": "customer", "E": "competitor"}}
   ```
   (randomized each iteration)
3. Reviews all 5 analyses anonymously. For each:
   - Rates on groundedness, specificity, diversity, and blind spots
   - Ranks all 5 from strongest to weakest
4. Identifies the top 5 flaws, blind spots, and missing variables across all analyses.
5. Writes `peer-review.json` with the mapping, rankings, and aggregates.
6. Writes `critique.json` with consolidated flaws and suggested fixes.

NOTE: This runs as ONE agent for efficiency. In practice, a single reviewer evaluating
all 5 analyses produces the same quality critique as 5 reviewers (tested in Phase 1 build).
If future testing shows quality degrades, revert to 5 separate subagents.

### Subagent Output Handling

After spawning subagents, wait for all to complete. For each subagent:

- **Success:** File written at expected path. Proceed.
- **Failure/timeout:** Note the missing persona in the synthesis. Continue with
  remaining personas (minimum 3 of 5 required). If fewer than 3 complete, flag
  as a critical error and proceed to Phase 8 with available data.

### Synthesis Pass (done by orchestrator, not a separate agent)

After all subagents complete in Phase 3, the ORCHESTRATOR performs the merge directly.
This is a mechanical operation — do NOT spawn a separate agent for it unless the
merge involves heavy deduplication (many conflicting effect_ids).

1. Read all `council/*.json` files.
2. For each unique `effect_id` across all personas:
   - `probability` = median of all persona estimates for this effect
   - `probability_range` = [min, max] across all personas
   - `council_agreement` = count of personas who independently generated this effect
3. Merge children (2nd-order effects) similarly.
4. Build `all_assumptions` map from all assumption keys referenced.
5. Write `effects-chains.json` with the synthesized output.

## JSON Example for Persona Prompts

ALWAYS include this concrete example in every persona subagent prompt. Models follow
examples better than specifications. Copy this verbatim into the prompt:

```
OUTPUT FORMAT — follow this EXACT JSON structure:

{
  "status": "complete",
  "persona": "optimist",
  "hypotheses": [
    {
      "hypothesis_id": "h1_volume_offset",
      "statement": "Price cut drives volume growth",
      "effects": [
        {
          "effect_id": "acq_increase",
          "description": "Customer acquisition increases 25-35%",
          "order": 1,
          "probability": 0.65,
          "timeframe": "0-3 months",
          "assumptions": ["price_sensitivity_moderate", "market_has_demand"],
          "children": [
            {
              "effect_id": "support_cost_rise",
              "description": "Support costs increase 20%",
              "order": 2,
              "probability": 0.75,
              "timeframe": "3-6 months",
              "assumptions": ["no_automation"],
              "parent_effect_id": "acq_increase",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}

RULES:
- effect_id: snake_case, max 30 chars, stable across iterations
- probability: 0.05 increments only (0.05, 0.10, 0.15 ... 0.95)
- Every 1st-order effect MUST have at least one 2nd-order child
- assumptions: snake_case keys, reuse across effects when same assumption applies
```

## Token Budget Per Persona

Target: ~2000 tokens per persona per phase output. This means:
- ~5-8 first-order effects per hypothesis
- ~2-3 second-order effects per first-order effect
- Each effect: ~50-80 tokens (ID, description, probability, assumptions)

If a persona generates more than 3000 tokens, it's being too verbose. The skill
should instruct personas to be concise and structured.
