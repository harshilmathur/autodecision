<!--
phase: 1.5
phase_name: ELICIT
runs_in:
  - full       (outer, after GROUND, before HYPOTHESIZE — UNLESS --skip-elicit)
  - medium     (outer, after GROUND, before HYPOTHESIZE — UNLESS --skip-elicit)
  - quick      (SKIPPED entirely — single-pass mode does not elicit)
  - revise     (interactive revision input is the elicit equivalent)
reads:
  - ~/.autodecision/runs/{slug}/config.json
  - ~/.autodecision/runs/{slug}/ground-data.md
  - ~/.autodecision/runs/{slug}/context-extracted.md (if --context was provided)
  - references/persona-council.md (to display canonical 5 personas to user)
writes:
  - ~/.autodecision/runs/{slug}/user-inputs.md (or empty placeholder if user declined)
gates:
  - User confirms or modifies: assumptions, persona council, sub-questions, tilt
  - Persona modifications restricted to {add | remove | rename}; never invent a 6th persona type without rules
-->

# Phase 1.5: ELICIT

## Purpose

Before the loop runs, review the analysis setup with the user. This is the single
biggest quality improvement: getting domain-specific knowledge and user preferences
BEFORE the system starts simulating. Every minute spent here saves 10 minutes of
irrelevant simulation.

## Inputs
- `config.json` (from Phase 0: decision, sub-questions, constraints)
- `ground-data.md` (from Phase 1: web search results)

## Outputs
- `user-inputs.md` in the run directory
- Potentially updated `config.json` (if user modifies sub-questions or constraints)

## Adaptive ELICIT Rules

Not every decision needs all blocks. Use these rules to skip blocks that add
friction without value:

| Block | Always Ask | Skip When |
|-------|-----------|-----------|
| Block 1: Assumptions + Data | YES — always | Never skip. Fast scan, high value. |
| Block 2: Personas | Only for novel decisions | Skip if a template was used (templates already tune personas) |
| Block 3: Decision Tilt | YES — always | Never skip. One question, frames the entire analysis. |
| Block 3.5: Urgency Check | Only if urgency detected | Skip if no time-pressure signals in decision statement or ground data |
| Block 4: Domain Knowledge | Only when data gaps exist | Skip if grounding returned substantive data for ALL sub-questions |

**Result:** Minimum 2 questions (assumptions + tilt), maximum 5 for novel ungrounded
urgent decisions.

## Process

Present review blocks to the user via AskUserQuestion. Each block is skippable.

### Block 1: Review Assumptions and Data

Present the key findings from ground-data.md and the sub-questions from config.json:

> "Before I start the analysis, here's what I'm working with. Any corrections or additions?"
>
> **Decision:** {decision_statement}
>
> **Sub-questions I'll analyze:**
> 1. {sub-question 1}
> 2. {sub-question 2}
> ...
>
> {If context-extracted.md exists:}
> **Data from your documents:**
> - {top extractions from context-extracted.md, showing [D#] tags}
> - {note: "N total extractions from M files. Want me to surface specific items I missed?"}
>
> **Key data I found (Phase 1 grounding):**
> - {top 3-5 data points from ground-data.md}
> {If any conflicts between document data and web data, flag them:}
> - {CONFLICT: [D2] says X but [G3] says Y — which is correct?}
>
> **Does this look right? Anything I'm missing or getting wrong?**
>
> Options:
> A) Looks good, proceed
> B) I have corrections / additional data (provide below)
> C) Skip — just run the analysis

If user provides corrections or data:
- Record in `user-inputs.md`
- Update `config.json` if sub-questions change
- Tag user-provided data as "(user-provided)" throughout the analysis

### Block 2: Review Personas (skip if template was used)

**Skip this block** if a decision template was used (pricing, expansion, build-vs-buy,
hiring). Templates already include persona enhancements tuned for the decision type.
Note in user-inputs.md: "Personas: DEFAULT (template-tuned, skipped review)."

**Ask this block** only for novel decisions without a template.

Present the 5 default personas and ask if the user wants to modify:

