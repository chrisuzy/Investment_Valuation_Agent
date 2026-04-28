"""
Module 4: Intrinsic Valuation (DCF) — Ginzu-faithful implementation.

Projects FCFF through high-growth and transition periods per ginzu_spec_v2.md §6,
computes Gordon terminal value, discounts at a year-by-year cumulative factor,
applies failure probability to value_as_going_concern BEFORE the equity bridge,
then bridges to equity using the full Stage 9 formula:

    equity = value_of_operating_assets - debt - minority + cash_usable + cross_holdings

Key mechanics that differ from the previous implementation:
  - Operating Income = Revenue × Margin (NOT compounded EBIT)
  - Margin path linearly converges from operating_margin_next_year to target over K years
  - Tax path: flat effective for years 1–5, linear convergence to marginal for 6–10
  - Dynamic NOL carryforward with NOPAT = EBIT − max(0, EBIT−NOL_start) × rate
  - Reinvestment = ΔRevenue / Sales-to-Capital with lag (0–3 years)
  - WACC path: flat for years 1–5, linear convergence to terminal for 6–10
  - Cumulative discount factors built year-by-year
  - Terminal WACC default = riskfree + ERP (proxy for Damodaran mature_market_erp)
  - Terminal ROIC default = terminal WACC (no excess returns)
  - Failure overlay applied to value_as_going_concern BEFORE bridge
  - Failure tie-to "B" uses (bv_equity + bv_debt) × proceeds_pct
  - Trapped cash adjustment to cash_usable
"""

from __future__ import annotations

