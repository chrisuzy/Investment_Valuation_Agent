"""
Central Data Dictionary — all variable schemas for the valuation engine.

Every module imports from here. No module may introduce variables outside these models.
All rates/ratios are decimal (0.05 = 5%). All monetary values in reporting currency.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# A. Macro & Risk Variables (from Damodaran country-level datasets)
# ---------------------------------------------------------------------------

class MacroInputs(BaseModel):
    risk_free_rate: float = Field(description="10/20/30-year treasury yield")
    equity_risk_premium: float = Field(description="Equity Risk Premium (ERP)")
    country_risk_premium: float = Field(default=0.0, description="Country Risk Premium (CRP)")
    tax_rate_marginal: float = Field(description="Marginal/statutory corporate tax rate")
    tax_rate_effective: float | None = Field(default=None, description="Effective tax rate")
    default_spread: float | None = Field(default=None, description="Corporate debt default spread")


# ---------------------------------------------------------------------------
# B. Raw Financial Inputs (from Capital IQ, per fiscal year)
# ---------------------------------------------------------------------------

class RawFinancials(BaseModel):
    fiscal_year: int = Field(description="Fiscal year label")
    revenues: float = Field(description="Total revenue")
    ebit: float = Field(description="Operating income (EBIT)")
    ebitda: float | None = Field(default=None, description="EBITDA")
    net_income: float | None = Field(default=None, description="Net income")
    interest_expense: float | None = Field(default=None, description="Interest expense")
    capex: float | None = Field(default=None, description="Capital expenditures")
    d_a: float | None = Field(default=None, description="Depreciation & amortization")
    noncash_wc: float | None = Field(default=None, description="Non-cash working capital")
    change_in_noncash_wc: float | None = Field(default=None, description="Change in non-cash WC")
    net_debt_issued: float | None = Field(default=None, description="Net debt issuance")
    cash_and_marketable_securities: float | None = Field(default=None, description="Cash + marketable securities")
    bv_equity: float | None = Field(default=None, description="Book value of equity")
    bv_debt: float | None = Field(default=None, description="Book value of debt")
    mv_equity: float | None = Field(default=None, description="Market cap — reporting currency (for WACC math)")
    mv_equity_listing: float | None = Field(default=None, description="Market cap as-traded — listing currency (for display)")
    mv_debt: float | None = Field(default=None, description="Market value of debt (reporting currency)")
    shares_outstanding: float | None = Field(default=None, description="Primary shares outstanding")
    stock_price: float | None = Field(default=None, description="Current stock price — listing currency")
    stock_price_reporting: float | None = Field(default=None, description="Current stock price — reporting currency (for cross-ccy comparison)")
    cross_holdings: float | None = Field(default=None, description="Investments in affiliates / cross holdings")
    minority_interests: float | None = Field(default=None, description="Minority interests")
    r_and_d_expense: float | None = Field(default=None, description="R&D expense")
    earnings_before_tax: float | None = Field(default=None, description="Earnings before tax")
    total_tax_expense: float | None = Field(default=None, description="Income tax expense")


# ---------------------------------------------------------------------------
# C. Adjustment Inputs (R&D and Operating Leases)
# ---------------------------------------------------------------------------

class AdjustmentInputs(BaseModel):
    amortization_period_n: int = Field(default=5, description="R&D amortization period in years")
    r_and_d_expense_current: float = Field(default=0.0, description="Current year R&D expense")
    r_and_d_expense_past: list[float] = Field(default_factory=list, description="Past R&D expenses [t=1..n], most recent first")
    operating_lease_expense_current: float = Field(default=0.0, description="Current operating lease expense")
    operating_lease_commitments: list[float] = Field(default_factory=list, description="Future lease commitments by year")
    has_r_and_d: bool = Field(default=False, description="Whether to capitalize R&D")
    has_operating_leases: bool = Field(default=False, description="Whether to capitalize leases")


# ---------------------------------------------------------------------------
# D. Adjusted Financials (Module 1 output)
# ---------------------------------------------------------------------------

class AdjustedFinancials(BaseModel):
    unamortized_r_and_d: float = Field(default=0.0)
    amortization_r_and_d: float = Field(default=0.0)
    value_of_research_asset: float = Field(default=0.0)
    pv_of_operating_leases: float = Field(default=0.0)
    depreciation_on_lease_asset: float = Field(default=0.0, description="Straight-line: PV / total_lease_years")
    lease_adjustment_to_ebit: float = Field(default=0.0, description="= lease_expense - depreciation_on_lease")
    lease_years_total: int = Field(default=0, description="5 + n_additional_years")
    lease_n_additional_years: int = Field(default=0, description="Years embedded in beyond-year-5 figure")
    adjusted_ebit: float
    adjusted_net_income: float | None = Field(default=None)
    adjusted_bv_equity: float | None = Field(default=None)
    adjusted_mv_debt: float | None = Field(default=None)


# ---------------------------------------------------------------------------
# E. Industry Data (from Damodaran industry-level datasets)
# ---------------------------------------------------------------------------

class IndustryData(BaseModel):
    industry_name: str = Field(description="Damodaran industry classification")
    region: str = Field(default="US", description="US, Global, or China")
    beta_u: float = Field(description="Unlevered beta (industry average)")
    beta_u_corrected_for_cash: float | None = Field(default=None, description="Unlevered beta corrected for cash")
    industry_d_e_ratio: float | None = Field(default=None, description="Industry average D/E ratio")
    industry_effective_tax_rate: float | None = Field(default=None, description="Industry average effective tax rate")
    cost_of_equity: float | None = Field(default=None, description="Industry average cost of equity")
    cost_of_debt_pretax: float | None = Field(default=None, description="Industry average pre-tax cost of debt")
    wacc: float | None = Field(default=None, description="Industry average WACC")
    pretax_operating_margin: float | None = Field(default=None, description="Industry pre-tax operating margin")
    after_tax_operating_margin: float | None = Field(default=None, description="Industry after-tax operating margin")
    sales_to_capital: float | None = Field(default=None, description="Sales / Invested Capital ratio")
    revenue_growth: float | None = Field(default=None, description="Industry average revenue growth")
    std_dev_stock: float | None = Field(default=None, description="Industry average std deviation in stock prices")
    roic: float | None = Field(default=None, description="Industry average ROIC (from EVA dataset)")
    ev_ebitda: float | None = Field(default=None)
    ev_sales: float | None = Field(default=None)
    pe_ratio: float | None = Field(default=None)
    pbv_ratio: float | None = Field(default=None)


# ---------------------------------------------------------------------------
# F. Cost of Capital (Module 2 output)
# ---------------------------------------------------------------------------

class CostOfCapital(BaseModel):
    # Approach + branch labels (human-readable description of which paths were taken)
    approach_used: str = Field(default="detailed")
    beta_branch_used: str = Field(default="single_business_us")
    erp_branch_used: str = Field(default="country_of_incorporation")
    kd_branch_used: str = Field(default="industry_fallback")

    # Beta
    beta_u: float = Field(default=0.0, description="Unlevered beta")
    beta_l: float = Field(description="Levered beta")

    # MV debt decomposition
    mv_straight_debt: float = Field(default=0.0)
    mv_convertible_straight_part: float = Field(default=0.0)
    equity_in_convertible: float = Field(default=0.0)
    mv_leases: float = Field(default=0.0)
    mv_debt_total: float = Field(default=0.0, description="Sum: straight + convertible-straight-part + leases")
    book_debt: float = Field(default=0.0)
    d_e_ratio: float = Field(description="Company D/E ratio (market values)")

    # Equity + preferred market values
    mv_equity: float = Field(default=0.0)
    mv_preferred: float = Field(default=0.0)
    total_capital: float = Field(default=0.0, description="MV_E + MV_D + MV_P")

    # Component costs
    cost_of_equity: float
    cost_of_debt_pretax: float
    cost_of_debt_aftertax: float
    cost_of_preferred: float = Field(default=0.0)

    # Weights
    weight_equity: float
    weight_debt: float
    weight_preferred: float = Field(default=0.0)

    # Derived intermediates
    risk_free_rate: float = Field(default=0.0)
    equity_risk_premium: float = Field(default=0.0, description="Total ERP (base + country/region adjustment)")
    interest_coverage_ratio: float | None = Field(default=None, description="Populated when synthetic rating was used")
    synthetic_rating: str | None = Field(default=None, description="Populated when synthetic rating was used")

    # Final
    wacc: float

    # User-facing warnings about unsupported branch selections or data gaps
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# G. Cash Flow Metrics (Module 3 output)
# ---------------------------------------------------------------------------

class CashFlowMetrics(BaseModel):
    adjusted_capex: float
    adjusted_d_a: float
    reinvestment_firm: float
    reinvestment_equity: float | None = Field(default=None)
    fcff: float
    fcfe: float | None = Field(default=None)
    adjusted_invested_capital: float | None = Field(default=None)
    roic: float | None = Field(default=None)
    roe: float | None = Field(default=None)
    rir_firm: float | None = Field(default=None)
    rir_equity: float | None = Field(default=None)
    expected_growth_ebit: float | None = Field(default=None)
    expected_growth_ni: float | None = Field(default=None)

    # --- Historical-series diagnostics for three-story joint examination ---
    # Most-recent-first; e.g. historical_roic_by_year[0] = FY-0 ROIC.
    # Each list is up to 5 entries; None where data insufficient.
    historical_roic_by_year: list[float | None] = Field(default_factory=list)
    historical_s_c_by_year: list[float | None] = Field(default_factory=list)
    historical_margin_by_year: list[float | None] = Field(default_factory=list)
    historical_revenue_growth_by_year: list[float | None] = Field(default_factory=list)
    historical_roic_avg_3yr: float | None = Field(default=None)
    historical_roic_avg_5yr: float | None = Field(default=None)
    historical_s_c_avg_3yr: float | None = Field(default=None)
    historical_s_c_avg_5yr: float | None = Field(default=None)
    historical_margin_avg_3yr: float | None = Field(default=None)
    historical_margin_avg_5yr: float | None = Field(default=None)
    historical_revenue_growth_avg_3yr: float | None = Field(default=None)
    historical_revenue_growth_avg_5yr: float | None = Field(default=None)


class TaxHistory(BaseModel):
    """Five-year historical effective tax rate series (most-recent-first)."""
    yearly: list[float | None] = Field(default_factory=list)
    avg_3yr: float | None = Field(default=None)
    avg_5yr: float | None = Field(default=None)


# ---------------------------------------------------------------------------
# H. Valuation Assumptions (user-adjustable DCF inputs)
# ---------------------------------------------------------------------------

class BusinessSegment(BaseModel):
    """One business segment for multi-business beta calculation."""
    name: str = Field(description="Segment label")
    industry_us: str | None = Field(default=None, description="Matches a Damodaran US industry name")
    industry_global: str | None = Field(default=None, description="Matches a Damodaran Global industry name")
    revenue: float = Field(default=0.0, description="Segment revenue in reporting currency units")


class SegmentMember(BaseModel):
    """One country or region inside a composite segment decomposition."""
    to: str = Field(description="Damodaran country or region name")
    kind: str = Field(default="country", description="'country' | 'region'")
    weight: float = Field(default=0.0, description="Weight within the composite (0..1)")
    erp: float | None = Field(default=None, description="Resolved ERP for this member")


class SegmentResolution(BaseModel):
    """How a raw CIQ segment name was mapped to Damodaran's risk dataset."""
    raw_name: str
    mapped_to: str | None = Field(default=None, description="Canonical country/region, or None if unresolved")
    mapped_kind: str = Field(default="unresolved", description="'country' | 'region' | 'composite' | 'unresolved'")
    erp: float | None = Field(default=None, description="Blended ERP for this segment")
    members: list[SegmentMember] = Field(default_factory=list, description="Non-empty for composites")
    confidence: float = Field(default=0.0, description="0..1 — 1.0 = exact, 0.3 = weak default")
    source: str = Field(default="auto", description="'exact_country' | 'alias' | 'composite' | 'weak_default' | 'unresolved' | 'user'")
    note: str | None = Field(default=None)


