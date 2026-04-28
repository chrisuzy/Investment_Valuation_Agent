"""
Fetch CIQ data by preparing a template with the ticker and opening it in Excel.

Flow:
  1. Copy CIQ_Fetch_Template.xlsx, set B1 = ticker (via openpyxl)
  2. Open the file in Excel (os.startfile — like double-clicking)
  3. CIQ plugin resolves all formulas automatically
  4. Wait for user to save (poll file modification time), OR auto-save via COM
  5. Read resolved values with read_ciq_template.py

Usage:
    python -m tools.fetch_via_template NVDA
    python -m tools.fetch_via_template NVDA --output path/to/save.xlsx
"""

from __future__ import annotations

import sys
import os
import time
import argparse
import shutil
from pathlib import Path

import openpyxl

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "ciq_fetches"
TEMPLATE_FILE = TEMPLATE_DIR / "CIQ_Fetch_Template.xlsx"


def fetch_via_template(ticker: str, output_path: str | None = None, max_wait: int = 120) -> str:
    """Prepare template with ticker, open in Excel, wait for CIQ to resolve, save."""

    if output_path is None:
        output_path = str(TEMPLATE_DIR / f"{ticker}_fetch.xlsx")

    # Step 1: Copy template and set ticker using openpyxl
    work_copy = str(TEMPLATE_DIR / f"_active_fetch.xlsx")
    wb = openpyxl.load_workbook(str(TEMPLATE_FILE))
    wb["CIQ_Data"]["B1"] = ticker
    wb.save(work_copy)
    wb.close()
    print(f"Prepared template with ticker={ticker}")

    # Step 2: Open in Excel (like double-clicking — CIQ plugin will resolve)
    print(f"Opening in Excel...")
    os.startfile(work_copy)

    # Step 3: Wait for CIQ to resolve and user to save (or auto-detect)
    # Poll: check if the file has been modified (Excel saves update mtime)
    initial_mtime = Path(work_copy).stat().st_mtime
    print(f"Waiting for formulas to resolve (up to {max_wait}s)...")
    print(f"  When Excel finishes loading data, press Ctrl+S to save, or wait.")

    # Also try COM to poll cell values and auto-save
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        time.sleep(8)  # Wait for Excel to open and CIQ to start

        excel = win32com.client.GetActiveObject("Excel.Application")
        # Find our workbook by name
        target_name = Path(work_copy).name
        found_wb = None
        for i in range(1, excel.Workbooks.Count + 1):
            if excel.Workbooks(i).Name == target_name:
                found_wb = excel.Workbooks(i)
                break

        if found_wb:
            ws = found_wb.Sheets("CIQ_Data")
            print(f"Connected to workbook via COM")

            # Poll until formulas resolve
            start = time.time()
            while time.time() - start < max_wait:
                time.sleep(3)
                unresolved = 0
                for sample_row in range(6, 220, 20):
                    try:
                        text = str(ws.Cells(sample_row, 3).Text or "")
                        if any(m in text.upper() for m in ["GETTING", "LOADING", "#NAME"]):
                            unresolved += 1
                    except Exception:
                        unresolved += 1

                elapsed = time.time() - start
                if unresolved == 0:
                    print(f"All formulas resolved in {elapsed:.0f}s")
                    # Auto-save
                    found_wb.SaveAs(str(Path(output_path).resolve()), FileFormat=51)
                    found_wb.Close(SaveChanges=False)
                    print(f"Saved to: {output_path}")
                    pythoncom.CoUninitialize()
                    # Clean up work copy
                    try:
                        Path(work_copy).unlink(missing_ok=True)
                    except Exception:
                        pass
                    return output_path
                else:
                    print(f"  {elapsed:.0f}s: {unresolved} sample cells still resolving...")

            print("Timeout — saving whatever we have")
            found_wb.SaveAs(str(Path(output_path).resolve()), FileFormat=51)
            found_wb.Close(SaveChanges=False)
            pythoncom.CoUninitialize()
            try:
                Path(work_copy).unlink(missing_ok=True)
            except Exception:
                pass
            return output_path
        else:
            print(f"Could not find workbook '{target_name}' via COM")
            pythoncom.CoUninitialize()
    except ImportError:
        print("pywin32 not available — waiting for manual save")
    except Exception as e:
        print(f"COM connection failed: {e}")
        print("Falling back to manual save detection...")

    # Fallback: wait for file modification (user saves manually)
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(2)
        current_mtime = Path(work_copy).stat().st_mtime
        if current_mtime > initial_mtime:
            print(f"File saved! Copying to {output_path}")
            shutil.copy2(work_copy, output_path)
            try:
                Path(work_copy).unlink(missing_ok=True)
            except Exception:
                pass
            return output_path

    print(f"Timeout after {max_wait}s. Please save the file manually.")
    return work_copy


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CIQ data via template")
    parser.add_argument("ticker", help="Ticker symbol (e.g., NVDA)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--max-wait", type=int, default=120, help="Max seconds to wait")
    args = parser.parse_args()

    result_path = fetch_via_template(args.ticker, args.output, args.max_wait)
    print(f"\nDone! File: {result_path}")
