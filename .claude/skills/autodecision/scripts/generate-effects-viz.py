#!/usr/bin/env python3
"""
generate-effects-viz.py — turn a run directory into a self-contained effects-cascade HTML page.

Reads:
  {run_dir}/config.json                         → decision text
  {run_dir}/iteration-{latest}/effects-chains.json  → hypotheses, effects, 2nd-order chains
  {run_dir}/iteration-{latest}/adversary.json       → worst cases, black swans, correlations, lethality
  {run_dir}/DECISION-BRIEF.md                   → hypothesis status (Eliminated / Supported / Weakened)

Writes:
  {run_dir}/EFFECTS-VIZ.html — self-contained, zero dependencies beyond d3 CDN, opens anywhere.

Requires: Python 3.8+ (stdlib only). Template at
  {skill_dir}/templates/effects-orbital.html with the `__INLINED_DATA__` marker.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path


# ---------- helpers ----------

def find_latest_iteration(run_dir: Path) -> Path | None:
    """Return the highest-numbered iteration directory with effects-chains.json."""
    iters = []
    for d in run_dir.iterdir():
        if d.is_dir() and d.name.startswith("iteration-"):
            try:
                n = int(d.name.split("-", 1)[1])
            except ValueError:
                continue
            if (d / "effects-chains.json").exists():
                iters.append((n, d))
    if not iters:
        return None
    iters.sort()
    return iters[-1][1]


def _normalize_hypotheses(raw) -> list:
    """Accept list or dict form, return list of dicts with hypothesis_id set.
    Also unify effect-list keys: some runs use 'effects', others 'first_order_effects' or 'first_order'.
    Some runs keep 2nd-order in a separate 'second_order' list; fold those into `children`."""
    if not raw:
        return []
    if isinstance(raw, dict):
        out = []
        for hid, hdata in raw.items():
            if isinstance(hdata, dict):
                hdata = dict(hdata)
                hdata.setdefault("hypothesis_id", hid)
                out.append(hdata)
        raw = out
    if not isinstance(raw, list):
        return []

    normalized = []
    for h in raw:
        if not isinstance(h, dict):
            continue
        h = dict(h)  # shallow copy

        # Find the FO list
        fo_list = h.get("effects") or h.get("first_order_effects") or h.get("first_order") or []
        if not isinstance(fo_list, list):
            fo_list = []

        # Find a separate SO list (adobe-style), group by parent
        so_list = h.get("second_order") or h.get("second_order_effects") or []
        so_by_parent: dict[str, list] = {}
        if isinstance(so_list, list):
            for so in so_list:
                if isinstance(so, dict):
                    parent = so.get("parent") or so.get("parent_effect_id") or so.get("triggered_by")
                    if parent:
                        so_by_parent.setdefault(parent, []).append(so)

        # Normalize each FO: probability + children
        fo_norm = []
        for fo in fo_list:
            if not isinstance(fo, dict):
                continue
            fo = dict(fo)
            # Probability variants
            if "probability" not in fo:
                fo["probability"] = fo.get("median_probability") or fo.get("p") or 0
            # Children: nested or pulled from so_by_parent
            if not fo.get("children"):
                fo_id = fo.get("effect_id")
                if fo_id and fo_id in so_by_parent:
                    children = []
                    for c in so_by_parent[fo_id]:
                        c = dict(c)
                        if "probability" not in c:
                            c["probability"] = c.get("median_probability") or c.get("p") or 0
                        children.append(c)
                    fo["children"] = children
            # Normalize each child's probability field too
            if isinstance(fo.get("children"), list):
                for c in fo["children"]:
                    if isinstance(c, dict) and "probability" not in c:
                        c["probability"] = c.get("median_probability") or c.get("p") or 0
            fo_norm.append(fo)

        h["effects"] = fo_norm
        normalized.append(h)
    return normalized


_AGREEMENT_STRING_TO_INT = {
    "very_strong": 5, "very strong": 5, "unanimous": 5,
    "strong": 4,
    "moderate": 3, "mixed": 3,
    "weak": 2,
    "very_weak": 1, "very weak": 1, "split": 2, "none": 1,
}


def _coerce_agreement(value, default: int = 3) -> int:
    """Some runs use strings ('very_strong'), others ints 1-5. Normalize to int."""
    if isinstance(value, int):
        return max(1, min(5, value))
    if isinstance(value, float):
        return max(1, min(5, int(round(value))))
    if isinstance(value, str):
        return _AGREEMENT_STRING_TO_INT.get(value.strip().lower(), default)
    return default


def _build_from_flat_chains(run_dir: Path, ec: dict) -> list:
    """Handle the 'effects_chains' flat-list schema (buy-vs-rent style):
    - Hypothesis list comes from iteration-*/hypotheses.json
    - Effects are a flat list with `hypothesis` field linking each to its hypothesis_id
    - Children may be nested under each effect"""
    # Pick up hypothesis metadata
    hyp_meta = {}
    for d in sorted(run_dir.iterdir(), key=lambda p: p.name):
        if not (d.is_dir() and d.name.startswith("iteration-")):
            continue
        hp = d / "hypotheses.json"
        if hp.exists():
            try:
                hraw = json.loads(hp.read_text(encoding="utf-8"))
                hlist = hraw.get("hypotheses") if isinstance(hraw, dict) else hraw
                if isinstance(hlist, list):
                    for h in hlist:
                        if isinstance(h, dict) and h.get("hypothesis_id"):
                            hyp_meta.setdefault(h["hypothesis_id"], h)
            except Exception:
                pass

    # Group effects by hypothesis id
    chains = ec.get("effects_chains") or []
    grouped: dict[str, list] = {}
    for e in chains:
        if not isinstance(e, dict):
            continue
        hid = e.get("hypothesis") or e.get("hypothesis_id")
        if not hid:
            continue
        prob = e.get("iteration_2_probability") or e.get("iteration_1_probability") or e.get("probability") or 0
        effect = {
            "effect_id": e.get("effect_id", ""),
            "description": e.get("description", ""),
            "probability": prob,
            "probability_range": e.get("probability_range") or [prob, prob],
            "council_agreement": _coerce_agreement(e.get("council_agreement")),
            "timeframe": e.get("timeframe", ""),
            "children": [],
        }
        for c in (e.get("children") or []):
            if not isinstance(c, dict):
                continue
            cprob = c.get("iteration_2_probability") or c.get("iteration_1_probability") or c.get("probability") or 0
            effect["children"].append({
                "effect_id": c.get("effect_id", ""),
                "description": c.get("description", ""),
                "probability": cprob,
                "council_agreement": _coerce_agreement(c.get("council_agreement")),
            })
        grouped.setdefault(hid, []).append(effect)

    # Build the hypothesis list in the order of hyp_meta (stable)
    hyps = []
    for hid, hdata in hyp_meta.items():
        hyps.append({
            "hypothesis_id": hid,
            "statement": hdata.get("statement", ""),
            "effects": grouped.get(hid, []),
        })
    # If hypotheses.json was empty, fall back to whatever IDs appeared in the chains
    if not hyps:
        for hid, effects in grouped.items():
            hyps.append({"hypothesis_id": hid, "effects": effects})
    return hyps


def pick_effects_source(run_dir: Path):
    """Pick the iteration with the richest effects data. Iter-2 is often a delta — iter-1 has
    the canonical structure. Score by total effect count, prefer fuller.
    Handles both `hypotheses`-keyed schemas and the flat `effects_chains` schema."""
    best = None
    for d in sorted(run_dir.iterdir(), key=lambda p: p.name):
        if not (d.is_dir() and d.name.startswith("iteration-")):
            continue
        p = d / "effects-chains.json"
        if not p.exists():
            continue
        try:
            ec = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Prefer the standard 'hypotheses' schema when populated
        hyps = _normalize_hypotheses(ec.get("hypotheses"))
        total_effects = sum(len(h.get("effects", []) or []) for h in hyps)

        # If no hypotheses or no effects, try the flat effects_chains schema (buy-vs-rent style)
        if total_effects == 0 and ec.get("effects_chains"):
            flat_hyps = _build_from_flat_chains(run_dir, ec)
            total_flat = sum(len(h.get("effects", []) or []) for h in flat_hyps)
            if total_flat > 0:
                hyps = flat_hyps
                total_effects = total_flat

        score = total_effects * 1000 + len(hyps)
        if best is None or score > best[0]:
            best = (score, ec, hyps, d.name)
    if best is None:
        return None, None, None
    return best[1], best[2], best[3]


def load_adversary(run_dir: Path) -> dict:
    """Load adversary.json from the richest iteration. Handles both schemas."""
    best = None
    for d in sorted(run_dir.iterdir(), key=lambda p: p.name):
        if not (d.is_dir() and d.name.startswith("iteration-")):
            continue
        p = d / "adversary.json"
        if not p.exists():
            continue
        try:
            adv = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Score: prefer one with `targets` (per-hyp detail), else fall back to one with worst_cases
        has_targets = bool(adv.get("targets"))
        wc_count = len(adv.get("worst_cases", []) or [])
        bs_count = len(adv.get("black_swans", []) or [])
        score = (has_targets * 10000) + wc_count * 10 + bs_count
        if best is None or score > best[0]:
            best = (score, adv)
    return best[1] if best else {}


def _best_text_field(d: dict, keys: tuple, max_len: int = 300) -> str:
    """Return the first non-empty string from the given keys, truncated."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:max_len]
    return ""


