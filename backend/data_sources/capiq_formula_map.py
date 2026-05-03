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
    # Optional 5th-arg currency override for =CIQ(...). E.g. "<FILING>" → return
    # the value converted to the filing (reporting) currency. Without this, CIQ
    # returns values in the listing currency for market-data items.
    currency_override: str | None = None


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
    CIQField("stock_price",            "IQ_CLOSEPRICE",      description="Closing Stock Price (listing currency)"),
    CIQField("mv_equity",              "IQ_MARKETCAP",       description="Market Capitalization (listing currency)"),
    # Reporting-currency variants — CIQ's 4th argument "REPORTED" converts the
    # market-data value to the company's filing currency. The 4th-arg scope token
    # is the universal S&P syntax (verified working against the live plugin).
    # "TRADED" (or blank) = trading/listing currency; "REPORTED" = filing currency.
    CIQField("stock_price_reporting",  "IQ_CLOSEPRICE", description="Closing Stock Price (reporting currency)",
             currency_override="REPORTED"),
    CIQField("mv_equity_reporting",    "IQ_MARKETCAP",  description="Market Capitalization (reporting currency)",
             currency_override="REPORTED"),
    CIQField("reporting_currency",     "IQ_FILING_CURRENCY", description="Filing/Reporting Currency"),
    CIQField("primary_exchange",       "IQ_EXCHANGE",        description="Primary Exchange Listing"),
    CIQField("effective_tax_rate_ciq", "IQ_EFFECT_TAX_RATE", description="Effective Tax Rate (CIQ, in %)"),
    # S&P issuer rating — when present, Cost of Capital auto-switches to the
    # actual_rating kd_approach and looks up the appropriate default spread.
    # Empty / NA / 0 → falls through to the industry / synthetic-rating path.
    CIQField("actual_rating",          "IQ_SP_ISSUER_RATING", description="S&P Issuer Credit Rating"),
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


# ──────────────────────────────────────────────────────────────
# Geographic Segment fields (top 10 by revenue, current fiscal year)
#
# CIQ mnemonic family:
#   IQ_GEO_SEG_NAME_ABS  — nth geographic segment name (rank in 9th arg)
#   IQ_GEO_SEG_REV_ABS   — nth geographic segment revenue
#
# "_ABS" suffix means absolute-sorted (largest first). 9th argument is the
# rank (1..10). Period = IQ_FY returns latest fiscal year.
#
# Companies vary: some report 4 segments, some 10+. Slots 5-10 often come
# back as zero-revenue corporate/unallocated labels; reader filters them.
# ──────────────────────────────────────────────────────────────
GEO_SEGMENT_RANKS = list(range(1, 11))

GEO_SEGMENT_FIELDS: list[CIQField] = []
for _rank in GEO_SEGMENT_RANKS:
    GEO_SEGMENT_FIELDS.append(
        CIQField(
            f"geo_seg_name_{_rank}",
            "IQ_GEO_SEG_NAME_ABS",
            description=f"Geographic segment #{_rank} name",
        )
    )
    GEO_SEGMENT_FIELDS.append(
        CIQField(
            f"geo_seg_rev_{_rank}",
            "IQ_GEO_SEG_REV_ABS",
            description=f"Geographic segment #{_rank} revenue",
        )
    )


# All fields grouped for easy iteration
ALL_FIELDS = (
    INCOME_STATEMENT_FIELDS
    + BALANCE_SHEET_FIELDS
    + MARKET_FIELDS
    + CASHFLOW_FIELDS
    + OPTION_FIELDS
    + LEASE_COMMITMENT_FIELDS
    + PERIOD_DATE_FIELDS
    + GEO_SEGMENT_FIELDS
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

    # Lookup table for currency overrides by variable name (populated below)
    _CCY_OVERRIDES: dict[str, str] = {
        f.variable_name: f.currency_override
        for f in ALL_FIELDS if f.currency_override
    }

    def _make_formula(var_name: str, mnemonic: str, period: str | None) -> str:
        # CIQ signature: =CIQ(identifier, mnemonic, [period_or_date], [currency_scope])
        # The 4th argument is the currency scope: "TRADED" (default, trading
        # currency) or "REPORTED" (filing/reporting currency). Verified against
        # the live S&P Capital IQ Excel plugin.
        ccy = _CCY_OVERRIDES.get(var_name)
        if ccy:
            per = period or ""
            ciq_call = f'CIQ("{ticker}","{mnemonic}","{per}","{ccy}")'
        elif period:
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
