"""Parse Damodaran EV/EBITDA spreadsheets (vebitda.xls, etc.).

Key field: EV/EBITDA (all firms) → ev_ebitda
"""
from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int, safe_str,
)


def parse_vebitda(file_path: str | Path) -> dict[str, dict]:
    """Parse EV/EBITDA .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")
    # This file has two header rows (row 7 and row 8). The actual column names are in row 8.
    header_row = find_header_row(ws, "Industry Name")
    headers = get_headers(ws, header_row)

    # The file has duplicate column names for "positive EBITDA only" and "all firms" sections.
    # We want the "All firms" section (columns 6-9 typically).
    # Find the second occurrence of EV/EBITDA
    col = {}
    ev_ebitda_count = 0
    for i, h in enumerate(headers):
        if h == "EV/EBITDA":
            ev_ebitda_count += 1
            if ev_ebitda_count == 2:
                col["ev_ebitda_all"] = i
        elif h == "EV/EBIT":
            if "ev_ebit_first" not in col:
                col["ev_ebit_first"] = i
        elif h == "Industry Name":
            col["Industry Name"] = i
        elif h == "Number of firms":
            col["Number of firms"] = i

    # Fallback: use first EV/EBITDA if only one exists
    if "ev_ebitda_all" not in col:
        for i, h in enumerate(headers):
            if h == "EV/EBITDA":
                col["ev_ebitda_all"] = i
                break

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name_col = col.get("Industry Name")
        if name_col is None:
            continue
        name = (safe_str(ws, r, name_col) or "").strip()
        if not name or name.lower() in ("total market", "total"):
            continue
        result[name] = {
            "ev_ebitda": safe_float(ws, r, col.get("ev_ebitda_all")),
        }
    return result
