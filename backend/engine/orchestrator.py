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
    report.cashflow = compute_cashflow_and_growth(
        report.adjusted, raw_current, inputs.adjustment_inputs,
        report.cost_of_capital, raw_prior, macro=inputs.macro_inputs,
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
    #     data to display next to the industry references. Pulls from the
    #     raw financials we already have + the WACC we just computed.
    tax_rate = (
        inputs.macro_inputs.tax_rate_marginal
        if inputs.macro_inputs and inputs.macro_inputs.tax_rate_marginal is not None
        else 0.21
    )
    computed_cm = compute_company_metrics(
        inputs.raw_financials,
        cost_of_capital=report.cost_of_capital,
        tax_rate=tax_rate,
    )
    # Preserve any user-supplied std_dev_stock / marginal_sales_to_capital
    # by only overwriting null fields on the input.
    existing = inputs.company_metrics
    if existing is None:
        inputs.company_metrics = computed_cm
    else:
        for field_name in (
            "revenue_growth", "pretax_operating_margin", "sales_to_capital",
            "marginal_sales_to_capital", "roic", "cost_of_capital",
        ):
            if getattr(existing, field_name, None) is None:
                setattr(existing, field_name, getattr(computed_cm, field_name))

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
