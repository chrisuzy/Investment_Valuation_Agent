"""
Module 5: Relative Valuation (Multiples) — intrinsic vs market multiples.

Computes fundamentally justified PE, PBV, EV/EBITDA, EV/Sales multiples
and compares them with actual market multiples.
"""

from __future__ import annotations

from .data_dictionary import (
    AdjustedFinancials,
    RawFinancials,
    CashFlowMetrics,
    CostOfCapital,
    ValuationAssumptions,
    MultiplesResult,
    MacroInputs,
)


def compute_multiples(
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    cf_metrics: CashFlowMetrics,
    cost_of_capital: CostOfCapital,
    assumptions: ValuationAssumptions,
    macro: MacroInputs,
) -> MultiplesResult:
    """
    Compute intrinsic and market multiples for relative valuation comparison.

    Args:
        adjusted: Module 1 output.
        raw: Current year raw financials.
        cf_metrics: Module 3 output.
        cost_of_capital: Module 2 output.
        assumptions: Valuation assumptions.
        macro: Macro inputs.

    Returns:
        MultiplesResult with intrinsic and market multiples.
    """
    stable_growth = assumptions.stable_growth_rate
    if stable_growth is None:
        stable_growth = macro.risk_free_rate
    stable_growth = min(stable_growth, macro.risk_free_rate)

    ke = cost_of_capital.cost_of_equity
    wacc = cost_of_capital.wacc
    tax_rate = macro.tax_rate_marginal

    rir_firm = cf_metrics.rir_firm
    rir_equity = cf_metrics.rir_equity

    # --- Equity multiples ---
    pe_intrinsic = None
    pbv_intrinsic = None

    if ke > stable_growth:
        # Payout ratio = 1 - reinvestment rate (equity)
        payout = 1 - (rir_equity or 0.0)
        pe_intrinsic = payout / (ke - stable_growth)

        # PBV = (ROE - g) / (Ke - g)
        roe = cf_metrics.roe
        if roe is not None:
            pbv_intrinsic = (roe - stable_growth) / (ke - stable_growth)

    # --- Firm value multiples ---
    ev_sales_intrinsic = None
    ev_ebitda_intrinsic = None

    if wacc > stable_growth:
        # EV/Sales = after_tax_margin * (1 - rir) / (WACC - g)
        after_tax_margin = (adjusted.adjusted_ebit * (1 - tax_rate)) / raw.revenues if raw.revenues > 0 else 0.0
        rir = rir_firm or 0.0
        ev_sales_intrinsic = after_tax_margin * (1 - rir) / (wacc - stable_growth)

        # EV/EBITDA: more complex
        ebitda = raw.ebitda
        if ebitda and ebitda > 0:
            da_ratio = (raw.d_a or 0.0) / ebitda
            reinv_ratio = cf_metrics.reinvestment_firm / ebitda if ebitda > 0 else 0.0
            ev_ebitda_intrinsic = (
                (1 - tax_rate) - da_ratio * (1 - tax_rate) - reinv_ratio
            ) / (wacc - stable_growth)

    # --- Market multiples (actual) ---
    pe_market = None
    adj_ni = adjusted.adjusted_net_income or raw.net_income
    if adj_ni and adj_ni > 0 and raw.mv_equity:
        pe_market = raw.mv_equity / adj_ni

    return MultiplesResult(
        pe_ratio_intrinsic=pe_intrinsic,
        pbv_ratio_intrinsic=pbv_intrinsic,
        ev_ebitda_intrinsic=ev_ebitda_intrinsic,
        ev_sales_intrinsic=ev_sales_intrinsic,
        pe_ratio_market=pe_market,
    )
