"""Parse Damodaran industry tax rate spreadsheets (taxrate.xls, etc.).

Data on sheet "Industry Averages", header contains "Industry name".
"""

from __future__ import annotations

from pathlib import Path

from .xls_utils import (
    open_data_sheet, find_header_row, get_headers, build_col_map, safe_float, safe_int, safe_str,
)


def parse_industry_tax_rates(file_path: str | Path) -> dict[str, dict]:
    """Parse industry tax rates .xls → dict keyed by industry name."""
    ws = open_data_sheet(str(file_path), "Industry Averages")

    # Header may say "Industry name" or "Industry Name" — try both
    try:
        header_row = find_header_row(ws, "Industry name")
    except ValueError:
        header_row = find_header_row(ws, "Industry Name")

    # Use positional access since column names are duplicated
    # Row 8: C0=Industry name, C1=Number of firms, C2..C5=intermediate,
    #         C6=Avg all companies, C7=Avg money-making (effective), C8=Aggregate
    industry_col = 0
    firms_col = 1
    effective_col = 7  # "Average across only money-making companies" (accrual)
    aggregate_col = 8  # "Aggregate tax rate" (accrual)

    result: dict[str, dict] = {}
    for r in range(header_row + 1, ws.nrows):
        name = (safe_str(ws, r, industry_col) or "").strip()
        if not name or name.lower() == "total market":
            continue
        result[name] = {
            "effective_tax_rate_avg": safe_float(ws, r, effective_col),
            "aggregate_tax_rate": safe_float(ws, r, aggregate_col),
            "number_of_firms": safe_int(ws, r, firms_col),
        }

    return result
