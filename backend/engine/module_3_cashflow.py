"""
Module 3: Cash Flow & Growth — FCFF, FCFE, ROIC, ROE, reinvestment, fundamental growth rates.

Takes Module 1 adjusted financials + raw data to compute reinvestment, free cash flows,
return metrics, and expected fundamental growth rates.
"""

from __future__ import annotations

from .data_dictionary import (
    AdjustedFinancials,
    RawFinancials,
    AdjustmentInputs,
    CostOfCapital,
    CashFlowMetrics,
    MacroInputs,
)


def _safe_mean(values: list[float | None]) -> float | None:
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def _compute_historical_series(
    history: list[RawFinancials],
    tax_rate: float,
    r_and_d_asset_current: float,
) -> dict:
    """Compute 5-year historical diagnostic series for three-story examination.

    Convention:
      NOPAT_i        = raw_EBIT_i × (1 - tax_rate_effective)
      IC_i           = bv_equity_i + R&D_asset_proxy + bv_debt_i - cash_i
      ROIC_i         = NOPAT_i / IC_{i+1}   (prior-year IC denominator, standard)
      S_C_i          = Revenue_i / IC_i      (current-year IC, matches Damodaran)
      Margin_i       = EBIT_i / Revenue_i    (pre-tax)
      RevGrowth_i    = Revenue_i / Revenue_{i+1} - 1

    Uses current-year R&D asset as a proxy for historical IC (simplification:
    the folder's per-year R&D capitalization would require re-running M1 five
    times; since this is diagnostic display only, we use the current value).
    Any component missing → that year's entry is None.

    The DISPLAY window is 5 years, but we look one extra year back (to i+1=5)
    for the ROIC prior-year-IC denominator and the revenue-growth prior
    revenue, so FY-4 ROIC / RevGrowth compute cleanly when the CIQ template
    returned at least 6 years of annual history (it returns 11 by default).
    """
    n_display = min(len(history), 5)
    n_total = min(len(history), 6)  # display window + 1 lookback slot
    roic: list[float | None] = [None] * n_display
    s_c: list[float | None] = [None] * n_display
    margin: list[float | None] = [None] * n_display
    rev_growth: list[float | None] = [None] * n_display

    # Per-year IC for every year we can compute one (display window + lookback)
    ic_current: list[float | None] = []
    for i in range(n_total):
        f = history[i]
        bv_eq = f.bv_equity
        bv_debt = f.bv_debt
        cash = f.cash_and_marketable_securities
        if bv_eq is not None and bv_debt is not None and cash is not None:
            ic_current.append(bv_eq + r_and_d_asset_current + bv_debt - cash)
        else:
            ic_current.append(None)

    for i in range(n_display):
        f = history[i]
        ebit_i = f.ebit
        rev_i = f.revenues

        # Margin
        if ebit_i is not None and rev_i not in (None, 0):
            margin[i] = ebit_i / rev_i

        # S/C — current-year IC
        if rev_i is not None and ic_current[i] not in (None, 0):
            s_c[i] = rev_i / ic_current[i]

        # ROIC — prior-year IC (i+1 in a most-recent-first list); reaches
        # one year beyond the display window into ic_current[n_display].
        if i + 1 < n_total and ebit_i is not None and ic_current[i + 1] not in (None, 0):
            nopat_i = ebit_i * (1 - tax_rate)
            roic[i] = nopat_i / ic_current[i + 1]

        # Revenue growth — from prior year (also reaches one year beyond)
        if i + 1 < len(history):
            rev_prev = history[i + 1].revenues
            if rev_i is not None and rev_prev not in (None, 0):
                rev_growth[i] = rev_i / rev_prev - 1

    return {
        "historical_roic_by_year": roic,
        "historical_s_c_by_year": s_c,
        "historical_margin_by_year": margin,
        "historical_revenue_growth_by_year": rev_growth,
        "historical_roic_avg_3yr": _safe_mean(roic[:3]),
        "historical_roic_avg_5yr": _safe_mean(roic),
        "historical_s_c_avg_3yr": _safe_mean(s_c[:3]),
        "historical_s_c_avg_5yr": _safe_mean(s_c),
        "historical_margin_avg_3yr": _safe_mean(margin[:3]),
        "historical_margin_avg_5yr": _safe_mean(margin),
        "historical_revenue_growth_avg_3yr": _safe_mean(rev_growth[:3]),
        "historical_revenue_growth_avg_5yr": _safe_mean(rev_growth),
    }