def extract_threats_flat(adv: dict) -> tuple[list, list]:
    """Return (worst_cases, black_swans) as lists. Handles multiple key conventions
    across schema versions:
      - container key: worst_cases / worst_case_scenarios / red_team_scenarios; black_swans / black_swan_scenarios
      - text field: description / scenario / name / event (current adversary.md spec uses `event` for black swans)
      - severity score: lethality_score / probability_estimate (heuristic mapping from `severity` enum if absent)
      - hypothesis link: affected_hypotheses (current spec) / invalidates (current spec for black swans) /
                        affected_options / which_options_exposed / hypotheses (legacy)
    """
    def _affected_keys(o):
        return (o.get("affected_hypotheses")
                or o.get("invalidates")
                or o.get("which_options_exposed")
                or o.get("affected_options")
                or o.get("hypotheses")
                or [])

    wcs = []
    for wc in (adv.get("worst_cases") or adv.get("worst_case_scenarios") or adv.get("red_team_scenarios") or []):
        if not isinstance(wc, dict):
            continue
        desc = _best_text_field(wc, ("description", "scenario", "name", "event"))
        if not desc:
            continue
        impact_str = (wc.get("impact") or wc.get("severity") or "").lower()
        lethality = wc.get("lethality_score")
        if not lethality:
            if "catastrophic" in impact_str or "existential" in impact_str or impact_str == "high":
                lethality = 8 if impact_str == "high" else 9
            elif "severe" in impact_str or "major" in impact_str or impact_str == "med":
                lethality = 6 if impact_str == "med" else 7
            else:
                lethality = 5
        wcs.append({
            "description": desc,
            "lethality": lethality,
            "probability": wc.get("probability") or wc.get("probability_estimate"),
            "affected": _affected_keys(wc),
        })

    bss = []
    for bs in (adv.get("black_swans") or adv.get("black_swan_scenarios") or []):
        if not isinstance(bs, dict):
            continue
        desc = _best_text_field(bs, ("description", "scenario", "name", "event"))
        if not desc:
            continue
        bss.append({
            "description": desc,
            "impact": _best_text_field(bs, ("impact",), max_len=200),
            "affected": _affected_keys(bs),
        })
    return wcs, bss


