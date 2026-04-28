"""Parse Damodaran capex spreadsheets (capex.xls, capexGlobal.xls, etc.).

Key field: Sales/Invested Capital (LTM) → sales_to_capital
"""
from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int, safe_str,
)


def parse_capex(file_path: str | Path) -> dict[str, dict]:
    """Parse capex .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")
    header_row = find_header_row(ws, "Industry Name")
    col = build_col_map(get_headers(ws, header_row))

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name = (safe_str(ws, r, col.get("Industry Name")) or "").strip()
        if not name or name.lower() in ("total market", "total"):
            continue
        result[name] = {
            "sales_to_capital": safe_float(ws, r, col.get("Sales/ Invested Capital (LTM)")),
            "capex_to_depreciation": safe_float(ws, r, col.get("Cap Ex/Deprecn")),
            "net_capex_to_sales": safe_float(ws, r, col.get("Net Cap Ex/Sales")),
        }
    return result
