<!--
phase: 9
phase_name: PUBLISH
runs_in:
  - full       (optional — user-invoked after DECIDE via offer or /autodecision:publish)
  - medium     (optional — same)
  - quick      (optional — same)
  - revise     (optional — offered after revision output)
  - challenge  (optional — offered after challenge brief)
  - summarize  (optional — offered after summary output)
reads:
  - ~/.autodecision/runs/{slug}/DECISION-BRIEF.md (or CHALLENGE-BRIEF.md, SUMMARY.md)
writes:
  - PDF artifact (via anthropic-skills:pdf, pandoc, or HTML fallback)
  - Routes to: Notion, email draft, gist, Slack, Drive, or local file
gates:
  - At least one output route must succeed (Local is always available as fallback)
-->

# Phase: PUBLISH

## Purpose

Turn a Decision Brief into a shareable artifact. Produce a PDF, let the user pick
where to send it (Notion page, email draft, secret gist, Slack, Drive, or just
save locally), and route through whichever connectors are available in the
current session. Always falls back to "PDF on disk, path in clipboard" — local
works everywhere.

Content is never modified. This phase only packages and ships.

## Invocation

```
/autodecision:publish                    # interactive: pick run, pick destination
/autodecision:publish {slug}             # full brief → interactive destination menu
/autodecision:publish {slug} --summary   # SUMMARY.md → interactive destination menu
```

No destination flags. Every run goes through the menu. Picking "Local" from the
menu is one keystroke — not worth a flag.

## Progress Template

```
Publish: Resolve run + content          [pending]
Publish: Generate PDF                    [pending]
Publish: Detect destinations             [pending]
Publish: Route to destination            [pending]
Publish: Offer cwd export                [pending]
```

## Step 1: RESOLVE RUN + CONTENT

### 1a. Resolve slug

If `{slug}` is provided:

```bash
if [ -d ~/.autodecision/runs/{slug} ]; then
  echo "found"
else
  # Try prefix match
  matches=$(ls -d ~/.autodecision/runs/{slug}* 2>/dev/null)
  # If exactly 1 match, use it. If 0, list all. If 2+, disambiguate.
fi
```

- **Exact match:** proceed.
- **Prefix match (unique):** proceed with the matched slug, tell the user.
- **Multiple prefix matches:** show all, ask user via AskUserQuestion to pick.
- **No match:** list all runs (newest first), ask user to pick.

If `{slug}` is omitted: list runs newest first, ask user to pick via
AskUserQuestion. Show decision statement + timestamp for each.

```bash
# Newest first
ls -t ~/.autodecision/runs/ | head -20
```

### 1b. Select content source

| Flag | Source | If missing |
|------|--------|-----------|
| (default) | `~/.autodecision/runs/{slug}/DECISION-BRIEF.md` | Fatal error: "Brief not found. Did this run complete Phase 8?" |
| `--summary` | `~/.autodecision/runs/{slug}/SUMMARY.md` | Fatal error: "Run `/autodecision:summarize {slug}` first." |

Do NOT auto-generate a summary when `--summary` is passed and the file is
missing. Summarize is its own command. Error cleanly and point the user to it.

### 1c. Set working variables

```
SLUG="{slug}"
CONTENT_KIND="brief" | "summary"
SOURCE_MD="~/.autodecision/runs/$SLUG/DECISION-BRIEF.md"    # or SUMMARY.md
BASENAME="DECISION-BRIEF" | "SUMMARY"
SHARE_DIR="~/.autodecision/runs/$SLUG/share"
PDF_PATH="$SHARE_DIR/$BASENAME.pdf"
HTML_PATH="$SHARE_DIR/$BASENAME.html"
```

```bash
mkdir -p "$SHARE_DIR"
```

## Step 2: GENERATE PDF (or styled HTML)

Try methods in priority order. First success wins. Surface the method used
in the final status message.

### 2a. anthropic-skills:pdf (preferred)

Check if the `anthropic-skills:pdf` skill is available in this session. If yes,
invoke it via the Skill tool with the source markdown file as input and
`PDF_PATH` as the output target.

If the skill errors or isn't available, fall through to 2b.

### 2b. pandoc → PDF

Check for pandoc on PATH:

```bash
if command -v pandoc >/dev/null 2>&1; then
  pandoc "$SOURCE_MD" -o "$PDF_PATH" 2>&1
fi
```

