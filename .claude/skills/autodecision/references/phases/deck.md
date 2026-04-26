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

## ⛔ FORBIDDEN PATTERNS — read first, before any code

Before you do anything else, internalise: **this phase produces
`deck-spec.json`, then invokes the renderer.** It does NOT produce a
PPTX through any other path. The following patterns are HARD_FAIL — if
you find yourself writing them, STOP and start over.

| Forbidden | Why | Do this instead |
|---|---|---|
| `from pptx import Presentation; prs = Presentation()` anywhere in your output | You're rolling your own deck builder. The renderer already does this with all the visual + compatibility hooks. | Build `deck-spec.json` and invoke `scripts/render-deck.py --spec ... --out ...`. |
| `Bash` heredoc with python-pptx code that adds slides/shapes | Same as above — inline PPTX construction. | Same — emit the spec, run the renderer. |
| Skipping `deck-spec.json` and going "straight to PPTX" | The spec is the contract — it's also the artifact users edit and re-render. | Always write the spec to disk first; then render. |
| Writing the deck to a path other than `~/.autodecision/runs/{slug}/DECK.pptx` | Breaks downstream automation that expects this exact path. | Use the canonical path. The spec goes to `deck-spec.json` in the same directory. |
| Naming the file anything other than `DECK.pptx` (e.g., `microsoft-llms-decision-deck.pptx`) | Same as above — breaks the contract. | `DECK.pptx`, all caps. |
| "Improvising" a layout because the brief is unusual | The renderer + the fallback table in this doc handle every brief shape we've seen. | Apply the documented fallback for whatever section is missing. |
| Building the deck inline because the renderer "isn't available" | If `scripts/render-deck.py` is missing, the plugin install is broken. | STOP and report to the user. Do not produce a substitute deck. |

If your output starts with `from pptx import Presentation` or contains
`add_slide(...)` for any reason, you have made the wrong deck. The
output of this phase is a `deck-spec.json` and a `DECK.pptx` produced
by the named renderer, full stop.

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

### Fallbacks for missing or older-schema sections

Briefs predating schema v1.1 (and quick-mode briefs) sometimes omit
sections the deck would normally pull from. Apply these fallbacks rather
than failing or skipping the slide:

| Missing | Fallback |
|---|---|
| `## Sources` | Synthesize `[G#]` tags from the bullets in `## Data Foundation` (or the inline footnote-style "Sources: ..." line some older briefs use). Use sequential numbering. The Sources slide can ship with 7-10 tags — that's enough to anchor the deck. |
| `### Irrational Actors` (only Worst + Black Swan present) | Replace the third column with **MITIGATIONS** — a synthesized list of how the recommended hypothesis defuses the worst-cases / black-swans. Reads tighter than padding the slide with weak content. |
| `### Cross-correlations` (a 4th adversarial subsection some briefs add) | Keep the 3-column adversary slide as Worst / Black Swan / Irrational. Roll cross-correlations into the slide's commentary or footnote — don't add a 4th column. |
| `## Council Dynamics` mentions strongest/weakest but no peer-review.json exists | Score the radar from the narrative. Strongest persona gets 4-5 across the relevant dimensions; weakest gets 1-2 on the dimension Council Dynamics flags (e.g., "narrow ranges" → low Range Width). The narrative IS the canonical source for these examples; JSON is an optional refinement. |
| `## Hypotheses Explored` table absent (rare; quick-mode) | Skip slide 6 (table) and slide 7 (matrix). Both depend on hypothesis structure. |
| `## Key Assumptions` table absent | Skip slide 13 (sensitivity tornado). Convergence Log alone isn't enough. |
| `## Appendix A: Decision Timeline` absent | Skip slide 15 (roadmap). The recommendation slide already names the action — losing the gantt is acceptable. |

When you skip a slide, **renumber `page_num` and TOC ranges** for every
slide after it. The validator will warn on duplicates, not on gaps, so
gaps go undetected and slide 9 footer-numbered "9" will sit at deck
position 8 if you forget.

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