> **Council personas for this decision:**
>
> 1. **Growth Optimist** — looks for upside, market opportunity, creative alternatives
> 2. **Risk Pessimist** — looks for downside, failure modes, hidden costs
> 3. **Competitor Strategist** — thinks like the competition
> 4. **Regulator/Constraint** — sees legal, regulatory, structural constraints
> 5. **Customer Advocate** — thinks like the end user
>
> These work well for most business decisions. You can:
> - **Add a persona** (e.g., "Investor" for fundraising decisions, "Engineer" for technical decisions)
> - **Remove a persona** (e.g., Regulator may be irrelevant for some decisions)
> - **Modify a persona** (e.g., change Competitor to a specific competitor name)
>
> Options:
> A) Default 5 personas — proceed
> B) I want to customize (specify below)
> C) Skip

If user customizes:
- Record custom persona definitions in `user-inputs.md`
- Update persona prompts accordingly for this run
- Custom personas follow the same structure: optimization objective, blind spot,
  contrarian question, no-hedging rule

### Block 3: Decision Tilt

> **What are you optimizing for with this decision?** This tilts the analysis toward
> your strategic priority. Every hypothesis gets scored, but the recommendation
> weights your priority higher.
>
> A) **Maximize enterprise value** (Recommended) — balance growth, defensibility, and long-term value creation
> B) **Build moat** — prioritize competitive advantage and defensibility over speed or cost
> C) **Capital efficiency** — minimize spend, maximize ROI, shortest payback period
> D) **Time to market** — speed and first-mover advantage above all
> E) **Risk minimization** — most reversible, safest path, smallest blast radius
> F) Skip — no tilt, balanced analysis

Store the tilt in `config.json` as `"tilt": "maximize_enterprise_value"` (or the
selected value). Thread into every persona prompt:

```
DECISION TILT: {tilt_name}
Weight your analysis toward {tilt description}. When two effects have similar
probability, favor the one that better serves this tilt. In your recommendation,
explain how the preferred option serves this strategic priority.
```

The Decision Brief header shows: "Tilt: {tilt_name}" so readers know the analysis
has an explicit strategic lens.

| Tilt | Weights Higher | Persona Most Affected |
|------|---------------|----------------------|
| maximize_enterprise_value | Growth + defensibility + sustainable economics | All equally |
| moat | Competitive advantage, switching costs, network effects | Competitor, Optimist |
| capital_efficiency | ROI, payback, burn rate | Pessimist, Regulator |
| time_to_market | Speed, first-mover, deployment timeline | Optimist, Customer |
| risk_minimization | Reversibility, downside protection, incremental approach | Pessimist, Regulator |

### Block 3.5: Urgency Check (conditional — only if urgency detected)

**Detection:** Scan the decision statement + ground-data.md for urgency signals:
- Words/phrases: "compete with", "before they", "window", "imminent", "soon",
  "now or never", "race", "closing", "deadline", "time-sensitive", "first mover"
- Competitive framing: "X is about to...", "if we don't act..."
- Temporal pressure in sub-questions: "how fast do we need..."

**If NO urgency signals found:** Skip this block silently.

**If urgency signals found:** Ask via AskUserQuestion:

> "This decision has a time-pressure element. What's the hard evidence for the urgency?"
>
> A) **Hard deadline** — regulatory, contractual, or board-mandated date (specify)
> B) **Observed action** — competitor filing, hiring, public announcement (specify)
> C) **Market signal** — industry rumor, advisor engagement, indirect evidence
> D) **Gut feeling** — competitive pressure, fear of missing out, no specific evidence

Record the answer in `user-inputs.md` as:

```
## Urgency Assessment
- Status: {HARD / SOFT / SPECULATIVE / NONE}
- Evidence: {user's specific answer}
```

And in `config.json` add: `"urgency": {"grade": "HARD/SOFT/SPECULATIVE/NONE", "evidence": "..."}`

**How this flows through the system:**

