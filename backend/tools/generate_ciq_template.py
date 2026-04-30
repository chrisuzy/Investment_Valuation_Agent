"""
Generate a reusable CIQ template Excel file.

How it works:
  1. Cell B1 = ticker (e.g., "NVDA")
  2. All CIQ formulas reference $B$1 as the ticker
  3. User opens in Excel with CIQ plugin → formulas auto-resolve
  4. User saves → backend reads the resolved values

Usage:
  python -m tools.generate_ciq_template           # generates template
  python -m tools.generate_ciq_template NVDA       # generates with NVDA as default ticker
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Add parent to path so we can import from data_sources
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources.capiq_formula_map import (
    INCOME_STATEMENT_FIELDS,
    BALANCE_SHEET_FIELDS,
    MARKET_FIELDS,
    CASHFLOW_FIELDS,
    OPTION_FIELDS,
    LEASE_COMMITMENT_FIELDS,
    PERIOD_DATE_FIELDS,
)


# ── Configuration ──────────────────────────────────────────────
YEARS_BACK = 10
QUARTERLY_BACK = 8
RD_YEARS_BACK = 10

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "ciq_fetches"

# ── Styles ─────────────────────────────────────────────────────
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
SECTION_FILL = PatternFill("solid", fgColor="D9E2F3")
SECTION_FONT = Font(bold=True, size=11)
TICKER_FILL = PatternFill("solid", fgColor="FFFF00")
TICKER_FONT = Font(bold=True, size=14)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def generate_template(default_ticker: str = "NVDA") -> Path:
    """Generate the CIQ fetch template Excel file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "CIQ_Fetch_Template.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CIQ_Data"

    # ── Row 1: Ticker input ────────────────────────────────────
    ws["A1"] = "Ticker:"
    ws["A1"].font = Font(bold=True, size=12)
    ws["B1"] = default_ticker
    ws["B1"].font = TICKER_FONT
    ws["B1"].fill = TICKER_FILL
    ws["B1"].alignment = Alignment(horizontal="center")

    ws["C1"] = "← Change this ticker, then wait for CIQ to resolve all formulas, then Save."
    ws["C1"].font = Font(italic=True, color="666666")

    # ── Row 2: Instructions ────────────────────────────────────
    ws["A2"] = "Instructions:"
    ws["B2"] = "1) Enter ticker in B1  2) Wait for #GETTING_DATA to disappear  3) Save (Ctrl+S)  4) Load in app"
    ws["B2"].font = Font(italic=True, color="444444")

    # ── Row 3: blank separator ────────────────────────────────
    row = 4

    # ── Column headers ─────────────────────────────────────────
    headers = ["Variable", "Period", "CIQ Formula", "Resolved Value", "Description"]
    col_widths = [30, 12, 55, 20, 40]
    for c, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row, c, h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(c)].width = w

    row += 1
    formula_rows: list[dict] = []  # track all formula rows for the reader

    def add_section(title: str):
        nonlocal row
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        cell = ws.cell(row, 1, title)
        cell.font = SECTION_FONT
        cell.fill = SECTION_FILL
        row += 1

    # Expense-type fields: CIQ returns negative, Damodaran uses positive.
    # Wrap these with ABS() in the template so values are positive from the start.
    EXPENSE_VARIABLES = {"interest_expense", "capex", "d_a", "operating_lease_expense"}

    # Build lookup of currency-override tokens (e.g. "<FILING>") per variable.
    # These are CIQ's magic 5th-argument values that resolve at query time to
    # the company's actual filing / trading currency — no per-ticker hardcoding.
    from data_sources.capiq_formula_map import ALL_FIELDS
    _CCY_OVERRIDES = {f.variable_name: f.currency_override for f in ALL_FIELDS if f.currency_override}

    def add_formula_row(variable: str, mnemonic: str, period: str, description: str):
        nonlocal row
        # Build formula referencing $B$1 as ticker
        # Use the full XLL path so CIQ plugin resolves both via COM and manual open.
        # CIQ signature: CIQ(identifier, mnemonic, [period], [date], [currency])
        ccy = _CCY_OVERRIDES.get(variable)
        if ccy:
            # Emit all 5 args. Empty "" for period/date when period == "current"
            if period == "current":
                ciq_call = f'_xll.ciqfunctions.udf.CIQ($B$1,"{mnemonic}","","","{ccy}")'
            else:
                ciq_call = f'_xll.ciqfunctions.udf.CIQ($B$1,"{mnemonic}","{period}","","{ccy}")'
        elif period == "current":
            ciq_call = f'_xll.ciqfunctions.udf.CIQ($B$1,"{mnemonic}")'
        else:
            ciq_call = f'_xll.ciqfunctions.udf.CIQ($B$1,"{mnemonic}","{period}")'

        # Wrap expense-type fields with ABS() so values are always positive
        if variable in EXPENSE_VARIABLES:
            formula = f"=ABS({ciq_call})"
        else:
            formula = f"={ciq_call}"

        ws.cell(row, 1, variable).border = THIN_BORDER
        ws.cell(row, 2, period).border = THIN_BORDER
        # Column C: the actual CIQ formula (Excel will evaluate it)
        cell_c = ws.cell(row, 3)
        cell_c.value = formula
        cell_c.border = THIN_BORDER
        cell_c.font = Font(color="0000CC", size=10)
        # Column D: formula that just references C (so resolved value is in D)
        cell_d = ws.cell(row, 4)
        cell_d.value = f"=C{row}"
        cell_d.border = THIN_BORDER
        cell_d.number_format = '#,##0.00'
        # Column E: description
        ws.cell(row, 5, description).border = THIN_BORDER

        formula_rows.append({
            "row": row,
            "variable": variable,
            "period": period,
            "mnemonic": mnemonic,
        })
        row += 1

    # ── Income Statement (multi-year annual) ───────────────────
    add_section("INCOME STATEMENT (Annual)")
    for field in INCOME_STATEMENT_FIELDS + CASHFLOW_FIELDS:
        max_yr = RD_YEARS_BACK if field.variable_name in ("r_and_d_expense", "r_and_d_expense_fn") else YEARS_BACK
        for yr in range(max_yr + 1):
            period = f"IQ_FY-{yr}"
            add_formula_row(field.variable_name, field.mnemonic, period, field.description)

    # ── Income Statement (quarterly for LTM) ──────────────────
    add_section("INCOME STATEMENT (Quarterly — for LTM)")
    for field in INCOME_STATEMENT_FIELDS + CASHFLOW_FIELDS:
        for q in range(QUARTERLY_BACK):
            period = f"IQ_FQ-{q}"
            add_formula_row(field.variable_name, field.mnemonic, period, field.description)

    # ── Balance Sheet (multi-year annual) ────────────────────────
    add_section("BALANCE SHEET (Annual)")
    for field in BALANCE_SHEET_FIELDS:
        for yr in range(YEARS_BACK + 1):
            period = f"IQ_FY-{yr}"
            add_formula_row(field.variable_name, field.mnemonic, period, field.description)

    # ── Balance Sheet (quarterly FQ-0 for point-in-time LTM) ──
    add_section("BALANCE SHEET (Quarterly — latest 10-Q)")
    for field in BALANCE_SHEET_FIELDS:
        add_formula_row(field.variable_name, field.mnemonic, "IQ_FQ-0", f"{field.description} (latest quarter)")

    # ── Market Data (current only) ─────────────────────────────
    add_section("MARKET DATA (Current)")
    for field in MARKET_FIELDS:
        # Skip effective_tax_rate_ciq — handled separately with /100
        if field.variable_name == "effective_tax_rate_ciq":
            continue
        add_formula_row(field.variable_name, field.mnemonic, "current", field.description)

    # Effective tax rate: special formula with /100 (CIQ returns percentage, we need decimal)
    add_formula_row("effective_tax_rate_ciq", "IQ_EFFECT_TAX_RATE", "IQ_FY", "Effective Tax Rate (CIQ, /100)")
    # Override the formula in the last row to add /100
    tax_row = row - 1
    ws.cell(tax_row, 3).value = '=_xll.ciqfunctions.udf.CIQ($B$1,"IQ_EFFECT_TAX_RATE","IQ_FY")/100'

    # ── Options (current only) ─────────────────────────────────
    add_section("EMPLOYEE OPTIONS (Current)")
    for field in OPTION_FIELDS:
        add_formula_row(field.variable_name, field.mnemonic, "current", field.description)

    # ── Lease Commitments (current only) ───────────────────────
    add_section("OPERATING LEASE COMMITMENTS (Current)")
    for field in LEASE_COMMITMENT_FIELDS:
        add_formula_row(field.variable_name, field.mnemonic, "current", field.description)

    # ── Period Dates ───────────────────────────────────────────
    add_section("PERIOD DATES")
    add_formula_row("period_date_annual", "IQ_PERIODDATE", "IQ_FY-0", "Most recent 10-K period end date")
    add_formula_row("period_date_quarterly", "IQ_PERIODDATE", "IQ_FQ-0", "Most recent 10-Q period end date")

    # ── Metadata sheet: row map for the reader ─────────────────
    ws_meta = wb.create_sheet("_RowMap")
    ws_meta["A1"] = "row"
    ws_meta["B1"] = "variable"
    ws_meta["C1"] = "period"
    ws_meta["D1"] = "mnemonic"
    for i, fr in enumerate(formula_rows, 2):
        ws_meta.cell(i, 1, fr["row"])
        ws_meta.cell(i, 2, fr["variable"])
        ws_meta.cell(i, 3, fr["period"])
        ws_meta.cell(i, 4, fr["mnemonic"])

    # ── Save ───────────────────────────────────────────────────
    wb.save(str(output_path))
    print(f"Generated CIQ template: {output_path}")
    print(f"  {len(formula_rows)} formulas")
    print(f"  Default ticker: {default_ticker}")
    print(f"\nNext steps:")
    print(f"  1. Open {output_path.name} in Excel (with CIQ plugin)")
    print(f"  2. Change ticker in B1 if needed")
    print(f"  3. Wait for all formulas to resolve")
    print(f"  4. Save the file")
    print(f"  5. In the app, use 'Load from CIQ File' to import")

    return output_path


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    generate_template(ticker)
