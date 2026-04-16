#!/usr/bin/env python3
"""
Convert a Decision Brief markdown file to styled HTML.
No external dependencies — stdlib only. Handles the markdown patterns
used in Decision Briefs: headers, tables, bold, italic, lists,
blockquotes, code blocks, links, source tags, horizontal rules.

Usage:
    python3 md-to-html.py <input.md> <output.html> [title]

Exit codes:
    0  success
    1  usage error
    2  file error
"""

import re
import sys
import html as html_mod


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

def inline_format(text):
    """Bold, italic, code spans, links, source tags."""
    text = html_mod.escape(text)
    # Code spans first (protect contents)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic (single *)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Source tags [G1], [D2], [U#], [C3:persona]
    text = re.sub(
        r'\[(G|D|U|C)\d+(?::[a-zA-Z]+)?\]',
        r'<span class="tag">\g<0></span>',
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Block-level conversion
# ---------------------------------------------------------------------------

def md_to_html(md_text):
    """Convert markdown to HTML. Not a full CommonMark parser —
    tuned for Decision Brief patterns."""

    # Strip HTML comments (validator-refs blocks, etc.)
    md_text = re.sub(r'<!--[\s\S]*?-->', '', md_text)

    lines = md_text.split('\n')
    out = []
    i = 0
    in_table = False
    in_code = False
    in_ul = False
    in_ol = False
    in_bq = False

    def close_list():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append('</ul>')
            in_ul = False
        if in_ol:
            out.append('</ol>')
            in_ol = False

    def close_table():
        nonlocal in_table
        if in_table:
            out.append('</tbody></table>')
            in_table = False

    def close_bq():
        nonlocal in_bq
        if in_bq:
            out.append('</blockquote>')
            in_bq = False

    while i < len(lines):
        line = lines[i]

        # --- Code blocks ---
        if line.strip().startswith('```'):
            if in_code:
                out.append('</code></pre>')
                in_code = False
            else:
                close_list(); close_table(); close_bq()
                lang = html_mod.escape(line.strip()[3:].strip())
                cls = f' class="language-{lang}"' if lang else ''
                out.append(f'<pre><code{cls}>')
                in_code = True
            i += 1
            continue

        if in_code:
            out.append(html_mod.escape(line) + '\n')
            i += 1
            continue

        # --- Horizontal rule ---
        if re.match(r'^[\s]*[-*_]{3,}\s*$', line):
            close_list(); close_table(); close_bq()
            out.append('<hr>')
            i += 1
            continue

        # --- Headers ---
        hm = re.match(r'^(#{1,6})\s+(.*)', line)
        if hm:
            close_list(); close_table(); close_bq()
            lvl = len(hm.group(1))
            text = inline_format(hm.group(2))
            out.append(f'<h{lvl}>{text}</h{lvl}>')
            i += 1
            continue

        # --- Tables ---
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.strip().split('|')[1:-1]]
            # Separator row
            if all(re.match(r'^[-:]+$', c) for c in cells if c):
                i += 1
                continue
            if not in_table:
                close_list(); close_bq()
                out.append('<div class="table-wrap"><table><thead><tr>')
                for cell in cells:
                    out.append(f'<th>{inline_format(cell)}</th>')
                out.append('</tr></thead><tbody>')
                in_table = True
            else:
                out.append('<tr>')
                for cell in cells:
                    out.append(f'<td>{inline_format(cell)}</td>')
                out.append('</tr>')
            i += 1
            continue
        else:
            if in_table:
                out.append('</tbody></table></div>')
                in_table = False

        # --- Blockquote ---
        if line.strip().startswith('>'):
            close_list(); close_table()
            if not in_bq:
                out.append('<blockquote>')
                in_bq = True
            text = re.sub(r'^>\s?', '', line.strip())
            if text:
                out.append(f'<p>{inline_format(text)}</p>')
            i += 1
            continue
        else:
            close_bq()

        # --- List items ---
        ul_match = re.match(r'^(\s*)[-*]\s+(.*)', line)
        ol_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)

        if ol_match and not ul_match:
            close_table(); close_bq()
            if in_ul:
                out.append('</ul>')
                in_ul = False
            if not in_ol:
                out.append('<ol>')
                in_ol = True
            out.append(f'<li>{inline_format(ol_match.group(2))}</li>')
            i += 1
            continue

        if ul_match:
            close_table(); close_bq()
            if in_ol:
                out.append('</ol>')
                in_ol = False
            if not in_ul:
                out.append('<ul>')
                in_ul = True
            out.append(f'<li>{inline_format(ul_match.group(2))}</li>')
            i += 1
            continue

        # Close lists on blank or non-list line
        if (in_ul or in_ol) and line.strip() == '':
            close_list()
            i += 1
            continue
        if (in_ul or in_ol) and not ul_match and not ol_match:
            close_list()

        # --- Blank line ---
        if line.strip() == '':
            i += 1
            continue

        # --- Paragraph ---
        out.append(f'<p>{inline_format(line)}</p>')
        i += 1

    # Close any open elements
    close_list(); close_table(); close_bq()
    if in_code:
        out.append('</code></pre>')

    return '\n'.join(out)