1. `shared-context.md` includes the urgency grade and evidence.
2. Personas see: "URGENCY: {grade}. Evidence: {evidence}. Calibrate time-pressure
   effects accordingly — HARD urgency should be weighted at face value, SPECULATIVE
   urgency should be treated as uncertain (wide probability range)."
3. The Decision Brief header shows: `Urgency: {grade} ({evidence summary})`
4. Sensitivity analysis treats urgency-coded assumptions differently based on grade:
   - HARD: test as normal assumptions
   - SOFT/SPECULATIVE: automatically included in sensitivity analysis as HIGH sensitivity

**Why this exists:** The system tends to over-weight urgency when not grounded in
evidence. This question catches that bias at source — the user knows whether
their urgency is real.

### Block 4: Additional Domain Knowledge (skip if grounding is strong)

**Skip this block** if Phase 1 (GROUND) returned substantive data for ALL sub-questions
(no sub-question flagged as ungrounded). Note in user-inputs.md: "Domain Knowledge:
SKIPPED (grounding sufficient for all sub-questions)."

**Ask this block** if any sub-question has weak or missing grounding data.

Ask targeted questions based on the decision type and data gaps:

> **A few questions that would sharpen the analysis (answer any, skip the rest):**
>
> 1. {question derived from the biggest data gap in ground-data.md}
>    Example: "What's your current churn rate?" / "Who is your primary competitor?"
> 2. {question about internal context the system can't search for}
>    Example: "What's your current runway?" / "What % of revenue comes from enterprise?"
> 3. {question about the user's risk tolerance or decision framework}
>    Example: "Are you optimizing for growth or profitability?" / "Is this reversible if it fails?"
>
> **Have documents that would help?** (financial models, term sheets, internal reports)
>
> Options:
> A) Here are my answers: {free text}
> B) Attach files (provide paths — Claude Code only)
> C) Skip — work with what you have

If user chooses B (attach files): Run the same extraction pipeline from Phase 0
(see `scope.md` "Context File Extraction"). New extractions continue the `[D#]`
sequence from any existing context files. Append to `context-extracted.md` and
update `config.json` context_files array. Then re-present Block 1 briefly so the
user can see the new extractions alongside existing data.

Generate 3-5 questions based on:
- Missing data flagged in `ground-data.md`
- Constraints in `config.json` that need quantification
- Decision template guidance (if a template was used)
- Common data gaps for this decision type

If user provides answers:
- Record in `user-inputs.md`
- Feed into persona prompts as "USER-PROVIDED CONTEXT: {data}"
- Tag in the Decision Brief as "(user-provided)"

## Output: user-inputs.md

```markdown
# User Inputs: {decision_statement}

## Assumptions Review
- Status: {REVIEWED / SKIPPED}
- Corrections: {any corrections to sub-questions or ground data}
- Additional data: {any data the user provided}

## Persona Configuration
- Status: {DEFAULT / CUSTOMIZED / SKIPPED}
- Changes: {any persona additions, removals, or modifications}
- Custom personas: {definitions if any}

## Domain Knowledge
- Status: {PROVIDED / SKIPPED}
- Answers:
  1. {question}: {answer}
  2. {question}: {answer}
  3. {question}: {answer}
```

## Skip Behavior

If the user skips ALL blocks (or the command includes `--skip-elicit`):
- Write `user-inputs.md` with all statuses as "SKIPPED"
- Proceed to Phase 2

The ELICIT phase should take < 2 minutes if the user engages, 0 seconds if skipped.
It should NEVER feel like a barrier to running the analysis.

**Note:** The input quality gate that catches non-decisions and weak inputs now lives
in Phase 0 (SCOPE) — it runs before any work happens, including before ELICIT. See
`phases/scope.md` "Input Quality Gate."

## Integration with Personas

When user-inputs.md contains domain knowledge, EVERY persona subagent prompt
should include:

```
USER-PROVIDED CONTEXT (treat as high-confidence data, more reliable than web search):
- {data point 1}
- {data point 2}
- {data point 3}
```

This ensures user knowledge flows through the entire analysis, not just the grounding.
