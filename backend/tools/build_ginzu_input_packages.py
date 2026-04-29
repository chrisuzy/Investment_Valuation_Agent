"""
Build Ginzu input packages for the comparison experiment.

Given TEST_DATA/TEST_<TICKER>.xlsx, produce a Markdown file at
`docs/experiments/ginzu_inputs_<TICKER>.md` that lists:

  A. Every Ginzu "Input sheet" cell coordinate + label + value to paste in.
  B. R&D converter inputs (if company has R&D).
  C. Operating lease converter inputs (if company has leases).
  D. A table of Ginzu output cells for the user to fill in after recalc.

Run:
  cd backend && source .venv/bin/activate
  python tools/build_ginzu_input_packages.py            # all 4 companies
  python tools/build_ginzu_input_packages.py MSFT       # one company
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tools.read_ciq_template import read_ciq_template
from data_sources.damodaran_store import DamodaranStore
from data_sources.industry_mapper import IndustryMapper
from engine.ltm_calculator import compute_ltm_financials
from engine.data_dictionary import RawFinancials


COMPANIES = {
    # ticker → metadata (name, country, industry-US, industry-global)
    "MSFT":   {
        "company_name": "Microsoft Corporation",
        "country":      "United States",
        "industry_us":  "Software (System & Application)",
        "industry_glb": "Software (System & Application)",
        "ciq_ticker":   "NasdaqGS:MSFT",
    },
    "BABA":   {
        "company_name": "Alibaba Group Holding Limited",
        "country":      "China",
        "industry_us":  "Retail (General)",
        "industry_glb": "Retail (General)",
        "ciq_ticker":   "NYSE:BABA",
    },
    "TSLA":   {
        "company_name": "Tesla, Inc.",
        "country":      "United States",
        "industry_us":  "Auto & Truck",
        "industry_glb": "Auto & Truck",
        "ciq_ticker":   "NasdaqGS:TSLA",
    },
    "LENOVO": {
        "company_name": "Lenovo Group Limited",
        "country":      "Hong Kong",
        "industry_us":  "Computers/Peripherals",
        "industry_glb": "Computers/Peripherals",
        "ciq_ticker":   "SEHK:992",
    },
}

# Default valuation assumptions (user will usually want to tune these;
# we set sensible defaults that match our backend)
DEFAULT_ASSUMPTIONS = {
    "revenue_growth_next_year":    0.10,
    "operating_margin_next_year":  None,  # filled from current margin
    "revenue_growth_years_2_5":    0.08,
    "target_operating_margin":     None,  # filled from industry
    "margin_convergence_year":     5,
    "sales_to_capital_high":       2.0,
    "sales_to_capital_stable":     2.0,
    "stable_wacc_override":        0.085,
    "stable_roic_override":        0.12,
    "failure_probability":         0.0,
    "failure_tie_to":              "V",
    "distress_proceeds_pct":       0.5,
    "reinvestment_lag_override":   True,
    "reinvestment_lag_years":      1,
}


# ───────────────────────────────────────────────────────────────────────────
# Ginzu cell schema — exact coordinates for every Input sheet field we control
# ───────────────────────────────────────────────────────────────────────────

# Each entry: (cell, label for user, value-or-lambda, note)
INPUT_SHEET_SPEC = [
    # Header
    ("B3",  "Date of valuation",              lambda d: d["valuation_date"]),
    ("B4",  "Company name",                   lambda d: d["company_name"]),
    ("B7",  "Country of incorporation",       lambda d: d["country"]),
    ("B8",  "Industry (US)",                  lambda d: d["industry_us"]),
    ("B9",  "Industry (Global)",              lambda d: d["industry_global"]),

    # Base year financials — LTM (col B = this year, col C = last year)
    ("B10", "Revenues (LTM)",                 lambda d: d["rev_ltm"]),
    ("C10", "Revenues (prior FY)",            lambda d: d["rev_prior"]),
    ("D10", "Years since last 10K",           lambda d: d["years_since_10k"]),
    ("B11", "EBIT / Operating income (LTM)",  lambda d: d["ebit_ltm"]),
    ("C11", "EBIT / Operating income (prior FY)", lambda d: d["ebit_prior"]),
    ("B12", "Interest expense (LTM)",         lambda d: d["int_ltm"]),
    ("C12", "Interest expense (prior FY)",    lambda d: d["int_prior"]),
    ("B13", "Book value of equity",           lambda d: d["bv_eq"]),
    ("C13", "Book value of equity (prior)",   lambda d: d["bv_eq_prior"]),
    ("B14", "Book value of debt",             lambda d: d["bv_debt"]),
    ("C14", "Book value of debt (prior)",     lambda d: d["bv_debt_prior"]),
    ("B15", "Capitalize R&D?",                lambda d: d["has_rd"]),
    ("B16", "Have operating leases?",         lambda d: d["has_leases"]),
    ("B17", "Cash + marketable securities",   lambda d: d["cash"]),
    ("C17", "Cash + marketable (prior)",      lambda d: d["cash_prior"]),
    ("B18", "Cross holdings & non-op assets", lambda d: d["cross"]),
    ("C18", "Cross holdings (prior)",         lambda d: d["cross_prior"]),
    ("B19", "Minority interests",             lambda d: d["minority"]),
    ("C19", "Minority interests (prior)",     lambda d: d["minority_prior"]),
    ("B20", "Shares outstanding",             lambda d: d["shares"]),
    ("B21", "Current stock price",            lambda d: d["price"]),
    ("B22", "Effective tax rate",             lambda d: d["tax_eff"]),
    ("B23", "Marginal tax rate",              lambda d: d["tax_marg"]),

    # Value drivers
    ("B25", "Revenue growth rate — next year",        lambda d: d["rev_growth_yr1"]),
    ("B26", "Operating margin — next year",           lambda d: d["op_margin_yr1"]),
    ("B27", "CAGR revenue growth, years 2-5",         lambda d: d["rev_growth_2_5"]),
    ("B28", "Target pre-tax operating margin",        lambda d: d["target_margin"]),
    ("B29", "Year of margin convergence",             lambda d: d["conv_year"]),
    ("B30", "Sales/Capital ratio (years 1-5)",        lambda d: d["s_c_high"]),
    ("B31", "Sales/Capital ratio (years 6-10)",       lambda d: d["s_c_stable"]),

    # Market
    ("B33", "Risk-free rate",                         lambda d: d["rf"]),

    # Stable-period overrides (critical — Ginzu's defaults aren't stable for all firms)
    ("B56", "Override stable cost of capital? (Yes/No)", lambda _: "Yes"),
    ("B57", "Stable cost of capital (after yr 10)",      lambda d: d["stable_wacc"]),
    ("B59", "Override stable ROIC? (Yes/No)",            lambda _: "Yes"),
    ("B60", "Stable ROIC (after yr 10)",                 lambda d: d["stable_roic"]),

    # Failure
    ("B62", "Override zero failure? (Yes/No)",           lambda _: "No"),
    ("B64", "Tie proceeds to? (B/V)",                    lambda _: "V"),
    ("B65", "Distress proceeds as % of book/fair",       lambda _: 0.5),

    # Reinvestment lag
    ("B67", "Override reinvestment-lag=1? (Yes/No)",     lambda _: "Yes"),
    ("B68", "Lag years (0-3)",                           lambda d: d["reinv_lag"]),

    # Options (none for test companies)
    ("B36", "Have employee options outstanding?",        lambda _: "No"),
]


OUTPUT_CELLS_SPEC = [
    # (sheet, cell, label, module) — cell coordinates VERIFIED against
    # Ginzu_NVIDIA.xlsx by direct cell inspection.

    # ── M2 Cost of Capital ──
    ("Cost of capital worksheet", "B23", "Unlevered beta (β_u)",                 "M2"),
    ("Cost of capital worksheet", "C57", "Levered beta for equity (β_L)",        "M2"),
    ("Cost of capital worksheet", "B27", "Equity Risk Premium used",              "M2"),
    ("Cost of capital worksheet", "B37", "Pre-tax Cost of Debt",                  "M2"),
    ("Cost of capital worksheet", "B60", "Market Value of Equity",                "M2"),
    ("Cost of capital worksheet", "C60", "Market Value of Debt",                  "M2"),
    ("Cost of capital worksheet", "B61", "Weight of Equity",                      "M2"),
    ("Cost of capital worksheet", "C61", "Weight of Debt",                        "M2"),
    ("Cost of capital worksheet", "B62", "Cost of Equity",                        "M2"),
    ("Cost of capital worksheet", "C62", "After-tax Cost of Debt",                "M2"),
    ("Cost of capital worksheet", "E62", "WACC (blended, year 1)",                "M2"),
    ("Cost of capital worksheet", "B13", "Cost of capital — final (Approach 1)",  "M2"),

    # ── M1 R&D adjustment (R& D converter sheet) ──
    ("R& D converter", "B24", "Current-year R&D expense (input echo)",    "M1"),
    ("R& D converter", "D35", "Value of Research Asset (sum unamortized)", "M1"),
    ("R& D converter", "D37", "Amortization of research asset (this year)","M1"),
    ("R& D converter", "D39", "Adjustment to Operating Income (EBIT)",     "M1"),

    # ── M1 Lease adjustment (Operating lease converter sheet) ──
    #  (Only fill if B16 on Input sheet = "Yes")
    ("Operating lease converter", "F31", "Depreciation on operating-lease asset", "M1"),
    ("Operating lease converter", "F32", "Adjustment to Operating Expenses (EBIT)", "M1"),
    ("Operating lease converter", "F33", "Adjustment to Total Debt (PV of leases)", "M1"),

    # ── M4 DCF — year-by-year (Summary Sheet, rows per year) ──
    # Revenue/Margin/EBIT in rows 3-12 (year 1-10); FCFF in rows 16-25
    ("Summary Sheet", "B3",  "Revenue, Year 1",           "M4"),
    ("Summary Sheet", "B12", "Revenue, Year 10",          "M4"),
    ("Summary Sheet", "D3",  "Operating margin, Year 1",  "M4"),
    ("Summary Sheet", "D12", "Operating margin, Year 10", "M4"),
    ("Summary Sheet", "E3",  "Pre-tax EBIT, Year 1",      "M4"),
    ("Summary Sheet", "E12", "Pre-tax EBIT, Year 10",     "M4"),
    ("Summary Sheet", "F16", "FCFF, Year 1",              "M4"),
    ("Summary Sheet", "F25", "FCFF, Year 10",             "M4"),

    # ── M4 Terminal + PV (Valuation output) ──
    # NB: rows 32-34 in Ginzu are NVIDIA-specific (PV decomposed into Rest/AI/Auto).
    # For any other company, Ginzu will usually show a single "PV of cash flows"
    # row in C32 or collapse it into B40 directly. The Value as Going Concern (B40)
    # always equals the total PV (cashflows + terminal) so it's our safest anchor.
    ("Valuation output", "C30", "Cost of capital (terminal)",                      "M4"),
    ("Valuation output", "C31", "Cumulated discount factor (yr 10)",               "M4"),
    ("Valuation output", "B40", "Value as Going Concern (PV cash flows+terminal)", "M4"),

    # ── M7 Failure & Bridge (Valuation output) ──
    ("Valuation output", "B41", "Probability of failure",  "M7"),
    ("Valuation output", "B42", "Proceeds if firm fails",  "M7"),
    ("Valuation output", "B43", "Value of operating assets","M7"),
    ("Valuation output", "B44", "Subtract: Debt",          "M7"),
    ("Valuation output", "B45", "Subtract: Minority interests", "M7"),
    ("Valuation output", "B46", "Add: Cash",               "M7"),
    ("Valuation output", "B47", "Add: Non-operating assets","M7"),
    ("Valuation output", "B48", "Value of equity",         "M7"),
    ("Valuation output", "B49", "Subtract: Value of options", "M7"),
    ("Valuation output", "B50", "Value of equity in common stock", "M7"),
    ("Valuation output", "B51", "Number of shares",        "M7"),
    ("Valuation output", "B52", "Estimated value per share","M9"),
    ("Valuation output", "B53", "Market price",            "M9"),
    ("Valuation output", "B54", "Price as % of value",     "M9"),

    # ── M8 Options dilution (Option value sheet) ──
    ("Option value", "B28", "Value per option (BSM)",       "M8"),
    ("Option value", "B29", "Value of all options outstanding", "M8"),
]


# ───────────────────────────────────────────────────────────────────────────
# Data extraction
# ───────────────────────────────────────────────────────────────────────────

def extract_data_for_ticker(
    ticker: str, store: DamodaranStore, mapper: IndustryMapper
) -> dict[str, Any]:
    """Parse TEST_<ticker>.xlsx + lookups, build the value dict used by INPUT_SHEET_SPEC."""
    test_path = REPO_ROOT / "TEST_DATA" / f"TEST_{ticker}.xlsx"
    ciq = read_ciq_template(str(test_path))
    annual = ciq["annual"]
    current = ciq["current"]
    quarterly = ciq.get("quarterly", {})

    # Build RawFinancials for LTM. `current` only has market-data fields
    # (stock_price, mv_equity, options, lease commitments) — financial
    # statements + shares live in `annual[0]`.
    def _raw(yr_off: int, data: dict) -> RawFinancials:
        return RawFinancials(
            fiscal_year=2025 - yr_off,  # placeholder; LTM calc doesn't care
            revenues=float(data.get("revenues") or 0),
            ebit=float(data.get("ebit") or 0),
            ebitda=data.get("ebitda"),
            net_income=data.get("net_income"),
            interest_expense=data.get("interest_expense"),
            d_a=data.get("d_a"),
            capex=data.get("capex"),
            r_and_d_expense=data.get("r_and_d_expense"),
            earnings_before_tax=data.get("earnings_before_tax"),
            total_tax_expense=data.get("total_tax_expense"),
            cash_and_marketable_securities=data.get("cash_and_marketable_securities"),
            bv_equity=data.get("bv_equity"),
            bv_debt=data.get("bv_debt"),
            mv_equity=current.get("mv_equity") if yr_off == 0 else None,
            mv_debt=data.get("bv_debt"),
            shares_outstanding=data.get("shares_outstanding"),
            stock_price=current.get("stock_price") if yr_off == 0 else None,
            cross_holdings=data.get("cross_holdings"),
            minority_interests=data.get("minority_interests"),
        )

    # FY0 = annual[0] (statements + shares) + current (market-data overlays)
    fy0_data = {**annual.get(0, {}), **{k: v for k, v in current.items() if v is not None}}
    raw_fy0 = _raw(0, fy0_data)
    raw_prior = _raw(1, annual.get(1, {}))

    # Quarterly list for LTM rotation
    qlist = []
    for q in sorted(quarterly.keys()):
        qd = quarterly[q]
        qlist.append(RawFinancials(
            fiscal_year=q,
            revenues=float(qd.get("revenues") or 0),
            ebit=float(qd.get("ebit") or 0),
            ebitda=qd.get("ebitda"),
            net_income=qd.get("net_income"),
            interest_expense=qd.get("interest_expense"),
            d_a=qd.get("d_a"),
            capex=qd.get("capex"),
            r_and_d_expense=qd.get("r_and_d_expense"),
            earnings_before_tax=qd.get("earnings_before_tax"),
            total_tax_expense=qd.get("total_tax_expense"),
            cash_and_marketable_securities=qd.get("cash_and_marketable_securities"),
            bv_equity=qd.get("bv_equity"),
            bv_debt=qd.get("bv_debt"),
            shares_outstanding=qd.get("shares_outstanding"),
            stock_price=qd.get("stock_price"),
            cross_holdings=qd.get("cross_holdings"),
            minority_interests=qd.get("minority_interests"),
        ))

    quarters_since_10k = int(ciq.get("quarters_since_10k") or 0)
    ltm = compute_ltm_financials(raw_fy0, qlist, quarters_since_10k)

    # Country + industry lookup (hard-coded per test company — see COMPANIES)
    meta = COMPANIES.get(ticker, {})
    country = meta.get("country") or "United States"
    macro = store.lookup_country(country)
    industry_name = meta.get("industry_us") or "Semiconductor"
    ind = store.lookup_industry(industry_name, region="US")
    company_name = meta.get("company_name") or ticker

    # R&D:
    # - current-year R&D = LTM R&D = ltm.r_and_d_expense (or annual[0] if LTM==FY0)
    # - past R&D expenses = annual[1..10] most-recent-first for the R&D converter
    rd_current = float(ltm.r_and_d_expense or annual.get(0, {}).get("r_and_d_expense") or 0)
    rd_past: list[float] = []
    for yr in range(1, 11):
        v = annual.get(yr, {}).get("r_and_d_expense")
        if v is not None and v > 0:
            rd_past.append(float(v))
    has_rd = rd_current > 0 and len(rd_past) > 0

    # Lease commitments
    lease_commits = []
    for key in ("lease_commitment_yr1", "lease_commitment_yr2", "lease_commitment_yr3",
                "lease_commitment_yr4", "lease_commitment_yr5", "lease_commitment_beyond"):
        v = current.get(key)
        if v is not None and v > 0:
            lease_commits.append(float(v))
    has_leases = len(lease_commits) >= 2
    lease_expense = float(current.get("operating_lease_expense") or 0)

    # Derive sensible default assumptions from base-year data
    op_margin_current = ltm.ebit / ltm.revenues if ltm.revenues else 0
    target_margin = ind.pretax_operating_margin if (ind and ind.pretax_operating_margin) else max(op_margin_current * 0.9, 0.1)

    pd_annual = ciq.get("period_dates", {}).get("period_date_annual") or "2025-01-01"

    return {
        # Metadata
        "ticker": ticker,
        "company_name": company_name,
        "valuation_date": pd_annual,
        "country": country,
        "industry_us": meta.get("industry_us") or industry_name,
        "industry_global": meta.get("industry_glb") or industry_name,
        "years_since_10k": round(quarters_since_10k / 4.0, 2),

        # Base year flows
        "rev_ltm":  ltm.revenues,
        "rev_prior": raw_prior.revenues,
        "ebit_ltm": ltm.ebit,
        "ebit_prior": raw_prior.ebit,
        "int_ltm":  ltm.interest_expense or 0,
        "int_prior": raw_prior.interest_expense or 0,

        # Balance sheet
        "bv_eq":    ltm.bv_equity or 0,
        "bv_eq_prior": raw_prior.bv_equity or 0,
        "bv_debt":  ltm.bv_debt or 0,
        "bv_debt_prior": raw_prior.bv_debt or 0,
        "cash":     ltm.cash_and_marketable_securities or 0,
        "cash_prior": raw_prior.cash_and_marketable_securities or 0,
        "cross":    ltm.cross_holdings or 0,
        "cross_prior": raw_prior.cross_holdings or 0,
        "minority": ltm.minority_interests or 0,
        "minority_prior": raw_prior.minority_interests or 0,
        "shares":   ltm.shares_outstanding or 0,
        "price":    ltm.stock_price or 0,

        # Taxes
        "tax_eff":  ciq.get("effective_tax_rate") or 0.20,
        "tax_marg": macro.tax_rate_marginal if macro else 0.25,

        # R&D / lease toggles (string for Ginzu's Yes/No cells)
        "has_rd":     "Yes" if has_rd else "No",
        "has_leases": "Yes" if has_leases else "No",

        # Assumptions (Ginzu defaults that we also use)
        "rev_growth_yr1":   DEFAULT_ASSUMPTIONS["revenue_growth_next_year"],
        "op_margin_yr1":    op_margin_current,
        "rev_growth_2_5":   DEFAULT_ASSUMPTIONS["revenue_growth_years_2_5"],
        "target_margin":    target_margin,
        "conv_year":        DEFAULT_ASSUMPTIONS["margin_convergence_year"],
        "s_c_high":         ind.sales_to_capital if (ind and ind.sales_to_capital) else DEFAULT_ASSUMPTIONS["sales_to_capital_high"],
        "s_c_stable":       ind.sales_to_capital if (ind and ind.sales_to_capital) else DEFAULT_ASSUMPTIONS["sales_to_capital_stable"],
        "rf":               0.0425,   # consistent across all test uploads
        "stable_wacc":      DEFAULT_ASSUMPTIONS["stable_wacc_override"],
        "stable_roic":      DEFAULT_ASSUMPTIONS["stable_roic_override"],
        "reinv_lag":        DEFAULT_ASSUMPTIONS["reinvestment_lag_years"],

        # R&D past expenses (list, most recent first) + current-year LTM R&D + N
        "rd_past":      rd_past,
        "rd_current":   rd_current,
        "rd_amort_n":   5,

        # Lease data
        "lease_expense":  lease_expense,
        "lease_commits":  lease_commits,

        # ERP / CRP (for user info only — Ginzu derives from its country sheet)
        "erp":          macro.equity_risk_premium if macro else 0.0430,
        "crp":          macro.country_risk_premium if macro else 0.0,
    }


# ───────────────────────────────────────────────────────────────────────────
# Markdown package writer
# ───────────────────────────────────────────────────────────────────────────

def _fmt(v):
    """Format a value for the Ginzu-paste column."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, str):
        return v
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if abs(v) < 0.001 and v != 0:
            return f"{v:.6f}"
        if abs(v) >= 1000:
            return f"{v:,.2f}"
        return f"{v:.6f}" if abs(v) < 1 else f"{v:.4f}"
    return str(v)