from .data_dictionary import (
    CashFlowMetrics,
    CostOfCapital,
    AdjustedFinancials,
    RawFinancials,
    ValuationAssumptions,
    DCFResult,
    MacroInputs,
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _revenue_growth_path(
    g_year_1: float,
    g_years_2_5: float,
    g_terminal: float,
    high_growth_years: int,
    total_years: int,
) -> list[float]:
    """Revenue growth path: year 1 = g_year_1, years 2..K = g_years_2_5 (flat),
    years K+1..n = linear convergence from g_years_2_5 to g_terminal."""
    path = []
    for t in range(1, total_years + 1):
        if t == 1:
            path.append(g_year_1)
        elif t <= high_growth_years:
            path.append(g_years_2_5)
        else:
            transition = total_years - high_growth_years
            if transition <= 0:
                path.append(g_terminal)
            else:
                progress = (t - high_growth_years) / transition
                path.append(g_years_2_5 - (g_years_2_5 - g_terminal) * progress)
    return path


def _margin_path(
    margin_y1: float,
    margin_target: float,
    K: int,
    total_years: int,
) -> list[float]:
    """Margin path: year 1 = margin_y1; years 2..K = linear converge to margin_target;
    years K+1..n = margin_target (flat at target)."""
    path = []
    K = max(1, K)
    for t in range(1, total_years + 1):
        if t == 1:
            path.append(margin_y1)
        elif t <= K:
            path.append(margin_target - (margin_target - margin_y1) * (K - t) / K)
        else:
            path.append(margin_target)
    return path


def _tax_path(
    t_effective: float,
    t_marginal: float,
    override_convergence: bool,
    high_growth_years: int,
    total_years: int,
) -> tuple[list[float], float]:
    """Tax path: years 1..high_growth_years = effective (flat);
    years high_growth_years+1..total_years = linear converge to terminal;
    terminal rate = effective (if override) else marginal.
    Returns (path, terminal_rate)."""
    terminal = t_effective if override_convergence else t_marginal
    transition = total_years - high_growth_years
    step = (terminal - t_effective) / transition if transition > 0 else 0.0
    path = []
    for t in range(1, total_years + 1):
        if t <= high_growth_years:
            path.append(t_effective)
        else:
            path.append(path[-1] + step)
    return path, terminal


def _wacc_path(
    wacc_initial: float,
    wacc_terminal: float,
    high_growth_years: int,
    total_years: int,
) -> list[float]:
    """WACC path: flat at initial for years 1..high_growth_years;
    linear converge to terminal for years high_growth_years+1..total_years."""
    transition = total_years - high_growth_years
    step = (wacc_terminal - wacc_initial) / transition if transition > 0 else 0.0
    path = []
    for t in range(1, total_years + 1):
        if t <= high_growth_years:
            path.append(wacc_initial)
        else:
            path.append(path[-1] + step)
    return path


def _apply_nol_and_tax(
    ebit_path: list[float],
    tax_path: list[float],
    nol_initial: float,
) -> tuple[list[float], list[float]]:
    """Dynamic NOL carryforward. Returns (nopat_path, nol_end_path).

    For each year t:
      - If EBIT_t < 0: NOL grows (nol_end = nol_start − ebit_t, since ebit negative).
        NOPAT = ebit_t (loss, no tax).
      - Else: taxable = max(0, ebit_t − nol_start);
              tax = taxable × rate_t;
              nol_end = max(0, nol_start − ebit_t);
              NOPAT = ebit_t − tax.
    """
    nopat_path = []
    nol_path = []
    nol_end = nol_initial
    for t_idx, ebit_t in enumerate(ebit_path):
        rate = tax_path[t_idx]
        nol_start = nol_end
        if ebit_t < 0:
            nol_end = nol_start - ebit_t  # ebit negative so nol grows
            nopat_path.append(ebit_t)
        else:
            taxable = max(0.0, ebit_t - nol_start)
            tax_paid = taxable * rate
            nol_end = max(0.0, nol_start - ebit_t)
            nopat_path.append(ebit_t - tax_paid)
        nol_path.append(nol_end)
    return nopat_path, nol_path


def _reinvestment_path(
    extended_revenue: list[float],
    sc_high: float,
    sc_stable: float,
    lag: int,
    high_growth_years: int,
    total_years: int,
) -> list[float]:
    """Sales-to-Capital reinvestment with lag ∈ {0, 1, 2, 3}.

    extended_revenue[0] = base_year, [1]..[total_years] = projected, and the
    list is padded 3 years beyond total_years using terminal growth so the
    lag-shifted ΔRevenue can always be computed.

    For year t (1-indexed):
      S/C_t = sc_high if t ≤ high_growth_years else sc_stable
      reinvestment_t = (rev[t + lag] − rev[t + lag − 1]) / S/C_t
    """
    reinv = []
    for t in range(1, total_years + 1):
        sc = sc_high if t <= high_growth_years else sc_stable
        if sc is None or sc == 0:
            reinv.append(0.0)
            continue
        idx_a = t + lag
        idx_b = t + lag - 1
        if idx_a >= len(extended_revenue) or idx_b < 0:
            reinv.append(0.0)
            continue
        reinv.append((extended_revenue[idx_a] - extended_revenue[idx_b]) / sc)
    return reinv


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def compute_dcf(
    cf_metrics: CashFlowMetrics,
    cost_of_capital: CostOfCapital,
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    assumptions: ValuationAssumptions,
    macro: MacroInputs,
) -> DCFResult:
    # --- Resolve structural parameters ---
    n = assumptions.projection_years or 10
    high_growth_years = assumptions.high_growth_years or 5
    K = assumptions.margin_convergence_year or 5

    # --- Terminal growth dispatch: override_perpetuity → override_riskfree → RF ---
    if assumptions.override_growth_perpetuity and assumptions.growth_perpetuity_rate is not None:
        g_terminal = assumptions.growth_perpetuity_rate
    elif assumptions.override_riskfree and assumptions.riskfree_after_yr10 is not None:
        g_terminal = assumptions.riskfree_after_yr10
    else:
        g_terminal = macro.risk_free_rate

    # Enforce terminal growth ≤ riskfree (unless explicit override_perpetuity allows exceeding)
    if not assumptions.override_growth_perpetuity:
        g_terminal = min(g_terminal, macro.risk_free_rate)

    # Also surface stable_growth_rate field if set — it's an alternative way to force terminal growth
    if assumptions.stable_growth_rate is not None and not assumptions.override_growth_perpetuity:
        g_terminal = assumptions.stable_growth_rate
        g_terminal = min(g_terminal, macro.risk_free_rate)

    # --- Revenue growth inputs ---
    g_year_1 = assumptions.revenue_growth_next_year
    if g_year_1 is None:
        g_year_1 = cf_metrics.expected_growth_ebit or g_terminal
    g_years_2_5 = assumptions.revenue_growth_years_2_5
    if g_years_2_5 is None:
        # Ginzu default: B27 = B25 (years 2-5 grow at year-1 rate)
        g_years_2_5 = g_year_1

    # --- Margin inputs ---
    margin_y1 = assumptions.operating_margin_next_year
    if margin_y1 is None:
        margin_y1 = (adjusted.adjusted_ebit / raw.revenues) if raw.revenues else 0.0
    margin_target = assumptions.target_operating_margin
    if margin_target is None:
        margin_target = margin_y1  # no convergence if no target

    # --- Tax inputs ---
    t_marginal = macro.tax_rate_marginal
    t_effective = macro.tax_rate_effective if macro.tax_rate_effective is not None else t_marginal

    # --- Sales-to-Capital inputs ---
    sc_high = assumptions.sales_to_capital_high
    sc_stable = assumptions.sales_to_capital_stable
    if sc_high is None:
        sc_high = 2.5  # Damodaran default
    if sc_stable is None:
        sc_stable = sc_high

    # --- Reinvestment lag ---
    lag = assumptions.reinvestment_lag_years if assumptions.override_reinvestment_lag else 1
    lag = max(0, min(3, lag))

    # --- WACC: initial + terminal ---
    wacc_initial = cost_of_capital.wacc
    if assumptions.cost_of_capital_stable_override is not None:
        wacc_terminal = assumptions.cost_of_capital_stable_override
    elif assumptions.override_riskfree and assumptions.riskfree_after_yr10 is not None:
        # Ginzu default when RF override active: RF_new + mature_market_erp (≈ ERP)
        wacc_terminal = assumptions.riskfree_after_yr10 + macro.equity_risk_premium
    else:
        # Default terminal WACC: riskfree + mature market ERP (beta=1 proxy)
        wacc_terminal = macro.risk_free_rate + macro.equity_risk_premium

    # --- Terminal ROIC ---
    if assumptions.roic_stable_override is not None:
        roic_terminal = assumptions.roic_stable_override
    else:
        roic_terminal = wacc_terminal  # Default: no excess returns

    # --- NOL ---
    nol_initial = assumptions.nol_amount if assumptions.override_nol else 0.0

    # --- Paths ---
    g_path = _revenue_growth_path(g_year_1, g_years_2_5, g_terminal, high_growth_years, n)
    margin_path_vals = _margin_path(margin_y1, margin_target, K, n)
    tax_path_vals, tax_terminal = _tax_path(
        t_effective, t_marginal, assumptions.override_tax_convergence, high_growth_years, n
    )
    wacc_path_vals = _wacc_path(wacc_initial, wacc_terminal, high_growth_years, n)

    # --- Revenue projections (base + years 1..n + padding for lag) ---
    rev_base = raw.revenues or 0.0
    revenue_projections = []
    rev_prev = rev_base
    for g in g_path:
        rev_t = rev_prev * (1 + g)
        revenue_projections.append(rev_t)
        rev_prev = rev_t

    # Extended revenue (for reinvestment lag edge cases at year 9 and 10)
    extended_rev = [rev_base] + revenue_projections
    for _ in range(3):  # pad 3 years past year 10 using terminal growth
        extended_rev.append(extended_rev[-1] * (1 + g_terminal))

    # --- EBIT = Revenue × Margin ---
    ebit_projections = [revenue_projections[i] * margin_path_vals[i] for i in range(n)]

    # --- NOPAT with dynamic NOL ---
    nopat_projections, nol_projections = _apply_nol_and_tax(ebit_projections, tax_path_vals, nol_initial)

    # --- Reinvestment ---
    reinvestment_projections = _reinvestment_path(
        extended_rev, sc_high, sc_stable, lag, high_growth_years, n
    )

    # --- FCFF ---
    fcff_projections = [nopat_projections[i] - reinvestment_projections[i] for i in range(n)]

    # --- Terminal year ---
    rev_terminal = extended_rev[n] * (1 + g_terminal)  # rev[11]
    ebit_terminal = rev_terminal * margin_target
    nopat_terminal = ebit_terminal * (1 - tax_terminal)
    rir_terminal = g_terminal / roic_terminal if roic_terminal > 0 else 0.0
    reinvestment_terminal = rir_terminal * nopat_terminal if g_terminal > 0 else 0.0
    fcff_terminal = nopat_terminal - reinvestment_terminal

    # --- Terminal Value (Gordon) ---
    if wacc_terminal > g_terminal:
        terminal_value_firm = fcff_terminal / (wacc_terminal - g_terminal)
    else:
        terminal_value_firm = 0.0

    # --- Cumulative discount factors (year-by-year product) ---
    cumulative_df = []
    df_running = 1.0
    for wacc_t in wacc_path_vals:
        df_running = df_running / (1 + wacc_t)
        cumulative_df.append(df_running)

    # --- PV ---
    pv_fcff = [fcff_projections[i] * cumulative_df[i] for i in range(n)]
    pv_terminal = terminal_value_firm * cumulative_df[-1] if cumulative_df else 0.0
    pv_cash_flows_sum = sum(pv_fcff)
    value_as_going_concern = pv_cash_flows_sum + pv_terminal

    # --- Invested capital + ROIC path ---
    # IC_base = Adjusted BV Equity (includes R&D asset from M1) + BV Debt − cash + lease PV
    # Note: adjusted_bv_equity already = raw.bv_equity + value_of_research_asset
    ic_base = (
        (adjusted.adjusted_bv_equity if adjusted.adjusted_bv_equity is not None else (raw.bv_equity or 0.0))
        + (raw.bv_debt or 0.0)
        - (raw.cash_and_marketable_securities or 0.0)
        + (adjusted.pv_of_operating_leases or 0.0)
    )
    ic_path = [ic_base]
    roic_path = []
    for t_idx in range(n):
        ic_prev = ic_path[-1]
        roic_path.append(nopat_projections[t_idx] / ic_prev if ic_prev > 0 else 0.0)
        ic_path.append(ic_prev + reinvestment_projections[t_idx])

    # --- Failure overlay (BEFORE equity bridge, per Ginzu B40→B43) ---
    p_failure = assumptions.failure_probability
    if p_failure > 0:
        if assumptions.failure_tie_to == "B":
            bv_eq = raw.bv_equity or 0.0
            bv_debt = raw.bv_debt or 0.0
            distress_value = (bv_eq + bv_debt) * assumptions.distress_proceeds_pct
        else:
            distress_value = value_as_going_concern * assumptions.distress_proceeds_pct
        value_of_operating_assets = (
            value_as_going_concern * (1 - p_failure) + distress_value * p_failure
        )
    else:
        value_of_operating_assets = value_as_going_concern

    # --- Equity bridge ---
    debt_total = adjusted.adjusted_mv_debt if adjusted.adjusted_mv_debt is not None else (raw.bv_debt or 0.0)
    minority = raw.minority_interests or 0.0
    cross = raw.cross_holdings or 0.0
    cash = raw.cash_and_marketable_securities or 0.0

    # Trapped cash adjustment
    if assumptions.override_trapped_cash and assumptions.trapped_cash_amount > 0:
        cash_usable = cash - assumptions.trapped_cash_amount * (
            t_marginal - assumptions.trapped_cash_tax_rate
        )
    else:
        cash_usable = cash

    value_of_equity = (
        value_of_operating_assets
        - debt_total
        - minority
        + cash_usable
        + cross
    )

    # --- Per-share ---
    shares = raw.shares_outstanding or 1.0
    value_per_share = value_of_equity / shares

    return DCFResult(
        revenue_projections=revenue_projections,
        ebit_projections=ebit_projections,
        fcff_projections=fcff_projections,
        reinvestment_projections=reinvestment_projections,
        discount_factors=cumulative_df,
        pv_fcff=pv_fcff,
        terminal_value_firm=terminal_value_firm,
        pv_terminal_value=pv_terminal,
        pv_cash_flows_sum=pv_cash_flows_sum,
        value_of_operating_assets=value_of_operating_assets,
        value_of_equity=value_of_equity,
        value_per_share_pre_options=value_per_share,
    )