class GeographicSegment(BaseModel):
    """One country/region revenue share for multi-country ERP calculation."""
    name: str = Field(description="Country or region label")
    revenue: float = Field(default=0.0, description="Revenue earned in this location")
    pct: float | None = Field(default=None, description="Percentage of total segment revenue")
    resolution: SegmentResolution | None = Field(default=None, description="Auto-resolved mapping to Damodaran")


class ConvertibleDebt(BaseModel):
    """Convertible debt inputs for bond-pricing decomposition."""
    book_value: float = Field(default=0.0)
    interest_expense: float = Field(default=0.0)
    maturity_years: float = Field(default=0.0)
    market_value: float = Field(default=0.0, description="Total market value including conversion option")


class PreferredStock(BaseModel):
    """Preferred stock inputs for WACC preferred component."""
    shares: float = Field(default=0.0)
    price_per_share: float = Field(default=0.0)
    dividend_per_share: float = Field(default=0.0)


class MethodologyChoices(BaseModel):
    """Full Ginzu methodology-choice selectors — matches `Cost of capital worksheet`
    exactly. Every branch Ginzu offers exists as an option; not every branch is
    implemented yet. Supported branches compute normally; unsupported branches
    raise a clear runtime warning rather than silently falling through."""

    # --- Cost of Capital top-level approach (Ginzu cell B11) ---
    cost_of_capital_approach: str = Field(
        default="detailed",
        description=(
            "'direct' = analyst types WACC (supported); "
            "'detailed' = build from CAPM (supported, default); "
            "'industry_average' = Damodaran industry WACC + RF adjustment (NOT IMPLEMENTED); "
            "'decile' = regional risk-quartile lookup (NOT IMPLEMENTED)."
        ),
    )
    wacc_direct_input: float | None = Field(default=None, description="Direct WACC when approach='direct'")

    # --- Unlevered beta (Ginzu cell B21) ---
    beta_approach: str = Field(
        default="single_business_us",
        description=(
            "'single_business_us' = Damodaran US industry β_u (supported, default); "
            "'single_business_global' = Damodaran Global industry β_u (supported via region); "
            "'multi_business_us' = EV-weighted across business segments, US industries (NOT IMPLEMENTED); "
            "'multi_business_global' = EV-weighted, Global industries (NOT IMPLEMENTED); "
            "'direct_levered' = analyst provides β_L directly, skipping unlever/relever (supported); "
            "'direct_unlevered' = analyst provides β_U directly, relever still runs (supported)."
        ),
    )
    beta_direct_input: float | None = Field(default=None)

    # --- Equity risk premium (Ginzu cell B25) ---
    erp_approach: str = Field(
        default="country_of_incorporation",
        description=(
            "'country_of_incorporation' = Damodaran country ERP (supported, default); "
            "'operating_countries' = revenue-weighted blend across countries firm earns in (NOT IMPLEMENTED); "
            "'operating_regions' = revenue-weighted blend across Damodaran regions (NOT IMPLEMENTED); "
            "'direct' = analyst types ERP directly (supported)."
        ),
    )
    erp_direct_input: float | None = Field(default=None)

    # --- Pre-tax cost of debt (Ginzu cell B33) ---
    kd_approach: str = Field(
        default="industry_fallback",
        description=(
            "'direct' = analyst types Kd_pretax directly (supported); "
            "'industry_fallback' = Damodaran industry avg Kd (supported, default); "
            "'synthetic_rating' = derive from interest coverage → rating → spread (NOT IMPLEMENTED, needs synthrating.xls); "
            "'actual_rating' = rating → spread lookup (NOT IMPLEMENTED, needs ratings.xls)."
        ),
    )
    kd_direct_input: float | None = Field(default=None)
    synthetic_rating_firm_type: str = Field(
        default="large",
        description="'large' | 'small' | 'financial' (used when kd_approach='synthetic_rating')",
    )
    actual_rating: str | None = Field(
        default=None,
        description="e.g. 'Aaa/AAA', 'A2/A', 'Ba2/BB' (used when kd_approach='actual_rating')",
    )

    # --- Decile approach (Approach 3) ---
    decile_region: str = Field(
        default="US",
        description="'Emerging' | 'Europe' | 'Global' | 'Japan' | 'US'",
    )
    decile_risk_group: str = Field(
        default="Median",
        description="'First Decile' | 'First Quartile' | 'Median' | 'Third Quartile' | 'Ninth Decile'",
    )

    # --- MV debt via bond pricing ---
    debt_maturity_years: float = Field(
        default=5.0,
        description="Weighted-average debt maturity used to bond-price MV of debt",
    )
    use_bond_pricing_for_debt: bool = Field(
        default=False,
        description="When True, price debt at market via bond formula. Default False = use book as MV.",
    )

    # --- WACC level shift (for sensitivity analysis) ---
    wacc_level_shift_bps: float = Field(
        default=0.0,
        description=(
            "Additive level shift applied to the computed WACC, in basis points. "
            "Used by the sensitivity tornado to flex the total cost of capital by "
            "a single knob without reaching into the underlying inputs. "
            "E.g. 50 = +0.50% applied to WACC."
        ),
    )

    # --- Segments for multi-business and multi-country variants ---
    business_segments: list[BusinessSegment] = Field(default_factory=list)
    geographic_segments: list[GeographicSegment] = Field(default_factory=list)

    # --- Convertible debt ---
    convertible_debt: ConvertibleDebt = Field(default_factory=ConvertibleDebt)
    has_convertible: bool = Field(default=False)

    # --- Preferred stock ---
    preferred_stock: PreferredStock = Field(default_factory=PreferredStock)
    has_preferred: bool = Field(default=False)

    # Warnings emitted by the backend when the analyst selects a not-implemented
    # branch — populated at run time, read by the frontend for UI feedback.
    unsupported_branch_warnings: list[str] = Field(default_factory=list)


