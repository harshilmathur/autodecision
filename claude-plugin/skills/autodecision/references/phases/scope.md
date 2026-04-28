<!--
phase: 0
phase_name: SCOPE
runs_in:
  - full       (outer, runs once before the inner loop)
  - medium     (outer, runs once)
  - quick      (outer, runs once)
  - revise     (re-uses prior config, may patch via revision input)
reads:
  - user decision statement (from /autodecision invocation)
  - optional: --template flag (pricing | expansion | build-vs-buy | hiring)
  - optional: --context flag (one or more file paths, resolved relative to cwd)
  - optional: --skip-clarify flag (boolean — skips Phase 2.5 CLARIFY)
  - optional: --skip-elicit flag (boolean — skips Phase 1.5 ELICIT)
  - if template: references/templates/{template}.md
writes:
  - ~/.autodecision/runs/{slug}/config.json
  - ~/.autodecision/runs/{slug}/context-extracted.md (if --context provided)
gates:
  - Input quality gate passes (decision clarity + scope fit)
  - At least 2 sub-questions identified
  - Decision tilt set (default "balanced" if user did not specify)
-->

# Phase 0: SCOPE

## Purpose
Decompose the decision into sub-questions and constraints. This is the foundation
that all subsequent phases build on.

## Inputs
- User's decision statement (from the command invocation)
- Optional: `--context file1 [file2 ...]` (paths to context documents)

## Outputs
- `config.json` in the run directory
- `context-extracted.md` in the run directory (if `--context` provided)

## Input Quality Gate (MANDATORY — runs before anything else)

Before parsing, decomposing, or creating any run directory, evaluate whether the
input is suited to autodecision. This is the cheapest possible check — one look at
the raw statement before any web searches, agent spawns, or compute. Catches garbage
inputs in seconds instead of minutes.

### Signals

Score each 0-2:

| Signal | Green (2) | Yellow (1) | Red (0) |
|--------|-----------|------------|---------|
| **Decision clarity** | Clear action with identifiable alternatives ("Should we cut pricing by 20%?") | Vague but decomposable into a decision ("improve retention") | Not a decision at all — prediction, research question, opinion, or trivia ("when will iran war end?", "tell me about AI trends", "what's the best language?") |
| **Scope fit** | Business/strategy decision with real tradeoffs and stakeholders | Borderline — operational, personal, or trivial but still a decision ("should I use React or Vue?") | Not suited to autodecision — pure prediction, pure math, pure taste, no falsifiable assumptions, or already decided with no alternatives |

**Total: 0-4.**

### Dispatch

| Score | Action |
|-------|--------|
| 3-4 | **Proceed.** Input is a decision. Continue to decomposition (Step 1). |
| 1-2 | **Ask the user.** Present what's wrong and offer options (see below). |
| 0 | **Ask the user.** Strong recommendation to reframe or exit. |

### Flow (score 0-2)

Present via AskUserQuestion:

> {If not a decision (score 0):}
> "This reads more like a prediction or research question than a decision with
> tradeoffs. autodecision works best when there is a concrete action to evaluate —
> 'Should we do X?' not 'What will happen with Y?'"
>
> {If vague/borderline (score 1-2):}
> "This is broad enough that the analysis may not converge on anything actionable.
> A sharper framing would produce a better brief."
>
> {Always include 2-3 suggested reframings:}
> "Some options that would work better:"
> 1. {reframed version — more specific, action-oriented}
> 2. {reframed version — different angle on the same topic}
> 3. {reframed version — narrower scope}
>
> A) **Use one of these** — pick a number or type your own reframing
> B) **Proceed anyway** — I will run the analysis as-is (quality may suffer)
> C) **Exit** — stop the run

If A: restart Phase 0 with the new statement (new slug, new run directory). Write
the old input's `config.json` with `"status": "REFRAMED", "reframed_to": "{new slug}"`.

If B: record `"input_quality": "WEAK"` in `config.json`. Continue to decomposition.
The Decision Brief header will show `Input: WEAK (user chose to proceed)`.

If C: write `config.json` with `"status": "ABANDONED"`, log to journal, print:
"Run abandoned. No brief generated." Exit cleanly.

### Examples

| Input | Clarity | Fit | Score | Verdict |
|-------|---------|-----|-------|---------|
| "Should we cut pricing by 20%?" | 2 | 2 | 4 | Proceed |
| "Should we hire a VP Eng?" | 2 | 2 | 4 | Proceed |
| "improve retention" | 1 | 1 | 2 | Ask — suggest: "Should we invest in reducing churn below 5% this quarter?" |
| "when will iran war end?" | 0 | 0 | 0 | Ask — not a decision, suggest reframe or exit |
| "tell me about AI trends" | 0 | 0 | 0 | Ask — research question, not a decision |
| "should I use React?" | 2 | 1 | 3 | Proceed (borderline but passable) |

### Recording

Write to `config.json` before decomposition:

```json
{
  "input_quality": {
    "score": N,
    "decision_clarity": "GREEN/YELLOW/RED",
    "scope_fit": "GREEN/YELLOW/RED",
    "user_choice": "PROCEED/REFRAME/EXIT"
  }
}
```

## Context File Extraction (runs after quality gate, before decomposition)

If the user passed `--context`, extract key data points from each file before
decomposing into sub-questions. This makes decomposition sharper because you
know what's actually in the documents.

