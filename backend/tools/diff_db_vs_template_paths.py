"""
Diff two valuation paths for the same ticker:
  A. Upload the CIQ Fetch Template (template-path; ground truth)
  B. POST /api/valuation/from-database (DB-path; new)

Writes a diff report to /tmp/path_diff_<ticker>.txt listing every key
whose value differs, with both values side by side. Numeric diffs are
flagged as 'close' when abs-diff < 1e-6 and relative-diff < 0.001.

Run with the backend already serving at http://localhost:8000.

Usage:
    python -m tools.diff_db_vs_template_paths \
        --template TEST_DATA/CIQ_Fetch_Template_Lenovo.xlsx \
        --ticker SEHK:992 \
        --out /tmp/lenovo_diff.txt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

API = "http://localhost:8000/api"


def _numeric_close(a, b) -> bool:
    """True if both are numeric and within tight tolerance."""
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return False
    if a == b:
        return True
    diff = abs(a - b)
    if diff < 1e-6:
        return True
    base = max(abs(a), abs(b), 1e-9)
    return diff / base < 1e-3


def _walk(prefix: str, a, b, diffs: list):
    """Recursively collect differences. Lists compared index-by-index."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a.keys()) | set(b.keys())):
            _walk(f"{prefix}.{k}" if prefix else k, a.get(k), b.get(k), diffs)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append((prefix, f"len={len(a)}", f"len={len(b)}"))
        for i in range(max(len(a), len(b))):
            _walk(f"{prefix}[{i}]", a[i] if i < len(a) else None, b[i] if i < len(b) else None, diffs)
    else:
        if a == b or _numeric_close(a, b):
            return
        diffs.append((prefix, a, b))


def run_template_path(template_path: Path) -> dict:
    with open(template_path, "rb") as fh:
        r = requests.post(
            f"{API}/valuation/fetch-from-file",
            files={"file": (template_path.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"region": "US", "risk_free_rate": "0.0425"},
            timeout=60,
        )
    r.raise_for_status()
    return r.json()


def run_database_path(ticker: str) -> dict:
    r = requests.post(
        f"{API}/valuation/from-database",
        json={"ticker": ticker, "risk_free_rate": 0.0425},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


# Keys whose differences are expected and should not clutter the report:
#   - session id (random per call)
#   - timestamps derived from server mtime
EXPECTED_DIFFS = {
    "id",
    "inputs.fx_rate",              # template has CIQ-implied; DB often unset
    "inputs.fx_rate_source",       # likewise
    "inputs.fx_rate_date",
    "inputs.period_dates_annual",  # template has richer per-FY dates; DB stores only FY-0 + FQ-0
    "source_metadata",             # template tracks per-field source; DB path starts empty
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, type=Path,
                    help="Path to the CIQ Fetch Template .xlsx for template-path upload")
    ap.add_argument("--ticker", required=True,
                    help="Ticker to fetch via DB path, e.g. SEHK:992")
    ap.add_argument("--out", required=True, type=Path,
                    help="Where to write the diff report")
    args = ap.parse_args()

    print(f"[1/3] Upload template: {args.template.name}", file=sys.stderr)
    tpl = run_template_path(args.template)

    print(f"[2/3] DB path: {args.ticker}", file=sys.stderr)
    dbp = run_database_path(args.ticker)

    print("[3/3] Diff", file=sys.stderr)
    diffs: list = []
    _walk("", tpl, dbp, diffs)
    # Filter expected
    diffs = [(p, a, b) for p, a, b in diffs if not any(p == k or p.startswith(k + ".") for k in EXPECTED_DIFFS)]

    # Write report
    with open(args.out, "w") as fh:
        fh.write(f"Diff: TEMPLATE ({args.template.name})  vs  DATABASE ({args.ticker})\n")
        fh.write(f"Total differences (excluding expected): {len(diffs)}\n\n")

        # Group by top-level key for readability
        from collections import defaultdict
        by_section: dict = defaultdict(list)
        for path, a, b in diffs:
            top = path.split(".")[0].split("[")[0]
            by_section[top].append((path, a, b))

        for section in sorted(by_section.keys()):
            fh.write(f"=== {section} ({len(by_section[section])} diffs) ===\n")
            for path, a, b in by_section[section][:80]:
                sa = repr(a)[:80]
                sb = repr(b)[:80]
                fh.write(f"  {path}\n     TEMPLATE={sa}\n     DATABASE={sb}\n")
            if len(by_section[section]) > 80:
                fh.write(f"  … and {len(by_section[section]) - 80} more in this section\n")
            fh.write("\n")

    print(f"✓ Wrote diff report: {args.out} ({len(diffs)} differences)", file=sys.stderr)

    # Also print a compact summary to stdout so the shell caller sees top-of-list
    print(f"DIFF SUMMARY for {args.ticker}: {len(diffs)} total differences")
    for section, entries in sorted(by_section.items(), key=lambda x: -len(x[1])):
        print(f"  {section}: {len(entries)} diffs")


if __name__ == "__main__":
    main()