class ValuationAssumptions(BaseModel):
    projection_years: int = Field(default=10, description="Total projection years (high growth + transition)")
    high_growth_years: int = Field(default=5, description="High-growth period length")
    stable_growth_rate: float | None = Field(default=None, description="Terminal growth (defaults to risk_free_rate)")
    revenue_growth_next_year: float | None = Field(default=None)
    operating_margin_next_year: float | None = Field(default=None, description="User hypothesis for next year operating margin")
    revenue_growth_years_2_5: float | None = Field(default=None)
    target_operating_margin: float | None = Field(default=None)
    margin_convergence_year: int = Field(default=5)
    sales_to_capital_high: float | None = Field(default=None, description="Sales/Capital for high-growth years")
    sales_to_capital_stable: float | None = Field(default=None, description="Sales/Capital for stable years")
    cost_of_capital_stable_override: float | None = Field(default=None)
    roic_stable_override: float | None = Field(default=None)
    failure_probability: float = Field(default=0.0)
    distress_proceeds_pct: float = Field(default=0.5)
    failure_tie_to: str = Field(default="V", description="B=book value, V=fair value")
    override_reinvestment_lag: bool = Field(default=False)
    reinvestment_lag_years: int = Field(default=1)
    override_tax_convergence: bool = Field(default=False)
    override_nol: bool = Field(default=False)
    nol_amount: float = Field(default=0.0)
    override_riskfree: bool = Field(default=False)
    riskfree_after_yr10: float | None = Field(default=None)
    override_growth_perpetuity: bool = Field(default=False)
    growth_perpetuity_rate: float | None = Field(default=None)
    override_trapped_cash: bool = Field(default=False)
    trapped_cash_amount: float = Field(default=0.0)
    trapped_cash_tax_rate: float = Field(default=0.0)
    # Manual override for years 1..high_growth_years effective tax rate.
    # When set, _tax_path uses this instead of macro.tax_rate_effective.
    # Years 6-10 still converge to marginal as before.
    effective_tax_rate_override_years_1_5: float | None = Field(default=None)


