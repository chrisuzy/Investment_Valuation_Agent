"""
Valuation Orchestrator — chains Modules 1-6 into a complete valuation pipeline.

Supports full valuation and incremental recomputation when a user edits a variable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .data_dictionary import (
    CompanyValuationInput,
    AdjustedFinancials,
    CostOfCapital,
    CashFlowMetrics,
    DCFResult,
    MultiplesResult,
    FinalValuation,
)
from .module_1_adjustments import compute_adjustments
from .module_2_risk import compute_cost_of_capital
from .module_3_cashflow import compute_cashflow_and_growth
from .module_4_dcf import compute_dcf
from .module_5_multiples import compute_multiples
from .module_6_options import compute_options_and_final_value
from .ltm_calculator import compute_ltm_financials
from .company_metrics import compute_company_metrics

logger = logging.getLogger(__name__)


@dataclass
class ValuationReport:
    """Complete valuation output from all modules."""
    ticker: str
    ltm_financials: object = None          # RawFinancials — Ginzu-rotated base year
    adjusted: AdjustedFinancials | None = None
    cost_of_capital: CostOfCapital | None = None
    cashflow: CashFlowMetrics | None = None
    dcf: DCFResult | None = None
    multiples: MultiplesResult | None = None
    final: FinalValuation | None = None
    warnings: list[str] = field(default_factory=list)


def run_full_valuation(
    inputs: CompanyValuationInput,
    industry_lookup=None,
    country_erp_lookup=None,
) -> ValuationReport:
    """
    Run the full M1 → M6 valuation pipeline.

    Args:
        inputs: Complete input data bundle from Module 0.
        industry_lookup: optional callable(industry_name, region) -> IndustryData | None.
            Enables multi-business β. Typically wired to DamodaranStore.lookup_industry.
        country_erp_lookup: optional callable(country_name) -> total ERP | None.
            Enables operating-countries revenue-weighted ERP.

    Returns:
        ValuationReport with all intermediate and final results.
    """
    report = ValuationReport(ticker=inputs.ticker)

    # Sort raw financials: fiscal_year 0 = most recent
    financials = sorted(inputs.raw_financials, key=lambda r: r.fiscal_year, reverse=True)
    if not financials:
        report.warnings.append("No financial data available")
        return report

    raw_fy0 = financials[0]
    raw_prior = financials[1] if len(financials) > 1 else None

    # --- LTM rotation (Ginzu Trailing 12 month formula) ---
    # Build the Ginzu-rotated base year: LTM flow values + FQ-0 balance sheet snapshot.
    # Downstream modules (M1 adjustments, M2 WACC, M3 cashflow, M4 DCF) operate on this
    # LTM-rotated base, NOT on the stale FY0 10-K values.
    ltm = compute_ltm_financials(
        raw_fy0,
        list(inputs.quarterly_financials or []),
        inputs.quarters_since_10k or 0,
    )
    report.ltm_financials = ltm
    raw_current = ltm   # base year for all downstream modules

    # --- M2 consistency: source R&D current from LTM, not FY-0 ---
    # Ensures R&D capitalization uses the same time window (LTM) as the base-year EBIT.
    if ltm.r_and_d_expense is not None and inputs.adjustment_inputs.has_r_and_d:
        inputs.adjustment_inputs.r_and_d_expense_current = ltm.r_and_d_expense

    # Get pre-tax cost of debt for lease discounting (use industry data or default)
    cost_of_debt_pretax = inputs.industry_data.cost_of_debt_pretax or (
        inputs.macro_inputs.risk_free_rate + (inputs.macro_inputs.default_spread or 0.02)
    )

    # --- Module 1: Financial Adjustments ---
    report.adjusted = compute_adjustments(
        raw_current, inputs.adjustment_inputs, cost_of_debt_pretax
    )

    # --- Module 2: Risk & Cost of Capital ---
    mv_equity = raw_current.mv_equity or 0.0
    book_debt = raw_current.bv_debt or 0.0
    interest_expense = raw_current.interest_expense or 0.0
    report.cost_of_capital = compute_cost_of_capital(
        report.adjusted,
        inputs.macro_inputs,
        inputs.industry_data,
        mv_equity,
        methodology=inputs.methodology_choices,
        industry_lookup=industry_lookup,
        country_erp_lookup=country_erp_lookup,
        book_debt=book_debt,
        interest_expense=interest_expense,
        industry_global=inputs.industry_data_global,
    )

    # --- Module 3: Cash Flow & Growth ---
    # Pass the full raw_financials list (most-recent-first) so M3 can
    # compute historical ROIC / S/C / margin / growth series for the
    # three-story examination panel on Stories to Numbers.
    report.cashflow = compute_cashflow_and_growth(
        report.adjusted, raw_current, inputs.adjustment_inputs,
        report.cost_of_capital, raw_prior, macro=inputs.macro_inputs,
        raw_financials_history=financials,
    )

    # --- Module 4: DCF ---
    report.dcf = compute_dcf(
        report.cashflow, report.cost_of_capital, report.adjusted,
        raw_current, inputs.valuation_assumptions, inputs.macro_inputs
    )

    # --- Module 5: Multiples ---
    report.multiples = compute_multiples(
        report.adjusted, raw_current, report.cashflow,
        report.cost_of_capital, inputs.valuation_assumptions, inputs.macro_inputs
    )

    # --- Module 6: Options & Final Value ---
    report.final = compute_options_and_final_value(
        report.dcf, inputs.option_inputs, inputs.macro_inputs
    )

    # --- Populate company_metrics so the Input Sheet "Company" column has
    #     data to display next to the industry references. Uses the LTM-
    #     rotated base year (not raw FY0) so the "Company" ratios match
    #     what drives the DCF. Effective tax for historical ROIC — Damodaran
    #     convention, matches what the firm actually paid.
    tax_rate_for_roic = (
        inputs.macro_inputs.tax_rate_effective
        if inputs.macro_inputs and inputs.macro_inputs.tax_rate_effective is not None
        else (inputs.macro_inputs.tax_rate_marginal if inputs.macro_inputs else 0.21)
    )
    # Prepend LTM as the "current year" so fin0 == LTM; fin1 onwards are
    # the prior annual periods. This mirrors how every other engine module
    # reads the base year.
    ltm_then_prior: list = []
    if report.ltm_financials is not None:
        ltm_then_prior.append(report.ltm_financials)
    ltm_then_prior.extend(inputs.raw_financials)
    computed_cm = compute_company_metrics(
        ltm_then_prior,
        cost_of_capital=report.cost_of_capital,
        adjusted=report.adjusted,
        tax_rate=tax_rate_for_roic,
    )
    # All of these fields are DERIVED from raw financials + module outputs,
    # so they MUST refresh on every run. Previously we only filled null
    # fields, which caused a subtle bug after PATCH: the session's
    # company_metrics still held the prior run's cost_of_capital (non-null),
    # so the Input Sheet's "Company WACC" got stuck at the old value while
    # the Cost of Capital page showed the freshly-computed one. Always
    # overwrite.
    existing = inputs.company_metrics
    _DERIVED_CM_FIELDS = (
        "revenue_growth", "pretax_operating_margin", "sales_to_capital",
        "marginal_sales_to_capital", "roic", "cost_of_capital",
    )
    if existing is None:
        inputs.company_metrics = computed_cm
    else:
        for field_name in _DERIVED_CM_FIELDS:
            setattr(existing, field_name, getattr(computed_cm, field_name))
        # std_dev_stock is the only genuinely user-supplied field — if the
        # computed_cm doesn't know a value (we don't have a volatility
        # calculator yet) keep whatever the user passed.
        if computed_cm.std_dev_stock is not None:
            existing.std_dev_stock = computed_cm.std_dev_stock

    return report


# Module dependency graph for incremental recomputation
_MODULE_ORDER = ["M1", "M2", "M3", "M4", "M5", "M6"]
_DOWNSTREAM = {
    "M1": ["M2", "M3", "M4", "M5", "M6"],
    "M2": ["M3", "M4", "M5", "M6"],
    "M3": ["M4", "M5", "M6"],
    "M4": ["M6"],
    "M5": [],
    "M6": [],
}


def get_modules_to_rerun(edited_module: str) -> list[str]:
    """Given an edit in a module, return which modules need re-running."""
    if edited_module not in _DOWNSTREAM:
        return _MODULE_ORDER  # Full re-run on unknown
    return [edited_module] + _DOWNSTREAM[edited_module]