# Status text in real briefs almost always opens with a tag word, e.g.
# "**ELIMINATED.** ...", "CONDITIONAL — ...", "**LEADING RECOMMENDATION** (5/5)".
# We classify by the LEAD portion (everything before the first separator)
# rather than substring-anywhere — so descriptions like "applies if X fails
# to deliver" or "Real risk that compounds" classify by the opening tag,
# not by an incidental keyword later in the description.
_LEAD_SEPARATOR_RE = re.compile(r"[.:|—–—\-]| {2,}")


def _classify_status(status_cell: str) -> str:
    """Map a free-text status string to a short tag for color-coding.

    Tags: ELIMINATED / WEAKENED / RISK / LEADING / SUPPORTED / CONDITIONAL / OTHER.

    Algorithm:
      1. Strip leading markdown emphasis (`**`, `*`, `_`) and whitespace.
      2. Take everything before the first separator (period, colon, em/en/hyphen,
         double-space) as the LEAD chunk — this is the brief's actual tag word.
      3. Classify by keywords in the LEAD. Earlier branches win ties so the
         negative/strong tags don't get swallowed by the conditional fallback.
      4. If the LEAD has no recognizable keyword, fall back to a small set of
         substring matches across the full string (catches `**LEADING
         RECOMMENDATION**` where the bold separator splits the lead).
    """
    s = re.sub(r"^[\s*_`>]+", "", status_cell)
    parts = _LEAD_SEPARATOR_RE.split(s, maxsplit=1)
    lead = parts[0].strip().lower()
    # Strip trailing markdown emphasis from the lead chunk so "**ELIMINATED"
    # matches "eliminated".
    lead = re.sub(r"[*_`\s]+$", "", lead)

    def has(*words):
        return any(w in lead for w in words)

    # Word-boundary verb forms — avoids matching "failover", "failsafe", or
    # "failure" inside descriptions. Only fire on actual failure verbs.
    fail_re = re.compile(r"\b(failed|failing|fails|failure)\b")

    if has("eliminat", "dominated", "strictly worse"):
        return "ELIMINATED"
    if has("leading", "promoted") or lead == "new" or lead.startswith("new ") or "new hypothesis" in lead:
        return "LEADING"
    if has("fragile") or "weaken" in lead or fail_re.search(lead):
        return "WEAKENED"
    if "risk" in lead:
        return "RISK"
    # CONDITIONAL/REAL win over SUPPORTED in mixed-lead briefs like
    # "Conditional, partially supported" — the primary state is conditional;
    # the support qualifier is secondary.
    if has("conditional", "real"):
        return "CONDITIONAL"
    if has("supported", "recommend", "stable", "strongest", "dominant"):
        return "SUPPORTED"

    # Fall back to substring on the full string — catches cases where a
    # leading **bold** tag was split off (e.g. "**LEADING RECOMMENDATION**")
    full = status_cell.lower()
    if "leading recommendation" in full or "promoted" in full:
        return "LEADING"
    if "eliminat" in full:
        return "ELIMINATED"
    if "strongest" in full or "dominant" in full:
        return "SUPPORTED"
    return "OTHER"


