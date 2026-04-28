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


def compute_cashflow_and_growth(
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    adj_inputs: AdjustmentInputs,
    cost_of_capital: CostOfCapital,
    raw_prior_year: RawFinancials | None = None,
    macro: MacroInputs | None = None,
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
    if macro is not None:
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
    )
