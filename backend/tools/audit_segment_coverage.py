"""
tools/audit_segment_coverage.py

Scans every geographic segment label in the DB, tests resolution against
the current alias table + fuzzy matcher, and reports:
  - Total unique segment names
  - Coverage by layer (exact / alias / fuzzy / composite / weak / unresolved)
  - Full list of unresolved names sorted by frequency
  - Suggested additions for the segment_aliases.json file

Usage:
  python -m tools.audit_segment_coverage [--db PATH] [--suggest]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(_REPO_ROOT / "backend/data_sources/us_cn_hk.sqlite"))
    parser.add_argument("--suggest", action="store_true", help="Print alias suggestions for unresolved names")
    args = parser.parse_args()

    # ── Load DB ───────────────────────────────────────────────────────────────
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.execute("SELECT geographic_segments_json FROM companies WHERE geographic_segments_json IS NOT NULL AND geographic_segments_json != '[]'")
    rows = cur.fetchall()
    conn.close()

    print(f"Companies with segment data: {len(rows):,}")

    # ── Collect all segment names ─────────────────────────────────────────────
    name_counter: Counter = Counter()
    parse_errors = 0
    for (raw,) in rows:
        if not raw or raw in ("[]", "null"):
            continue
        try:
            segs = json.loads(raw)
            for s in segs:
                n = s.get("name", "").strip()
                if n:
                    name_counter[n] += 1
        except Exception:
            parse_errors += 1

    total_instances = sum(name_counter.values())
    unique_names = len(name_counter)
    print(f"Total segment instances:    {total_instances:,}")
    print(f"Unique segment names:       {unique_names:,}")
    if parse_errors:
        print(f"JSON parse errors:          {parse_errors}")

    # ── Load Damodaran store and resolver ─────────────────────────────────────
    from data_sources.damodaran_store import DamodaranStore
    from engine.segment_resolver import resolve_segment, reload_aliases

    reload_aliases()
    store = DamodaranStore.from_directory(str(_REPO_ROOT / "knowledge_base/damodaran"))

    print(f"\nResolving {unique_names:,} unique names against Damodaran + alias table...")

    # ── Resolve each unique name once ─────────────────────────────────────────
    layer_counts: Counter = Counter()
    unresolved: dict[str, int] = {}   # name → frequency
    low_confidence: list[tuple] = []  # (name, freq, matched_to, confidence)

    for name, freq in name_counter.items():
        res = resolve_segment(name, store)
        src = res.get("source", "unresolved")
        conf = res.get("confidence", 0)
        layer_counts[src] += freq

        if src == "unresolved":
            unresolved[name] = freq
        elif src == "fuzzy_country" and conf < 0.80:
            low_confidence.append((name, freq, res.get("mapped_to"), conf))

    # ── Summary table ─────────────────────────────────────────────────────────
    resolved_total = total_instances - sum(unresolved.values())
    print(f"\n{'='*65}")
    print(f"COVERAGE REPORT")
    print(f"{'='*65}")
    print(f"{'Source':<20} {'Instances':>12}  {'% of total':>10}")
    print("-"*45)
    order = ["exact_country", "alias", "fuzzy_country", "composite", "weak_default", "collapsed", "unresolved"]
    for src in order:
        cnt = layer_counts[src]
        pct = cnt / total_instances * 100 if total_instances else 0
        print(f"  {src:<18} {cnt:>12,}  {pct:>9.1f}%")
    print("-"*45)
    print(f"  {'TOTAL RESOLVED':<18} {resolved_total:>12,}  {resolved_total/total_instances*100:>9.1f}%")
    print(f"  {'UNRESOLVED':<18} {len(unresolved):>12,} unique names")

    # ── Low-confidence fuzzy matches (for review) ─────────────────────────────
    if low_confidence:
        low_confidence.sort(key=lambda x: -x[1])
        print(f"\n{'='*65}")
        print(f"FUZZY MATCHES WITH CONFIDENCE < 80% (review recommended)")
        print(f"{'='*65}")
        for name, freq, mapped, conf in low_confidence[:30]:
            print(f"  {freq:5d}×  {name!r:45s} → {mapped!r}  ({conf:.0%})")

    # ── Unresolved names ──────────────────────────────────────────────────────
    unresolved_sorted = sorted(unresolved.items(), key=lambda x: -x[1])
    print(f"\n{'='*65}")
    print(f"UNRESOLVED NAMES ({len(unresolved):,} unique, sorted by frequency)")
    print(f"{'='*65}")
    for name, freq in unresolved_sorted:
        print(f"  {freq:5d}×  {name!r}")

    if args.suggest:
        _print_suggestions(unresolved_sorted, store)


def _print_suggestions(unresolved_sorted, store):
    """Attempt difflib suggestions for the unresolved names."""
    import difflib
    from engine.segment_resolver import _normalise, _build_fuzzy_index

    idx = _build_fuzzy_index(store)
    norm_keys = list(idx.keys())

    print(f"\n{'='*65}")
    print("AUTO-SUGGESTIONS (difflib, cutoff 0.50 — lower than resolution threshold)")
    print(f"{'='*65}")
    for name, freq in unresolved_sorted[:50]:
        norm = _normalise(name)
        matches = difflib.get_close_matches(norm, norm_keys, n=1, cutoff=0.50)
        if matches:
            best_damo = idx[matches[0]]
            ratio = difflib.SequenceMatcher(None, norm, matches[0]).ratio()
            print(f"  {freq:5d}×  {name!r:45s} → {best_damo!r} ({ratio:.0%}) ?")
        else:
            print(f"  {freq:5d}×  {name!r:45s} → (no suggestion)")


if __name__ == "__main__":
    main()
