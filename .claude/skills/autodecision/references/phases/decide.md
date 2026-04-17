<!--
phase: 8
phase_name: DECIDE
runs_in:
  - full       (after final iteration, OR concurrent-start once Sensitivity completes if final iteration is known)
  - medium     (after iteration-1 completes; brief notes "Iterations: 1 | Converged: N/A (medium mode)")
  - quick      (lighter brief — see Quick Mode Variant section below)
  - revise     (writes new DECISION-BRIEF.md with revision header — see references/phases/revise.md)
reads:
  - ~/.autodecision/runs/{slug}/config.json
  - ~/.autodecision/runs/{slug}/ground-data.md
  - ~/.autodecision/runs/{slug}/context-extracted.md (if --context was provided)
  - ~/.autodecision/runs/{slug}/user-inputs.md (if exists)
  - ~/.autodecision/runs/{slug}/iteration-{LATEST}/{effects-chains,sensitivity,adversary,peer-review}.json
  - ~/.autodecision/runs/{slug}/convergence-log.json
  - references/output-format.md (template)
  - references/brief-schema.json (canonical structure — drives which sections appear per mode)
  - references/persona-council.md (Canonical Persona Names table — for Specialist/Source columns)
writes:
  - ~/.autodecision/runs/{slug}/DECISION-BRIEF.md
  - ~/.autodecision/runs/{slug}/COMPARISON-VS-QUICK.md (separate artifact, only if quick run exists for same slug)
  - ~/.autodecision/journal.jsonl (append)
  - ~/.autodecision/assumptions.jsonl (append/update)
gates:
  - Section order matches brief-schema.json positions for the active mode
  - Trailing <!-- validator-refs: ... --> block lists every worst_case/black_swan/irrational_actor/effect ID the brief preserves from source JSONs
  - No snake_case in human-readable prose (always use description field, never key/effect_id)
  - Phase 8.5 VALIDATE-BRIEF MUST run after this phase writes the brief
-->

# Phase 8: DECIDE

## Purpose
Make the possibility map legible. The brief is a decision map: what the exploration surfaced, where the council diverged, what survived adversarial pressure, what didn't. A recommendation appears at the end as one synthesis of the map, not as the product.

The possibility map IS the output. The decision is a downstream convenience for readers who need a single action. Do not compress the map to make the recommendation faster to find — the map is why we spent the compute.

