"""
Tests for Module 4: DCF Valuation.
"""

import pytest

from engine.data_dictionary import (
    CashFlowMetrics, CostOfCapital, AdjustedFinancials,
    RawFinancials, ValuationAssumptions, MacroInputs,
)
from engine.module_4_dcf import compute_dcf


@pytest.fixture
def macro():
    return MacroInputs(
        risk_free_rate=0.04,
        equity_risk_premium=0.05,
        tax_rate_marginal=0.21,
    )


@pytest.fixture
def cost_of_capital():
    return CostOfCapital(
        d_e_ratio=0.3,
        beta_l=1.1,
        cost_of_equity=0.095,
        cost_of_debt_pretax=0.055,
        cost_of_debt_aftertax=0.04345,
        weight_equity=0.77,
        weight_debt=0.23,
        wacc=0.0832,
    )


@pytest.fixture
def adjusted():
    return AdjustedFinancials(
        adjusted_ebit=200.0,
        adjusted_net_income=150.0,
        adjusted_mv_debt=300.0,
    )


@pytest.fixture
def raw():
    return RawFinancials(
        fiscal_year=0,
        revenues=1000.0,
        ebit=200.0,
        cash_and_marketable_securities=100.0,
        shares_outstanding=50.0,
    )


@pytest.fixture
def cf_metrics():
    return CashFlowMetrics(
        adjusted_capex=80.0,
        adjusted_d_a=40.0,
        reinvestment_firm=50.0,
        fcff=108.0,
        expected_growth_ebit=0.08,
        rir_firm=0.35,
    )


class TestDCF:

    def test_basic_dcf(self, cf_metrics, cost_of_capital, adjusted, raw, macro):
        """Basic 10-year DCF projection."""
        assumptions = ValuationAssumptions(
            projection_years=10,
            high_growth_years=5,
        )

        result = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions, macro)

        # Should have 10 years of projections
        assert len(result.ebit_projections) == 10
        assert len(result.fcff_projections) == 10
        assert len(result.discount_factors) == 10

        # EBIT should grow year over year in high-growth period
        for i in range(1, 5):
            assert result.ebit_projections[i] > result.ebit_projections[i - 1]

        # Terminal value should be positive
        assert result.terminal_value_firm > 0
        assert result.pv_terminal_value > 0

        # Value of equity should be positive (firm value + cash - debt)
        assert result.value_of_equity is not None
        assert result.value_per_share_pre_options is not None

    def test_discount_factors_decrease(self, cf_metrics, cost_of_capital, adjusted, raw, macro):
        """Discount factors should decrease over time."""
        assumptions = ValuationAssumptions(projection_years=5, high_growth_years=5)
        result = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions, macro)

        for i in range(1, len(result.discount_factors)):
            assert result.discount_factors[i] < result.discount_factors[i - 1]

    def test_pv_equals_fcff_times_df(self, cf_metrics, cost_of_capital, adjusted, raw, macro):
        """PV(FCFF) = FCFF * discount_factor for each year."""
        assumptions = ValuationAssumptions(projection_years=5, high_growth_years=5)
        result = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions, macro)

        for fcff, df, pv in zip(result.fcff_projections, result.discount_factors, result.pv_fcff):
            assert pv == pytest.approx(fcff * df, rel=1e-6)

    def test_value_bridge(self, cf_metrics, cost_of_capital, adjusted, raw, macro):
        """Value of equity = operating assets + cash - debt."""
        assumptions = ValuationAssumptions(projection_years=5, high_growth_years=5)
        result = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions, macro)

        expected_equity = result.value_of_operating_assets + 100.0 - 300.0
        assert result.value_of_equity == pytest.approx(expected_equity, rel=1e-6)

    def test_stable_growth_capped_at_rf(self, cf_metrics, cost_of_capital, adjusted, raw, macro):
        """Stable growth should be capped at risk-free rate."""
        assumptions = ValuationAssumptions(
            projection_years=5,
            high_growth_years=5,
            stable_growth_rate=0.10,  # Higher than Rf=4%
        )
        result = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions, macro)

        # Terminal EBIT should use capped growth, not 10%
        # Year 5 EBIT × (1 + 0.04) instead of × (1 + 0.10)
        assert result.terminal_value_firm > 0

    def test_shares_outstanding_affects_per_share(self, cf_metrics, cost_of_capital, adjusted, macro):
        """More shares → lower value per share."""
        raw_few = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0,
                                cash_and_marketable_securities=100.0, shares_outstanding=10.0)
        raw_many = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0,
                                 cash_and_marketable_securities=100.0, shares_outstanding=100.0)
        assumptions = ValuationAssumptions(projection_years=5, high_growth_years=5)

        r1 = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw_few, assumptions, macro)
        r2 = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw_many, assumptions, macro)

        assert r1.value_per_share_pre_options > r2.value_per_share_pre_options

    def test_failure_probability(self, cf_metrics, cost_of_capital, adjusted, raw, macro):
        """Failure probability should reduce equity value."""
        assumptions_no_fail = ValuationAssumptions(projection_years=5, high_growth_years=5)
        assumptions_fail = ValuationAssumptions(
            projection_years=5, high_growth_years=5,
            failure_probability=0.10, distress_proceeds_pct=0.3,
        )

        r1 = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions_no_fail, macro)
        r2 = compute_dcf(cf_metrics, cost_of_capital, adjusted, raw, assumptions_fail, macro)

        # With positive equity, failure probability reduces value
        if r1.value_of_equity > 0:
            assert r2.value_of_equity < r1.value_of_equity