# ---------------------------------------------------------------------------
# I. DCF Result (Module 4 output)
# ---------------------------------------------------------------------------

class DCFResult(BaseModel):
    revenue_projections: list[float] = Field(default_factory=list)
    ebit_projections: list[float] = Field(default_factory=list)
    fcff_projections: list[float] = Field(default_factory=list)
    reinvestment_projections: list[float] = Field(default_factory=list)
    discount_factors: list[float] = Field(default_factory=list)
    pv_fcff: list[float] = Field(default_factory=list)
    terminal_value_firm: float | None = Field(default=None)
    pv_terminal_value: float | None = Field(default=None)
    pv_cash_flows_sum: float | None = Field(default=None)
    value_of_operating_assets: float | None = Field(default=None)
    value_of_equity: float | None = Field(default=None)
    value_per_share_pre_options: float | None = Field(default=None)
    # Implied ROIC path (per-year closed-loop output of the three-story
    # examination). Years 1..10; terminal is reported separately.
    implied_roic_projections: list[float] = Field(default_factory=list)
    implied_roic_terminal: float | None = Field(default=None)


# ---------------------------------------------------------------------------
# J. Multiples Result (Module 5 output)
# ---------------------------------------------------------------------------

class MultiplesResult(BaseModel):
    pe_ratio_intrinsic: float | None = Field(default=None)
    pbv_ratio_intrinsic: float | None = Field(default=None)
    ev_ebitda_intrinsic: float | None = Field(default=None)
    ev_sales_intrinsic: float | None = Field(default=None)
    pe_ratio_market: float | None = Field(default=None)