Pandoc figures out the PDF engine (xelatex, lualatex, wkhtmltopdf, weasyprint) from
what's installed. If no engine is available, pandoc errors — fall through to 2c.

### 2c. Python md-to-html.py → styled HTML (then Print to PDF)

If PDF generation failed, produce a properly styled HTML file. **Do NOT dump raw
markdown into a `<pre>` tag.** The script at `scripts/md-to-html.py` converts
markdown to clean, print-friendly HTML with rendered tables, headers, bold, source
tag highlights, and `@media print` rules for File → Print → Save as PDF.

```bash
# Find the script. It lives alongside validate-brief.py in the skill's scripts/ dir.
SCRIPT_DIR="$(find ~/.claude/skills/autodecision/scripts \
                    claude-plugin/skills/autodecision/scripts \
                    .claude/skills/autodecision/scripts \
                    -name 'md-to-html.py' 2>/dev/null | head -1)"

if [ -n "$SCRIPT_DIR" ] && command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR" "$SOURCE_MD" "$HTML_PATH" "Decision Brief — $SLUG"
fi
```

The orchestrator can also run the script inline: it knows the skill directory path
and can construct the full path to `scripts/md-to-html.py`. The script takes 3 args:
`<input.md> <output.html> [title]`.

If the script succeeds, the HTML is ready. Open it and tell the user they can use
File → Print → Save as PDF for a shareable copy.

If Python is not available OR the script errors, fall through to 2d.

### 2d. pandoc → standalone HTML

If pandoc is available but its PDF engine isn't (and Python failed):

```bash
pandoc "$SOURCE_MD" -o "$HTML_PATH" --standalone --metadata title="$BASENAME"
```

This produces rendered HTML via pandoc's markdown parser. Acceptable quality.

### 2e. Raw fallback (last resort)

If nothing else works (no anthropic-skills:pdf, no pandoc, no Python), wrap the
markdown in basic HTML. This is the worst-case path — raw markdown is readable but
tables, bold, and headers won't render.

```bash
{
  printf '<!doctype html><meta charset="utf-8"><title>%s</title>\n' "$BASENAME"
  printf '<style>body{font:14px/1.5 -apple-system,system-ui,sans-serif;max-width:780px;margin:2em auto;padding:0 1em}table{border-collapse:collapse;width:100%%}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f5f5f5}pre{white-space:pre-wrap;background:#f8f8f8;padding:1em;border-radius:4px}</style>\n'
  printf '<pre>\n'
  sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' "$SOURCE_MD"
  printf '</pre>\n'
} > "$HTML_PATH"
```

### After HTML generation (2c/2d/2e): open and inform

```bash
case "$(uname -s)" in
  Darwin) open "$HTML_PATH" ;;
  Linux)  xdg-open "$HTML_PATH" ;;
  *)      echo "Open manually: $HTML_PATH" ;;
esac
```

Tell the user: "PDF conversion unavailable. Opened the brief in your browser.
Use File → Print → Save as PDF for a shareable PDF."

Set `PDF_PATH=""` (empty) to signal downstream routing that no PDF exists.
Destinations that need a PDF (Slack, Drive, email attachment) should fall back
to sending the markdown or degrade gracefully.

### Priority summary

```
2a  anthropic-skills:pdf  →  PDF (best)
2b  pandoc + engine       →  PDF
2c  python3 md-to-html.py →  styled HTML (tables, headers, print CSS)
2d  pandoc --standalone   →  rendered HTML (pandoc's markdown parser)
2e  raw <pre> wrap        →  raw text in HTML (last resort, bad quality)
```

**The common case on a Mac with Python but no pandoc is 2c.** This produces
a clean, readable HTML file with proper tables and a "Save as PDF" footer.

## Step 3: DETECT DESTINATIONS

Check which connectors are available in the current session by matching tool
name patterns against the active tool list. The tool list is visible to you.

| Destination | Required tool pattern | Sent as |
|------------|----------------------|---------|
| Notion | `*notion*create-pages*` AND `*notion*search*` | Page content (markdown) |
| Gmail draft | `*gmail*draft*` or `*mail*draft*` | PDF attached + body |
| Google Drive | `*drive*upload*` or `*gdrive*` | PDF file |
| Slack | `*slack*post*message*` or `*slack*send*` | PDF + summary text |
| Secret Gist | `gh` on PATH AND `gh auth status` exit 0 | Markdown file |
| Local | always | PDF on disk |

