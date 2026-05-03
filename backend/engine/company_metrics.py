"""
Compute the company's operating metrics for industry comparison.

Damodaran's *Ginzu* valuation methodology treats R&D as a capital asset
and operating leases as debt. Both adjustments materially change Invested
Capital and EBIT. When the Module-1 adjusted figures are available, this
module uses the Damodaran-canonical formulas:

    Adjusted Invested Capital
      = BV_equity + BV_debt
      + PV(operating leases)        # Damodaran lease capitalization
      + Research asset              # Damodaran R&D capitalization
      − Cash
      − Cross-holdings

    Adjusted EBIT
      = Raw EBIT
      + (current R&D − R&D amortization)
      + (lease expense − lease depreciation)

    NOPAT = Adjusted EBIT × (1 − marginal tax rate)
    ROIC  = NOPAT / Adjusted IC
    S/C   = Revenues / Adjusted IC

When the adjustments aren't available (bare-bones test data, or a firm
with no R&D and no operating leases), falls back to the unadjusted book
formulas.

Marginal Sales-to-Capital uses year-over-year Δ rather than levels.
"""

from __future__ import annotations

from engine.data_dictionary import (
    AdjustedFinancials,
    CompanyMetrics,
    CostOfCapital,
    RawFinancials,
)


def _unadjusted_ic(f: RawFinancials) -> float | None:
    bve = f.bv_equity
    bvd = f.bv_debt
    if bve is None or bvd is None:
        return None
    cash = f.cash_and_marketable_securities or 0.0
    return bve + bvd - cash


def _adjusted_ic(f: RawFinancials, adjusted: AdjustedFinancials | None) -> float | None:
    """Damodaran IC = book IC + research asset + PV(leases) − cross-holdings.

    Returns None if we lack the basics. If `adjusted` is None we just return
    the unadjusted book IC (same as the original simple formula).
    """
    base = _unadjusted_ic(f)
    if base is None:
        return None
    cross_h = f.cross_holdings or 0.0
    if adjusted is None:
        return base - cross_h
    research = adjusted.value_of_research_asset or 0.0
    lease_pv = adjusted.pv_of_operating_leases or 0.0
    return base + research + lease_pv - cross_h


def compute_company_metrics(
    financials: list[RawFinancials],
    cost_of_capital: CostOfCapital | None = None,
    adjusted: AdjustedFinancials | None = None,
    tax_rate: float = 0.21,
    years_since_10k: float = 1.0,
) -> CompanyMetrics:
    """Compute the Damodaran-style company metrics.

    When ``adjusted`` is provided, ROIC and Sales-to-Capital use Damodaran's
    adjusted EBIT + adjusted IC. Otherwise they fall back to the simple
    book formulas so the function still works for test data and for
    companies with no R&D / no operating leases.
    """
    if not financials:
        return CompanyMetrics()

    fin0 = financials[0]
    fin1 = financials[1] if len(financials) > 1 else None

    # 1. Revenue growth (most recent)
    revenue_growth = None
    if fin1 and fin1.revenues and fin1.revenues != 0:
        if years_since_10k > 0:
            revenue_growth = (fin0.revenues / fin1.revenues) ** (1 / years_since_10k) - 1
        else:
            revenue_growth = (fin0.revenues / fin1.revenues) - 1

    # 2. Pre-tax operating margin.
    # Use adjusted EBIT when available — matches Damodaran's "post-R&D-
    # capitalization" margin that feeds into target-margin comparisons.
    ebit_for_margin = adjusted.adjusted_ebit if (adjusted and adjusted.adjusted_ebit is not None) else fin0.ebit
    pretax_margin = None
    if fin0.revenues and fin0.revenues != 0:
        pretax_margin = ebit_for_margin / fin0.revenues

    # Invested capital — Damodaran adjusted (book IC + research asset + PV(leases) − cross-holdings)
    ic0 = _adjusted_ic(fin0, adjusted)
    ic1 = _adjusted_ic(fin1, adjusted) if fin1 else None
    # Fallbacks for comparability with legacy consumers
    ic0_book = _unadjusted_ic(fin0)

    # 3. Sales-to-capital ratio
    sales_to_cap = None
    if ic0 and ic0 != 0:
        sales_to_cap = fin0.revenues / ic0
    elif ic0_book and ic0_book != 0:
        sales_to_cap = fin0.revenues / ic0_book

    # 4. Marginal sales-to-capital — ΔRev / ΔIC over the latest year
    marginal_stc = None
    if fin1 and ic0 is not None and ic1 is not None and (ic0 - ic1) != 0:
        marginal_stc = (fin0.revenues - fin1.revenues) / (ic0 - ic1)

    # 5. ROIC — NOPAT / IC using adjusted EBIT and adjusted IC when possible
    roic = None
    ebit_for_roic = ebit_for_margin
    if ic0 and ic0 != 0:
        roic = ebit_for_roic * (1 - tax_rate) / ic0

    # 7. Cost of capital (WACC) — passthrough from Module 2
    wacc = cost_of_capital.wacc if cost_of_capital else None

    return CompanyMetrics(
        revenue_growth=revenue_growth,
        pretax_operating_margin=pretax_margin,
        sales_to_capital=sales_to_cap,
        marginal_sales_to_capital=marginal_stc,
        roic=roic,
        std_dev_stock=None,  # Only populated from industry reference data
        cost_of_capital=wacc,
    )