def compute_cashflow_and_growth(
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    adj_inputs: AdjustmentInputs,
    cost_of_capital: CostOfCapital,
    raw_prior_year: RawFinancials | None = None,
    macro: MacroInputs | None = None,
    raw_financials_history: list[RawFinancials] | None = None,
) -> CashFlowMetrics:
    """
    Compute reinvestment, free cash flows, return metrics, and growth rates.

    Args:
        adjusted: Module 1 output for current year.
        raw: Current year raw financials.
        adj_inputs: R&D/lease adjustment inputs.
        cost_of_capital: Module 2 output.
        raw_prior_year: Prior year raw financials (for invested capital calculation).
        macro: Macro inputs (for direct tax rate access). If omitted, reverse-engineer
               tax from cost_of_debt_pretax / cost_of_debt_aftertax (fragile fallback).

    Returns:
        CashFlowMetrics with all computed values.
    """
    # Damodaran convention for base-year NOPAT / ROIC / reinvestment-rate:
    # use the EFFECTIVE tax rate (what the firm actually paid) so historical
    # ROIC matches reality. Marginal is reserved for DCF projections
    # (Module 4) where it represents the tax the firm would pay on
    # incremental future earnings. Fall back to marginal if effective
    # isn't available, then to reverse-engineering from Kd.
    if macro is not None and macro.tax_rate_effective is not None:
        tax_rate = macro.tax_rate_effective
    elif macro is not None:
        tax_rate = macro.tax_rate_marginal
    elif cost_of_capital.cost_of_debt_pretax > 0:
        tax_rate = 1 - (cost_of_capital.cost_of_debt_aftertax / cost_of_capital.cost_of_debt_pretax)
    else:
        tax_rate = 0.0

    # --- Adjusted CapEx and D&A ---
    # CapEx is adjusted by adding back current R&D (treated as capital investment)
    # D&A is adjusted by adding R&D amortization + lease depreciation (Ginzu F34)
    capex = raw.capex or 0.0
    d_a = raw.d_a or 0.0

    adjusted_capex = capex + adj_inputs.r_and_d_expense_current
    adjusted_d_a = d_a + adjusted.amortization_r_and_d + adjusted.depreciation_on_lease_asset

    # --- Reinvestment ---
    change_in_noncash_wc = raw.change_in_noncash_wc or 0.0
    reinvestment_firm = adjusted_capex - adjusted_d_a + change_in_noncash_wc

    net_debt_issued = raw.net_debt_issued or 0.0
    reinvestment_equity = reinvestment_firm - net_debt_issued

    # --- Free Cash Flows ---
    nopat = adjusted.adjusted_ebit * (1 - tax_rate)
    fcff = nopat - reinvestment_firm

    adjusted_net_income = adjusted.adjusted_net_income or 0.0
    fcfe = adjusted_net_income - reinvestment_equity

    # --- Return Metrics ---
    roic = None
    roe = None
    adjusted_invested_capital = None

    if raw_prior_year is not None:
        # Invested capital = BV Equity + BV Debt - Cash (beginning of period = prior year end)
        prior_bv_equity = raw_prior_year.bv_equity or 0.0
        prior_bv_debt = raw_prior_year.bv_debt or 0.0
        prior_cash = raw_prior_year.cash_and_marketable_securities or 0.0

        # Adjust prior BV equity for R&D research asset
        # For simplicity, use current R&D asset value as proxy
        prior_adjusted_bv_equity = prior_bv_equity + adjusted.value_of_research_asset

        adjusted_invested_capital = prior_adjusted_bv_equity + prior_bv_debt - prior_cash

        if adjusted_invested_capital > 0:
            roic = nopat / adjusted_invested_capital

        if prior_adjusted_bv_equity > 0:
            roe = adjusted_net_income / prior_adjusted_bv_equity

    # --- Reinvestment Rates ---
    rir_firm = reinvestment_firm / nopat if nopat > 0 else None
    rir_equity = reinvestment_equity / adjusted_net_income if adjusted_net_income > 0 else None

    # --- Expected Growth Rates ---
    expected_growth_ebit = roic * rir_firm if (roic is not None and rir_firm is not None) else None
    expected_growth_ni = roe * rir_equity if (roe is not None and rir_equity is not None) else None

    # --- Historical-series diagnostics for three-story examination ---
    historical: dict = {}
    if raw_financials_history:
        historical = _compute_historical_series(
            raw_financials_history,
            tax_rate=tax_rate,
            r_and_d_asset_current=adjusted.value_of_research_asset or 0.0,
        )

    return CashFlowMetrics(
        adjusted_capex=adjusted_capex,
        adjusted_d_a=adjusted_d_a,
        reinvestment_firm=reinvestment_firm,
        reinvestment_equity=reinvestment_equity,
        fcff=fcff,
        fcfe=fcfe,
        adjusted_invested_capital=adjusted_invested_capital,
        roic=roic,
        roe=roe,
        rir_firm=rir_firm,
        rir_equity=rir_equity,
        expected_growth_ebit=expected_growth_ebit,
        expected_growth_ni=expected_growth_ni,
        historical_roic_by_year=historical.get("historical_roic_by_year", []),
        historical_s_c_by_year=historical.get("historical_s_c_by_year", []),
        historical_margin_by_year=historical.get("historical_margin_by_year", []),
        historical_revenue_growth_by_year=historical.get("historical_revenue_growth_by_year", []),
        historical_roic_avg_3yr=historical.get("historical_roic_avg_3yr"),
        historical_roic_avg_5yr=historical.get("historical_roic_avg_5yr"),
        historical_s_c_avg_3yr=historical.get("historical_s_c_avg_3yr"),
        historical_s_c_avg_5yr=historical.get("historical_s_c_avg_5yr"),
        historical_margin_avg_3yr=historical.get("historical_margin_avg_3yr"),
        historical_margin_avg_5yr=historical.get("historical_margin_avg_5yr"),
        historical_revenue_growth_avg_3yr=historical.get("historical_revenue_growth_avg_3yr"),
        historical_revenue_growth_avg_5yr=historical.get("historical_revenue_growth_avg_5yr"),
    )