For shell-based checks (Gist):

```bash
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  GIST_AVAILABLE=1
fi
```

**Local is always available.** The PDF (or HTML fallback) is already on disk —
nothing else to do except open it and copy the path.

Build a list of available destinations. If only Local is available, you can
skip the menu and route directly to Local (tell the user no connectors were
detected and proceed).

## Step 4: ROUTE TO DESTINATION

Render an AskUserQuestion menu with the detected destinations only. Local is
always first. Example (when Notion + gh are detected):

> "Where do you want to publish the Decision Brief for `{slug}`?"
>
> A) Local — open the PDF and copy the path to your clipboard
> B) Notion — create a new page under a parent you choose
> C) Secret Gist — create a private GitHub gist (URL only you can access)
> D) Cancel

Only show options that were detected in Step 3. Always include Local and Cancel.

### 4a. Local

```bash
# Open the PDF (or HTML if fallback)
TARGET="${PDF_PATH:-$HTML_PATH}"
case "$(uname -s)" in
  Darwin)
    open "$TARGET"
    printf "%s" "$TARGET" | pbcopy 2>/dev/null || true
    ;;
  Linux)
    xdg-open "$TARGET" 2>/dev/null || true
    printf "%s" "$TARGET" | (xclip -selection clipboard 2>/dev/null || xsel --clipboard 2>/dev/null || true)
    ;;
  *)
    start "" "$TARGET" 2>/dev/null || true
    ;;
esac
```

If clipboard copy silently fails (no pbcopy/xclip/xsel), say so in the status
message rather than claiming success.

**Status line:** `Opened $TARGET (path copied to clipboard if supported).`

### 4b. Notion

1. Ask the user where to put the page via AskUserQuestion:
   > "Which Notion workspace page should I create this under?"
   >
   > A) Search by name (you type a parent page title)
   > B) Paste a Notion URL or page ID
   > C) Cancel

2. If A: call `notion-search` with the user's title, show top 5 results, ask
   which. If B: parse the URL/ID directly.

3. Call `notion-create-pages` with:
   - Parent: the resolved parent page
   - Title: the decision statement from `config.json` (+ " — Decision Brief" or " — Summary")
   - Content: the full markdown from `SOURCE_MD`

   **One long page, not split by section.** The MCP accepts markdown content
   and Notion will render headers, tables, code blocks, and lists natively.
   Do not pre-chunk into blocks manually in v0.

4. If the brief contains image references (`![alt](...)`), warn: "This brief
   contains images — they won't render in Notion unless the paths are public
   URLs."

5. Return the created page URL.

**Status line:** `Created Notion page: {url}`

### 4c. Gmail draft (draft-only, never send)

1. Ask the user for the recipient(s) via AskUserQuestion (free text).

2. Build a short body from the Executive Summary section of the brief. Grep
   the brief for `## Executive Summary` through the next `## ` and use that
   as the email body. If no Executive Summary section exists, use the first
   200 words.

3. Call the gmail draft tool with:
   - To: user-provided recipients
   - Subject: `Decision Brief — {decision_statement}` (or `Summary —` for summaries)
   - Body: executive summary + "Full analysis attached as PDF."
   - Attachment: `$PDF_PATH` (if empty, attach the markdown instead and mention it)

4. Never call a send tool. Only draft tools. If the draft tool has a "send"
   parameter, explicitly set it to false.

5. Return the draft URL or message ID.

**Status line:** `Gmail draft created: {url or id}. Open Gmail to review and send.`

### 4d. Google Drive

1. Ask for destination folder (default: "Decisions"). If the folder doesn't
   exist, create it.

2. Upload `$PDF_PATH` to that folder. Filename: `{slug}-{basename}.pdf`.

3. If `$PDF_PATH` is empty (fallback case), upload the markdown file instead
   and note it in the status line.

**Status line:** `Uploaded to Drive: {url}`

### 4e. Slack

1. Ask for channel (free text, e.g. `#strategy` or `@username`).

2. Build summary message: first 3 bullets from Executive Summary +
   "Full brief attached."

3. Upload `$PDF_PATH` to the channel with the summary as the accompanying
   message.

**Status line:** `Posted to Slack {channel}: {permalink}`

### 4f. Secret Gist

