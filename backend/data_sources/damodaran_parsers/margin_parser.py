"""Parse Damodaran margin spreadsheets (margin.xls, marginGlobal.xls, marginChina.xls).

Data on sheet "Industry Averages", header contains "Industry Name".
"""

from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int, safe_str,
)


def parse_margins(file_path: str | Path) -> dict[str, dict]:
    """Parse margins .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")
    header_row = find_header_row(ws, "Industry Name")
    col = build_col_map(get_headers(ws, header_row))

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name = (safe_str(ws, r, col.get("Industry Name")) or "").strip()
        if not name or name.lower() == "total market":
            continue
        result[name] = {
            "gross_margin": safe_float(ws, r, col.get("Gross Margin")),
            "pretax_operating_margin": safe_float(ws, r, col.get("Pre-tax Unadjusted Operating Margin")),
            "aftertax_operating_margin": safe_float(ws, r, col.get("After-tax Unadjusted Operating Margin")),
            "pretax_lease_rd_adj_margin": safe_float(ws, r, col.get("Pre-tax Lease & R&D adj Margin")),
            "aftertax_lease_rd_adj_margin": safe_float(ws, r, col.get("After-tax Lease & R&D adj Margin")),
            "ebitda_margin": safe_float(ws, r, col.get("EBITDA/Sales")),
            "net_margin": safe_float(ws, r, col.get("Net Margin")),
            "number_of_firms": safe_int(ws, r, col.get("Number of firms")),
        }
    return result