def parse_brief_statuses(brief_path: Path) -> dict[str, dict[str, str]]:
    """Parse the '## Hypotheses Explored' table. Return {hypothesis_key: {short, detail}}.

    Stores each row under BOTH the raw first-cell key (`"1"`, `"H1"`) AND the
    canonical `"H{n}"` form, so the build_dataset lookup at `H{i}` succeeds
    regardless of whether the brief schema uses `#` (numeric) or `H#` columns.

    Status is classified by `_classify_status` into one of:
    ELIMINATED / WEAKENED / RISK / LEADING / SUPPORTED / CONDITIONAL / OTHER.
    """
    out: dict[str, dict[str, str]] = {}
    if not brief_path.exists():
        return out
    text = brief_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"## Hypotheses Explored\s*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if not m:
        return out
    table = m.group(1)
    row_index = 0  # 1-based positional counter for non-header data rows
    for line in table.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        first = cells[0].strip().lower()
        if first in ("", "#", "---") or set(first) <= {"-", ":"}:
            continue
        row_index += 1
        # Skip header row (e.g. "| # | Hypothesis | Status | Key Assumptions |")
        if first in ("hypothesis", "hyp", "id"):
            row_index -= 1
            continue
        raw_key = cells[0].strip().strip("*")
        status_cell = cells[2]
        short = _classify_status(status_cell)
        entry = {"short": short, "detail": status_cell}
        # Store under raw key ("1" or "H1") AND canonical positional ("H1")
        out[raw_key] = entry
        out[f"H{row_index}"] = entry
    return out


