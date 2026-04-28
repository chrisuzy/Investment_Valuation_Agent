"""Parse Damodaran EVA spreadsheets (EVA.xls, EVAGlobal.xls, etc.).

Key fields: ROC, Cost of Capital, Std Dev in Stock, ROIC
Header row is at row 18 (0-indexed) in these files.
"""
from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int, safe_str,
)


def parse_eva(file_path: str | Path) -> dict[str, dict]:
    """Parse EVA .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")
    header_row = find_header_row(ws, "Industry Name")
    col = build_col_map(get_headers(ws, header_row))

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name = (safe_str(ws, r, col.get("Industry Name")) or "").strip()
        if not name or name.lower() in ("total market", "total"):
            continue
        result[name] = {
            "roic": safe_float(ws, r, col.get("ROC")),
            "cost_of_capital_eva": safe_float(ws, r, col.get("Cost of Capital")),
            "std_dev_stock": safe_float(ws, r, col.get("Std Dev in Stock")),
            "cost_of_debt_eva": safe_float(ws, r, col.get("Cost of Debt")),
            "d_e_ratio": safe_float(ws, r, col.get("D/(D+E)")),
        }
    return result