## Inputs
- `config.json`, `ground-data.md`
- All iteration outputs (read only the LATEST iteration's files + `convergence-log.json`)
- `convergence-log.json` (full iteration history)

## Outputs
- `DECISION-BRIEF.md`

## CRITICAL: Human-Readable Output

Before writing ANY part of the brief, internalize this rule:

**The brief is a strategy memo for decision-makers. NEVER show internal identifiers.**

When you read `effect_id: "cci_phase2_review"` with `description: "CCI triggers
Phase-2 review"` from effects-chains.json, the brief says "CCI triggers Phase-2
review (P=0.80)" — NEVER "`cci_phase2_review` (0.80)".

Same for assumptions: `bank_partner_willing` in JSON becomes "At least one major
bank willing to partner" in the brief. Always use the `description` field, never
the `key` field.

Same for hypotheses: `h3_build_in_house` becomes "H3: Build the capability in-house".

If you catch yourself writing snake_case or backtick-wrapped identifiers in the
brief text, stop and rewrite. The reader should never see an underscore.

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

### Step 3: Synthesize Findings

The goal of Phase 8 is to make the exploration legible. That means two passes:

**Pass 1 — Map the possibility space.** For each major bucket the loop produced (hypotheses, effects by agreement tier, council dynamics, stable and fragile insights, adversarial scenarios, assumptions), write the section that shows what the exploration found in its own terms. Do NOT pre-summarize toward a recommendation. Do NOT drop a section because "the reader just wants the answer." The map IS the answer.

**Pass 2 — Synthesize a recommendation.** After the map is written, apply expected value reasoning across the hypothesis space:
- For each hypothesis, compute the expected net impact by weighting effects by probability
- Factor in worst-case scenarios and black swans from the adversary phase
- Identify the action with the best expected outcome ACROSS hypotheses
- Note which assumptions the recommendation depends on

The recommendation goes at the end of the brief (section 12), not the top. The Executive Summary at the top gives readers a 30-second preview of the map with the recommendation called out, but it is NOT a substitute for the full Recommendation block at the end.

### Step 4: Write Decision Brief

Write `DECISION-BRIEF.md` using the template from `references/output-format.md`.

**Section list and per-mode required/optional/skip rules: read `references/brief-schema.json`.** That file is canonical — `sections[].position`, `header`, `required_in`, `optional_in`, and `skip_in` arrays drive both the human-readable order below and the Phase 8.5 validator. Never define mode-skip rules inline here; if a section's mode applicability changes, change the schema.

#### Step 4a: Mandatory pre-write schema check

**BEFORE writing a single line of the brief**, do this explicitly:

1. Read `references/brief-schema.json`.
2. For the active mode (`full`, `medium`, `quick`, `revise`), enumerate EVERY `header` whose `required_in` array contains the active mode. Include required subsections (`### Worst Cases`, `### Black Swans`, `### Irrational Actors` under `## Adversarial Scenarios`; `### High-Confidence Effects`, `### Specialist Insights`, `### Exploratory Effects` under `## Effects Map`).
3. Write out the resulting checklist in your working context — literally, one header per line, in schema position order. Example for `full`:
   ```
   [ ] ## Executive Summary
   [ ] ## Data Foundation
   [ ] ## Hypotheses Explored
   [ ] ## Effects Map
         [ ] ### High-Confidence Effects
         [ ] ### Specialist Insights
         [ ] ### Exploratory Effects
   [ ] ## Council Dynamics
   [ ] ## Stable Insights
   [ ] ## Fragile Insights
   [ ] ## Adversarial Scenarios
         [ ] ### Worst Cases
         [ ] ### Black Swans
         [ ] ### Irrational Actors
   [ ] ## Key Assumptions
   [ ] ## Convergence Log
   [ ] ## Recommendation
   [ ] ## Appendix A: Decision Timeline
   [ ] ## Appendix B: Complete Effects Map
   [ ] ## Sources
   ```
4. Write the brief and check each item off as you emit its header.
5. After the draft, before validation, grep your own output for every unchecked item. If any is missing, you have not finished Step 4.

**This is not optional.** Historical runs produced structurally broken briefs because the writer internalized an older 12-section mental model (or the project's stale `CLAUDE.md`) and followed that instead of the schema. The checklist above defeats that failure mode by forcing schema enumeration before composition.

**Header rules (HARD_FAIL if violated):**
- Headers appear in schema position order. No reordering.
- Headers are LITERAL — `## Executive Summary`, never "Bottom Line" or "Summary".
- `## Adversarial Scenarios` is the section title. Never "Adversary Findings" or "Adversary Analysis".
- `## Council Dynamics` opens with the persona legend verbatim as its first content line (see output-format.md).
- `## Recommendation` uses the 7 literal bold labels (`**Action:**`, `**Confidence:**`, `**Confidence reasoning:**`, `**Depends on:**`, `**Monitor:**`, `**Pre-mortem:**`, `**Review trigger:**`) — not prose paragraphs.
- `## Key Assumptions` is a 5-column table, not a numbered list.
- `## Convergence Log` is a 6-column table with one row per iteration.
- Do NOT invent sections not in the schema (no `## Context`, `## Analysis Approach`, `## Methodology`).

#### Step 4b: Write the sections

**Section order (for human reference — schema is canonical):**

1. **Executive Summary** — 6-line bullet box. Decision, Recommendation (called out), Confidence, Hypotheses explored, Deepest disagreement, Dominant risk, Load-bearing assumption. NOT a standalone memo — a preview of the map with the recommendation visible. Literal header "## Executive Summary" — never "Bottom Line", "Headline", or "Summary".
2. **Data Foundation** — tag every external fact [G#]/[D#]/[U#]/[C#:persona] so downstream sections can reuse the tags. If `context-extracted.md` exists, include `[D#]` tagged items alongside ground data.
3. **Hypotheses Explored** (table format)
4. **Effects Map** (High-Confidence / Specialist / Exploratory subsections — top 15 effects by `council_agreement × probability`; the rest go to Appendix B)
5. **Council Dynamics** (who thought what, where they diverged — the diversity signal, not a footnote. MUST include the persona legend as the first line.)
6. **Minority-View Winners** (optional — include only if a single-persona insight became the recommendation)
7. **Stable Insights** (what survived adversarial pressure across iterations)
8. **Fragile Insights** (with decision boundaries)
9. **Adversarial Scenarios** (Worst Cases + Black Swans + Irrational Actors subsections — placed AFTER Stable/Fragile so readers know what held up before seeing what attacks it)
10. **Key Assumptions** (ranked by sensitivity)
11. **Convergence Log** — see schema's `skip_in` for which modes omit
12. **Recommendation** (the full 7-field synthesis block — Action, Confidence, Confidence reasoning, Depends on, Monitor, Pre-mortem, Review trigger). **Depends on** items MUST appear in the Key Assumptions table at position 10 — validator-enforced.
13. **Appendix A: Decision Timeline** — see schema for mode applicability
14. **Appendix B: Complete Effects Map** — every effect not in the top-15 cutoff for section 4. Preserves the full possibility map; keeps main body scannable.
15. **Appendix C: Quick Mode vs Full Loop Comparison** — only emitted when a quick run exists for the same slug
16. **Sources** — one row per [G#]/[U#]/[C#:persona] tag used in the brief. Every specific number cited anywhere needs a tag within 120 chars of the number; every tag needs a row here.

The order signals what matters. Sections 2-11 are the possibility map. Section 12 is one synthesis of that map. Sections 13-16 are reference material. The Executive Summary at section 1 lets decision-makers skim, but the bulk of the brief is exploration.

**After the Sources section, emit ONE trailing `<!-- validator-refs: ... -->` block at the very end.** See Step 4c for the exact format.

**Common failure modes to avoid:**
- Renaming "Executive Summary" to "Bottom Line", "Headline", or "Summary" — use the literal header.
- Renaming "Hypotheses Explored" to "Hypothesis Ranking" or similar — use the literal header.
- Moving Recommendation back to the top — it belongs at section 12.
- Dropping Black Swans or Irrational Actors from Adversarial Scenarios when the adversary phase produced them — never drop a subsection that has source data.
- Compressing Council Dynamics to one line — this is one of the main outputs, not a footnote. At minimum 5 bullets.
- Conflating Stable Insights and the Recommendation — Stable Insights are findings about the map, Recommendation is an action synthesized from those findings.
- Using `effect_id` or `assumption_key` in human-readable text — always use the description field, replace underscores with spaces, capitalize the first letter.

### Step 4c: Emit Validator Reference Block

The brief is post-validated by Phase 8.5, which checks that adversary scenarios,
effects, and convergence rows from the upstream JSONs actually made it into the
brief. The validator reads a **single trailing block** at the bottom of the brief
that lists every source ID the writer preserved. The block is an HTML comment, so
it is invisible when the brief renders.

**Format (one block at the very end of `DECISION-BRIEF.md`):**

```
<!-- validator-refs:
worst_cases: wc1_compound_negative, wc2_volume_offset_fails, wc3_enterprise_churn
black_swans: bs1_competitor_acquisition, bs2_regulatory_shock
irrational_actors: ia1_competitor_overreacts, ia2_sales_misuse
effects: acq_increase, churn_reduction, margin_compression, competitive_response
-->
```

Rules:
- **One block per brief, at the very end** (after the last appendix, before EOF).
- One section per line: `worst_cases:`, `black_swans:`, `irrational_actors:`,
  `effects:`. Only emit a line if you included at least one item of that type.
- IDs comma-separated, snake_case, exactly as they appear in the source JSON.
- Only list IDs for items you actually wrote about in the brief's prose. Do NOT
  pad the list to hit coverage — the validator spot-checks content presence.
- If a scenario appears in source JSON but did not make it into the brief (e.g.,
  you consolidated two worst cases into one), omit its ID. The validator's
  `min_coverage_pct: 60` for worst cases gives you headroom to consolidate.

**Why a trailing block instead of inline comments.** Inline `<!-- ref:id -->`
comments cluttered the raw markdown and bloated the brief. The trailing block
is a machine-readable index — clean for human readers, precise for the validator.

**Backward compatibility.** The validator still accepts the legacy inline
`<!-- ref:{id} -->` format for old briefs. New briefs MUST use the trailing
block. Do not mix formats in one brief.

If the validator reports `cross_ref_coverage_below` on re-validation, check:
1. Did you emit the trailing `<!-- validator-refs: ... -->` block?
2. Do the IDs match source JSON exactly (snake_case, no typos)?
3. Did you list every scenario/effect that appears in the prose?

### Step 5: Persist to Journal and Assumption Library

**This step is MANDATORY. The journal and assumption library are the compounding
knowledge assets. Without them, /autodecision:review and /autodecision:export
have nothing to work with.**

**5a. Append to journal.jsonl:**

```bash
# Create file if it doesn't exist
touch ~/.autodecision/journal.jsonl
```

Construct a journal entry JSON object (see `references/journal-spec.md` for full schema):
- `decision_id`: the run slug
- `decision_statement`: from config.json
- `timestamp`: current ISO 8601
- `mode`: "full" or "quick"
- `iterations`: number completed
- `converged`: boolean
- `recommendation`: one-line action from the brief
- `confidence`: HIGH/MEDIUM/LOW
- `hypotheses`: array of {hypothesis_id, statement, status}
- `top_effects`: top 3-5 effects by council_agreement and probability
- `load_bearing_assumptions`: assumptions with sensitivity HIGH
- `decision_boundaries`: from sensitivity analysis
- `tilt`: from config.json
- `outcome`: null (set later via /autodecision:review)

Append this as ONE line to `~/.autodecision/journal.jsonl`.

**5b. Update assumption library:**

```bash
touch ~/.autodecision/assumptions.jsonl
```

For each assumption in the final `effects-chains.json > all_assumptions`:
- Read `~/.autodecision/assumptions.jsonl`
- If assumption key already exists: append a reference entry updating `times_referenced`
  and adding this `decision_id`
- If assumption key is new: append a new assumption entry with `first_seen`, initial
  `times_referenced: 1`, and this decision's sensitivity/fragility ratings

### Step 5b: Revision Chain Header

Before finalizing the brief, check if revisions of this decision exist:

```bash
ls -d ~/.autodecision/runs/{slug}-revise-* 2>/dev/null
```

If revisions exist, add a revision chain line below the brief header metadata:

```
**Revision chain:** Original → [Revise 1: {change}]({path}) → [Revise 2: {change}]({path})
```

Read each revision's `config.json` or `user-inputs.md` to extract the change description.
If this IS a revision run, also add:
```
**This is a revision of:** [{original slug}]({original path}) | **Change:** "{revision input}"
```

### Step 5.5: Validate Brief (Phase 8.5)

Before printing, invoke the mechanical validator. See
`references/phases/validate-brief.md` for the full protocol.

**Before anything else: read this prohibition.**

Phase 8.5 means executing the named Python script `scripts/validate-brief.py`.
It does NOT mean writing an inline Python script in a Bash heredoc that checks
for the section headers you just authored. Self-certification against
self-invented headers always passes and catches nothing. If the validator is
down and you must self-check, do the written-prose checklist in the `PY_MISSING`
branch below — not an ad-hoc inline script. Specifically forbidden:

```bash
# FORBIDDEN — this is self-certification, not validation.
python3 <<'EOF'
required = ['## Context', '## Recommendation', '## Sources', 'Decision tilt', 'possibility map']
# ... checks against headers the writer invented, not the schema
EOF
```

The named script reads the canonical schema (`references/brief-schema.json`) and
enforces it. An inline script authored at brief-write time has no connection to
the schema — it checks whatever the writer decided to check. That is not a
mechanical validator. Do not substitute one for the other. If the reader sees
"Validation: 13/13 checks passed" in your run trace and those 13 checks came from
a block of Python you wrote in that same turn, the brief is unvalidated.

**Pre-flight — verify python3 is available** (the validator is Python; without
it the brief ships unchecked):

```bash
python3 --version >/dev/null 2>&1 && echo "PY_OK" || echo "PY_MISSING"
```

- `PY_OK` → proceed to invoke validator below.
- `PY_MISSING` → this is expected for most Cowork and non-developer installs.
  Not an error. Do BOTH of:
  1. Run the **self-check**: re-read the brief you just wrote and verify,
     header-by-header, that every required section from the Step 4a checklist
     is present in the final output. Any missing header triggers a rewrite of
     that section BEFORE proceeding to Step 6.
  2. Append a small footer note to the brief (place it after the Sources
     section, before the `<!-- validator-refs ... -->` block):
     ```
     *Structural self-check passed. Mechanical validation (unsourced-number
     detection, depends-on mirror, cross-reference coverage) wasn't available
     in this environment — install `python3` to enable the full validator.*
     ```
  Do NOT silently skip the self-check. It is the writer's only guarantee when
  the validator can't run.

**Invoke validator:**

```bash
python3 "{skill_dir}/scripts/validate-brief.py" \
  --run-dir "{run_dir}" \
  --schema  "{skill_dir}/references/brief-schema.json" \
  --mode    "{mode}"
```

- Exit 0 → continue to Step 6.
- Exit 1 → continue to Step 6. Append validation footer after the brief.
- Exit 2 → read `validation-report.json`, build corrective prompt, re-do Step 4
  (rewrite brief) ONCE. Then re-run the validator. If still exit 2, prepend a
  `VALIDATION_FAILED` warning to the brief and continue (full protocol in
  `validate-brief.md` Step 5). **The `VALIDATION_FAILED` banner MUST remain
  visible in any downstream artifact (PDF export, Notion publish, summary).
  Publish tooling that strips HTML/markdown warnings is a separate bug — file
  it, don't paper over it.**
- Exit 3 → log "Validator failed: {stderr}" and continue — but also run the
  fallback self-check in the `PY_MISSING` branch above and prepend the same
  banner. Script errors surface to the user, never get swallowed.

This step is MANDATORY for full/medium/revise runs. Quick mode runs it in a
reduced mode that only checks prohibited patterns and the quick-mode section
subset.

### Step 6: Print Brief to User

After validation passes (or fails through with the warning), print the full
Decision Brief to the conversation. Then print:
"Decision logged to journal. Run `/autodecision:review` to compare predictions vs reality later."

### Step 7: Offer Publish or Export

After printing, offer to publish or export:

> "Share this brief?"
> Options:
> A) Publish — run `/autodecision:publish` (PDF → Notion, email, gist, Slack, Drive, or local)
> B) Copy to current directory
> C) Skip

If A: invoke the publish skill with the current slug.
If B:
```bash
cp ~/.autodecision/runs/{slug}/DECISION-BRIEF.md ./{slug}-DECISION-BRIEF.md
```
Print: "Exported to ./{slug}-DECISION-BRIEF.md"

## Handling Incomplete Data

If phases are missing (status: partial or file missing):
- Note which phases are incomplete in the Brief header
- Reduce confidence rating accordingly
- Proceed with available data — an incomplete analysis is better than no analysis

## Convergence Status in Brief

- **Converged at iteration N:** "Insights stabilized after N iterations of adversarial pressure."
- **NOT REACHED after max iterations:** "Convergence not reached. This decision has genuine
  unresolvable uncertainty. The effects below represent the best available analysis but
  may shift with additional iteration. Delta values: [effects_delta], [assumption_stability],
  [ranking_flips], [contradictions]."

## Mode Variants

All modes (full, medium, quick, revise) write to `DECISION-BRIEF.md` using the
same template from `references/output-format.md`. **Section inclusion per mode is
defined exclusively by `references/brief-schema.json`** — each section declares
`required_in`, `optional_in`, `skip_in` arrays. Read those, emit accordingly.

Common header conventions per mode:
- **full:** `Iterations: {N} | Converged: yes at iteration M / NOT REACHED | Tilt: {tilt}`
- **medium (--iterations 1):** `Iterations: 1 | Converged: N/A (medium mode) | Tilt: {tilt}`
- **quick:** `Mode: Quick (single-pass, no council) | Grounding: GROUNDED/UNGROUNDED`
- **revise:** add the revision chain header — see `references/phases/revise.md`

Do NOT improvise alternative layouts per mode. Do NOT lead with recommendation
in any mode. Do NOT use "Why Not X" sections. One template, one structure, schema
drives what's emitted. The reader should not need to know how many iterations
ran to understand the brief.
