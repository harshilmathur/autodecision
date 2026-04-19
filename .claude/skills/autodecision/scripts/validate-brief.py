#!/usr/bin/env python3
"""
validate-brief.py — Mechanical validator for Decision Brief.

Reads DECISION-BRIEF.md + brief-schema.json + upstream JSON sources,
checks structure (section order, presence, subsections, tables, required
content), checks snake_case leaks in prose, checks cross-references via
HTML ref comments.

Exit codes:
  0 — all checks passed
  1 — soft warnings only (non-blocking)
  2 — hard fail (brief fails validation; orchestrator re-prompts DECIDE)
  3 — usage / script error

Outputs:
  {run_dir}/validation-report.json — machine-readable check results
  stdout — human-readable summary

Usage:
  validate-brief.py --run-dir ~/.autodecision/runs/{slug} \
                    --schema  {skill_dir}/references/brief-schema.json \
                    [--mode full|medium|quick]

The orchestrator reads validation-report.json after this script runs and
decides whether to re-prompt DECIDE based on severity_on_fail in the schema.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ----------------------------------------------------------------------
# utilities
# ----------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def die(msg: str, code: int = 3) -> None:
    log(f"ERROR: {msg}")
    sys.exit(code)


def latest_iteration(run_dir: Path) -> Path | None:
    iters = sorted([p for p in run_dir.glob("iteration-*") if p.is_dir()])
    return iters[-1] if iters else None


def resolve_iteration_source(run_dir: Path, rel_path: str) -> Path | None:
    """Resolve `iteration-{latest}/{file}` against the newest iteration that
    actually contains the file. The LIGHT-mode iterations 2+ re-run only
    simulate + converge, so adversary.json / sensitivity.json / critique.json
    live in iteration-1. Walk newest → oldest; use the first hit."""
    iters = sorted([p for p in run_dir.glob("iteration-*") if p.is_dir()], reverse=True)
    for it in iters:
        candidate = run_dir / rel_path.replace("iteration-{latest}", it.name)
        if candidate.exists():
            return candidate
    return None


def strip_code_blocks(md: str) -> str:
    """Remove fenced code blocks and inline code from markdown so regex
    checks can scan prose without false-positive hits inside ```...``` or
    `foo_bar`. Preserves line positions for accurate line numbers."""
    out_lines = []
    in_fence = False
    for line in md.split("\n"):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out_lines.append("")
            continue
        if in_fence:
            out_lines.append("")
            continue
        # strip inline `code`
        out_lines.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(out_lines)


def strip_html_comments(md: str) -> str:
    """Remove <!-- ... --> blocks. Preserves line count."""
    return re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)


def strip_markdown_links(md: str) -> str:
    """Remove [text](url) linking — keep the text, drop the url — so
    URL paths don't trigger snake_case checks."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)


