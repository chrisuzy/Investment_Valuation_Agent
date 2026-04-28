"""Parse Damodaran beta spreadsheets (betas.xls, betaGlobal.xls, betaChina.xls).

Data on sheet "Industry Averages", header at row 9.
"""

from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int,
)


def parse_betas(file_path: str | Path) -> dict[str, dict]:
    """Parse betas .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")
    header_row = find_header_row(ws, "Industry Name")
    col = build_col_map(get_headers(ws, header_row))

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name = (safe_str_cell(ws, r, col.get("Industry Name")) or "").strip()
        if not name or name.lower() == "total market":
            continue
        result[name] = {
            "beta_u": safe_float(ws, r, col.get("Unlevered beta")),
            "beta_u_corrected_for_cash": safe_float(ws, r, col.get("Unlevered beta corrected for cash")),
            "d_e_ratio": safe_float(ws, r, col.get("D/E Ratio")),
            "effective_tax_rate": safe_float(ws, r, col.get("Effective Tax rate")),
            "number_of_firms": safe_int(ws, r, col.get("Number of firms")),
        }
    return result


def _find_col(col_map: dict[str, int], candidates: list[str]) -> int | None:
    """Find the first matching column from a list of candidate header names."""
    for c in candidates:
        if c in col_map:
            return col_map[c]
    # Fallback: partial match (header contains candidate)
    for c in candidates:
        for h, idx in col_map.items():
            if c.lower() in h.lower():
                return idx
    return None


def safe_str_cell(ws, row, col):
    if col is None:
        return None
    try:
        v = ws.cell_value(row, col)
    except IndexError:
        return None
    return str(v).strip() if v != "" else None