def build_package(ticker: str, d: dict[str, Any]) -> str:
    """Produce the full Markdown package for one company."""
    lines = []
    lines.append(f"# Ginzu Input Package — {ticker} ({d['company_name']})")
    lines.append("")
    lines.append(f"**Generated:** 2026-04-29")
    lines.append(f"**Source:** `TEST_DATA/TEST_{ticker}.xlsx` (CIQ-resolved)")
    lines.append(f"**Ginzu workbook:** `knowledge_base/Ginzu_NVIDIA.xlsx`")
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    lines.append(f"1. Open `Ginzu_NVIDIA.xlsx`, immediately **Save As** `{ticker}_ginzu.xlsx`.")
    lines.append("2. In Excel, verify iterative calculation is ON: `File → Options → Formulas → Enable iterative calculation`.")
    lines.append("3. Go to the **Input sheet** and paste each value below into the listed cell.")
    lines.append("4. If 'Capitalize R&D? (B15)' is **Yes**, also fill Section B into the **R& D converter** sheet.")
    lines.append("5. If 'Have operating leases? (B16)' is **Yes**, also fill Section C into the **Operating lease converter** sheet.")
    lines.append("6. **IMPORTANT — NVIDIA-specific story rows (B44–B52):** leave them at their current NVIDIA values OR zero them out. They drive Ginzu's AI/Auto business-unit valuation which does not apply to this company. If left at NVIDIA values, the final VPS will include spurious AI/Auto PV; if zeroed, the final VPS will be lower than Ginzu's main DCF would compute for a non-NVIDIA firm.")
    lines.append("7. Let Excel recalculate (F9, or wait for auto-calc to settle if iteration is slow).")
    lines.append("8. Fill in Section D with Ginzu's computed values — these are the ground-truth numbers the comparison script will read.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Section A — Input sheet cells ──
    lines.append("## A. Input sheet cells")
    lines.append("")
    lines.append("| Cell | Label | Value to paste | Notes |")
    lines.append("|------|-------|----------------|-------|")
    for cell, label, getter, *rest in [(c, l, g) + tuple(r) for c, l, g, *r in [(*x, "") for x in INPUT_SHEET_SPEC]]:
        try:
            val = getter(d)
        except Exception as e:
            val = f"(error: {e})"
        note = rest[0] if rest else ""
        lines.append(f"| `{cell}` | {label} | `{_fmt(val)}` | {note} |")
    lines.append("")

    # ── Section B — R&D converter ──
    lines.append("## B. R&D converter inputs")
    lines.append("")
    if d["has_rd"] == "Yes":
        lines.append("Go to the **R& D converter** sheet in Ginzu.")
        lines.append("")
        lines.append("| Cell | Label | Value |")
        lines.append("|------|-------|-------|")
        lines.append(f"| `B6` | Amortization period N (years) | `{d['rd_amort_n']}` |")
        lines.append(f"| `B7` | Current year R&D expense (LTM) | `{_fmt(d['rd_current'])}` |")
        lines.append("")
        lines.append(f"Past-years R&D — {len(d['rd_past'])} years available from CIQ. Paste into cells B11, B12, B13… (most-recent year first):")
        lines.append("")
        lines.append("| Cell | Year offset | R&D expense |")
        lines.append("|------|-------------|-------------|")
        for i, rd in enumerate(d["rd_past"][:10]):
            lines.append(f"| `B{11+i}` | -{i+1} | `{_fmt(rd)}` |")
        if len(d["rd_past"]) < 5:
            lines.append("")
            lines.append(f"⚠ Only {len(d['rd_past'])} years of historical R&D. Ginzu's default N=5 amortization expects 5 years — ask user whether to (a) extend N to match available data, or (b) zero-fill the earliest years.")
    else:
        lines.append("_This company has no material R&D to capitalize. Leave Ginzu's B15 = 'No' and skip the R&D converter sheet._")
    lines.append("")

    # ── Section C — Leases ──
    lines.append("## C. Operating lease converter inputs")
    lines.append("")
    if d["has_leases"] == "Yes":
        lines.append("Go to the **Operating lease converter** sheet.")
        lines.append("")
        lines.append(f"- Current lease expense: `{_fmt(d['lease_expense'])}`")
        lines.append("")
        lines.append("Future commitments by year:")
        lines.append("")
        lines.append("| Year | Commitment |")
        lines.append("|------|-----------|")
        for i, c in enumerate(d["lease_commits"][:6]):
            label = f"Year {i+1}" if i < 5 else "Beyond year 5"
            lines.append(f"| {label} | `{_fmt(c)}` |")
    else:
        lines.append("_This company has no material operating-lease commitments (post-ASC 842 the balance-sheet lease liability is already in `bv_debt`). Leave Ginzu's B16 = 'No' and skip the lease converter sheet._")
    lines.append("")

    # ── Section D — Output cells to record ──
    lines.append("## D. Ginzu output cells — record after recalc")
    lines.append("")
    lines.append("Read each cell below from Ginzu **after** Excel has finished recalculating. Paste the value in the 'Ginzu value' column. Decimals please (e.g., `0.1179` not `11.79%`).")
    lines.append("")
    lines.append("| Module | Sheet | Cell | Metric | Ginzu value |")
    lines.append("|--------|-------|------|--------|-------------|")
    last_mod = None
    for sheet, cell, label, module in OUTPUT_CELLS_SPEC:
        if module != last_mod and last_mod is not None:
            lines.append("|     |     |     |     |     |")  # spacer row
        lines.append(f"| {module} | {sheet} | `{cell}` | {label} | _fill in_ |")
        last_mod = module
    lines.append("")
    lines.append("**M1** = R&D / lease capitalization adjustments. **M2** = Cost of capital. **M4** = DCF projection. **M7** = Failure + bridge. **M8** = Options. **M9** = Per-share.")
    lines.append("")

    # ── Extra context ──
    lines.append("## E. Context (for reference only — do not paste into Ginzu)")
    lines.append("")
    lines.append(f"- Ticker: `{ticker}`")
    lines.append(f"- Ginzu base ERP + CRP (from Damodaran country dataset): `{_fmt(d['erp']+d['crp'])}` ({_fmt(d['erp'])} base + {_fmt(d['crp'])} country)")
    lines.append(f"- Operating margin used (B26): LTM op-margin = `{_fmt(d['op_margin_yr1'])}`")
    lines.append(f"- Target operating margin used (B28): `{_fmt(d['target_margin'])}` (industry median if available, else 0.9× current)")
    lines.append("")
    lines.append("**Assumption parity.** Our backend uses the SAME assumptions as above when running the comparison. If you want to tune any assumption in Ginzu, tell Claude the new value and the backend run will be repeated with that value.")
    lines.append("")

    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────────

def main(tickers: list[str]):
    outdir = REPO_ROOT / "docs" / "experiments"
    outdir.mkdir(parents=True, exist_ok=True)

    dam_dir = REPO_ROOT / "knowledge_base" / "damodaran"
    store = DamodaranStore.from_directory(str(dam_dir))
    mapper = None  # unused for now

    for t in tickers:
        print(f"[{t}] extracting…")
        try:
            d = extract_data_for_ticker(t, store, mapper)
        except Exception as e:
            print(f"[{t}] FAILED: {e}")
            import traceback; traceback.print_exc()
            continue
        package = build_package(t, d)
        outpath = outdir / f"ginzu_inputs_{t}.md"
        outpath.write_text(package)
        print(f"[{t}] wrote {outpath.relative_to(REPO_ROOT)}  ({len(package.splitlines())} lines)")

    # Also write a top-level README for the experiment
    readme_path = outdir / "README.md"
    readme_path.write_text(
        "# Ginzu vs Backend — Comparison Experiment\n\n"
        "See `docs/superpowers/specs/2026-04-29-ginzu-vs-backend-comparison-design.md` for the full design.\n\n"
        "**Workflow:**\n\n"
        "1. **Phase 1 (done):** Claude prepared `ginzu_inputs_<TICKER>.md` for each test company.\n"
        "2. **Phase 2 (user, Windows):** Open `knowledge_base/Ginzu_NVIDIA.xlsx` on a Windows machine with Excel. For each ticker, Save-As `<TICKER>_ginzu.xlsx`, paste inputs per the package's Section A/B/C, let Excel recalc, fill in Section D with Ginzu's output values.\n"
        "3. **Phase 3 (Claude, after user returns):** Claude runs `backend/tools/run_ginzu_comparison.py <TICKER>` which reads the filled-in Section D and produces `ginzu_comparison_<TICKER>.md`.\n\n"
        "**Packages:**\n\n"
        + "\n".join(f"- [`ginzu_inputs_{t}.md`](./ginzu_inputs_{t}.md)" for t in tickers)
        + "\n"
    )
    print(f"[README] wrote {readme_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    args = sys.argv[1:] or list(COMPANIES.keys())
    main(args)
