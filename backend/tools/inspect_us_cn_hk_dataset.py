"""
Structural inspector for the US_CN_HK_dataset .xls files.

Produces a small JSON summary of:
  - each file's sheets
  - per sheet: total row & column counts, top 5 rows (header + samples)
  - no bulk data

so the LLM can understand the schema without being fed 40MB of financial data.

Output: /tmp/us_cn_hk_inspection.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
import xlrd  # legacy .xls reader

DATASET_DIR = Path("/home/chriszhang/claude_code_projects/AD_CC_pilot/US_CN_HK_dataset")
OUT_PATH = Path("/tmp/us_cn_hk_inspection.json")
TOP_ROWS = 25  # capture first N rows per sheet (CIQ exports often have headers deep)


def inspect_file(path: Path) -> dict:
    """Open .xls, extract sheets + top rows per sheet. Never load full data."""
    wb = xlrd.open_workbook(str(path), on_demand=True)
    sheets: list[dict] = []
    for sheet_name in wb.sheet_names():
        sh = wb.sheet_by_name(sheet_name)
        rows_total = sh.nrows
        cols_total = sh.ncols
        top: list[list] = []
        for r in range(min(TOP_ROWS, rows_total)):
            row_values = []
            for c in range(cols_total):
                v = sh.cell_value(r, c)
                # Convert Excel serial dates to isoformat for readability; others unchanged.
                if sh.cell_type(r, c) == xlrd.XL_CELL_DATE:
                    try:
                        dt = xlrd.xldate_as_datetime(v, wb.datemode)
                        v = dt.isoformat()
                    except Exception:
                        pass
                row_values.append(v)
            top.append(row_values)
        sheets.append({
            "sheet": sheet_name,
            "n_rows": rows_total,
            "n_cols": cols_total,
            "top_rows": top,
        })
        wb.unload_sheet(sheet_name)
    return {
        "file": path.name,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "sheets": sheets,
    }


def main():
    if not DATASET_DIR.exists():
        print(f"ERROR: {DATASET_DIR} does not exist", file=sys.stderr)
        sys.exit(1)

    files = sorted([p for p in DATASET_DIR.iterdir() if p.suffix.lower() in (".xls", ".xlsx")])
    if not files:
        print(f"ERROR: no Excel files in {DATASET_DIR}", file=sys.stderr)
        sys.exit(1)

    result = {
        "dataset_dir": str(DATASET_DIR),
        "n_files": len(files),
        "files": [inspect_file(p) for p in files],
    }

    OUT_PATH.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {OUT_PATH}")
    print(f"  files: {result['n_files']}")
    for f in result["files"]:
        for s in f["sheets"]:
            print(f"  {f['file']}:{s['sheet']}  {s['n_rows']} rows × {s['n_cols']} cols")


if __name__ == "__main__":
    main()
