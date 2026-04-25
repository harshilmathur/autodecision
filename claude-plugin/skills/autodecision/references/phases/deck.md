# Phase: Deck — render a Decision Brief as a McKinsey-styled PPTX

This phase consumes a finished `DECISION-BRIEF.md` and produces a
~16-slide PowerPoint deck via `scripts/render-deck.py`. Three pieces of
work the orchestrator performs in this phase:

1. **Parse** the brief into structured data per section
2. **Synthesize** action titles (one sentence claims, ≤14 words) and
   position data for the 2×2 matrix and per-persona radar
3. **Emit** a `deck-spec.json` and invoke the renderer

The renderer itself is dumb — it only knows how to draw slide types from
a spec. All synthesis happens here.

---

## Inputs

- `~/.autodecision/runs/{slug}/DECISION-BRIEF.md` — required, schema v1.1+
- `~/.autodecision/runs/{slug}/iteration-N/effects-chains.json` — preferred
  source for slide 9's effects bar chart (raw data with stable
  `effect_id`s and persona ranges); fall back to parsing the markdown
  table in Appendix B if missing
- `~/.autodecision/runs/{slug}/iteration-N/peer-review.json` and
  `critique.json` — used to score the radar slide

## Outputs

- `~/.autodecision/runs/{slug}/deck-spec.json` — structured spec
- `~/.autodecision/runs/{slug}/DECK.pptx` — rendered deck

---

## Step 1 — Parse the brief

Open `DECISION-BRIEF.md`. The schema is fixed (per
`references/brief-schema.json`); section headers are stable strings.
Extract these structures:

| Section | Extract |
|---|---|
| H1 (top of file) | Decision question (slide 1 title) |
| `## Executive Summary` | The Decision/Recommendation/Confidence/Disagreement/Risk/Assumption block (slide 3 fields) |
| `## Hypotheses Explored` | Table rows: number, hypothesis, status, key assumptions |
| `## Effects Map` → `### High-Confidence Effects` | Effects with probability, range, council_agreement (slide 9) |
| `## Council Dynamics` | Strongest/weakest/disagreement/blind-spot bullets |
| `## Adversarial Scenarios` → `### Worst Cases` / `### Black Swans` / `### Irrational Actors` | Scenario lists with probabilities |
| `## Key Assumptions` | Table rows for sensitivity tornado |
| `## Recommendation` | The 7-field block (Action / Confidence / Confidence reasoning / Depends on / Monitor / Pre-mortem / Review trigger) |
| `## Appendix A: Decision Timeline` | Roadmap table |
| `## Sources` | All `[G#]`/`[D#]`/`[U#]`/`[C#:persona]` tags with claim and source |

**Validate before continuing.** If any mandatory header is missing, stop
and tell the user the brief is malformed; do NOT attempt to render
partial decks.

---

## Step 2 — Synthesize action titles

Every content slide except section dividers has a serif title that must
be a **claim, not a topic**. This is the rule that defines McKinsey
style — the slide content is the evidence for the claim.

### Action title rules

1. **Complete sentence.** "Three high-sensitivity assumptions are
   load-bearing — if any one fails, aggressive deprecation becomes
   indefensible." NOT "Sensitivity analysis."
2. **Includes a number where the data supports one.** "Six hypotheses
   surfaced; only h6 survived 5/5 council endorsement." NOT "We
   evaluated several hypotheses."
3. **≤14 words.** Long enough to be a claim, short enough to fit on
   2 lines at 22pt. Hard cap.
4. **Falsifiable.** A skeptic should be able to point at the evidence
   and disagree with the claim. "Pro churn risk is real" passes.
   "Strategy looks good" fails.
5. **No hedging adjectives.** "May", "could", "potentially" weaken the
   claim. The brief already encodes uncertainty in
   probability/confidence fields — the title states the takeaway.
6. **Mention the recommendation entity** (h6, h3, etc.) when the claim
   is about it specifically.

### Slide-by-slide synthesis prompts

For each slide listed below, generate one action title using the input
material from the brief. Generate inline as part of this phase — do not
spawn a subagent.