# ---------------------------------------------------------------------------
# K. Option Inputs (employee stock options)
# ---------------------------------------------------------------------------

class OptionInputs(BaseModel):
    number_of_options: float = Field(default=0, description="Outstanding options/warrants")
    average_strike_price: float = Field(default=0.0)
    average_maturity: float = Field(default=0.0, description="Average remaining life in years")
    stock_price_std_dev: float = Field(default=0.0, description="Annualized std deviation of stock")
    dividend_yield: float = Field(default=0.0)
    has_options: bool = Field(default=False)


# ---------------------------------------------------------------------------
# L. Final Valuation (Module 6 / final output)
# ---------------------------------------------------------------------------

class FinalValuation(BaseModel):
    call_value_per_option: float = Field(default=0.0)
    value_of_all_options: float = Field(default=0.0)
    value_per_share: float


# ---------------------------------------------------------------------------
# Composite: full input bundle from Module 0
# ---------------------------------------------------------------------------

class CompanyMetrics(BaseModel):
    """7 company metrics for comparison against industry averages."""
    revenue_growth: float | None = Field(default=None, description="Revenue growth (most recent year)")
    pretax_operating_margin: float | None = Field(default=None, description="EBIT / Revenues")
    sales_to_capital: float | None = Field(default=None, description="Revenues / Invested Capital")
    marginal_sales_to_capital: float | None = Field(default=None, description="ΔRevenues / ΔInvested Capital")
    roic: float | None = Field(default=None, description="EBIT(1-t) / Invested Capital")
    std_dev_stock: float | None = Field(default=None, description="Std deviation in stock prices")
    cost_of_capital: float | None = Field(default=None, description="WACC")


