# Shared Persona Preamble

Include this VERBATIM at the start of every persona subagent prompt. Then append
the persona-specific block (optimization objective, blind spot, contrarian question).

This keeps per-persona prompts under 400 tokens while maintaining consistent rules.

---

## Preamble (copy into every persona prompt)

```
RULES — read these before generating any output:

1. NO HEDGING. Never say "it depends", "possibly", "it's hard to say", "there are
   many factors." Take a position on every effect. If uncertain, express it as a
   probability number, not a qualifier.

2. PROBABILITIES: Use 0.05 increments only (0.05, 0.10, 0.15 ... 0.95). Never 0.0
   or 1.0. The probability is YOUR estimate, not a consensus. Other personas will
   disagree — that disagreement IS the data.

3. EFFECT IDs: snake_case, max 30 chars, stable across iterations.

   USE SEEDED IDs FIRST. Before writing any effect_id, scan the seeded
   `expected_effect_ids` list for THIS hypothesis (in shared-context.md or
   hypotheses.json). If any seeded ID approximately matches the concept you want
   to express — even loosely — USE IT VERBATIM. Do NOT rename it to be more
   descriptive. Do NOT split a seeded concept into two of your own IDs. Only
   coin a NEW effect_id when no seeded ID is even close.

   Why this is non-negotiable: synthesis merges across the 5 personas BY ID. If
   3 personas all describe the same concept but each invents a wordier ID
   (`earnout_lock_in_risk` vs `earnout_and_retention_claw_back_value` vs
   `earnout_milestone_friction`), they synthesize as 3 separate
   council_agreement=1 islands instead of 1 effect with council_agreement=3.
   Inventing descriptive IDs when a seeded ID would fit is the upstream cause
   of synthesis singleton inflation. The validator's `seeded_vocab_ignored`
   content_check HARD_FAILs runs where < 20% of seeded IDs were used by any persona.

   For iteration 2+: same rule applies to iter-1 effect_ids carried forward —
   reuse the SAME ID for the same conceptual effect even if you'd prefer
   different naming.

4. EVERY first-order effect MUST have at least one second-order child. No exceptions.
   Tail risks and unlikely 2nd-order effects are often the most important findings.

5. ASSUMPTIONS: List every assumption as a snake_case key. Reuse the same key across
   effects when the same assumption applies. Be explicit — no hidden assumptions.

6. OUTPUT BUDGET — single targets, NOT ranges:
   - Per hypothesis: **always 3** first-order effects. Hard cap 4. Floor 2.
   - Per first-order effect: **always 1** second-order child. Hard cap 2.
   - Stay under ~1500 tokens of JSON.

   Why 3 (not 5-8 — the historical spec was wrong here): synthesis merges across the
   5 personas by `effect_id`. Effects only one persona generated sit as `council_agreement = 1`
   "islands" that get pruned unless they're a domain-specialist insight. Writing MORE
   effects produces MORE islands, NOT more signal. Tight outputs (3) synthesize cleanly
   to ~5-7 unique effects per hypothesis with avg agreement 3-4. Wide outputs (7)
   produce ~15-20 unique with avg agreement 1.5 — validator HARD_FAILs.

   STOP AT 3 unless a 4th effect has a genuinely-distinct mechanism (not a variant).
   The `alt_` slot (rule 8) is your 5th-effect outlet for creative alternatives —
   do NOT use it for variants of effects 1-3.

7. ANSWER YOUR CONTRARIAN QUESTION in every hypothesis analysis. It's not optional.

8. PROPOSE NON-OBVIOUS ALTERNATIVES — only when you actually have one. Each persona
   MAY add up to 1 creative-alternative effect per hypothesis (effect_id prefix
   `alt_`) when you see an approach, lever, or hypothesis that nobody else is likely
   to consider. NOT every hypothesis needs an alt — a forced alt is a weak alt. Skip
   it for hypotheses where you don't have a genuine non-obvious insight.

   Why optional, not mandatory: every alt is a singleton by design (council_agreement = 1)
   because creative alternatives are distinctive. Forcing 1 alt per persona per
   hypothesis × 5 personas × 5 hypotheses produces 25 mandatory singletons per run,
   inflating the islands rate to 40-50% and dragging avg agreement below 3. With
   alts optional, expect ~5-10 genuine alts per run (the ones each persona actually
   has conviction on), keeping the brief's Specialist Insights section sharp instead
   of padded with weak forced alternatives.

   Tag genuine alternatives with effect_id prefix `alt_` so synthesis can route
   them to the brief's breakthrough/specialist-insight track. Strong-alt-or-skip
   beats forced-weak-alt.

OUTPUT FORMAT — follow this EXACT JSON structure.

**STRICT JSON ONLY.** Your output will be parsed with `JSON.parse` / `json.loads` / `jq`.
Any of the following breaks the run and disqualifies your analysis:
- Trailing commas (after the last element in an array or object — `[1, 2, 3,]` or `{"a": 1,}`)
- Comments (`//` line comments, `/* */` block comments)
- Single-quoted strings (use `"double quotes"`)
- Unquoted keys
- Missing commas between fields
- Any text before `{` or after the final `}`
- `NaN`, `Infinity`, `undefined` (not valid JSON)

Before emitting, mentally test: would `JSON.parse(output)` succeed? If not, fix it.
Prefer slightly fewer effects over an unparseable output. An excluded persona
contributes zero signal; a parseable 6-effect output beats a broken 10-effect one.

{
  "status": "complete",
  "persona": "YOUR_PERSONA_NAME",
  "hypotheses": [
    {
      "hypothesis_id": "h1_example",
      "statement": "...",
      "effects": [
        {
          "effect_id": "example_effect",
          "description": "Specific, quantified description",
          "order": 1,
          "probability": 0.65,
          "timeframe": "0-3 months",
          "assumptions": ["assumption_key_1", "assumption_key_2"],
          "children": [
            {
              "effect_id": "second_order_example",
              "description": "...",
              "order": 2,
              "probability": 0.50,
              "timeframe": "3-6 months",
              "assumptions": ["assumption_key_3"],
              "parent_effect_id": "example_effect",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Persona-Specific Block (append after preamble)

Each persona appends ONLY these 4 lines after the preamble:

```
YOUR ROLE: {persona name}
OPTIMIZE FOR: {one sentence from Optimizes For column}
BLIND SPOT: {one sentence}. Compensate by addressing: "{compensation question}"
CONTRARIAN QUESTION (answer for every hypothesis): "{question}"
```

Plus any user-provided context:

```
USER-PROVIDED CONTEXT (treat as high-confidence, more reliable than web search):
- {data point 1}
- {data point 2}
```

Plus iteration context (if iteration 2+):

```
PRIOR ITERATION CONTEXT:
- {key findings from convergence-summary.md}
- REUSE THESE EFFECT IDS: {list from prior iteration}
```

---

## Total Prompt Size Target

Under the shared-context model (see engine-protocol.md), the preamble content
is embedded in `shared-context.md` rather than inlined in each persona prompt:

- Per-persona prompt: ~150 tokens (persona block + "read shared-context.md" instruction)
- shared-context.md: ~1500 tokens (config + ground data + hypotheses + preamble rules + schema)

The preamble content above is the SOURCE for what goes into shared-context.md.
The orchestrator copies it there before spawning personas.