**Platform requirement:** `--context` requires filesystem access (Claude Code only).
If running in Cowork or another environment without filesystem access, print:
"File attachments require Claude Code (filesystem access). In Cowork, paste the
relevant content into the conversation and it will be picked up during ELICIT."

### Step A: Validate files

For each path after `--context`:
1. Resolve relative to cwd
2. Check the file exists. If missing: warn ("File not found: {path}, skipping") and continue.
3. Check extension is supported: `.md`, `.txt`, `.pdf`, `.csv`, `.json`, `.png`, `.jpg`, `.jpeg`.
   If unsupported: warn ("Unsupported file type: {ext}. Export to PDF or CSV for best results.") and skip.

### Step B: Read and extract

For each valid file, read the content and extract key data points into a structured
list. Each extraction gets a sequential `[D#]` tag (flat numbering across all files):

```
- [D1] Revenue: $4.2M ARR as of Q1 2026 (acme-financials.csv, row 12)
- [D2] Gross margin: 72% (acme-financials.csv, row 15)
- [D3] TAM estimate: $2.1B by 2028 (acme-financials.csv, row 24)
- [D4] Series A terms: $8M at $40M pre-money (term-sheet.pdf, p.1)
- [D5] Liquidation preference: 1x non-participating (term-sheet.pdf, p.3)
- [D6] Projected 18-month runway at current burn (term-sheet.pdf, p.5)
```

**Extraction rules:**
- Priority: numbers, dates, terms, and concrete claims over narrative text
- Each extraction: one data point, with source file + location in parentheses
- Per-file cap: max 15 extractions, ~500 tokens
- Total cap across all files: 800 tokens. Prioritize by file order (user listed most important first).
- If a file exceeds its cap: keep the highest-signal items and note: "N additional
  data points in {filename}. Ask during ELICIT to surface specific items."

### Step C: Write outputs

Write `context-extracted.md` to the run directory:

```markdown
# Context Extractions

Source files: {filename1}, {filename2}, ...

- [D1] Revenue: $4.2M ARR as of Q1 2026 (acme-financials.csv, row 12)
- [D2] Gross margin: 72% (acme-financials.csv, row 15)
...
```

Add context file metadata to `config.json`:

```json
{
  "context_files": [
    {
      "filename": "acme-financials.csv",
      "original_path": "/Users/foo/deals/acme-financials.csv",
      "type": "csv",
      "extractions": 3
    }
  ],
  "has_context_docs": true
}
```

**Storage:** No file copies. Store `original_path` as a reference. Originals stay
where the user put them. Only copy into the run directory if the source is a temp
file (path starts with `/tmp/` or OS temp directory), since it'll be cleaned up.
Copies on export are handled by `/autodecision:export`.

### Quality gate interaction

File presence is a positive signal for the input quality gate. A weak decision
statement (score 1) with strong context documents can score higher because the
documents provide the specificity the statement lacks. Add +1 to the quality gate
score if `--context` files are present and at least 3 extractions were produced.
Cap total score at 4.

---

## Process

1. Parse the decision statement.
2. Parse flags:
   - `--template {name}` — set `template_used` in config.json.
   - `--context {paths}` — note paths for Step B extraction.
   - `--skip-elicit` — set `skip_elicit: true` in config.json.
   - `--skip-clarify` — set `skip_clarify: true` in config.json (Phase 2.5 CLARIFY will
     write `clarify-answers.json` with `status: "skipped", reason: "user_flag"` and
     return immediately).
   - `--iterations {N}` — set `iterations_max` in config.json.
   Default all unset flags to `false`/`null`.
3. Decompose into 2-5 sub-questions. Each sub-question should be independently answerable.
   - If decomposition yields > 5 sub-questions, the decision is too broad. Ask the user to
     narrow it before proceeding.
   - If decomposition yields < 2, the decision may be too simple for the full loop.
     Suggest `/autodecision:quick` instead.
4. Identify explicit constraints (budget limits, timelines, non-negotiables).
5. Create the run directory and write `config.json`.

## Sub-Question Design

Good sub-questions are:
- **Independent:** answerable without solving the others first
- **Specific:** "How will existing customers react to a 20% price drop?" not "What about customers?"
- **Testable:** you could imagine searching for data that answers them

Bad sub-questions are:
- Circular: "Is this a good decision?" (that's the whole point)
- Too broad: "What will happen?" (decompose further)
- Too narrow: "Will revenue be $1.2M or $1.3M?" (false precision)

## Template Support

If the user specifies `--template pricing` (or another template name), read the
corresponding template file from `references/templates/{name}.md` and pre-populate
the sub-questions and constraints. The user can then modify them.

If no template is specified, decompose from scratch.

## Example Output

```json
{
  "status": "complete",
  "decision_statement": "Should we cut pricing by 20%?",
  "sub_questions": [
    "How will customer acquisition rate change with a 20% lower price?",
    "How will existing customers respond (churn, satisfaction, upsell)?",
    "How will competitors respond to our price change?",
    "What happens to unit economics and runway at the new price point?"
  ],
  "constraints": [
    "Must maintain positive unit economics within 12 months",
    "Cannot lose more than 5% of existing enterprise customers"
  ],
  "grounding": "PENDING",
  "template_used": null,
  "skip_elicit": false,
  "skip_clarify": false,
  "iterations_max": 2,
  "created_at": "2026-04-14T12:00:00Z"
}
```