def humanize_hypothesis_label(hid: str) -> str:
    """Turn 'h1_full_replace_all_1y' into 'H1: Full Replace All 1Y' (best-effort fallback)."""
    parts = hid.split("_")
    if not parts:
        return hid
    h_prefix = parts[0].upper()
    rest = " ".join(p.capitalize() for p in parts[1:]) if len(parts) > 1 else ""
    return f"{h_prefix}: {rest}" if rest else h_prefix


def build_dataset(run_dir: Path) -> dict:
    """Read a run dir and return the JSON object the orbital template expects."""
    config_path = run_dir / "config.json"
    decision_text = f"Decision: {run_dir.name.replace('-', ' ').title()}"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            for key in ("decision_statement", "decision", "question", "statement"):
                if cfg.get(key):
                    decision_text = cfg[key]
                    break
        except Exception:
            pass

    ec, raw_hyps, iter_name = pick_effects_source(run_dir)
    if not raw_hyps:
        raise FileNotFoundError(
            f"No usable `hypotheses` with effects found in any iteration of {run_dir.name}. "
            f"Run may use a non-standard structure (flat effects_chains, merged_effects, etc)."
        )

    adv = load_adversary(run_dir)
    per_hyp_targets = adv.get("targets") or {}
    flat_wcs, flat_bss = ([], [])
    if not per_hyp_targets:
        flat_wcs, flat_bss = extract_threats_flat(adv)

    brief_statuses = parse_brief_statuses(run_dir / "DECISION-BRIEF.md")

    hypotheses_out = []
    for i, h in enumerate(raw_hyps, start=1):
        hid = h.get("hypothesis_id") or h.get("id") or f"h{i}"
        label_short = f"H{i}"
        label_full = humanize_hypothesis_label(hid)
        status_info = brief_statuses.get(label_short, {"short": "UNKNOWN", "detail": ""})

        effects_out = []
        for e in h.get("effects", []):
            effect = {
                "id": e.get("effect_id", ""),
                "desc": (e.get("description") or "")[:240],
                "p": e.get("probability", 0),
                "p_range": e.get("probability_range", [e.get("probability", 0)] * 2),
                "agreement": _coerce_agreement(e.get("council_agreement")),
                "timeframe": e.get("timeframe", ""),
                "specialist": bool(e.get("specialist_insight", False)),
                "children": [],
            }
            for c in (e.get("children") or []):
                effect["children"].append({
                    "id": c.get("effect_id", ""),
                    "desc": (c.get("description") or "")[:240],
                    "p": c.get("probability", 0),
                    "agreement": _coerce_agreement(c.get("council_agreement")),
                })
            effects_out.append(effect)

        # Adversarial data: prefer per-hypothesis `targets` format; fall back to flat lists
        # distributed round-robin by hypothesis index.
        target = per_hyp_targets.get(hid) or {}
        worst_case_text = (target.get("most_lethal_attack_vector") or "")[:300]
        black_swan_text = (target.get("unlisted_black_swan") or "")[:300]
        lethality = target.get("lethality_score", 0)
        correlations = target.get("hidden_correlations") or []

        if not worst_case_text and flat_wcs:
            # Try to MATCH: some flat worst cases list `affected` hypothesis ids they threaten.
            # If this hypothesis is affected by one, use that. Otherwise fall back to round-robin.
            matched = next((wc for wc in flat_wcs if hid in (wc.get("affected") or [])), None)
            wc = matched or flat_wcs[(i - 1) % len(flat_wcs)]
            worst_case_text = wc["description"]
            lethality = wc.get("lethality") or 7
        if not black_swan_text and flat_bss:
            matched = next((bs for bs in flat_bss if hid in (bs.get("affected") or [])), None)
            bs = matched or flat_bss[(i - 1) % len(flat_bss)]
            black_swan_text = bs["description"]

        hypotheses_out.append({
            "id": hid,
            "label": label_full,
            "effects": effects_out,
            "worst_case": worst_case_text,
            "black_swan": black_swan_text,
            "lethality": lethality,
            "correlations": correlations,
            "status": status_info["short"],
            "status_detail": status_info["detail"],
        })

    return {
        "decision": decision_text,
        "hypotheses": hypotheses_out,
    }


