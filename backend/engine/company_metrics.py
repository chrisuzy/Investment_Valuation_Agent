"""
Compute 7 company metrics for comparison against industry averages.

Metrics:
1. Revenue growth (most recent year)
2. Pre-tax operating margin (EBIT / Revenues)
3. Sales to capital ratio (Revenues / Invested Capital)
4. Marginal sales to capital (ΔRevenues / ΔInvested Capital)
5. ROIC — EBIT(1-t) / Invested Capital
6. Std deviation in stock prices (from industry data if not computed)
7. Cost of capital (WACC from Module 2)
"""

from __future__ import annotations

from engine.data_dictionary import (
    CompanyMetrics,
    RawFinancials,
    CostOfCapital,
)


def compute_company_metrics(
    financials: list[RawFinancials],
    cost_of_capital: CostOfCapital | None = None,
    tax_rate: float = 0.21,
    years_since_10k: float = 1.0,
) -> CompanyMetrics:
    """Compute 7 company metrics from raw financial data."""
    if not financials:
        return CompanyMetrics()

    fin0 = financials[0]
    fin1 = financials[1] if len(financials) > 1 else None

    # 1. Revenue growth
    revenue_growth = None
    if fin1 and fin1.revenues and fin1.revenues != 0:
        if years_since_10k > 0:
            revenue_growth = (fin0.revenues / fin1.revenues) ** (1 / years_since_10k) - 1
        else:
            revenue_growth = (fin0.revenues / fin1.revenues) - 1

    # 2. Pre-tax operating margin
    pretax_margin = None
    if fin0.revenues and fin0.revenues != 0:
        pretax_margin = fin0.ebit / fin0.revenues

    # Helper: invested capital = BV Equity + BV Debt - Cash
    def invested_capital(f: RawFinancials) -> float | None:
        bve = f.bv_equity
        bvd = f.bv_debt
        cash = f.cash_and_marketable_securities
        if bve is not None and bvd is not None:
            return bve + bvd - (cash or 0)
        return None

    ic0 = invested_capital(fin0)
    ic1 = invested_capital(fin1) if fin1 else None

    # 3. Sales to capital ratio
    sales_to_cap = None
    if ic0 and ic0 != 0:
        sales_to_cap = fin0.revenues / ic0

    # 4. Marginal sales to capital
    marginal_stc = None
    if fin1 and ic0 is not None and ic1 is not None and (ic0 - ic1) != 0:
        marginal_stc = (fin0.revenues - fin1.revenues) / (ic0 - ic1)

    # 5. ROIC
    roic = None
    if ic0 and ic0 != 0:
        roic = fin0.ebit * (1 - tax_rate) / ic0

    # 7. Cost of capital (WACC)
    wacc = cost_of_capital.wacc if cost_of_capital else None

    return CompanyMetrics(
        revenue_growth=revenue_growth,
        pretax_operating_margin=pretax_margin,
        sales_to_capital=sales_to_cap,
        marginal_sales_to_capital=marginal_stc,
        roic=roic,
        std_dev_stock=None,  # Populated from industry data if available
        cost_of_capital=wacc,
    )
