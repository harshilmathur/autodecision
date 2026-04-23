---
description: Publish a Decision Brief — generate a PDF and route to an available connector (Notion, email draft, gist, Slack, Drive, or local)
agent: build
---

# /autodecision-publish

Turn a Decision Brief into a shareable artifact. Generate PDF, pick a destination from whatever connectors are available in the current session.

Run on: $ARGUMENTS

## Usage

```
/autodecision-publish                    # interactive — pick a run, pick a destination
/autodecision-publish {slug}             # full brief → interactive destination menu
/autodecision-publish {slug} --summary   # SUMMARY.md → interactive destination menu
```

No destination flags. Every run goes through the menu. The menu only shows destinations that are actually available in the session.

## Bootstrap

Read via `read`:
1. `.claude/skills/autodecision/SKILL.md`
2. `.opencode/host-adapter.md` — OpenCode overrides (PDF chain, connector discovery)
3. `.claude/skills/autodecision/references/phases/publish.md` — the publish protocol

## Execute

Follow `phases/publish.md` with these OpenCode-specific adaptations:

### Step 1: Resolve target

- If `$ARGUMENTS` has a slug: use it. Verify `~/.autodecision/runs/{slug}/DECISION-BRIEF.md` exists (or `SUMMARY.md` if `--summary`).
- If no slug: via `glob` on `~/.autodecision/runs/*/`, list recent runs and use `question` to let the user pick.
- If `--summary` is set but `SUMMARY.md` is missing: tell the user to run `/autodecision-summarize {slug}` first. **Never auto-generate a summary.**

### Step 2: Generate PDF

Follow the priority chain from `phases/publish.md`, adapted for OpenCode (host-adapter.md §7):

1. **Check for a `pdf` skill** — invoke `skill` tool to list available skills. If any declares markdown → PDF conversion, use it.
2. **Pandoc** — via `bash`: `command -v pandoc && pandoc "{brief}" -o "{out}.pdf"`.
3. **`md-to-html.py` fallback** — find the script:
   ```bash
   script="$(find .claude ~/.claude ~/.config/opencode .opencode claude-plugin -name md-to-html.py -path '*/autodecision/*' 2>/dev/null | head -1)"
   python3 "$script" "{brief}" "{out}.html"
   ```
   User opens the HTML in a browser and does "File → Print → Save as PDF."
4. **Raw HTML wrap** — last resort: wrap the markdown in `<pre>` tags and write an HTML file.

Write the PDF (or HTML) to `~/.autodecision/runs/{slug}/share/`.

### Step 3: Detect available destinations

Inspect the available tool list at runtime. Only offer destinations whose connectors are actually present:

- **Local** — always available (write to cwd or a user-provided path)
- **Notion** — if a Notion MCP or connector tool is present
- **Gmail draft** — if a Gmail/email connector is present (**draft only; never auto-send**)
- **Google Drive** — if a Drive connector is present
- **Slack** — if a Slack connector is present
- **Secret gist** — if a GitHub CLI or MCP is present (**secret**, never public)

### Step 4: Route

Use `question` to offer the detected destinations as a multi-choice. Execute the user's pick:

- **Local:** `cp ~/.autodecision/runs/{slug}/share/DECISION-BRIEF.pdf ./`
- **Notion:** create a page under a user-picked parent, attach the PDF.
- **Gmail draft:** create a draft with the PDF attached to a user-picked recipient. Subject: `"Decision Brief: {decision_statement}"`. Never send.
- **Google Drive:** upload to a user-picked folder.
- **Slack:** upload to a user-picked channel (prefer DM by default).
- **Secret gist:** `gh gist create --private {brief_path}` — never public.

### Step 5: cwd export

Always also copy the generated PDF (or HTML) to the current working directory as `{slug}-DECISION-BRIEF.pdf`. Report the local path.

### Step 6: Journal

Append `type: "publish"` entry to `~/.autodecision/journal.jsonl` per `journal-spec.md`: `{decision_id, timestamp, destination, artifact_path}`.

## Hard Rules

- **Never auto-sends email.** Drafts only. Always.
- **Never publishes to the open web.** No public URLs. No public gists. No "Anyone with the link."
- **Never modifies the source markdown.** Just packages and routes.
- **Never auto-generates a summary.** `--summary` requires an existing `SUMMARY.md`.
- **User confirmation before any external side-effect.** Every destination needs a `question` confirmation step before execution.