class UnresolvedField(BaseModel):
    """A data field that couldn't be auto-resolved during CIQ ingestion.

    The frontend reads this list and presents manual-entry UI (dropdown for
    enum kinds, numeric input for number, etc.). The user resolves each
    field via PATCH and the valuation re-runs.

    This is the graceful-degradation mechanism: when industry lookup misses,
    when CIQ returns #N/A, when an exchange prefix is unknown — instead of
    silently defaulting, we report the gap so the user can fix it."""

    path: str = Field(description="Dot-path to the field, e.g. 'industry_data.industry_name'")
    kind: str = Field(description="'enum' | 'number' | 'percentage' | 'currency' | 'country'")
    reason: str = Field(description="Human-readable explanation of why auto-resolve failed")
    options: list[str] | None = Field(default=None, description="For enum/currency/country kinds")
    current_value: object | None = Field(default=None, description="What we defaulted to (may be None)")
    required: bool = Field(default=True, description="Whether downstream math blocks on this")
    suggestion: object | None = Field(default=None, description="Heuristic guess (e.g., industry median)")


class CompanyValuationInput(BaseModel):
    ticker: str
    company_name: str | None = Field(default=None)
    country: str | None = Field(default=None)
    reporting_currency: str | None = Field(default=None, description="Currency of financial statements (math currency)")
    stock_price_currency: str | None = Field(default=None, description="Currency of listed stock price")
    # FX rate: multiplier that converts a LISTING-currency number to the REPORTING currency.
    # Example — Lenovo: stock_price=11.83 HKD, stock_price_reporting=1.52 USD → fx_rate = 1.52 / 11.83 ≈ 0.128
    # When reporting_currency == stock_price_currency, fx_rate = 1.0.
    fx_rate: float | None = Field(default=None, description="FX: listing ccy → reporting ccy multiplier")
    fx_rate_source: str = Field(default="unknown", description="'CIQ implied' | 'manual' | 'unavailable' | 'unknown'")
    fx_rate_date: str | None = Field(default=None, description="Date of the FX rate (usually the LTM balance-sheet date)")
    raw_financials: list[RawFinancials] = Field(description="Multi-year, most recent first")
    quarterly_financials: list[RawFinancials] = Field(default_factory=list, description="Quarterly data for LTM (FQ-0..FQ-3)")
    quarters_since_10k: int = Field(default=0, description="Quarters since last annual filing (1-4)")
    period_date_10k: str | None = Field(default=None, description="Most recent 10-K period end date")
    period_date_10q: str | None = Field(default=None, description="Most recent 10-Q period end date")
    period_dates_annual: dict[str, str | None] = Field(default_factory=dict, description="Per-FY period dates: {'0': date, '1': date, ...}")
    effective_tax_rate_ciq: float | None = Field(default=None, description="Effective tax rate fetched from CIQ")
    adjustment_inputs: AdjustmentInputs = Field(default_factory=AdjustmentInputs)
    macro_inputs: MacroInputs
    industry_data: IndustryData
    industry_data_global: IndustryData | None = Field(default=None, description="Global industry data for comparison")
    company_metrics: CompanyMetrics | None = Field(default=None, description="Company metrics for industry comparison")
    option_inputs: OptionInputs = Field(default_factory=OptionInputs)
    valuation_assumptions: ValuationAssumptions = Field(default_factory=ValuationAssumptions)
    methodology_choices: MethodologyChoices = Field(default_factory=MethodologyChoices)
    # Historical effective tax rate (last 5 fiscal years) + averages.
    # Used by the Tax Override Panel on Stories to Numbers as reference data.
    tax_history: TaxHistory | None = Field(default=None)
