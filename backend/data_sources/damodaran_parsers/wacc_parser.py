"""Parse Damodaran WACC spreadsheets (wacc.xls, waccGlobal.xls, waccChina.xls).

Data on sheet "Industry Averages", header row contains "Industry Name".
"""

from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int, safe_str,
)


def _find_col(col_map: dict[str, int], candidates: list[str]) -> int | None:
    """Find the first matching column from a list of candidate header names."""
    for c in candidates:
        if c in col_map:
            return col_map[c]
    for c in candidates:
        for h, idx in col_map.items():
            if c.lower() in h.lower():
                return idx
    return None


def parse_wacc(file_path: str | Path) -> dict[str, dict]:
    """Parse WACC .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")
    header_row = find_header_row(ws, "Industry Name")
    col = build_col_map(get_headers(ws, header_row))

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name = (safe_str(ws, r, col.get("Industry Name")) or "").strip()
        if not name or name.lower() == "total market":
            continue
        result[name] = {
            "cost_of_equity": safe_float(ws, r, col.get("Cost of Equity")),
            "cost_of_debt_pretax": safe_float(ws, r, col.get("Cost of Debt")),
            "after_tax_cost_of_debt": safe_float(ws, r, col.get("After-tax Cost of Debt")),
            "tax_rate": safe_float(ws, r, col.get("Tax Rate")),
            "weight_equity": safe_float(ws, r, col.get("E/(D+E)")),
            "weight_debt": safe_float(ws, r, col.get("D/(D+E)")),
            "wacc": safe_float(ws, r, col.get("Cost of Capital")),
            "number_of_firms": safe_int(ws, r, col.get("Number of Firms")),
            "std_dev_stock": safe_float(ws, r, _find_col(col, ["Std Dev in Stock", "Standard deviation", "Std Dev"])),
        }
    return result
