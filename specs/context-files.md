# Spec: Context File Attachments (`--context`)

**Status:** Draft (revised after eng review)
**Author:** autodecision team
**Date:** 2026-04-16

---

## Problem

Right now the engine gets a one-line decision statement and whatever web search turns up. But real high-stakes decisions usually have context that doesn't exist on the internet: term sheets, internal P&Ls, board decks, competitor teardowns, offer letters, financial models, internal memos.

Users either front-load everything into the decision statement (which makes the input a wall of text that degrades quality gate scoring and slug generation) or they drip-feed it during ELICIT Block 4 (Domain Knowledge), which only fires when grounding has gaps and doesn't structure the input.

**The fix:** let users attach files alongside the decision question. The engine extracts, tags, and threads the content through the full pipeline.

---

## Invocation

### Flag syntax (primary)

```
/autodecision "Should we take the Series A at these terms?" --context term-sheet.pdf
/autodecision "Should we acquire Acme?" --context acme-financials.csv competitive-analysis.md
/autodecision:quick "Build vs buy auth?" --context vendor-comparison.md
/autodecision:challenge "We're dropping UPI fees to zero" --context rbi-circular.pdf internal-cost-model.csv
/autodecision:revise pricing-cut --context updated-financials.csv
```

Multiple files: space-separated after `--context`. Each path is resolved relative to cwd.

### ELICIT prompt (secondary)

During Phase 1.5, Block 4 (Domain Knowledge), add a new sub-option:

> **Have documents that would help ground this analysis?** (financial models, term sheets, internal reports, competitive analysis)
>
> A) Attach files (provide paths)
> B) Type additional context
> C) Skip

This catches the case where someone didn't think to attach files upfront. Files provided here go through the same extraction pipeline.

### No auto-detection

Files in cwd are NOT auto-detected. Too magical, too risky (might ingest something sensitive). The user must explicitly name every file.

### Platform: Claude Code only

`--context` requires filesystem access. It works in Claude Code. In Cowork, there's no local filesystem.

If a Cowork user passes `--context`:

> "File attachments require Claude Code (filesystem access). In Cowork, paste the relevant content into the conversation and it'll be picked up during ELICIT."

The ELICIT Block 4 "type additional context" path works in both environments. Document this distinction in README.

---

## New Source Tag: `[D#]`

Context files get their own tag class, sitting alongside the existing three:

| Tag | Source | Example |
|-----|--------|---------|
| `[G#]` | Ground data (Phase 1 web search) | `[G1] SaaS price elasticity median -1.2 to -1.8 (ProfitWell 2024)` |
| `[U#]` | User-provided facts (Phase 1.5 ELICIT) | `[U1] "Our LTV:CAC is 3.1:1"` |
| `[C#:persona]` | Council estimates (Phase 3) | `[C1:pessimist] "Volume offset P=0.15"` |
| **`[D#]`** | **Context document** | **`[D1] Series A terms: $8M at $40M pre (term-sheet.pdf, p.2)`** |

Flat sequential numbering: `[D1]`, `[D2]`, `[D3]`, etc. across all files. The file-of-origin goes in the Sources table (section 16), not the tag. This matches how `[G#]` works: you don't encode which search query produced `[G3]`.

### No fact/claim classification in v1

All `[D#]` tags are treated uniformly. The persona prompt says:

> "These are from user-provided documents. Treat verifiable data points (revenue figures, contract terms, headcount) as high-confidence data. Treat projections, estimates, and assertions as assumptions to stress-test."

The model is good at this distinction. Formal `[D#:fact]` / `[D#:claim]` suffixes are a v2 addition if users ask for it. The tag format is backward-compatible, so adding suffixes later breaks nothing.

---

## Pipeline Integration

### Where context files enter

Extraction is folded into Phase 0 (SCOPE), not a separate phase. It runs after the input quality gate passes and before sub-question decomposition, so the decomposition benefits from knowing what's in the documents.

```
Phase 0: SCOPE
  ├── Parse input + --context flag
  ├── INPUT QUALITY GATE
  │     (file presence is a positive signal: weak statement + strong docs = score boost)
  ├── EXTRACT CONTEXT (inline, ~30 sec)
  │     ├── Validate files exist + supported type
  │     ├── Read each file, extract key items → context-extracted.md
  │     ├── Store file references in config.json
  │     └── (no file copies — see Storage below)
  ├── Decompose into sub-questions (now informed by doc content)
  └── Write config.json

Phase 1: GROUND
  ├── Web search queries SHARPER because extractions provide domain terms
  ├── Conflicting evidence between docs and web flagged explicitly
  └── ground-data.md unchanged in structure (doc extractions live separately)

Phase 1.5: ELICIT
  ├── Block 1 shows document extractions alongside web data for review
  ├── User can correct, prune, or add context to extractions
  ├── Block 4 offers file attachment (secondary path for late additions)
  └── user-inputs.md records any extraction corrections

Phase 3: SIMULATE
  ├── shared-context.md includes document context block
  ├── Personas see: "DOCUMENT CONTEXT (from user-provided files):"
  └── Framing: "Treat verifiable data as high-confidence. Treat projections as assumptions."

Phase 8: DECIDE
  ├── Brief uses [D#] tags throughout (same rules as [G#])
  ├── Data Foundation section shows document extractions
  └── Sources table includes document rows with file-of-origin
```