```bash
# gh defaults to secret when --public is NOT passed
gh gist create "$SOURCE_MD" \
  --filename "$(basename "$SOURCE_MD")" \
  --desc "Decision Brief: {decision_statement}"
```

**Never pass `--public`.** Gist is explicitly the private-share path. Parse
the gist URL from stdout.

Gists don't support PDF rendering — always use the markdown source, not the
PDF. Print this in the status line so the user knows.

**Status line:** `Created secret gist (markdown, not PDF): {url}. Only people with this URL can view it.`

### 4g. Cancel

Do nothing. Return to conversation.

## Step 5: OFFER CWD EXPORT

After routing completes (except on Cancel), offer to also save the PDF to the
current working directory:

> "Also save the PDF to the current directory?"
>
> A) Save `{slug}-{basename}.pdf` to cwd
> B) Skip

If A:
```bash
cp "$PDF_PATH" "./$SLUG-$BASENAME.pdf" 2>/dev/null && \
  echo "Saved ./$SLUG-$BASENAME.pdf" || \
  echo "No PDF to copy (HTML fallback was used; file is at $HTML_PATH)"
```

If the PDF doesn't exist (HTML fallback), skip the offer or offer the HTML instead.

## Step 6: PRINT STATUS

Print a three-line status summary before ending the turn:

```
Published: {slug} ({content kind})
Destination: {Local|Notion|Gmail draft|Drive|Slack|Gist}
{Where it is: URL or path}
```

Then the next user action, specific to the destination:

- Local: "Open the PDF to review or forward."
- Notion: "Review the page and share with your team."
- Gmail: "Review the draft and send when ready."
- Drive: "Share the Drive link with stakeholders."
- Slack: "Team can read it now."
- Gist: "Share the gist URL privately — anyone with the link can view."

## Step 6.5: Mention the visualizer (experimental)

After the status lines, print one experimental tip on a new line:

"Tip: `/autodecision:visualize {slug}` renders an interactive orbital diagram of the effects cascade (experimental)."

Skip the tip if the user cancelled the publish menu, or if the source run is
quick mode (no `effects-chains.json` exists, so the visualizer has nothing to
render). Detect quick mode by reading `config.json > mode` or by checking that
no `iteration-*/effects-chains.json` exists in the run directory.

This is informational only — no AskUserQuestion, no auto-invoke. The user
chose to publish; surfacing a follow-on prompt is noise. The tip is a single
line they can ignore or copy.

## Edge cases

| Case | Behavior |
|------|----------|
| Slug doesn't exist | List all runs, ask user to pick via AskUserQuestion |
| Slug is a prefix matching one run | Use it, tell the user "Matched `{full-slug}`" |
| Slug prefix matches multiple | Disambiguation menu |
| `--summary` but `SUMMARY.md` missing | Fatal: "Run `/autodecision:summarize {slug}` first." |
| `DECISION-BRIEF.md` missing | Fatal: "Brief not found. Did this run complete Phase 8?" |
| No connectors detected (only Local available) | Skip menu, go straight to Local, tell user |
| PDF generation fails (no skill, no pandoc, no engines) | HTML fallback + open in browser |
| Brief contains `![image](...)` | Warn before Notion/PDF: "Embedded images may not render if paths aren't public URLs." |
| `gh` present but not authenticated | Filter Gist out of the menu (not "silently fail") |
| User cancels menu | Return cleanly, no status lines |

## What this phase NEVER does

- **Never auto-sends email.** Draft only.
- **Never publishes to the open web.** No public hosted URLs, no public gists,
  no public Notion pages (child of user-chosen parent only).
- **Never modifies the source markdown.** `DECISION-BRIEF.md` and `SUMMARY.md`
  in the run directory stay untouched.
- **Never creates a summary on the fly.** `--summary` requires an existing `SUMMARY.md`.
- **Never skips the cwd export offer** except on Cancel.

## Persist

Append a publish entry to `~/.autodecision/journal.jsonl` so `/autodecision:review`
can see that a brief was published:

```json
{
  "decision_id": "{slug}",
  "type": "publish",
  "content": "brief" | "summary",
  "destination": "local|notion|gmail|drive|slack|gist",
  "target": "{url or path}",
  "timestamp": "...",
  "pdf_method": "anthropic-skills|pandoc|html-fallback"
}
```

This is a sibling event to the original decision entry — it doesn't overwrite
anything. Keeps an audit trail of where each brief went.