Score each of the 5 personas 1-5 on five rigor dimensions. **The Council
Dynamics narrative is the canonical source.** `peer-review.json` and
`critique.json` are optional refinements when present, but every
example brief in the repo synthesizes the radar from narrative alone —
this is the normal path, not a fallback.

| Dimension | Narrative signal (primary) | JSON refinement (if present) |
|---|---|---|
| Effects identified | "Surfaced X, Y, Z" calls out → 4-5; minor → 2-3 | Count of effects attributed to that persona in `effects-chains.json` |
| Range width | "Narrow ranges" / "joint-probability inflation" → 1-2 | Mean disagreement-range width on that persona's effects |
| Adversarial coverage | "Designed the reversibility structure" → 4-5; "underweighted X" → 1-2 | Count of adversarial scenarios that persona generated |
| Counter-factual depth | Critique flags ("joint-probability inflation", "blind spot caught against") inverted | Same — count flags, invert |
| Quantitative rigor | Specific numbers in the persona's quoted findings → 4-5; vague → 1-2 | Specific-number-per-effect ratio |

**Calibration rule:** the radar must visibly reflect the strongest/weakest
ranking that Council Dynamics names. If Optimist is "#5 peer rank" or
"weakest", its area on the radar MUST be visibly the smallest. If
Pessimist or Regulator is "#1", their area MUST be visibly the largest.
The radar IS the visual evidence for the verbal ranking — they cannot
disagree.

**When to skip:** only if `## Council Dynamics` itself is missing or
contains no strongest/weakest signal (rare; most quick-mode briefs still
include this section).

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

**Quick mode (8-slide structure):** quick briefs lack `## Council
Dynamics`, `## Adversarial Scenarios`, `## Convergence Log`, and
`## Appendix A: Decision Timeline`. Drop every slide that depends on
those sections — slides 7 (matrix), 10 (council two-column), 11
(radar), 12 (adversarial three-column), 13 (sensitivity tornado), 14
(Part 4 section divider), 15 (roadmap). The remaining 8 slides:

| New page | Old page | Type | Notes |
|---|---|---|---|
| 1 | 1 | `title_cover` | Subtitle: "Quick Decision Brief — single-pass analysis, no council" |
| 2 | 2 | `toc_dark` | 4 items only: Recommendation / How we explored / What the analysis found / Appendix — Sources |
| 3 | 3 | `recommendation` | The 6-field grid still applies. Use CONFIDENCE / DEPENDS ON / MONITOR / PRE-MORTEM / DOMINANT RISK / BETTER ALTERNATIVE (last two replace DEEPEST DISAGREEMENT and REVIEW TRIGGER which need a council). |
| 4 | 4 | `section_divider` | Part 2: How we explored. Lead question: "Quick-mode single-pass against grounded data — what did the analysis surface?" |
| 5 | 5 | `action_text` | "How we analyzed" — call out the single-pass mode, hypothesis count, effect count, and that confidence is bounded LOW-MEDIUM by design. |
| 6 | 6 | `table` | 4-column hypotheses table. "Status" pill column + "Why" instead of "Key assumptions" (quick briefs don't enumerate per-hypothesis assumptions). |
| 7 | 9 | `chart_bar` | Top 12 effects from `## Effects` (1st + 2nd order combined). Single-pass: agreement is heuristic; commentary should call this out. |
| 8 | 16 | `table` | Sources synthesized from `## Data Foundation` (quick briefs predate `## Sources` schema — fallback rule). |

`page_num` and TOC ranges reflect the new 1-8 numbering, not the
original 16-slide positions. Recommendation uses prefix `1/  RECOMMENDATION`,
methodology `2.1/`, hypotheses `2.2/`, effects `3.1/`, sources `APPENDIX  SOURCES`.

**Page numbers must match positions.** If you skip slide 7, slides 8+
shift down. The `page_num` field in each slide must equal its 1-indexed
position in the `slides` array. Sources slide stays the last `page_num`
in the deck.

**TOC slide ranges must reflect actual deck positions.** If you skipped
slide 7, "How we explored this decision" runs `4 – 6` not `4 – 7`.

---

## Step 5 — Render

```bash
python3 "{skill_dir}/scripts/render-deck.py" \
  --spec ~/.autodecision/runs/{slug}/deck-spec.json \
  --out  ~/.autodecision/runs/{slug}/DECK.pptx
```

`{skill_dir}` is the absolute path to this skill's directory (e.g.,
`~/.claude/plugins/marketplaces/autodecision/skills/autodecision/` for
plugin installs, or the local checkout's `claude-plugin/skills/autodecision/`).
The renderer ships inside the skill, alongside `validate-brief.py`.

The renderer calls `validate_spec()` first. Hard errors (missing
required fields, unknown slide types, header/col_widths mismatches)
abort with a clear list. Warnings (duplicate page numbers, unusual
column counts, recommendation field count) print to stderr but rendering
continues.

If validation fails, **read the error list and fix the spec** rather
than removing slides or retrying. Common errors and the fix:

| Error pattern | Cause | Fix |
|---|---|---|
| `missing required field 'col_widths'` on a `table` slide | Spec was hand-edited and the field got dropped | Re-add `col_widths` matching `headers` length, OR delete the field entirely (renderer will distribute evenly) |
| `has N headers but M col_widths` | Header/width arrays drifted | Make them match; for sources tables with long council tags, prefer `[1.7, 1.0, 7.0, 2.6]` |
| `unknown slide type` | Typo or non-supported type | See `_SLIDE_REQUIRED_FIELDS` in render-deck.py for the canonical list |
| `item[N] missing 'x'` on `matrix_2x2` | Bubble missing position | Every bubble needs `x`, `y`, `size`, `label` minimum |

If the render exits non-zero for any other reason, surface the error to
the user verbatim. Do not retry silently.

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

## PowerPoint compatibility (handled by the renderer)

The renderer (`scripts/render-deck.py`) normalises several quirks of
python-pptx's output that would otherwise trigger PowerPoint's "the
file has an issue, repair?" prompt on macOS. Authors of this phase do
NOT need to think about any of this — but the post-save hooks in
`build_from_spec` exist for a reason; do not remove them.

| Normalisation | What it fixes |
|---|---|
| `_strip_printer_settings(prs)` | Removes the default-template Windows DEVMODE binary (`ppt/printerSettings/printerSettings1.bin`) that has no place on macOS. |
| `_normalize_slide_size(prs)` | Strips the stale `type="screen4x3"` attribute from `<p:sldSz>` (we use 16:9 dimensions; the declared type was inconsistent). Slide dimensions also use exact PowerPoint EMU values (`Emu(12192000) × Emu(6858000)`), not `Inches(13.333)` which drifts by 305 EMU. |
| `_fill_root_group_xfrm(prs)` | python-pptx writes the slide root group as empty `<p:grpSpPr/>`. PowerPoint expects a populated `<a:xfrm>` block with zero offsets/extents — schema says optional, PowerPoint disagrees. |
| `_add_missing_end_para_rpr(prs)` | Every `<a:p>` must end with `<a:endParaRPr/>` per PowerPoint. python-pptx omits it; we append it on every paragraph that lacks one. |
| `Emu(int(...))` wraps on length arithmetic | Python 3 division of Length values returns float; EMU must be integer. Wrap any `length / N` site in `Emu(int(...))`. |

If a future PowerPoint version surfaces a new "repair" prompt, diff the
output deck against the user's repaired copy (`diff -rq` on unzipped
zips) — the structural delta tells you exactly what python-pptx is
still emitting wrong, and a new normalisation hook can be added before
`prs.save(...)`.

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