### Extraction (inside Phase 0, after quality gate)

This is inline work in the orchestrator. Not a subagent. ~30 seconds.

#### Process

1. **Validate files.** For each path in `--context`:
   - Resolve relative to cwd
   - Check file exists (if missing: warn and continue with the rest, don't block)
   - Check extension is in supported list (if not: warn, skip file)
   - Platform check: if no filesystem access (Cowork), error with paste-instead message

2. **Read and extract.** For each file:
   - Read the file content (Claude reads .md, .txt, .pdf, .csv, .json, images natively)
   - Extract key data points into a structured list:
     ```
     - [D1] Revenue: $4.2M ARR as of Q1 2026 (acme-financials.csv, row 12)
     - [D2] Gross margin: 72% (acme-financials.csv, row 15)
     - [D3] TAM estimate: $2.1B by 2028 (acme-financials.csv, row 24)
     - [D4] Series A terms: $8M at $40M pre-money (term-sheet.pdf, p.1)
     - [D5] Liquidation preference: 1x non-participating (term-sheet.pdf, p.3)
     - [D6] Projected 18-month runway at current burn (term-sheet.pdf, p.5)
     ```
   - Priority: numbers, dates, terms, and concrete claims over narrative text
   - Each extraction: one data point, source file + location reference in parens

3. **Extraction caps (output, not input):**
   - **Per file:** max 15 extractions
   - **Per file token budget:** ~500 tokens of extracted content. If a file yields more, keep the highest-signal items and note: "N additional data points in {filename} — ask during ELICIT to surface specific items."
   - **Total across all files:** 800 tokens hard cap. Prioritize by file order (user listed most important first).
   - No input file size cap. A 100-page PDF is fine. The extraction step reads it, pulls the top items, and moves on.

4. **Write outputs:**
   ```
   ~/.autodecision/runs/{slug}/
   ├── context-extracted.md       # All extractions with [D#] tags
   └── config.json                # Updated with context_files metadata
   ```

   No file copies. See Storage section below.

#### config.json additions

```json
{
  "context_files": [
    {
      "filename": "term-sheet.pdf",
      "original_path": "/Users/foo/deals/term-sheet.pdf",
      "type": "pdf",
      "extractions": 5
    },
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

### Shared Context Integration

`shared-context.md` gets a new block (after user-provided domain knowledge, before hypotheses):

```markdown
## Document Context (from user-provided files)

The following data points were extracted from documents the user attached.
Treat verifiable data (revenue figures, contract terms, dates, headcount) as
high-confidence, more reliable than web search. Treat projections, estimates,
and assertions as assumptions to stress-test in your analysis.

- [D1] Revenue: $4.2M ARR as of Q1 2026
- [D2] Gross margin: 72%
- [D3] TAM estimate: $2.1B by 2028
- [D4] Series A terms: $8M at $40M pre-money
- [D5] Liquidation preference: 1x non-participating
- [D6] Projected 18-month runway at current burn
```

Target budget: ~300-500 tokens for the document context block. Sits within the existing ~1500 token target for shared-context.md in iter-1 (making it ~1800-2000 with docs).

---

## Supported File Types

| Type | Extensions | How read | Notes |
|------|-----------|----------|-------|
| Markdown | `.md` | Direct read | Best format. Users should prefer this for prepared context. |
| Plain text | `.txt` | Direct read | |
| PDF | `.pdf` | Claude native PDF reading | For very large PDFs (>20 pages), extraction still works but user should note which pages matter most. |
| CSV | `.csv` | Direct read, parse as table | Extract column headers + key data rows |
| JSON | `.json` | Direct read, parse structure | Extract top-level keys + values |
| Images | `.png`, `.jpg`, `.jpeg` | Claude native image reading | Screenshots of dashboards, org charts, slides |

**Not supported (v1):** `.docx`, `.xlsx`, `.pptx`. Tell the user: "Export to PDF or CSV for best results." These require parsing libraries and aren't worth the complexity for v1.

---

## Storage

**Reference, don't copy.** Store the original file path and a content hash in `config.json`. The extractions in `context-extracted.md` are what the pipeline uses downstream. Originals stay where the user put them.

```json
{
  "context_files": [
    {
      "filename": "term-sheet.pdf",
      "original_path": "/Users/foo/deals/term-sheet.pdf",
      "type": "pdf",
      "extractions": 5
    }
  ]
}
```

**Exception: export.** When the user runs `/autodecision:export`, copy the originals into the archive so the bundle is self-contained. The export protocol (`commands/export.md`) reads `config.json.context_files[].original_path` and copies each file into `exports/{slug}/context-docs/`. If the original is gone, note it in the export manifest.

**Exception: temp files.** If the original path starts with `/tmp/` or similar temp directory, copy immediately since it'll be cleaned up. Store the copy at `~/.autodecision/runs/{slug}/context-docs/{filename}` and update `original_path` to point there.

---

## Context Window Budget

This is the constraint that shapes everything.

| Component | Tokens (approx) |
|-----------|-----------------|
| shared-context.md baseline (existing) | ~1500 (iter-1), ~2500 (iter-2+) |
| Document context block (new) | ~300-500 |
| **Total with docs** | **~1800-3000** |

### Rules

1. **Extract, don't pass through.** Never dump raw file content into shared-context.md. Always extract discrete data points. A 50-page board deck becomes 10-15 tagged items (~400 tokens).
2. **Per-file cap:** 15 extractions, ~500 tokens.
3. **Total cap:** 800 tokens across all files. Prioritize by file order (user listed most important first).
4. **User review.** During ELICIT Block 1, show the extractions. "I extracted N items from your documents. Here they are. Want to keep all, prune, or surface specific items I missed?"

---

## Brief Changes

### Data Foundation (section 2)

Add document extractions alongside existing ground data and user context:

```markdown
## Data Foundation

- [G1] SaaS price elasticity median -1.2 to -1.8 (ProfitWell 2024)
- [G2] Competitor X raised $200M Series C in Q3 2025 (Crunchbase)
- [D1] Revenue: $4.2M ARR as of Q1 2026 (acme-financials.csv)
- [D2] Gross margin: 72% (acme-financials.csv)
- [D3] TAM estimate: $2.1B by 2028 (acme-financials.csv)
- [D4] Series A terms: $8M at $40M pre-money (term-sheet.pdf, p.1)
- [D5] Liquidation preference: 1x non-participating (term-sheet.pdf, p.3)
- [U1] "Our churn rate is 4.2% monthly" (user-provided, ELICIT)
```

No separate subsections needed. The tag prefix (`[G#]` / `[D#]` / `[U#]`) already tells the reader the source class. Keep it flat like the existing format.

### Sources (section 16)

Add `[D#]` rows to the Sources table:

```markdown
| Tag | Type | Claim | Source |
|-----|------|-------|--------|
| [G1] | Ground | SaaS price elasticity median -1.2 to -1.8 | ProfitWell 2024 report |
| [D1] | Document | Revenue: $4.2M ARR, Q1 2026 | acme-financials.csv, row 12 |
| [D4] | Document | Series A: $8M at $40M pre | term-sheet.pdf, p.1 |
| [U1] | User | Monthly churn 4.2% | User-provided (ELICIT) |
```

The "Source" column carries the file-of-origin + location. This is where readers trace a `[D#]` tag back to its file, not in the tag itself.

### Validator changes

`brief-schema.json` content_checks: add `[D#]` to the allowed tag patterns alongside `[G#]`, `[U#]`, `[C#:persona]`.

`validate-brief.py`: recognize `\[D\d+\]` as a valid source tag. Simple flat pattern, same complexity as `[G#]` and `[U#]`.

---

## File Structure

```
~/.autodecision/runs/{slug}/
├── config.json                  # Updated: context_files array with original_path refs
├── context-extracted.md         # NEW: all extractions with [D#] tags
├── ground-data.md               # Existing (unchanged in structure)
├── shared-context.md            # Updated: includes document context block
├── user-inputs.md               # Updated: extraction corrections if any
└── ...
```

No `context-docs/` directory in the run. Originals stay at their original paths. Only copied into exports or when source is a temp file.

---

## Mode Support

| Mode | Context files? | Notes |
|------|---------------|-------|
| Full | Yes | Full extraction + ELICIT review of extractions |
| Medium | Yes | Same as full |
| Quick | Yes | Extraction only, no ELICIT review |
| Challenge | Yes | Extract, feed to adversary as context to stress-test |
| Revise | Yes (additive) | New files add to existing context. Revision header notes "Added context: {files}" |
| Compare | Yes | Each side can have different context files |

---

## What This Does NOT Do

1. **Auto-detect files in cwd.** Too magical, too risky.
2. **Support URLs as context.** That's Phase 1 web search. Keep boundaries clean.
3. **Parse .docx/.xlsx/.pptx.** Export to PDF/CSV. Not worth the parsing complexity in v1.
4. **Make context files required.** Most decisions work fine with web grounding alone. Power feature.
5. **Replace web search.** Context files supplement grounding, they don't replace it. Phase 1 still runs.
6. **Classify fact vs claim formally.** Personas handle this naturally. Add formal classification in v2 if users need it.
7. **Work in Cowork.** Requires filesystem access. Cowork users paste content during ELICIT instead.

---

## Implementation: Files to Change

### New files

| File | What |
|------|------|
| (none) | No new phase files. Extraction folds into scope.md. |

### Modified files

| File | Change | Size |
|------|--------|------|
| `references/phases/scope.md` | Parse `--context`, validate files, extract, write `context-extracted.md`, store refs in config.json. Add extraction section after quality gate, before decomposition. | Medium |
| `references/engine-protocol.md` | Add `context-extracted.md` to file structure diagram. Add `--context` to prerequisites. Update shared-context.md contents list. | Small |
| `references/phases/ground.md` | Note that extraction data sharpens search queries. Flag conflicts between docs and web. | Small |
| `references/phases/elicit.md` | Block 1: show document extractions for review. Block 4: add file attachment sub-option. | Medium |
| `references/phases/simulate.md` | Document the document context block in shared-context.md section. | Small |
| `references/phases/decide.md` | `[D#]` tags in brief, Sources table rows. | Small |
| `references/phases/challenge.md` | Accept `--context`, feed extractions to adversary context. | Small |
| `references/phases/revise.md` | Accept `--context` for additive context. | Small |
| `references/output-format.md` | Add `[D#]` tag class to Data Foundation template and Sources table template. | Small |
| `references/brief-schema.json` | Add `[D#]` to valid tag patterns in content_checks. | Small |
| `references/validation.md` | Add `[D#]` tag recognition. | Small |
| `scripts/validate-brief.py` | Recognize `\[D\d+\]` tags. | Small |
| `SKILL.md` | Add `--context` flag to Command Routing section. | Small |
| `CLAUDE.md` | Document `--context` flag, `[D#]` tags, Claude Code only note. | Small |
| `README.md` | Add context files section to Quick Start and Commands. | Small |

**Total: 15 files modified, 0 new files.** ~30% smaller surface than the original spec.

---

## Open Questions

1. **Multi-file conflict detection.** If two files contradict each other (file A says revenue is $4M, file B says $3.8M), should extraction flag this? Probably yes, as a note in `context-extracted.md`: "CONFLICT: [D1] and [D4] report different revenue figures." Personas and the adversary will pick this up naturally.

2. **File updates during revise.** If a user does `/autodecision:revise slug --context updated-model.csv`, should the old file's extractions be replaced or both kept? Recommendation: additive. New extractions get new `[D#]` numbers. The revision header notes what changed. Old extractions remain for comparison.

3. **Image extraction quality.** Claude can read images, but extracting structured numbers from a screenshot of a dashboard is harder than from a CSV. Worth a brief note in the extraction output: "Note: [D7]-[D9] extracted from image (screenshot.png). Verify numbers manually." Not a blocker.

4. **ELICIT-attached files and tag numbering.** If the user attaches 2 files via `--context` (producing [D1]-[D6]) and then attaches a third file during ELICIT, the new extractions continue the sequence ([D7]-[D10]). The ELICIT extraction appends to `context-extracted.md` and updates config.json.

---

## Build Order

1. `scope.md` — parse `--context`, validate, extract, write `context-extracted.md` + config.json metadata
2. `engine-protocol.md` — update file structure, shared-context contents, prerequisites
3. `ground.md` — note extraction sharpens queries, flag doc-vs-web conflicts
4. `elicit.md` — show extractions in Block 1, file attachment in Block 4
5. `simulate.md` — document context block in shared-context.md
6. `decide.md` + `output-format.md` + `brief-schema.json` — brief output changes
7. `challenge.md` + `revise.md` — mode support
8. `validation.md` + `validate-brief.py` — tag recognition
9. `SKILL.md` + `CLAUDE.md` + `README.md` — docs

---

## v2 Candidates (deferred)

These are features that could follow if users ask:

| Feature | Why deferred |
|---------|-------------|
| **Fact/claim classification** (`[D#:fact]`, `[D#:claim]`) | Personas handle this naturally. Add formal tags if users want explicit control. |
| **Auto-assumption injection** | Claims auto-generating assumption keys in effects-chains.json. Risk: key proliferation. |
| **Conflict detection** | Formal multi-file contradiction flagging beyond the note-in-extraction approach. |
| **Cowork support** | Would require Cowork file upload API or clipboard integration. |
| **URL-as-context** | `--context https://...` fetching a URL and treating it like a file. Overlaps with Phase 1 web search. |
