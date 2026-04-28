"""Parse Damodaran country tax rates (countrytaxrates.xls).

Data on sheet "Sheet1", header at row 5.
Columns: Country, Corporate Tax Rate, Tax Rate Accounting for Global Minimum Tax
"""

from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_str,
)


def parse_country_tax_rates(file_path: str | Path) -> dict[str, dict]:
    """Parse countrytaxrates.xls → dict keyed by country name."""
    wb = __import__("xlrd").open_workbook(str(file_path))

    # Try common sheet names
    ws = None
    for name in ["Sheet1", "sheet1", "Country Tax Rates"]:
        try:
            ws = wb.sheet_by_name(name)
            break
        except Exception:
            continue
    if ws is None:
        ws = wb.sheet_by_index(0)

    header_row = find_header_row(ws, "Country")
    col = build_col_map(get_headers(ws, header_row))

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        country = (safe_str(ws, r, col.get("Country")) or "").strip()
        if not country:
            continue
        result[country] = {
            "corporate_tax_rate": safe_float(ws, r, col.get("Corporate Tax Rate")),
            "tax_rate_global_min": safe_float(ws, r, col.get("Tax Rate Accounting for Global Minimum Tax")),
        }
    return result
