"""
Capital IQ Formula Mapping — maps Data Dictionary variables to CIQ mnemonics.

CIQ formula syntax: =CIQ("TICKER", "MNEMONIC", "PERIOD")
  - PERIOD: "IQ_FY-0" (most recent FY), "IQ_FY-1" (prior FY), "IQ_LTM" (trailing 12m)
  - For point-in-time items (balance sheet): "IQ_FY-0" gives end-of-period value

This mapping can be adjusted if your CIQ plugin uses different mnemonics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CIQField:
    """A single CIQ data point to fetch."""
    variable_name: str       # Data Dictionary variable name
    mnemonic: str            # CIQ mnemonic (e.g., "IQ_TOTAL_REV")
    is_balance_sheet: bool = False  # True = point-in-time, False = flow (period)
    description: str = ""


# ──────────────────────────────────────────────────────────────
# Income Statement / Flow items
# ──────────────────────────────────────────────────────────────
INCOME_STATEMENT_FIELDS = [
    CIQField("revenues",             "IQ_TOTAL_REV",         description="Total Revenue"),
    CIQField("ebit",                 "IQ_EBIT",              description="Operating Income (EBIT)"),
    CIQField("ebitda",               "IQ_EBITDA",            description="EBITDA"),
    CIQField("net_income",           "IQ_NI",                description="Net Income"),
    CIQField("interest_expense",     "IQ_INTEREST_EXP",      description="Interest Expense"),
    CIQField("d_a",                  "IQ_DA_CF",             description="Depreciation & Amortization (from Cash Flow)"),
    CIQField("r_and_d_expense",      "IQ_RD_EXP",            description="R&D Expense"),
    CIQField("r_and_d_expense_fn",   "IQ_RD_EXP_FN",         description="R&D Expense (footnote fallback)"),
    CIQField("capex",                "IQ_CAPEX",             description="Capital Expenditures"),
    CIQField("operating_lease_expense", "IQ_OPERATING_LEASE_PAYMENTS", description="Operating Lease Payments"),
    CIQField("earnings_before_tax",  "IQ_EBT_EXCL",          description="Earnings Before Tax (excl unusual items)"),
    CIQField("total_tax_expense",    "IQ_INC_TAX",           description="Income Tax Expense"),
]

# ──────────────────────────────────────────────────────────────
# Balance Sheet / Point-in-time items
# ──────────────────────────────────────────────────────────────
BALANCE_SHEET_FIELDS = [
    CIQField("cash_and_marketable_securities", "IQ_CASH_EQUIV",    is_balance_sheet=True, description="Cash & Equivalents"),
    CIQField("bv_equity",            "IQ_TOTAL_EQUITY",      is_balance_sheet=True, description="Total Stockholders' Equity"),
    CIQField("bv_debt",              "IQ_TOTAL_DEBT",        is_balance_sheet=True, description="Total Debt"),
    CIQField("shares_outstanding",   "IQ_TOTAL_OUTSTANDING_FILING_DATE",  is_balance_sheet=True, description="Total Shares Outstanding (Filing Date)"),
    CIQField("cross_holdings",      "IQ_LT_INVEST",          is_balance_sheet=True, description="Long-term Investments (Cross Holdings)"),
    CIQField("minority_interests",  "IQ_MINORITY_INTEREST",  is_balance_sheet=True, description="Minority Interests"),
]

# ──────────────────────────────────────────────────────────────
# Market / Pricing items (typically current/LTM only)
# ──────────────────────────────────────────────────────────────
MARKET_FIELDS = [
    CIQField("stock_price",          "IQ_CLOSEPRICE",        description="Closing Stock Price"),
    CIQField("mv_equity",            "IQ_MARKETCAP",         description="Market Capitalization"),
    CIQField("reporting_currency",   "IQ_FILING_CURRENCY",   description="Filing/Reporting Currency"),
    CIQField("primary_exchange",     "IQ_EXCHANGE",          description="Primary Exchange Listing"),
    CIQField("effective_tax_rate_ciq", "IQ_EFFECT_TAX_RATE", description="Effective Tax Rate (CIQ, in %)"),
]

# ──────────────────────────────────────────────────────────────
# Cash Flow Statement items
# ──────────────────────────────────────────────────────────────
# Note: net_debt_issued, change_in_noncash_wc, noncash_wc removed —
# not used in Damodaran's valuation model (he uses Sales/Capital for reinvestment)
CASHFLOW_FIELDS: list[CIQField] = []

# ──────────────────────────────────────────────────────────────
# Option / Equity Compensation items (current only)
# ──────────────────────────────────────────────────────────────
OPTION_FIELDS = [
    CIQField("options_outstanding",     "IQ_OPTIONS_END_OS",       description="Options Outstanding (End of Period)"),
    CIQField("options_avg_strike",      "IQ_OPTIONS_STRIKE_PRICE_OS", description="Weighted Avg Strike Price (Outstanding)"),
    CIQField("options_avg_maturity",    "IQ_OPTIONS_AVG_LIFE",     description="Weighted Avg Remaining Life"),
]

# ──────────────────────────────────────────────────────────────
# Operating Lease Commitments (footnote data, year 1-5 + beyond)
# ──────────────────────────────────────────────────────────────
LEASE_COMMITMENT_FIELDS = [
    CIQField("lease_commitment_yr1", "IQ_OL_COMM_CY",        description="Op Lease Commitment Year 1"),
    CIQField("lease_commitment_yr2", "IQ_OL_COMM_CY1",       description="Op Lease Commitment Year 2"),
    CIQField("lease_commitment_yr3", "IQ_OL_COMM_CY2",       description="Op Lease Commitment Year 3"),
    CIQField("lease_commitment_yr4", "IQ_OL_COMM_CY3",       description="Op Lease Commitment Year 4"),
    CIQField("lease_commitment_yr5", "IQ_OL_COMM_CY4",       description="Op Lease Commitment Year 5"),
    CIQField("lease_commitment_beyond", "IQ_OL_COMM_NEXT_FIVE", description="Op Lease Commitment Beyond Year 5"),
]


# ──────────────────────────────────────────────────────────────
# Period Date fields (for computing quarters since 10-K)
# ──────────────────────────────────────────────────────────────
PERIOD_DATE_FIELDS = [
    CIQField("period_date_annual",    "IQ_PERIODDATE", description="10-K period end date (annual)"),
    CIQField("period_date_quarterly", "IQ_PERIODDATE", description="10-Q period end date (quarterly)"),
]


# All fields grouped for easy iteration
ALL_FIELDS = (
    INCOME_STATEMENT_FIELDS
    + BALANCE_SHEET_FIELDS
    + MARKET_FIELDS
    + CASHFLOW_FIELDS
    + OPTION_FIELDS
    + LEASE_COMMITMENT_FIELDS
    + PERIOD_DATE_FIELDS
)


def generate_ciq_formulas(
    ticker: str,
    years_back: int = 5,
    quarterly_back: int = 8,
    rd_years_back: int = 10,
) -> list[dict]:
    """
    Generate CIQ formula specifications for a given ticker.

    Returns a list of dicts, each with:
        {
            "variable": str,        # Data Dictionary name
            "mnemonic": str,        # CIQ mnemonic
            "period": str,          # e.g., "IQ_FY-0" or "IQ_FQ-0"
            "formula": str,         # Full Excel formula string
            "fiscal_year_offset": int,  # 0 = current, 1 = prior, etc.
        }

    Flow items (income/cashflow): fetched for FY-0 through FY-{years_back} + quarterly FQ-0..FQ-{quarterly_back-1}
    Balance sheet items: fetched for FY-0 through FY-{years_back}
    Market items: current only (no period)
    Option items: current only
    Lease commitments: current only
    R&D expense: fetched for up to rd_years_back years (default 10)
    """
    # Expense-type fields: wrap with ABS() so values are always positive (Damodaran convention)
    _EXPENSE_VARS = {"interest_expense", "capex", "d_a", "operating_lease_expense"}

    def _make_formula(var_name: str, mnemonic: str, period: str | None) -> str:
        if period:
            ciq_call = f'CIQ("{ticker}","{mnemonic}","{period}")'
        else:
            ciq_call = f'CIQ("{ticker}","{mnemonic}")'
        if var_name in _EXPENSE_VARS:
            return f"=ABS({ciq_call})"
        return f"={ciq_call}"

    formulas = []

    # Income statement + Cash flow: multi-year annual
    for field in INCOME_STATEMENT_FIELDS + CASHFLOW_FIELDS:
        # Use rd_years_back for R&D expense, years_back for everything else
        max_yr = rd_years_back if field.variable_name in ("r_and_d_expense", "r_and_d_expense_fn") else years_back
        for yr in range(max_yr + 1):
            period = f"IQ_FY-{yr}"
            formula = _make_formula(field.variable_name, field.mnemonic, period)
            formulas.append({
                "variable": field.variable_name,
                "mnemonic": field.mnemonic,
                "period": period,
                "formula": formula,
                "fiscal_year_offset": yr,
            })

    # Income statement: quarterly (for LTM computation)
    for field in INCOME_STATEMENT_FIELDS + CASHFLOW_FIELDS:
        for q in range(quarterly_back):
            period = f"IQ_FQ-{q}"
            formula = _make_formula(field.variable_name, field.mnemonic, period)
            formulas.append({
                "variable": field.variable_name,
                "mnemonic": field.mnemonic,
                "period": period,
                "formula": formula,
                "fiscal_year_offset": 0,
            })

    # Balance sheet: multi-year annual
    for field in BALANCE_SHEET_FIELDS:
        for yr in range(years_back + 1):
            period = f"IQ_FY-{yr}"
            formula = _make_formula(field.variable_name, field.mnemonic, period)
            formulas.append({
                "variable": field.variable_name,
                "mnemonic": field.mnemonic,
                "period": period,
                "formula": formula,
                "fiscal_year_offset": yr,
            })

    # Balance sheet: quarterly (FQ-0 for point-in-time LTM)
    for field in BALANCE_SHEET_FIELDS:
        period = "IQ_FQ-0"
        formula = _make_formula(field.variable_name, field.mnemonic, period)
        formulas.append({
            "variable": field.variable_name,
            "mnemonic": field.mnemonic,
            "period": period,
            "formula": formula,
            "fiscal_year_offset": 0,
        })

    # Market items: current only (no period or LTM)
    for field in MARKET_FIELDS:
        formula = _make_formula(field.variable_name, field.mnemonic, None)
        formulas.append({
            "variable": field.variable_name,
            "mnemonic": field.mnemonic,
            "period": "current",
            "formula": formula,
            "fiscal_year_offset": 0,
        })

    # Options: current only
    for field in OPTION_FIELDS:
        formula = _make_formula(field.variable_name, field.mnemonic, None)
        formulas.append({
            "variable": field.variable_name,
            "mnemonic": field.mnemonic,
            "period": "current",
            "formula": formula,
            "fiscal_year_offset": 0,
        })

    # Lease commitments: current only
    for field in LEASE_COMMITMENT_FIELDS:
        formula = _make_formula(field.variable_name, field.mnemonic, None)
        formulas.append({
            "variable": field.variable_name,
            "mnemonic": field.mnemonic,
            "period": "current",
            "formula": formula,
            "fiscal_year_offset": 0,
        })

    # Period dates: most recent annual (FY-0) and quarterly (FQ-0)
    formulas.append({
        "variable": "period_date_annual",
        "mnemonic": "IQ_PERIODDATE",
        "period": "IQ_FY-0",
        "formula": _make_formula("period_date_annual", "IQ_PERIODDATE", "IQ_FY-0"),
        "fiscal_year_offset": 0,
    })
    formulas.append({
        "variable": "period_date_quarterly",
        "mnemonic": "IQ_PERIODDATE",
        "period": "IQ_FQ-0",
        "formula": _make_formula("period_date_quarterly", "IQ_PERIODDATE", "IQ_FQ-0"),
        "fiscal_year_offset": 0,
    })

    return formulas