# ---------------------------------------------------------------------------
# CSS — print-friendly, clean typography
# ---------------------------------------------------------------------------

CSS = """\
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'Helvetica Neue', Arial, sans-serif;
    max-width: 840px;
    margin: 2em auto;
    padding: 0 1.5em;
    line-height: 1.65;
    color: #1a1a1a;
    font-size: 15px;
}
h1 { font-size: 1.6em; margin-top: 1.5em; color: #111; }
h2 {
    font-size: 1.3em; border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0.3em; margin-top: 2em; color: #222;
}
h3 { font-size: 1.1em; margin-top: 1.5em; color: #333; }
.table-wrap { overflow-x: auto; margin: 1em 0; }
table {
    border-collapse: collapse; width: 100%;
    font-size: 0.92em;
}
th, td {
    border: 1px solid #d0d0d0; padding: 8px 12px;
    text-align: left; vertical-align: top;
}
th { background: #f7f7f7; font-weight: 600; }
tr:nth-child(even) { background: #fafafa; }
pre {
    white-space: pre-wrap; background: #f5f5f5;
    padding: 1em; border-radius: 6px;
    font-size: 0.9em; overflow-x: auto;
}
code {
    background: #f0f0f0; padding: 2px 5px;
    border-radius: 3px; font-size: 0.9em;
}
pre code { background: none; padding: 0; }
blockquote {
    border-left: 4px solid #ccc; margin: 1em 0;
    padding: 0.5em 1em; color: #555; background: #fafafa;
    border-radius: 0 4px 4px 0;
}
blockquote p { margin: 0.3em 0; }
ul, ol { padding-left: 1.5em; }
li { margin: 0.4em 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 2em 0; }
strong { font-weight: 600; }
a { color: #0066cc; text-decoration: none; }
a:hover { text-decoration: underline; }
.tag {
    background: #e8f0fe; color: #1a56db;
    padding: 1px 5px; border-radius: 3px;
    font-size: 0.85em; font-weight: 500;
    white-space: nowrap;
}
footer {
    margin-top: 3em; padding-top: 1em;
    border-top: 1px solid #eee; color: #888;
    font-size: 0.85em;
}
@media print {
    body { max-width: none; margin: 0; padding: 0 0.5in; font-size: 11px; }
    h1, h2, h3 { page-break-after: avoid; }
    table, pre, blockquote { page-break-inside: avoid; }
    .tag { background: #eee; color: #333; border: 1px solid #ccc; }
    a { color: #333; }
    footer { display: none; }
}
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.html> [title]",
              file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "Decision Brief"

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except (OSError, IOError) as e:
        print(f"Error reading {input_path}: {e}", file=sys.stderr)
        sys.exit(2)

    body = md_to_html(md_content)
    title_esc = html_mod.escape(title)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc}</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
<footer>
Generated by Auto-Decision Engine &middot;
File &rarr; Print &rarr; Save as PDF for a shareable copy.
</footer>
</body>
</html>"""

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
    except (OSError, IOError) as e:
        print(f"Error writing {output_path}: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