def inline_data_into_template(template_path: Path, data: dict) -> str:
    """Inject the JSON dataset into the template, replacing the __INLINED_DATA__ marker."""
    html = template_path.read_text(encoding="utf-8")
    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    # Replace the `null` between __DATA_START__ and __DATA_END__ markers
    pattern = re.compile(r"/\*__DATA_START__\*/\s*.*?\s*/\*__DATA_END__\*/", re.DOTALL)
    new_marker = f"/*__DATA_START__*/ {data_json} /*__DATA_END__*/"
    if not pattern.search(html):
        raise RuntimeError("Template missing __DATA_START__ / __DATA_END__ markers")
    return pattern.sub(lambda _: new_marker, html)


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True, help="Path to the decision run directory")
    ap.add_argument("--output", help="Output HTML path. Defaults to {run_dir}/EFFECTS-VIZ.html")
    ap.add_argument("--template", help="Template HTML path. Defaults to next to this script.")
    ap.add_argument("--quiet", action="store_true", help="Suppress informational output")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.is_dir():
        print(f"ERROR: run-dir does not exist: {run_dir}", file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    default_template = script_dir.parent / "templates" / "effects-orbital.html"
    template_path = Path(args.template).resolve() if args.template else default_template
    if not template_path.exists():
        print(f"ERROR: template not found: {template_path}", file=sys.stderr)
        return 2

    output_path = Path(args.output).resolve() if args.output else run_dir / "EFFECTS-VIZ.html"

    try:
        data = build_dataset(run_dir)
    except FileNotFoundError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        print("  (Quick-mode runs don't produce effects-chains.json. Visualization requires a full-mode run.)",
              file=sys.stderr)
        return 3

    html = inline_data_into_template(template_path, data)
    output_path.write_text(html, encoding="utf-8")

    if not args.quiet:
        total_fo = sum(len(h["effects"]) for h in data["hypotheses"])
        total_so = sum(len(e["children"]) for h in data["hypotheses"] for e in h["effects"])
        worst_cases = sum(1 for h in data["hypotheses"] if h.get("worst_case"))
        swans = sum(1 for h in data["hypotheses"] if h.get("black_swan"))
        print(f"Wrote {output_path}")
        print(f"  decision:     {data['decision'][:80]}")
        print(f"  hypotheses:   {len(data['hypotheses'])}")
        print(f"  1st-order:    {total_fo}")
        print(f"  2nd-order:    {total_so}")
        print(f"  worst cases:  {worst_cases}")
        print(f"  black swans:  {swans}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