| Slide # | Slide type | Input material | Title pattern |
|---|---|---|---|
| 3 | recommendation | Executive Summary + Recommendation block | "{Joint claim} — {what to ship}" or "{Aggressive path} survives <X% of plausible scenarios; {alternative} instead" |
| 5 | action_text (methodology) | Convergence Log + counts | "The analysis explored {N} hypotheses across {K} iterations of a {M}-persona council, stress-tested by {Q} adversarial scenarios" |
| 6 | table (hypotheses) | Hypotheses table | "{N} hypotheses surfaced; only {winner} survived {endorsement}" |
| 7 | matrix_2x2 | Hypotheses + Adversarial coverage | Position the recommended hypothesis vs the rejected one in claim form |
| 9 | chart_bar (effects) | Effects Map | "The strongest signals point to {pattern under aggressive} and {pattern under safer alternative}" |
| 10 | two_column (council) | Council Dynamics | "The deepest disagreement — {axis A} vs {axis B} — IS the data" |
| 11 | radar | peer-review.json + critique.json | "{Strongest persona} scored highest on {dimensions}; {weakest persona}'s {weakness} drove its #{N} peer rank" |
| 12 | three_column (adversarial) | Adversarial Scenarios | "{N} adversarial scenarios — {how many} push toward {outcome}; only {recommended structure} neutralizes them" |
| 13 | chart_tornado (sensitivity) | Key Assumptions | "{N} high-sensitivity assumptions are load-bearing — if any one fails, {alternative path} becomes indefensible" |
| 15 | table (roadmap) | Appendix A | "The recommendation maps to a {N}-checkpoint roadmap with clear kill criteria at each stage" |

**Quality bar.** Before writing the spec, re-read each title and check:
(a) is it a sentence? (b) does it include a number? (c) ≤14 words?
(d) falsifiable? If any title fails 2+ checks, regenerate it.

---

## Step 3 — Synthesize position data

Two slides need data the brief doesn't directly encode:

### Slide 7 — 2×2 strategic positioning

Plot every hypothesis on `(reversibility, franchise_risk)` ∈ [0, 1]²:

- **Reversibility** (x-axis): how recoverable is the bet?
  - h1 aggressive irreversible → 0.10
  - h2 risk path → 0.20
  - h3 hybrid additive → 0.85
  - h6 with binding triggers → 0.93
- **Franchise risk** (y-axis): catastrophic-if-wrong magnitude
  - aggressive deprecation → 0.85
  - additive strategies → 0.20-0.35
