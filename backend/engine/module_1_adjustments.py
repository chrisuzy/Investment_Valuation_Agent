"""
Module 1: Financial Adjustments — R&D Capitalization + Operating Lease Conversion.

Capitalizes R&D expenses as an intangible asset and converts operating leases
to debt equivalents, producing adjusted EBIT, net income, book equity, and debt.
"""

from __future__ import annotations

from .data_dictionary import RawFinancials, AdjustmentInputs, AdjustedFinancials


def capitalize_r_and_d(
    r_and_d_expense_current: float,
    r_and_d_expense_past: list[float],
    amortization_period_n: int,
) -> tuple[float, float, float]:
    """
    Capitalize R&D: treat current expense as a capital investment, amortize past expenses.

    Args:
        r_and_d_expense_current: Current year R&D spend
        r_and_d_expense_past: Past R&D expenses, index 0 = year t-1, index 1 = year t-2, etc.
        amortization_period_n: Number of years to amortize over

    Returns:
        (unamortized_r_and_d, amortization_r_and_d, value_of_research_asset)
    """
    n = amortization_period_n
    if n <= 0 or not r_and_d_expense_past:
        return 0.0, 0.0, r_and_d_expense_current

    unamortized = 0.0
    amortization = 0.0

    for t_idx, rd_expense in enumerate(r_and_d_expense_past):
        t = t_idx + 1  # t=1 is most recent past year
        if t > n:
            break
        # Unamortized portion: fraction of life remaining = (n - t) / n
        unamortized += rd_expense * (n - t) / n
        # Amortization: straight-line = expense / n
        amortization += rd_expense / n

    value_of_research_asset = r_and_d_expense_current + unamortized
    return unamortized, amortization, value_of_research_asset


def capitalize_operating_leases(
    operating_lease_commitments: list[float],
    cost_of_debt_pretax: float,
) -> tuple[float, int, int]:
    """
    Compute PV of operating lease commitments using Damodaran's method.

    The "beyond year 5" amount is split into an annuity over n_additional years,
    where n_additional = round(beyond / avg(yr1..yr5)).

    Args:
        operating_lease_commitments: [yr1, yr2, yr3, yr4, yr5, beyond5] (6 elements).
        cost_of_debt_pretax: Pre-tax cost of debt used as discount rate.

    Returns:
        (pv, n_additional, total_years)
    """
    if not operating_lease_commitments or cost_of_debt_pretax <= 0:
        return 0.0, 0, 0

    pv = 0.0
    n_yr = min(len(operating_lease_commitments), 5)

    # Years 1-5: discount each individually
    for i in range(n_yr):
        pv += operating_lease_commitments[i] / (1 + cost_of_debt_pretax) ** (i + 1)

    # Beyond year 5: annuity method (Ginzu rule — n_additional may be 0)
    n_additional = 0
    if len(operating_lease_commitments) > 5 and operating_lease_commitments[5] > 0:
        beyond = operating_lease_commitments[5]
        avg_yr1_5 = sum(operating_lease_commitments[:5]) / max(n_yr, 1)
        if avg_yr1_5 > 0:
            n_additional = round(beyond / avg_yr1_5)
        else:
            n_additional = 1
        if n_additional > 0:
            annual_annuity = beyond / n_additional
            for j in range(n_additional):
                year = 6 + j
                pv += annual_annuity / (1 + cost_of_debt_pretax) ** year
        else:
            # Edge case: beyond < avg(yr1..5) → treat as single payment in year 6
            pv += beyond / (1 + cost_of_debt_pretax) ** 6

    # total_years uses max(n_additional, 0) explicitly — when n_additional = 0,
    # the lease spans 5 explicit years + 1 lump-in-yr6, so the Ginzu rule keeps
    # denominator = 5 + n_additional = 5 for straight-line depreciation.
    total_years = n_yr + n_additional
    return pv, n_additional, total_years


