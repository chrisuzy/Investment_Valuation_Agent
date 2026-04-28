"""Shared utilities for parsing Damodaran .xls files."""

from __future__ import annotations

import xlrd


def open_data_sheet(file_path: str, sheet_name: str = "Industry Averages") -> xlrd.sheet.Sheet:
    """Open an xls file and return the named data sheet."""
    wb = xlrd.open_workbook(str(file_path))
    try:
        return wb.sheet_by_name(sheet_name)
    except xlrd.XLRDError:
        # Fallback: try sheet index 1 (index 0 is usually explanations)
        if wb.nsheets > 1:
            return wb.sheet_by_index(1)
        return wb.sheet_by_index(0)


def find_header_row(ws: xlrd.sheet.Sheet, target_col: str, max_rows: int = 20) -> int:
    """Find the row index containing a specific column header."""
    for r in range(min(max_rows, ws.nrows)):
        for c in range(ws.ncols):
            try:
                val = str(ws.cell_value(r, c)).strip()
            except IndexError:
                continue
            if val == target_col:
                return r
    raise ValueError(f"Could not find header row containing '{target_col}' in sheet '{ws.name}'")


def get_headers(ws: xlrd.sheet.Sheet, row: int) -> list[str]:
    """Get all column headers from a given row."""
    return [str(ws.cell_value(row, c)).strip() for c in range(ws.ncols)]


def build_col_map(headers: list[str]) -> dict[str, int]:
    """Build a header-name → column-index map (skips empty headers)."""
    return {h: i for i, h in enumerate(headers) if h}


def safe_float(ws: xlrd.sheet.Sheet, row: int, col: int | None) -> float | None:
    """Read a cell as float, returning None on missing/empty/error."""
    if col is None:
        return None
    try:
        val = ws.cell_value(row, col)
    except IndexError:
        return None
    if isinstance(val, (int, float)) and val != "":
        return float(val)
    return None


def safe_int(ws: xlrd.sheet.Sheet, row: int, col: int | None) -> int | None:
    """Read a cell as int, returning None on missing/empty/error."""
    if col is None:
        return None
    try:
        val = ws.cell_value(row, col)
    except IndexError:
        return None
    if isinstance(val, (int, float)) and val != "":
        return int(val)
    return None


def safe_str(ws: xlrd.sheet.Sheet, row: int, col: int | None) -> str | None:
    """Read a cell as string, returning None on missing/empty."""
    if col is None:
        return None
    try:
        val = ws.cell_value(row, col)
    except IndexError:
        return None
    if val is None or val == "":
        return None
    return str(val).strip()