- **Bubble size**: derived from `council_agreement × dominant_probability`
  for the hypothesis (reuse what's in the brief)
- **Bubble color**: red for "AVOID" quadrant hypotheses, dark blue for the
  recommended one, lighter blues/greens for default-quadrant
- **Label position**: choose `right` / `left` / `below` per item to
  prevent label-on-label overlap (see `add_matrix_2x2_slide` docs)

The recommended hypothesis gets `note: "RECOMMENDED"` (italic small
label above the bubble).

If the brief's hypothesis count is <4, skip this slide.

### Slide 11 — Per-persona radar

Score each of the 5 personas 1-5 on five rigor dimensions:

| Dimension | Source signal |
|---|---|
| Effects identified | Count of effects attributed to that persona in `effects-chains.json` |
| Range width | Mean disagreement-range width on that persona's effects |
| Adversarial coverage | Count of adversarial scenarios that persona generated or strongly endorsed |
| Counter-factual depth | Critique flags ("joint-probability inflation", "blind spot") inverted: more flags → lower score |
| Quantitative rigor | Specific-number-per-effect ratio in the persona's contributions |

The Council Dynamics section will already name the strongest/weakest
personas — your scores must reflect that ranking. If Optimist is named
weakest, its area on the radar must visibly be the smallest.

If `peer-review.json` is missing, skip this slide (set the radar slide
type to `null` and remove from spec).

---

## Step 4 — Build the deck spec

Emit `~/.autodecision/runs/{slug}/deck-spec.json` matching the schema
documented inline in `scripts/render-deck.py` (`build_from_spec`).
Standard 16-slide structure for full-mode briefs:

| Slide | Type | Notes |
|---|---|---|
| 1 | `title_cover` | Title from H1, brand "Autodecision" |
| 2 | `toc_dark` | 5 items with slide ranges |
| 3 | `recommendation` | The 7-field grid; **prefix `1/  RECOMMENDATION`** |
| 4 | `section_divider` | Part 2: How we explored |
| 5 | `action_text` | `2.1/  HOW WE ANALYZED` |
| 6 | `table` | `2.2/  HYPOTHESES` |
| 7 | `matrix_2x2` | `2.3/  STRATEGIC POSITIONING` (skip if <4 hypotheses) |
| 8 | `section_divider` | Part 3: What the council found |
| 9 | `chart_bar` | `3.1/  EFFECTS MAP` |
| 10 | `two_column` | `3.2/  COUNCIL DYNAMICS` |
| 11 | `radar` | `3.3/  COUNCIL DEPTH` (skip if no peer-review.json) |
| 12 | `three_column` | `3.4/  ADVERSARIAL PRESSURE` |
| 13 | `chart_tornado` | `3.5/  SENSITIVITY` |
| 14 | `section_divider` | Part 4: Path forward |
| 15 | `table` | `4.1/  ROADMAP` |
| 16 | `table` | `APPENDIX  SOURCES` |

**Quick mode (8-slide reduction):** drop slides 7, 11, 13, 14 — keep
recommendation, methodology, hypotheses, effects, council dynamics,
adversarial, roadmap, sources. Renumber prefixes accordingly.

**Page numbers must match positions.** If you skip slide 7, slides 8+
shift down. The `page_num` field in each slide must equal its 1-indexed
position in the `slides` array. Sources slide stays the last `page_num`
in the deck.

**TOC slide ranges must reflect actual deck positions.** If you skipped
slide 7, "How we explored this decision" runs `4 – 6` not `4 – 7`.

---

## Step 5 — Render

```bash
python3 scripts/render-deck.py \
  --spec ~/.autodecision/runs/{slug}/deck-spec.json \
  --out  ~/.autodecision/runs/{slug}/DECK.pptx
```

If the render exits non-zero, surface the error to the user verbatim.
Do not retry silently.

---

## Style invariants (do not deviate)

- **Brand string is "Autodecision"** in all footers and the cover. Not
  "Autodecision Engine".
- **Title prefix scheme is `N/`** for top-level, `N.M/` for subsections,
  `APPENDIX` (no number) for appendices.
- **Action titles must be claims** (see Step 2 rules).
- **Sources column always shows tagged-evidence pattern.** Format every
  slide's source line as `Source: Decision Brief — {Section} · [tag1],
  [tag2], ...`.
- **The 2×2's recommended hypothesis is the ONLY one with a `note`
  field.** Don't decorate other bubbles.
- **Every numeric claim in the deck cites a `[G#]`/`[C#:persona]` tag
  within 120 characters of the number** (mirrors the brief's source
  discipline).

---

## Common failures to avoid

- Rendering a quick-mode brief without warning — the radar will look
  empty and the matrix will have 1-2 bubbles.
- Generating action titles that are topics, not claims ("Effects
  analysis" instead of "The strongest signals point to franchise
  risk under aggressive paths").
- Skipping a slide without renumbering page_num and TOC ranges → footer
  page numbers no longer match the TOC.
- Embedding hex colors in the spec where named colors work — use
  `MCK_BLUE`, `NAVY`, `RED`, `GREEN`, `ACCENT_CORAL`, `GREY_FOOT` for
  consistency. Hex is reserved for matrix/radar where matplotlib
  consumes them directly.
- Long slide titles. Hard cap is 14 words; aim for 10-12.

---

## Authoring guidance (avoid common spec bugs)

- **Cover title** — keep it ≤65 chars total. The renderer auto-shrinks
  the font (38pt / 32pt / 28pt) based on the longest \\n-split line, but
  short and punchy beats long-and-shrunk. Don't insert manual `\n`
  unless you're sure each split fits in the 5.8" title gutter at the
  selected font size.
- **Hypothesis status pills** — keep status text ≤22 chars (one short
  phrase like "Conditional", "Risk if unilateral", "Leading · 5/5"). The
  renderer auto-shrinks longer text but a one-line pill always reads
  cleaner. Put longer status nuance in the "Key assumptions" column.
- **2×2 matrix bubbles** — never place a bubble within 0.05 of x=0.5 or
  y=0.5 (the quadrant dividers). The renderer auto-nudges anything
  within 0.04, but plotting consciously off the dividers gives you
  control over which quadrant the bubble belongs to. A bubble on the
  line reads as "doesn't fit anywhere" and undermines the matrix.
- **Sources table col_widths** — when council tags include the long
  `iter2council` form (e.g., `C13:iter2council`), use widths
  `[1.7, 1.0, 7.0, 2.6]` instead of the default `[0.7, 1.2, 7.5, 2.9]`.
  The default fits short tags only.
- **Sources row count** — the auto-row-height now floors at 0.28", so
  13-15 rows fit. Beyond 15, split into two slides or trim to the most
  load-bearing tags.