def compute_adjustments(
    raw: RawFinancials,
    adj_inputs: AdjustmentInputs,
    cost_of_debt_pretax: float,
) -> AdjustedFinancials:
    """
    Compute all Module 1 adjustments: R&D capitalization + operating lease conversion.

    Args:
        raw: Current year raw financial data.
        adj_inputs: R&D and operating lease input data.
        cost_of_debt_pretax: Pre-tax cost of debt (for discounting lease commitments).

    Returns:
        AdjustedFinancials with all adjusted values.
    """
    # Start with raw values
    adjusted_ebit = raw.ebit
    adjusted_net_income = raw.net_income
    adjusted_bv_equity = raw.bv_equity
    # MV of debt fallback: if no market value fetched (bond-pricing not implemented),
    # use book value as the Damodaran-style proxy. This matches Ginzu's default behavior
    # for firms without actively-traded debt where bond repricing isn't material.
    adjusted_mv_debt = raw.mv_debt if raw.mv_debt is not None else raw.bv_debt

    unamortized_r_and_d = 0.0
    amortization_r_and_d = 0.0
    value_of_research_asset = 0.0
    pv_of_operating_leases = 0.0

    # --- R&D Capitalization ---
    if adj_inputs.has_r_and_d:
        unamortized_r_and_d, amortization_r_and_d, value_of_research_asset = (
            capitalize_r_and_d(
                adj_inputs.r_and_d_expense_current,
                adj_inputs.r_and_d_expense_past,
                adj_inputs.amortization_period_n,
            )
        )

        # Adjusted EBIT = EBIT + current R&D - amortization of past R&D
        adjusted_ebit = adjusted_ebit + adj_inputs.r_and_d_expense_current - amortization_r_and_d

        # Adjusted Net Income = Net Income + current R&D - amortization
        if adjusted_net_income is not None:
            adjusted_net_income = adjusted_net_income + adj_inputs.r_and_d_expense_current - amortization_r_and_d

        # Adjusted BV Equity = BV Equity + value of research asset
        if adjusted_bv_equity is not None:
            adjusted_bv_equity = adjusted_bv_equity + value_of_research_asset

    # --- Operating Lease Capitalization (Damodaran method) ---
    depreciation_on_lease_asset = 0.0
    lease_adjustment_to_ebit = 0.0
    lease_years_total = 0
    lease_n_additional_years = 0

    if adj_inputs.has_operating_leases:
        pv_of_operating_leases, lease_n_additional_years, lease_years_total = (
            capitalize_operating_leases(
                adj_inputs.operating_lease_commitments,
                cost_of_debt_pretax,
            )
        )

        # Adjusted MV Debt = MV Debt + PV of operating leases
        if adjusted_mv_debt is not None:
            adjusted_mv_debt = adjusted_mv_debt + pv_of_operating_leases
        else:
            adjusted_mv_debt = pv_of_operating_leases

        # Damodaran: depreciation = PV / total_lease_years (straight-line)
        if lease_years_total > 0:
            depreciation_on_lease_asset = pv_of_operating_leases / lease_years_total

        # Adjustment to Operating Earnings = Lease Expense - Depreciation on Lease Asset
        lease_adjustment_to_ebit = (
            adj_inputs.operating_lease_expense_current - depreciation_on_lease_asset
        )
        adjusted_ebit = adjusted_ebit + lease_adjustment_to_ebit

    return AdjustedFinancials(
        unamortized_r_and_d=unamortized_r_and_d,
        amortization_r_and_d=amortization_r_and_d,
        value_of_research_asset=value_of_research_asset,
        pv_of_operating_leases=pv_of_operating_leases,
        depreciation_on_lease_asset=depreciation_on_lease_asset,
        lease_adjustment_to_ebit=lease_adjustment_to_ebit,
        lease_years_total=lease_years_total,
        lease_n_additional_years=lease_n_additional_years,
        adjusted_ebit=adjusted_ebit,
        adjusted_net_income=adjusted_net_income,
        adjusted_bv_equity=adjusted_bv_equity,
        adjusted_mv_debt=adjusted_mv_debt,
    )