def extract_h2_sections(md: str) -> list[tuple[int, str]]:
    """Return list of (1-indexed line number, header_text) for '## ' headers,
    ignoring headers inside code fences."""
    found: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(md.split("\n"), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## ") and not line.startswith("## #"):
            found.append((i, line.rstrip()))
    return found


def extract_subsections_between(md: str, start_line: int, end_line: int) -> list[tuple[int, str]]:
    """Return '### ' headers between start_line (exclusive) and end_line
    (exclusive). 1-indexed."""
    lines = md.split("\n")
    found: list[tuple[int, str]] = []
    in_fence = False
    for i in range(start_line, min(end_line, len(lines) + 1)):
        line = lines[i - 1]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("### "):
            found.append((i, line.rstrip()))
    return found


def section_body(md: str, start_line: int, end_line: int) -> str:
    lines = md.split("\n")
    return "\n".join(lines[start_line:end_line - 1]) if end_line > start_line else ""


def has_markdown_table(text: str) -> bool:
    """Detect a markdown table: at least one | row followed by a separator
    row of the form |---|---|..."""
    lines = text.split("\n")
    for i in range(len(lines) - 1):
        if "|" in lines[i] and re.match(r"^\s*\|?\s*:?-+", lines[i + 1].strip()):
            return True
    return False


def table_columns(text: str) -> list[str]:
    """Return column headers from the first markdown table in text."""
    lines = text.split("\n")
    for i in range(len(lines) - 1):
        if "|" in lines[i] and re.match(r"^\s*\|?\s*:?-+", lines[i + 1].strip()):
            cells = [c.strip() for c in lines[i].strip("|").split("|")]
            return [c for c in cells if c]
    return []


def count_bullets(text: str) -> int:
    return sum(1 for line in text.split("\n") if re.match(r"^\s*[-*]\s+\S", line))


def extract_refs(md: str) -> list[str]:
    """
    Return a flat list of all ref IDs preserved in the brief.

    New format (primary) — one trailing block at end of brief:

        <!-- validator-refs:
        worst_cases: wc1_a, wc2_b
        black_swans: bs1_c
        irrational_actors: ia1_d
        effects: acq_increase, churn_reduction
        -->

    Legacy format (fallback) — inline per item:

        - something ... <!-- ref:wc1_a -->

    Both formats are merged into one list. Downstream coverage checks
    test presence by membership, so dedup isn't required but is cheap.
    """
    ids: list[str] = []

    # Trailing block: capture everything between <!-- validator-refs: and -->
    block_match = re.search(
        r"<!--\s*validator-refs:\s*(.*?)-->",
        md,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if block_match:
        body = block_match.group(1)
        # Each line is "category: id1, id2, id3"
        for line in body.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            _, _, values = line.partition(":")
            for token in values.split(","):
                token = token.strip()
                if re.fullmatch(r"[a-z][a-z0-9_]*", token):
                    ids.append(token)

    # Legacy inline comments (backward compat)
    ids.extend(re.findall(r"<!--\s*ref:([a-z][a-z0-9_]+)\s*-->", md))

    return ids


def extract_refs_by_category(md: str) -> dict[str, set[str]]:
    """
    Parse the trailing <!-- validator-refs: --> block into categories.
    Returns {} if the block is absent (legacy briefs).
    Known keys: worst_cases, black_swans, irrational_actors, effects.
    """
    out: dict[str, set[str]] = {}
    block_match = re.search(
        r"<!--\s*validator-refs:\s*(.*?)-->",
        md,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not block_match:
        return out
    for line in block_match.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, values = line.partition(":")
        key = key.strip().lower()
        bucket = {
            t.strip()
            for t in values.split(",")
            if re.fullmatch(r"[a-z][a-z0-9_]*", t.strip())
        }
        if bucket:
            out[key] = bucket
    return out


# ----------------------------------------------------------------------
# check results
# ----------------------------------------------------------------------

class Report:
    def __init__(self, schema: dict):
        self.schema = schema
        self.checks: list[dict] = []

    def add(self, name: str, status: str, severity: str, detail: str, **extra) -> None:
        self.checks.append(
            {"name": name, "status": status, "severity": severity, "detail": detail, **extra}
        )

    def severities_present(self) -> set[str]:
        return {c["severity"] for c in self.checks if c["status"] == "FAIL"}

    def exit_code(self) -> int:
        sev = self.severities_present()
        if "HARD_FAIL" in sev:
            return 2
        if "WARN" in sev:
            return 1
        return 0

    def as_dict(self) -> dict:
        passes = sum(1 for c in self.checks if c["status"] == "PASS")
        fails = sum(1 for c in self.checks if c["status"] == "FAIL")
        return {
            "schema_version": self.schema.get("schema_version"),
            "summary": {"passed": passes, "failed": fails, "total": len(self.checks)},
            "exit_code": self.exit_code(),
            "severities_failed": sorted(self.severities_present()),
            "checks": self.checks,
        }


# ----------------------------------------------------------------------
# checks
# ----------------------------------------------------------------------

def required_in_mode(section: dict, mode: str) -> bool:
    return mode in section.get("required_in", [])


def optional_in_mode(section: dict, mode: str) -> bool:
    return mode in section.get("optional_in", [])


def skipped_in_mode(section: dict, mode: str) -> bool:
    return mode in section.get("skip_in", [])


def check_section_order_and_presence(md: str, schema: dict, mode: str, report: Report) -> dict:
    """Return {position: (start_line, end_line)} for every section found."""
    found_h2 = extract_h2_sections(md)
    # Build a map of header_text -> line_number
    found_by_header = {h: ln for ln, h in found_h2}
    positions: dict[int, tuple[int, int]] = {}

    # Compute end-of-each-found-header
    sorted_found = sorted(found_h2, key=lambda t: t[0])
    total_lines = len(md.split("\n"))
    header_spans: dict[str, tuple[int, int]] = {}
    for idx, (ln, h) in enumerate(sorted_found):
        end = sorted_found[idx + 1][0] if idx + 1 < len(sorted_found) else total_lines + 1
        header_spans[h] = (ln, end)

    last_found_line = 0
    for sec in schema["sections"]:
        pos = sec["position"]
        header = sec["header"]
        required = required_in_mode(sec, mode)
        optional = optional_in_mode(sec, mode)
        skipped = skipped_in_mode(sec, mode)

        if header in found_by_header:
            line = found_by_header[header]
            span = header_spans[header]
            positions[pos] = span
            # Order check: must appear after the previous found section
            if line < last_found_line:
                report.add(
                    f"section_order[{pos}:{header}]",
                    "FAIL", "HARD_FAIL",
                    f"Section '{header}' appears at line {line}, but a later section appeared at line {last_found_line}. Sections must be in schema order.",
                )
            else:
                report.add(
                    f"section_order[{pos}:{header}]",
                    "PASS", "INFO",
                    f"Section '{header}' at line {line}",
                )
            last_found_line = max(last_found_line, line)
        else:
            if required:
                report.add(
                    f"section_missing[{pos}:{header}]",
                    "FAIL", "HARD_FAIL",
                    f"Required section '{header}' not found (mode={mode}).",
                )
            elif skipped:
                report.add(
                    f"section_skipped[{pos}:{header}]",
                    "PASS", "INFO",
                    f"Section '{header}' correctly omitted in {mode} mode.",
                )
            elif optional:
                report.add(
                    f"section_optional[{pos}:{header}]",
                    "PASS", "INFO",
                    f"Optional section '{header}' omitted (allowed in {mode} mode).",
                )

    # Recommendation-position check: must not appear before position 12
    rec_header = "## Recommendation"
    if rec_header in found_by_header:
        rec_line = found_by_header[rec_header]
        # Find what H2s came before it
        earlier = [h for ln, h in sorted_found if ln < rec_line and h != rec_header]
        if len(earlier) < 5:  # heuristic: at least 5 H2s before Recommendation
            report.add(
                "recommendation_position",
                "FAIL", "HARD_FAIL",
                f"Section 'Recommendation' appears at line {rec_line} with only {len(earlier)} section(s) before it. "
                f"Recommendation MUST be section 12 — the full possibility map (Data Foundation through Convergence Log) "
                f"must precede it. Move it to after Convergence Log.",
            )
        else:
            report.add(
                "recommendation_position",
                "PASS", "INFO",
                f"Recommendation at line {rec_line} with {len(earlier)} preceding sections.",
            )

    return positions


def check_section_content(md: str, schema: dict, positions: dict, mode: str, report: Report) -> None:
    md_plain = strip_code_blocks(strip_html_comments(md))
    lines = md.split("\n")
    for sec in schema["sections"]:
        pos = sec["position"]
        header = sec["header"]
        if pos not in positions:
            continue
        start, end = positions[pos]
        body_lines = lines[start:end - 1]
        body = "\n".join(body_lines)
        body_plain = "\n".join(md_plain.split("\n")[start:end - 1])

        # min_lines (WARN — the section is present; it's just thin. HARD_FAIL is reserved for structural problems.)
        if "min_lines" in sec:
            nonblank = sum(1 for l in body_lines if l.strip())
            if nonblank < sec["min_lines"]:
                report.add(
                    f"min_lines[{pos}:{header}]",
                    "FAIL", "WARN",
                    f"Section '{header}' has {nonblank} non-blank lines; schema requires >= {sec['min_lines']}.",
                )
            else:
                report.add(
                    f"min_lines[{pos}:{header}]",
                    "PASS", "INFO",
                    f"{nonblank} non-blank lines.",
                )

        # min_bullets
        if "min_bullets" in sec:
            n = count_bullets(body)
            if n < sec["min_bullets"]:
                report.add(
                    f"min_bullets[{pos}:{header}]",
                    "FAIL", "WARN",
                    f"Section '{header}' has {n} bullets; schema requires >= {sec['min_bullets']}. "
                    f"This section should cover multiple dimensions (strongest analysis, weakest analysis, "
                    f"key disagreement, uncertainty hotspot, etc.), not be compressed to a one-liner.",
                )
            else:
                report.add(
                    f"min_bullets[{pos}:{header}]",
                    "PASS", "INFO",
                    f"{n} bullets.",
                )

        # required_content (mode-specific or flat)
        required_content = sec.get("required_content", []) or \
                           sec.get("required_content_in", {}).get(mode, [])
        for rc in required_content:
            pat = rc["pattern"]
            if re.search(pat, body):
                report.add(
                    f"required_content[{pos}:{rc['desc']}]",
                    "PASS", "INFO",
                    f"Found: {rc['desc']}",
                )
            else:
                report.add(
                    f"required_content[{pos}:{rc['desc']}]",
                    "FAIL", "HARD_FAIL",
                    f"Section '{header}' missing required content: {rc['desc']} (pattern: {pat}).",
                )

        # requires_table (flat or mode-specific)
        needs_table = sec.get("requires_table", False) or \
                      (mode in sec.get("requires_table_in", []))
        if needs_table:
            if has_markdown_table(body):
                # Column check if specified
                if "table_columns" in sec:
                    actual = table_columns(body)
                    expected = sec["table_columns"]
                    missing = [c for c in expected if c not in actual]
                    if missing:
                        report.add(
                            f"table_columns[{pos}:{header}]",
                            "FAIL", "WARN",
                            f"Table missing columns: {missing}. Expected: {expected}. Actual: {actual}.",
                        )
                    else:
                        report.add(
                            f"table_columns[{pos}:{header}]",
                            "PASS", "INFO",
                            f"Table has expected columns: {expected}",
                        )
                else:
                    report.add(
                        f"table_present[{pos}:{header}]",
                        "PASS", "INFO",
                        "Table present.",
                    )
            else:
                report.add(
                    f"table_missing[{pos}:{header}]",
                    "FAIL", "HARD_FAIL",
                    f"Section '{header}' requires a markdown table but none was found.",
                )

        # required_subsections (mode-specific or flat)
        required_subs = sec.get("required_subsections", []) or \
                        sec.get("required_subsections_in", {}).get(mode, [])
        if required_subs:
            found_subs = [h for _, h in extract_subsections_between(md, start + 1, end)]
            for sub in required_subs:
                if any(s.startswith(sub) for s in found_subs):
                    report.add(
                        f"subsection[{pos}:{sub}]",
                        "PASS", "INFO",
                        f"Subsection present: {sub}",
                    )
                else:
                    report.add(
                        f"subsection_missing[{pos}:{sub}]",
                        "FAIL", "HARD_FAIL",
                        f"Section '{header}' is missing required subsection '{sub}' (mode={mode}).",
                    )


def check_cross_references(md: str, schema: dict, run_dir: Path, positions: dict, report: Report) -> None:
    refs_found = set(extract_refs(md))
    for sec in schema["sections"]:
        for xref in sec.get("cross_references", []):
            name = xref["name"]
            src_template = xref["source_file"]
            # Resolve against the newest iteration that contains the file.
            # Iteration 2+ in LIGHT mode does NOT re-emit adversary.json / etc.,
            # so those files live in iteration-1. Walk newest → oldest.
            if "iteration-{latest}" in src_template:
                src_path = resolve_iteration_source(run_dir, src_template)
                display_path = src_path if src_path else (run_dir / src_template.replace("iteration-{latest}", "iteration-*"))
            else:
                src_path_resolved = run_dir / src_template
                src_path = src_path_resolved if src_path_resolved.exists() else None
                display_path = src_path_resolved
            if src_path is None:
                report.add(
                    f"xref_source_missing[{name}]",
                    "FAIL", "WARN",
                    f"Cross-reference source not found: {display_path}.",
                )
                continue
            try:
                src_data = json.loads(src_path.read_text())
            except json.JSONDecodeError as e:
                report.add(
                    f"xref_source_unparseable[{name}]",
                    "FAIL", "WARN",
                    f"Cross-reference source {src_path.name} failed to parse: {e}.",
                )
                continue

            jq_path = xref.get("source_jq", "")
            # Tiny jq-like evaluator — supports .foo[].bar and .foo | length
            src_ids_or_count = eval_jq(src_data, jq_path)

            match_mode = xref.get("match_mode", "id_coverage")
            if match_mode == "count_min":
                expected_count = src_ids_or_count if isinstance(src_ids_or_count, int) else 0
                sub_header = xref.get("brief_subsection", "")
                if sub_header:
                    actual = count_items_in_subsection(md, sub_header)
                else:
                    actual = 0
                if actual >= expected_count and expected_count > 0:
                    report.add(
                        f"xref[{name}]",
                        "PASS", "INFO",
                        f"Subsection '{sub_header}' has {actual} items (source has {expected_count}).",
                    )
                elif expected_count == 0:
                    report.add(
                        f"xref[{name}]",
                        "PASS", "INFO",
                        f"Source has 0 items; nothing to preserve.",
                    )
                else:
                    report.add(
                        f"xref[{name}]",
                        "FAIL", "HARD_FAIL",
                        f"Subsection '{sub_header}' has {actual} items; source {src_path.name} has {expected_count}. "
                        f"Every item in the source JSON must be represented in the brief.",
                    )
            elif match_mode == "count_exact":
                expected_count = src_ids_or_count if isinstance(src_ids_or_count, int) else 0
                sub_header = xref.get("brief_subsection", "")
                actual_rows = count_table_rows_in_section(md, sub_header)
                if actual_rows == expected_count:
                    report.add(
                        f"xref[{name}]",
                        "PASS", "INFO",
                        f"Table in '{sub_header}' has {actual_rows} rows, matching source count {expected_count}.",
                    )
                else:
                    report.add(
                        f"xref[{name}]",
                        "FAIL", "HARD_FAIL",
                        f"Table in '{sub_header}' has {actual_rows} rows; source {src_path.name} has {expected_count} iterations. Must match exactly.",
                    )
            else:
                # id_coverage: refs in brief must cover >= min_coverage_pct of source IDs
                source_ids = set(src_ids_or_count) if isinstance(src_ids_or_count, list) else set()
                covered = source_ids & refs_found
                if not source_ids:
                    report.add(
                        f"xref[{name}]",
                        "PASS", "INFO",
                        f"Source has 0 IDs.",
                    )
                    continue
                pct = 100.0 * len(covered) / len(source_ids)
                need_pct = xref.get("min_coverage_pct", 100)
                if pct >= need_pct:
                    report.add(
                        f"xref[{name}]",
                        "PASS", "INFO",
                        f"{len(covered)}/{len(source_ids)} source IDs referenced ({pct:.0f}%, need >= {need_pct}%).",
                    )
                else:
                    missing = sorted(source_ids - covered)
                    report.add(
                        f"xref[{name}]",
                        "FAIL", "HARD_FAIL",
                        f"Only {len(covered)}/{len(source_ids)} source IDs referenced ({pct:.0f}%, need >= {need_pct}%). "
                        f"Missing refs for: {missing[:5]}{'...' if len(missing) > 5 else ''}. "
                        f"Add <!-- ref:ID --> comments next to items preserved from the source JSON.",
                    )


def eval_jq(data, path: str):
    """Minimal jq evaluator supporting:
       .a.b.c         — nested field access
       .a[].b         — flatmap over array
       . | length     — length of current value
       Returns a list for [] expansions, an int for length, or scalar."""
    if not path or path == ".":
        return data
    if "|" in path:
        left, right = (p.strip() for p in path.split("|", 1))
        left_val = eval_jq(data, left)
        if right == "length":
            return len(left_val) if hasattr(left_val, "__len__") else 0
        return eval_jq(left_val, right)
    # tokenize
    tokens = re.findall(r"\.[a-zA-Z_][a-zA-Z_0-9]*|\[\]", path)
    cur = [data]
    flat = False
    for tok in tokens:
        if tok == "[]":
            new = []
            for item in cur:
                if isinstance(item, list):
                    new.extend(item)
            cur = new
            flat = True
        else:
            key = tok[1:]
            cur = [item[key] for item in cur if isinstance(item, dict) and key in item]
    return cur if flat else (cur[0] if cur else None)


def count_items_in_subsection(md: str, sub_header: str) -> int:
    """Count bullets OR paragraph entries in a ### subsection."""
    lines = md.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == sub_header or line.startswith(sub_header + " "):
            start = i + 1
            break
    if start is None:
        return 0
    # end at next ## or ### header
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## ") or lines[i].startswith("### "):
            end = i
            break
    body = "\n".join(lines[start:end])
    bullet_count = count_bullets(body)
    # paragraph count — non-empty blocks separated by blank lines, excluding the header
    paragraphs = [p for p in re.split(r"\n\s*\n", body.strip()) if p.strip() and not p.strip().startswith("#")]
    # Use whichever is larger — bullets OR paragraphs (some briefs use each for black swans)
    return max(bullet_count, len(paragraphs))


def count_table_rows_in_section(md: str, header: str) -> int:
    """Count data rows in the first markdown table under the given ## header."""
    lines = md.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == header or line.startswith(header + " ") or line.startswith(header):
            start = i + 1
            break
    if start is None:
        return 0
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## ") and not lines[i].startswith(header):
            end = i
            break
    body = "\n".join(lines[start:end])
    body_lines = body.split("\n")
    rows = 0
    in_table = False
    for i, line in enumerate(body_lines):
        if "|" in line and i + 1 < len(body_lines) and re.match(r"^\s*\|?\s*:?-+", body_lines[i + 1].strip()):
            in_table = True
            continue  # header row
        if in_table:
            if "|" in line and not re.match(r"^\s*\|?\s*:?-+", line.strip()):
                rows += 1
            elif not line.strip() or line.startswith("#"):
                break
    return rows


def check_prohibited_patterns(md: str, schema: dict, report: Report) -> None:
    md_clean = strip_html_comments(md)
    md_clean = strip_markdown_links(md_clean)
    md_plain = strip_code_blocks(md_clean)
    for pat in schema.get("prohibited_patterns", []):
        name = pat["name"]
        regex = pat["regex"]
        sev = pat.get("severity", schema["severity_on_fail"].get(name, "HARD_FAIL"))
        # For "raw_effect_id_in_prose", only match OUTSIDE code blocks — so scan md_clean (keeps inline backticks)
        # For "snake_case_in_prose", match in md_plain (no code)
        scan_target = md_clean if pat.get("exempt_in_inline_code") is False else md_plain
        hits = []
        for i, line in enumerate(scan_target.split("\n"), start=1):
            if line.startswith("|") and pat.get("exempt_in_tables", True):
                continue
            if line.startswith("#"):
                continue
            for m in re.finditer(regex, line):
                hits.append((i, m.group(0), line.strip()[:120]))
        # Filter: snake_case matches that are entirely in URL-looking tokens, emails, or markdown table header rows
        hits = [h for h in hits if not re.fullmatch(r"https?://\S+|[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+", h[1])]
        if hits:
            sample = [f"line {ln}: {tok} (\"{ctx[:60]}...\")" for ln, tok, ctx in hits[:5]]
            report.add(
                f"prohibited[{name}]",
                "FAIL", sev,
                f"{len(hits)} occurrence(s) of '{name}'. First: " + "; ".join(sample),
                hits=[{"line": ln, "token": tok, "context": ctx} for ln, tok, ctx in hits[:20]],
            )
        else:
            report.add(
                f"prohibited[{name}]",
                "PASS", "INFO",
                f"No occurrences of '{name}'.",
            )


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

def _header_line_map(md: str) -> dict[str, tuple[int, int]]:
    """Return {header: (start_line, end_line)} for every H2 in the brief."""
    sorted_found = sorted(extract_h2_sections(md), key=lambda t: t[0])
    total_lines = len(md.split("\n"))
    spans: dict[str, tuple[int, int]] = {}
    for idx, (ln, h) in enumerate(sorted_found):
        end = sorted_found[idx + 1][0] if idx + 1 < len(sorted_found) else total_lines + 1
        spans[h] = (ln, end)
    return spans


def check_unsourced_numbers(md: str, schema: dict, positions: dict, report: Report) -> None:
    """
    Enforce content_checks.unsourced_dollar_figure: every dollar figure,
    percentage, multiplier, or ratio in prose must have a source tag
    [G#]/[D#]/[U#]/[C#:persona] within 120 chars. Exempt sections from the schema.
    """
    content_checks = schema.get("content_checks", {})
    cfg = content_checks.get("unsourced_dollar_figure")
    if not cfg:
        return

    num_regex = cfg["regex_for_numbers"]
    tag_regex = cfg["regex_for_tag"]
    proximity = cfg.get("proximity_chars", 120)
    exempt_headers = set(cfg.get("exempt_sections", []))

    # Strip code blocks first — we scan in scan_text, so all offsets MUST be
    # in scan_text coordinates. Earlier versions built exempt_ranges from `md`
    # coordinates and then checked violations in `scan_text` coordinates,
    # causing false HARD_FAILs when code blocks BEFORE an exempt section
    # shifted the offset such that the exempt header appeared at a different
    # byte position post-strip. Detected in the saas-founder run.
    scan_text = strip_code_blocks(md)

    # Build (start, end) byte ranges for exempt sections — in scan_text coords
    exempt_ranges: list[tuple[int, int]] = []
    headers = extract_h2_sections(scan_text)
    lines = scan_text.split("\n")

    def line_to_char(ln: int) -> int:
        return sum(len(l) + 1 for l in lines[:ln])

    for i, (ln, header) in enumerate(headers):
        if header in exempt_headers:
            start = line_to_char(ln)
            if i + 1 < len(headers):
                end = line_to_char(headers[i + 1][0])
            else:
                end = len(scan_text)
            exempt_ranges.append((start, end))

    # Find all numeric claims
    violations: list[tuple[int, str]] = []
    for m in re.finditer(num_regex, scan_text):
        start = m.start()
        # Skip if in exempt section
        if any(lo <= start < hi for lo, hi in exempt_ranges):
            continue
        # Look in a window [start-proximity, start+proximity+len(match)] for a tag
        window_start = max(0, start - proximity)
        window_end = min(len(scan_text), m.end() + proximity)
        window = scan_text[window_start:window_end]
        if re.search(tag_regex, window):
            continue
        # Exempt simple percent/dollar ranges inside table probability ranges
        # (those are council estimates but the validator tolerates "[0.5-0.8]" form)
        violations.append((start, m.group(0)))

    if violations:
        examples = ", ".join(f"'{v[1]}'" for v in violations[:5])
        report.add(
            "unsourced_dollar_figure",
            "FAIL", "HARD_FAIL",
            f"{len(violations)} numeric claim(s) lack a source tag [G#]/[D#]/[U#]/[C#:persona] within {proximity} chars. Examples: {examples}. Either add the source or rewrite the claim qualitatively.",
            count=len(violations),
        )
    else:
        report.add(
            "unsourced_dollar_figure",
            "PASS", "INFO",
            "All numeric claims carry a source tag or appear in an exempt section.",
        )


def check_depends_on_mirrors_assumptions(md: str, schema: dict, positions: dict, report: Report) -> None:
    """
    Enforce content_checks.depends_on_missing_assumption: every bullet in the
    Recommendation's 'Depends on:' line must correspond to a Key Assumptions row.
    """
    content_checks = schema.get("content_checks", {})
    if "depends_on_missing_assumption" not in content_checks:
        return

    # Locate Recommendation section (position 12) and Key Assumptions (position 10)
    header_spans = _header_line_map(md)
    rec_range = header_spans.get("## Recommendation")
    assump_range = header_spans.get("## Key Assumptions")
    if not rec_range or not assump_range:
        # Either section missing — a different check already flagged it
        return

    rec_body = section_body(md, rec_range[0], rec_range[1])
    assump_body = section_body(md, assump_range[0], assump_range[1])

    # Extract "Depends on:" content — can be a line or bullet list
    depends_match = re.search(
        r"\*\*Depends on:\*\*\s*(.+?)(?=\n\s*-\s*\*\*|\n\s*\n|$)",
        rec_body,
        flags=re.DOTALL,
    )
    if not depends_match:
        return  # required_content check handles missing "Depends on:"
    depends_text = depends_match.group(1).strip()

    # Collect candidate items: split by commas and "and" for inline lists,
    # or take sub-bullets if present.
    candidates = [c.strip() for c in re.split(r",|\band\b", depends_text) if c.strip()]
    if not candidates:
        return

    # Extract assumption descriptions from the Key Assumptions table
    assump_descriptions: list[str] = []
    in_table = False
    for line in assump_body.split("\n"):
        if "|" in line and re.search(r"\|\s*-+\s*\|", line):
            in_table = True
            continue
        if in_table and line.strip().startswith("|"):
            cells = parse_table_row(line)
            # Columns: Rank | Assumption | Sensitivity | Effects Impacted | Fragility
            if len(cells) >= 2:
                assump_descriptions.append(cells[1].lower())

    if not assump_descriptions:
        return  # table check handles missing rows

    # For each candidate, check substring or token-overlap > 60%
    missing: list[str] = []
    for cand in candidates:
        cand_norm = cand.lower().strip("*`_ ")
        if not cand_norm:
            continue
        cand_tokens = set(re.findall(r"\w+", cand_norm))
        # Remove stop tokens
        cand_tokens -= {"the", "a", "an", "of", "to", "in", "on", "for", "is", "and", "or"}
        if not cand_tokens:
            continue
        matched = False
        for desc in assump_descriptions:
            if cand_norm in desc or desc in cand_norm:
                matched = True
                break
            desc_tokens = set(re.findall(r"\w+", desc))
            desc_tokens -= {"the", "a", "an", "of", "to", "in", "on", "for", "is", "and", "or"}
            if not desc_tokens:
                continue
            overlap = len(cand_tokens & desc_tokens) / max(len(cand_tokens), 1)
            if overlap > 0.6:
                matched = True
                break
        if not matched:
            missing.append(cand[:80])

    if missing:
        report.add(
            "depends_on_missing_assumption",
            "FAIL", "HARD_FAIL",
            f"Recommendation cites {len(missing)} assumption(s) that don't mirror Key Assumptions rows: {missing}. Either add to Key Assumptions or rewrite the Recommendation.",
            missing=missing,
        )
    else:
        report.add(
            "depends_on_missing_assumption",
            "PASS", "INFO",
            "All 'Depends on:' items mirror Key Assumptions rows.",
        )


def parse_table_row(line: str) -> list[str]:
    """Parse a pipe-delimited markdown row into cell strings."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def check_synthesis_dedup_quality(schema: dict, run_dir: Path, mode: str, report: Report) -> None:
    """
    Enforce content_checks.synthesis_dedup_skipped: synthesis must merge effects
    across personas. Average council_agreement across 1st-order effects below the
    minimum threshold means most effects are persona-unique islands and the
    semantic dedup step from references/persona-council.md was skipped.
    """
    cfg = schema.get("content_checks", {}).get("synthesis_dedup_skipped")
    if not cfg:
        return
    if mode in cfg.get("skip_in_modes", []):
        return

    # Find latest iteration-N/effects-chains.json
    iter_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and re.match(r"iteration-\d+$", d.name)],
        key=lambda d: int(d.name.split("-")[1]),
    )
    ec_path = None
    for d in reversed(iter_dirs):
        candidate = d / "effects-chains.json"
        if candidate.is_file():
            ec_path = candidate
            break
    if not ec_path:
        # No effects-chains.json — different check (intermediate-files gate) handles it
        return

    try:
        ec = json.loads(ec_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        report.add(
            "synthesis_dedup_skipped",
            "FAIL", "WARN",
            f"Could not read {ec_path}: {e}",
        )
        return

    agreements: list[int] = []
    for h in ec.get("hypotheses", []):
        for e in h.get("effects", []):
            agr = e.get("council_agreement")
            if isinstance(agr, (int, float)):
                agreements.append(int(agr))
    if not agreements:
        return  # nothing to measure
    avg = sum(agreements) / len(agreements)
    minimum = cfg.get("minimum", 1.5)
    warn_below = cfg.get("warn_below", 2.0)
    total_effects = len(agreements)
    one_persona_only = sum(1 for a in agreements if a <= 1)
    pct_islands = round(one_persona_only / total_effects * 100, 1)

    if avg < minimum:
        report.add(
            "synthesis_dedup_skipped",
            "FAIL",
            schema.get("severity_on_fail", {}).get("synthesis_dedup_skipped", "HARD_FAIL"),
            (
                f"Avg council_agreement across {total_effects} first-order effects in "
                f"{ec_path.name} is {avg:.2f} (minimum {minimum}). {one_persona_only}/{total_effects} "
                f"({pct_islands}%) sit at council_agreement=1 — synthesis did NOT dedup novel IDs across "
                f"personas. {cfg.get('remediation', 'Re-run synthesis with semantic dedup.')}"
            ),
            avg_council_agreement=round(avg, 2),
            minimum=minimum,
            total_first_order_effects=total_effects,
            council_agreement_one_count=one_persona_only,
            council_agreement_one_pct=pct_islands,
            source=str(ec_path.relative_to(run_dir)),
        )
    elif avg < warn_below:
        report.add(
            "synthesis_dedup_skipped",
            "PASS", "WARN",
            (
                f"Avg council_agreement {avg:.2f} (minimum {minimum}) is above the hard floor but "
                f"below the warn threshold ({warn_below}). {pct_islands}% of effects are persona-unique. "
                "Synthesis dedup looks light — consider an additional pass."
            ),
            avg_council_agreement=round(avg, 2),
            minimum=minimum,
            warn_below=warn_below,
            council_agreement_one_pct=pct_islands,
            source=str(ec_path.relative_to(run_dir)),
        )
    else:
        report.add(
            "synthesis_dedup_skipped",
            "PASS", "INFO",
            (
                f"Avg council_agreement {avg:.2f} across {total_effects} first-order effects "
                f"(minimum {minimum}). Synthesis dedup looks healthy."
            ),
            avg_council_agreement=round(avg, 2),
            source=str(ec_path.relative_to(run_dir)),
        )


def _extract_first_order_per_hyp(persona_data: dict) -> tuple[dict[str, list[dict]], bool]:
    """Return ({hypothesis_id: [first_order_effect_dict, ...]}, recognized_shape)
    for a council file.

    Robust to all observed schema shapes in the wild (catalogued from real runs):

    1. CANONICAL — `hypotheses` as a list of objects:
       {"hypotheses": [{"hypothesis_id": "h1", "effects": [...]}]}

    2. FLAT-ALT — `effects_by_hypothesis` dict, no `hypotheses` field:
       {"effects_by_hypothesis": {"h1": [...effects...]}}
       (or wrapped: {"effects_by_hypothesis": {"h1": {"effects": [...]}}})

    3. DICT-KEYED — `hypotheses` as a dict keyed by hypothesis_id, inner dict
       contains an effects-list field:
         "first_order_effects" — most common
         "first_order"         — saas-founder-20m-strategic-invest run
         "effects"             — legacy
       {"hypotheses": {"h1": {"first_order_effects": [...]}}}

    Returns (per_hyp_dict, recognized_shape_bool). The bool is False when the
    persona file doesn't match any known shape (e.g. malformed or genuinely
    novel schema) — callers should surface this as a validator WARN rather
    than silently treat as zero effects.

    Filters to first-order only (effect.order == 1, OR no order field when source
    is a "first_order(_effects)" container which is implicitly first-order).
    Skips non-dict entries silently — never crashes on malformed input.
    """
    out: dict[str, list[dict]] = {}
    recognized = False

    # Effects-list field names known to contain first-order effects.
    # Order matters: "first_order_effects" wins if both are present.
    FO_CONTAINER_KEYS = ("first_order_effects", "first_order")
    GENERIC_KEYS = ("effects",)

    def _filter_fo(effs, container_implies_fo: bool = False) -> list[dict]:
        if not isinstance(effs, list):
            return []
        result = []
        for e in effs:
            if not isinstance(e, dict):
                continue
            order = e.get("order")
            if order is None and container_implies_fo:
                result.append(e)
            elif order == 1:
                result.append(e)
        return result

    def _unwrap_effects(v) -> tuple[list[dict], bool]:
        """Pull the effects list + flag whether the container implies first-order."""
        if isinstance(v, list):
            return v, False  # bare list, rely on order field
        if isinstance(v, dict):
            for k in FO_CONTAINER_KEYS:
                if k in v:
                    return v[k] or [], True
            for k in GENERIC_KEYS:
                if k in v:
                    return v[k] or [], False
        return [], False

    hyp_field = persona_data.get("hypotheses")
    ebh = persona_data.get("effects_by_hypothesis")

    if isinstance(hyp_field, list):
        # Shape 1: canonical
        recognized = True
        for h in hyp_field:
            if not isinstance(h, dict):
                continue
            hid = h.get("hypothesis_id", "?")
            container = h.get("effects") or h.get("first_order_effects") or h.get("first_order") or []
            implies_fo = ("first_order_effects" in h) or ("first_order" in h)
            out[hid] = _filter_fo(container, container_implies_fo=implies_fo)
    elif isinstance(hyp_field, dict):
        # Shape 3: dict-keyed
        recognized = True
        for hid, v in hyp_field.items():
            effs, implies_fo = _unwrap_effects(v)
            out[hid] = _filter_fo(effs, container_implies_fo=implies_fo)
    elif isinstance(ebh, dict):
        # Shape 2: flat alt
        recognized = True
        for hid, v in ebh.items():
            effs, implies_fo = _unwrap_effects(v)
            out[hid] = _filter_fo(effs, container_implies_fo=implies_fo)

    return out, recognized


def check_per_persona_overproduction(schema: dict, run_dir: Path, mode: str, report: Report) -> None:
    """
    Enforce content_checks.per_persona_overproduction: per-persona output budget
    is 5-8 first-order effects per hypothesis (per persona-preamble.md rule 6).

    Defaults: WARN > warn_threshold (8) — likely tiered analysis or borderline.
              HARD_FAIL > fail_threshold (12) — catastrophic redundant invention.

    The 5-8 range allows tiered effect modeling (e.g. 4 motive tiers + 3 cash
    tiers in one hypothesis) and specialist insights without false-positiving.
    The runtime Phase 2.5 Pre-Synthesis Discipline Gate in simulate.md catches
    catastrophic patterns at synthesis time; this check is the brief-validation
    backstop.
    """
    cfg = schema.get("content_checks", {}).get("per_persona_overproduction")
    if not cfg:
        return
    if mode in cfg.get("skip_in_modes", []):
        return

    iter_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and re.match(r"iteration-\d+$", d.name)],
        key=lambda d: int(d.name.split("-")[1]),
    )
    if not iter_dirs:
        return  # no iterations — nothing to check (intermediate-files gate handles missing data)

    warn_threshold = cfg.get("warn_threshold", 8)
    fail_threshold = cfg.get("fail_threshold", 12)

    # Inspect council/*.json across ALL iterations (not just latest) — iter-1 bloat
    # surfaces just as much as iter-N bloat for upstream diagnosis.
    violations: list[dict] = []  # rows: {iter, persona, hypothesis, count, severity}
    council_files_seen = 0
    council_files_unreadable: list[str] = []
    council_files_unknown_shape: list[str] = []
    for d in iter_dirs:
        council_dir = d / "council"
        if not council_dir.is_dir():
            continue
        for council_file in sorted(council_dir.glob("*.json")):
            council_files_seen += 1
            try:
                data = json.loads(council_file.read_text())
            except (json.JSONDecodeError, OSError) as e:
                council_files_unreadable.append(f"{council_file.relative_to(run_dir)}: {e}")
                continue
            persona = data.get("persona") or council_file.stem
            # Use the universal helper (handles all known schema shapes)
            per_hyp, recognized = _extract_first_order_per_hyp(data)
            if not recognized:
                council_files_unknown_shape.append(
                    f"{council_file.relative_to(run_dir)} (top keys: {list(data.keys())[:6]})"
                )
                continue
            for hyp_id, fo_effects in per_hyp.items():
                count = len(fo_effects)
                if count > fail_threshold:
                    violations.append({
                        "iteration": d.name,
                        "persona": persona,
                        "hypothesis": hyp_id,
                        "first_order_count": count,
                        "severity": "FAIL",
                    })
                elif count > warn_threshold:
                    violations.append({
                        "iteration": d.name,
                        "persona": persona,
                        "hypothesis": hyp_id,
                        "first_order_count": count,
                        "severity": "WARN",
                    })

    if council_files_seen == 0:
        # No council files to inspect — could be a quick-mode legacy or a partial run.
        # Don't fail; the intermediate-files gate handles missing data.
        return

    if council_files_unreadable:
        report.add(
            "per_persona_overproduction",
            "FAIL", "WARN",
            f"Could not read {len(council_files_unreadable)} council file(s): {council_files_unreadable[:3]}",
        )

    if council_files_unknown_shape:
        report.add(
            "per_persona_overproduction",
            "PASS", "WARN",
            (
                f"{len(council_files_unknown_shape)} council file(s) had unrecognized schema "
                f"shape — counts excluded from overproduction check. Examples: "
                f"{council_files_unknown_shape[:3]}. Update _extract_first_order_per_hyp in "
                f"validate-brief.py to support this shape if it recurs."
            ),
            unknown_shape_count=len(council_files_unknown_shape),
            samples=council_files_unknown_shape[:5],
        )

    fail_violations = [v for v in violations if v["severity"] == "FAIL"]
    warn_violations = [v for v in violations if v["severity"] == "WARN"]

    if fail_violations:
        # Build a compact summary
        sample = fail_violations[:5]
        sample_str = "; ".join(
            f"{v['iteration']}/{v['persona']}/{v['hypothesis']}={v['first_order_count']}"
            for v in sample
        )
        more = f" (+{len(fail_violations) - 5} more)" if len(fail_violations) > 5 else ""
        report.add(
            "per_persona_overproduction",
            "FAIL",
            schema.get("severity_on_fail", {}).get("per_persona_overproduction", "HARD_FAIL"),
            (
                f"{len(fail_violations)} (persona, hypothesis) cell(s) exceed the hard cap of "
                f"{fail_threshold} first-order effects. Examples: {sample_str}{more}. "
                f"{cfg.get('remediation', 'Re-spawn over-producing personas with the trim re-prompt from simulate.md Step 2.5.')}"
            ),
            fail_threshold=fail_threshold,
            warn_threshold=warn_threshold,
            council_files_inspected=council_files_seen,
            fail_count=len(fail_violations),
            warn_count=len(warn_violations),
            sample_violations=sample,
        )
    elif warn_violations:
        sample = warn_violations[:5]
        sample_str = "; ".join(
            f"{v['iteration']}/{v['persona']}/{v['hypothesis']}={v['first_order_count']}"
            for v in sample
        )
        more = f" (+{len(warn_violations) - 5} more)" if len(warn_violations) > 5 else ""
        report.add(
            "per_persona_overproduction",
            "PASS", "WARN",
            (
                f"{len(warn_violations)} (persona, hypothesis) cell(s) exceed the soft cap of "
                f"{warn_threshold} first-order effects (still below hard cap {fail_threshold}). "
                f"Examples: {sample_str}{more}. The runtime Pre-Synthesis Discipline Gate "
                "should have caught these — verify the gate ran in simulate.md Step 2.5."
            ),
            fail_threshold=fail_threshold,
            warn_threshold=warn_threshold,
            council_files_inspected=council_files_seen,
            warn_count=len(warn_violations),
            sample_violations=sample,
        )
    else:
        report.add(
            "per_persona_overproduction",
            "PASS", "INFO",
            (
                f"All {council_files_seen} council file(s) are within the per-hypothesis "
                f"first-order budget (<= {warn_threshold} per persona per hypothesis)."
            ),
            council_files_inspected=council_files_seen,
            warn_threshold=warn_threshold,
        )


def _extract_council_effect_ids_per_hyp(persona_data: dict) -> dict[str, set]:
    """Return {hypothesis_id: set(effect_id, ...)} of first-order IDs in a council file.

    Thin wrapper around _extract_first_order_per_hyp — handles all schema shapes
    catalogued there. Returns sets of effect_ids (strings only, skips malformed).
    """
    per_hyp, _recognized = _extract_first_order_per_hyp(persona_data)
    return {
        hid: {e["effect_id"] for e in effs if isinstance(e.get("effect_id"), str)}
        for hid, effs in per_hyp.items()
    }


def _extract_seeded_per_hyp(hypotheses_data: dict) -> dict[str, list[str]]:
    """Return {hypothesis_id: [seeded_effect_id, ...]} from a hypotheses.json file.

    Robust to multiple shapes:
    - CANONICAL: {"hypotheses": [{"hypothesis_id": ..., "expected_effect_ids": [...]}]}
    - ITER-2 CARRYFORWARD: {"carried_over": [...], "new_in_iter_2": [...]} (no
      `expected_effect_ids` field — caller should fall back to iter-1 in this case).
    - DICT-KEYED: {"hypotheses": {hyp_id: {"expected_effect_ids": [...]}}}

    Returns {} when no recognized seeded vocabulary is found — caller decides
    whether to fall back to an earlier iteration.
    """
    out: dict[str, list[str]] = {}
    hyp = hypotheses_data.get("hypotheses")
    if isinstance(hyp, list):
        for h in hyp:
            if not isinstance(h, dict):
                continue
            # Accept both `hypothesis_id` (canonical) and `id` (saas-founder run uses this)
            hid = h.get("hypothesis_id") or h.get("id")
            if not hid:
                continue
            ids = h.get("expected_effect_ids") or []
            if isinstance(ids, list):
                out[hid] = [i for i in ids if isinstance(i, str)]
    elif isinstance(hyp, dict):
        for hid, v in hyp.items():
            if isinstance(v, dict):
                ids = v.get("expected_effect_ids") or []
                if isinstance(ids, list):
                    out[hid] = [i for i in ids if isinstance(i, str)]
    return out


def check_seeded_vocab_adoption(schema: dict, run_dir: Path, mode: str, report: Report) -> None:
    """
    Enforce content_checks.seeded_vocab_ignored: personas must actually USE the
    seeded `expected_effect_ids` from hypotheses.json instead of inventing
    descriptive variants.

    Reads each iteration's hypotheses.json (for seeded IDs) and council/*.json
    (for actual IDs personas used). Computes adoption rate per iteration:
    seeded IDs that appeared in at least one persona's output / total seeded.

    WARN below warn_threshold (50%), HARD_FAIL below fail_threshold (20%).
    """
    cfg = schema.get("content_checks", {}).get("seeded_vocab_ignored")
    if not cfg:
        return
    if mode in cfg.get("skip_in_modes", []):
        return

    iter_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and re.match(r"iteration-\d+$", d.name)],
        key=lambda d: int(d.name.split("-")[1]),
    )
    if not iter_dirs:
        return

    # Use latest iteration that has BOTH hypotheses.json and council/*.json for the
    # USAGE side (the brief reflects the latest iteration).
    latest = None
    for d in reversed(iter_dirs):
        if (d / "hypotheses.json").is_file() and (d / "council").is_dir():
            latest = d
            break
    if not latest:
        return  # nothing to check (other gates handle missing data)

    # Try the latest iteration's hypotheses.json for SEEDED vocab. If it uses the
    # carryforward schema (no `expected_effect_ids` per hypothesis — has
    # `carried_over` / `new_in_iter_2` instead), fall back to the earliest iter
    # that has actual seeded vocab. Iter-1's seeded list is the canonical
    # vocabulary that personas should adopt across all iterations.
    seeded_by_hyp: dict[str, set] = {}
    seeded_source_iter = None
    for d_try in [latest] + [d for d in iter_dirs if d != latest]:
        hyp_path = d_try / "hypotheses.json"
        if not hyp_path.is_file():
            continue
        try:
            hyp = json.loads(hyp_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            if d_try == latest:
                report.add(
                    "seeded_vocab_ignored",
                    "FAIL", "WARN",
                    f"Could not read {hyp_path.relative_to(run_dir)}: {e}",
                )
            continue
        per_hyp_seeded = _extract_seeded_per_hyp(hyp)
        per_hyp_seeded = {hid: set(ids) for hid, ids in per_hyp_seeded.items() if ids}
        if per_hyp_seeded:
            seeded_by_hyp = per_hyp_seeded
            seeded_source_iter = d_try.name
            break

    total_seeded = sum(len(s) for s in seeded_by_hyp.values())
    if total_seeded == 0:
        report.add(
            "seeded_vocab_ignored",
            "PASS", "WARN",
            "No seeded effect_ids found in any iteration's hypotheses.json — Shared Effect ID Vocabulary mechanism (phases/hypothesize.md) is not being used. Personas have no shared vocabulary to converge on.",
        )
        return

    # Aggregate persona usage across all council files in this iteration
    used_ids_by_hyp: dict[str, set] = {hid: set() for hid in seeded_by_hyp}
    council_files_seen = 0
    council_files_unreadable: list[str] = []
    for council_file in sorted((latest / "council").glob("*.json")):
        council_files_seen += 1
        try:
            data = json.loads(council_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            council_files_unreadable.append(f"{council_file.relative_to(run_dir)}: {e}")
            continue
        per_hyp_ids = _extract_council_effect_ids_per_hyp(data)
        for hid, ids in per_hyp_ids.items():
            if hid in used_ids_by_hyp:
                used_ids_by_hyp[hid].update(ids)

    if council_files_seen == 0:
        return

    # Adoption: for each seeded ID, was it used by at least one persona?
    seeded_used = 0
    per_hyp_breakdown: list[dict] = []
    for hid, seeded in seeded_by_hyp.items():
        used = used_ids_by_hyp.get(hid, set())
        adopted = sum(1 for s in seeded if s in used)
        seeded_used += adopted
        per_hyp_breakdown.append({
            "hypothesis": hid,
            "seeded_count": len(seeded),
            "adopted_count": adopted,
            "adoption_pct": round(100 * adopted / len(seeded), 1) if seeded else 0,
        })

    adoption_pct = round(100 * seeded_used / total_seeded, 1)
    warn_threshold = cfg.get("warn_threshold", 50)
    fail_threshold = cfg.get("fail_threshold", 20)

    if council_files_unreadable:
        report.add(
            "seeded_vocab_ignored",
            "FAIL", "WARN",
            f"Could not read {len(council_files_unreadable)} council file(s): {council_files_unreadable[:3]}",
        )

    if adoption_pct < fail_threshold:
        report.add(
            "seeded_vocab_ignored",
            "FAIL",
            schema.get("severity_on_fail", {}).get("seeded_vocab_ignored", "HARD_FAIL"),
            (
                f"Only {seeded_used}/{total_seeded} ({adoption_pct}%) of seeded effect_ids "
                f"were used by any persona in {latest.name}/council/. Below the hard floor "
                f"of {fail_threshold}%. Personas invented descriptive variants instead of "
                f"using the seeded vocabulary, so synthesis dedup must work much harder. "
                f"{cfg.get('remediation', 'Verify shared-context.md presents seeded vocab prominently.')}"
            ),
            adoption_pct=adoption_pct,
            seeded_used=seeded_used,
            total_seeded=total_seeded,
            warn_threshold=warn_threshold,
            fail_threshold=fail_threshold,
            council_files_inspected=council_files_seen,
            per_hypothesis_breakdown=per_hyp_breakdown,
            iteration=latest.name,
            seeded_source_iteration=seeded_source_iter,
        )
    elif adoption_pct < warn_threshold:
        report.add(
            "seeded_vocab_ignored",
            "PASS", "WARN",
            (
                f"Only {seeded_used}/{total_seeded} ({adoption_pct}%) of seeded effect_ids "
                f"were used by any persona in {latest.name}/council/. Above the hard floor "
                f"({fail_threshold}%) but below the healthy threshold ({warn_threshold}%). "
                f"Synthesis dedup is doing more work than it should. Consider tightening "
                f"shared-context.md's seeded-vocab block per engine-protocol.md."
            ),
            adoption_pct=adoption_pct,
            seeded_used=seeded_used,
            total_seeded=total_seeded,
            warn_threshold=warn_threshold,
            council_files_inspected=council_files_seen,
            per_hypothesis_breakdown=per_hyp_breakdown,
            iteration=latest.name,
            seeded_source_iteration=seeded_source_iter,
        )
    else:
        report.add(
            "seeded_vocab_ignored",
            "PASS", "INFO",
            (
                f"{seeded_used}/{total_seeded} ({adoption_pct}%) of seeded effect_ids "
                f"adopted by at least one persona in {latest.name}/council/. "
                f"Seeded vocabulary mechanism is working."
            ),
            adoption_pct=adoption_pct,
            seeded_used=seeded_used,
            total_seeded=total_seeded,
            council_files_inspected=council_files_seen,
            iteration=latest.name,
            seeded_source_iteration=seeded_source_iter,
        )


def check_assumptions_field_present(schema: dict, run_dir: Path, mode: str, report: Report) -> None:
    """
    Enforce content_checks.assumptions_field_missing: backstop for the iter-2
    schema drift pattern where personas drop the `assumptions` field entirely
    from their council-file effects. The synthesized effects-chains.json then
    has effects with no assumptions, and the Judge's assumption_stability
    metric silently goes to 0%.

    Reads iteration-{latest}/effects-chains.json (the synthesized output, where
    drift would have manifested even after synthesis tried to recover).

    Computes: % of first-order effects with non-empty `assumptions` array.
    WARN below warn_threshold (50%) — drift detected, recoverable.
    HARD_FAIL below fail_threshold (10%) — catastrophic, Judge metric crash.
    """
    cfg = schema.get("content_checks", {}).get("assumptions_field_missing")
    if not cfg:
        return
    if mode in cfg.get("skip_in_modes", []):
        return

    iter_dirs = sorted(
        [d for d in run_dir.iterdir() if d.is_dir() and re.match(r"iteration-\d+$", d.name)],
        key=lambda d: int(d.name.split("-")[1]),
    )
    if not iter_dirs:
        return

    # Find the latest iteration with effects-chains.json
    ec_path = None
    for d in reversed(iter_dirs):
        candidate = d / "effects-chains.json"
        if candidate.is_file():
            ec_path = candidate
            break
    if not ec_path:
        return  # other gates handle missing data

    try:
        ec = json.loads(ec_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        report.add(
            "assumptions_field_missing",
            "FAIL", "WARN",
            f"Could not read {ec_path.relative_to(run_dir)}: {e}",
        )
        return

    # Iterate first-order effects across all hypotheses
    total_first_order = 0
    with_assumptions = 0
    for h in ec.get("hypotheses", []) or []:
        if not isinstance(h, dict):
            continue
        for e in h.get("effects", []) or []:
            if not isinstance(e, dict):
                continue
            # Only count first-order
            if e.get("order", 1) != 1:
                continue
            total_first_order += 1
            assumptions = e.get("assumptions")
            if isinstance(assumptions, list) and len(assumptions) > 0:
                with_assumptions += 1

    if total_first_order == 0:
        # No first-order effects — different gate handles this
        return

    pct = round(100 * with_assumptions / total_first_order, 1)
    warn_threshold = cfg.get("warn_threshold", 50)
    fail_threshold = cfg.get("fail_threshold", 10)

    if pct < fail_threshold:
        report.add(
            "assumptions_field_missing",
            "FAIL",
            schema.get("severity_on_fail", {}).get("assumptions_field_missing", "HARD_FAIL"),
            (
                f"Only {with_assumptions}/{total_first_order} ({pct}%) of first-order effects "
                f"in {ec_path.name} have non-empty `assumptions` arrays. Below the hard floor "
                f"of {fail_threshold}%. Personas dropped the assumptions field — Judge's "
                f"assumption_stability metric will silently crash to 0%. "
                f"{cfg.get('remediation', 'Verify persona-preamble.md rule 3 includes the canonical-schema clause.')}"
            ),
            pct_with_assumptions=pct,
            with_assumptions=with_assumptions,
            total_first_order=total_first_order,
            warn_threshold=warn_threshold,
            fail_threshold=fail_threshold,
            iteration=ec_path.parent.name,
        )
    elif pct < warn_threshold:
        report.add(
            "assumptions_field_missing",
            "PASS", "WARN",
            (
                f"Only {with_assumptions}/{total_first_order} ({pct}%) of first-order effects "
                f"in {ec_path.name} have non-empty `assumptions` arrays. Above the hard floor "
                f"({fail_threshold}%) but below the healthy threshold ({warn_threshold}%). "
                f"Schema drift detected — some personas may be dropping the field."
            ),
            pct_with_assumptions=pct,
            with_assumptions=with_assumptions,
            total_first_order=total_first_order,
            warn_threshold=warn_threshold,
            iteration=ec_path.parent.name,
        )
    else:
        report.add(
            "assumptions_field_missing",
            "PASS", "INFO",
            (
                f"{with_assumptions}/{total_first_order} ({pct}%) of first-order effects in "
                f"{ec_path.name} have non-empty `assumptions` arrays. Schema integrity holds."
            ),
            pct_with_assumptions=pct,
            with_assumptions=with_assumptions,
            total_first_order=total_first_order,
            iteration=ec_path.parent.name,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path,
                    help="Run directory (e.g. ~/.autodecision/runs/slug/)")
    ap.add_argument("--schema", required=True, type=Path,
                    help="Path to brief-schema.json")
    ap.add_argument("--mode", default="full", choices=["full", "medium", "quick"],
                    help="Run mode; controls which sections are required")
    ap.add_argument("--brief-name", default="DECISION-BRIEF.md",
                    help="Name of brief file inside run-dir")
    ap.add_argument("--quiet", action="store_true", help="Suppress stdout summary")
    args = ap.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        die(f"run-dir not found: {run_dir}")
    schema_path = args.schema.expanduser().resolve()
    if not schema_path.is_file():
        die(f"schema not found: {schema_path}")
    brief_path = run_dir / args.brief_name
    if not brief_path.is_file():
        die(f"brief not found: {brief_path}")

    schema = json.loads(schema_path.read_text())
    md = brief_path.read_text()

    report = Report(schema)

    positions = check_section_order_and_presence(md, schema, args.mode, report)
    check_section_content(md, schema, positions, args.mode, report)
    check_prohibited_patterns(md, schema, report)
    check_cross_references(md, schema, run_dir, positions, report)
    # Content-level checks (new in schema v1.1): source tags + depends-on mirror
    if args.mode in ("full", "medium"):
        check_unsourced_numbers(md, schema, positions, report)
        check_depends_on_mirrors_assumptions(md, schema, positions, report)
    # Synthesis dedup quality (skipped in quick mode where there is no council)
    check_synthesis_dedup_quality(schema, run_dir, args.mode, report)
    # Per-persona overproduction backstop (new in schema v1.3)
    check_per_persona_overproduction(schema, run_dir, args.mode, report)
    # Seeded vocabulary adoption backstop (new in schema v1.4)
    check_seeded_vocab_adoption(schema, run_dir, args.mode, report)
    # Assumptions field present backstop (new in schema v1.6)
    check_assumptions_field_present(schema, run_dir, args.mode, report)

    out = run_dir / "validation-report.json"
    out.write_text(json.dumps(report.as_dict(), indent=2))

    if not args.quiet:
        d = report.as_dict()
        print(f"Brief: {brief_path}")
        print(f"Mode:  {args.mode}")
        print(f"Report: {out}")
        print(f"Checks: {d['summary']['passed']} passed, {d['summary']['failed']} failed "
              f"(severities: {d['severities_failed'] or ['none']})")
        if d["summary"]["failed"]:
            print("\nFAILURES:")
            for c in d["checks"]:
                if c["status"] == "FAIL":
                    print(f"  [{c['severity']}] {c['name']}: {c['detail']}")

    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
