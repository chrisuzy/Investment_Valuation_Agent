"""
Tests for the valuation orchestrator — end-to-end pipeline test.
"""

import pytest

from engine.data_dictionary import (
    CompanyValuationInput, RawFinancials, AdjustmentInputs,
    MacroInputs, IndustryData, OptionInputs, ValuationAssumptions,
)
from engine.orchestrator import run_full_valuation, get_modules_to_rerun


@pytest.fixture
def sample_inputs():
    """Synthetic company inputs for pipeline testing."""
    return CompanyValuationInput(
        ticker="TEST",
        company_name="Test Corp",
        country="United States",
        raw_financials=[
            RawFinancials(
                fiscal_year=0,
                revenues=10000.0,
                ebit=2000.0,
                ebitda=2500.0,
                net_income=1500.0,
                interest_expense=200.0,
                capex=800.0,
                d_a=500.0,
                change_in_noncash_wc=50.0,
                net_debt_issued=100.0,
                cash_and_marketable_securities=500.0,
                bv_equity=5000.0,
                bv_debt=3000.0,
                mv_equity=15000.0,
                mv_debt=3000.0,
                shares_outstanding=100.0,
                stock_price=150.0,
            ),
            RawFinancials(
                fiscal_year=-1,
                revenues=9000.0,
                ebit=1800.0,
                bv_equity=4500.0,
                bv_debt=2800.0,
                cash_and_marketable_securities=400.0,
            ),
        ],
        adjustment_inputs=AdjustmentInputs(
            amortization_period_n=5,
            r_and_d_expense_current=500.0,
            r_and_d_expense_past=[450.0, 400.0, 350.0, 300.0, 250.0],
            operating_lease_expense_current=200.0,
            operating_lease_commitments=[200.0, 180.0, 160.0, 140.0, 120.0, 300.0],
            has_r_and_d=True,
            has_operating_leases=True,
        ),
        macro_inputs=MacroInputs(
            risk_free_rate=0.04,
            equity_risk_premium=0.05,
            country_risk_premium=0.0,
            tax_rate_marginal=0.21,
        ),
        industry_data=IndustryData(
            industry_name="Software (System & Application)",
            region="US",
            beta_u=1.05,
            beta_u_corrected_for_cash=1.20,
            cost_of_debt_pretax=0.055,
        ),
        option_inputs=OptionInputs(
            number_of_options=5.0,
            average_strike_price=120.0,
            average_maturity=3.0,
            stock_price_std_dev=0.30,
            has_options=True,
        ),
        valuation_assumptions=ValuationAssumptions(
            projection_years=10,
            high_growth_years=5,
        ),
    )


class TestOrchestrator:

    def test_full_pipeline_produces_value(self, sample_inputs):
        """Full pipeline should produce a positive value per share."""
        report = run_full_valuation(sample_inputs)

        assert report.adjusted is not None
        assert report.cost_of_capital is not None
        assert report.cashflow is not None
        assert report.dcf is not None
        assert report.multiples is not None
        assert report.final is not None

        # The final value should be positive for a profitable company
        assert report.final.value_per_share > 0

    def test_pipeline_consistency(self, sample_inputs):
        """Results should be internally consistent."""
        report = run_full_valuation(sample_inputs)

        # Adjusted EBIT > raw EBIT (growing R&D adds back more than amortization)
        assert report.adjusted.adjusted_ebit > 2000.0

        # WACC between cost of debt and cost of equity
        coc = report.cost_of_capital
        assert coc.cost_of_debt_aftertax <= coc.wacc <= coc.cost_of_equity

        # Weights sum to 1
        assert coc.weight_equity + coc.weight_debt == pytest.approx(1.0)

        # DCF projections have correct length
        assert len(report.dcf.ebit_projections) == 10

        # Options reduce value
        assert report.final.value_per_share < report.dcf.value_per_share_pre_options

    def test_no_options_pipeline(self, sample_inputs):
        """Pipeline works without options."""
        sample_inputs.option_inputs = OptionInputs(has_options=False)
        report = run_full_valuation(sample_inputs)

        assert report.final.value_of_all_options == 0.0
        assert report.final.value_per_share == pytest.approx(
            report.dcf.value_per_share_pre_options
        )

    def test_no_rd_no_leases(self, sample_inputs):
        """Pipeline works with no adjustments."""
        sample_inputs.adjustment_inputs = AdjustmentInputs(
            has_r_and_d=False, has_operating_leases=False
        )
        report = run_full_valuation(sample_inputs)
        assert report.adjusted.adjusted_ebit == 2000.0

    def test_empty_financials(self):
        """Pipeline handles empty financial data gracefully."""
        inputs = CompanyValuationInput(
            ticker="EMPTY",
            raw_financials=[],
            macro_inputs=MacroInputs(
                risk_free_rate=0.04, equity_risk_premium=0.05, tax_rate_marginal=0.21
            ),
            industry_data=IndustryData(industry_name="Test", beta_u=1.0, cost_of_debt_pretax=0.05),
        )
        report = run_full_valuation(inputs)
        assert "No financial data" in report.warnings[0]


class TestIncrementalRecomputation:

    def test_m1_edit_reruns_all(self):
        modules = get_modules_to_rerun("M1")
        assert modules == ["M1", "M2", "M3", "M4", "M5", "M6"]

    def test_m4_edit_reruns_m4_m6(self):
        modules = get_modules_to_rerun("M4")
        assert modules == ["M4", "M6"]

    def test_m5_edit_reruns_m5_only(self):
        modules = get_modules_to_rerun("M5")
        assert modules == ["M5"]

    def test_m6_edit_reruns_m6_only(self):
        modules = get_modules_to_rerun("M6")
        assert modules == ["M6"]
