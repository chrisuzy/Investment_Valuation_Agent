"""
Tests for Module 3: Cash Flow & Growth.

Hand-calculated expected values for reinvestment, FCFF/FCFE, ROIC/ROE, growth rates.
"""

import pytest

from engine.data_dictionary import (
    AdjustedFinancials,
    RawFinancials,
    AdjustmentInputs,
    CostOfCapital,
)
from engine.module_3_cashflow import compute_cashflow_and_growth


@pytest.fixture
def cost_of_capital():
    """Standard cost of capital for testing (21% implied tax rate)."""
    return CostOfCapital(
        d_e_ratio=0.4,
        beta_l=1.2,
        cost_of_equity=0.10,
        cost_of_debt_pretax=0.06,
        cost_of_debt_aftertax=0.06 * 0.79,  # tax = 21%
        weight_equity=0.714,
        weight_debt=0.286,
        wacc=0.0839,
    )


@pytest.fixture
def raw_current():
    return RawFinancials(
        fiscal_year=0,
        revenues=1000.0,
        ebit=200.0,
        net_income=150.0,
        capex=80.0,
        d_a=40.0,
        change_in_noncash_wc=10.0,
        net_debt_issued=20.0,
        bv_equity=500.0,
        bv_debt=300.0,
        cash_and_marketable_securities=50.0,
    )


@pytest.fixture
def raw_prior():
    return RawFinancials(
        fiscal_year=-1,
        revenues=900.0,
        ebit=180.0,
        bv_equity=450.0,
        bv_debt=280.0,
        cash_and_marketable_securities=40.0,
    )


class TestCashFlowAndGrowth:

    def test_no_rd_adjustments(self, cost_of_capital, raw_current, raw_prior):
        """Basic case with no R&D capitalization."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            adjusted_bv_equity=500.0,
            adjusted_mv_debt=300.0,
            amortization_r_and_d=0.0,
            value_of_research_asset=0.0,
        )
        adj_inputs = AdjustmentInputs(has_r_and_d=False, has_operating_leases=False)

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        # Adjusted capex = 80 + 0 (no R&D) = 80
        assert result.adjusted_capex == pytest.approx(80.0)
        # Adjusted D&A = 40 + 0 = 40
        assert result.adjusted_d_a == pytest.approx(40.0)
        # Reinvestment = 80 - 40 + 10 = 50
        assert result.reinvestment_firm == pytest.approx(50.0)
        # Reinvestment equity = 50 - 20 = 30
        assert result.reinvestment_equity == pytest.approx(30.0)

        # NOPAT = 200 * (1 - 0.21) = 158
        nopat = 200.0 * 0.79
        # FCFF = 158 - 50 = 108
        assert result.fcff == pytest.approx(nopat - 50.0, rel=1e-3)
        # FCFE = 150 - 30 = 120
        assert result.fcfe == pytest.approx(120.0)

    def test_with_rd_adjustments(self, cost_of_capital, raw_current, raw_prior):
        """R&D capitalization: capex includes R&D, D&A includes amortization."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=260.0,  # 200 + 100 (R&D) - 40 (amortization)
            adjusted_net_income=210.0,
            adjusted_bv_equity=800.0,
            adjusted_mv_debt=300.0,
            amortization_r_and_d=40.0,
            value_of_research_asset=300.0,
        )
        adj_inputs = AdjustmentInputs(
            r_and_d_expense_current=100.0,
            has_r_and_d=True,
            has_operating_leases=False,
        )

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        # Adjusted capex = 80 + 100 = 180
        assert result.adjusted_capex == pytest.approx(180.0)
        # Adjusted D&A = 40 + 40 = 80
        assert result.adjusted_d_a == pytest.approx(80.0)
        # Reinvestment = 180 - 80 + 10 = 110
        assert result.reinvestment_firm == pytest.approx(110.0)

    def test_roic_calculation(self, cost_of_capital, raw_current, raw_prior):
        """ROIC = NOPAT / adjusted invested capital."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            adjusted_bv_equity=500.0,
            adjusted_mv_debt=300.0,
            value_of_research_asset=0.0,
            amortization_r_and_d=0.0,
        )
        adj_inputs = AdjustmentInputs()

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        # Prior adjusted invested capital = prior_bv_equity + research_asset + prior_bv_debt - prior_cash
        # = (450 + 0) + 280 - 40 = 690
        nopat = 200.0 * 0.79
        expected_roic = nopat / 690.0
        assert result.roic == pytest.approx(expected_roic, rel=1e-3)
        assert result.adjusted_invested_capital == pytest.approx(690.0)

    def test_roe_calculation(self, cost_of_capital, raw_current, raw_prior):
        """ROE = adjusted net income / prior adjusted BV equity."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            value_of_research_asset=100.0,
            amortization_r_and_d=20.0,
        )
        adj_inputs = AdjustmentInputs()

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        # Prior adjusted BV equity = 450 + 100 (research asset) = 550
        expected_roe = 150.0 / 550.0
        assert result.roe == pytest.approx(expected_roe, rel=1e-3)

    def test_growth_identity(self, cost_of_capital, raw_current, raw_prior):
        """Expected growth = ROIC * reinvestment rate (identity check)."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            value_of_research_asset=0.0,
            amortization_r_and_d=0.0,
        )
        adj_inputs = AdjustmentInputs()

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        if result.roic is not None and result.rir_firm is not None:
            assert result.expected_growth_ebit == pytest.approx(
                result.roic * result.rir_firm, rel=1e-6
            )

        if result.roe is not None and result.rir_equity is not None:
            assert result.expected_growth_ni == pytest.approx(
                result.roe * result.rir_equity, rel=1e-6
            )

    def test_no_prior_year(self, cost_of_capital, raw_current):
        """Without prior year, ROIC/ROE/growth should be None."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            value_of_research_asset=0.0,
            amortization_r_and_d=0.0,
        )
        adj_inputs = AdjustmentInputs()

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior_year=None
        )

        assert result.roic is None
        assert result.roe is None
        assert result.adjusted_invested_capital is None
        assert result.expected_growth_ebit is None
        # FCFF/reinvestment should still be computed
        assert result.fcff is not None
        assert result.reinvestment_firm is not None

    def test_fcff_matches_nopat_minus_reinvestment(self, cost_of_capital, raw_current, raw_prior):
        """FCFF = NOPAT - reinvestment (identity)."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            value_of_research_asset=0.0,
            amortization_r_and_d=0.0,
        )
        adj_inputs = AdjustmentInputs()

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        nopat = 200.0 * 0.79
        assert result.fcff == pytest.approx(nopat - result.reinvestment_firm, rel=1e-6)

    def test_fcfe_matches_ni_minus_equity_reinvestment(self, cost_of_capital, raw_current, raw_prior):
        """FCFE = adjusted net income - reinvestment_equity."""
        adjusted = AdjustedFinancials(
            adjusted_ebit=200.0,
            adjusted_net_income=150.0,
            value_of_research_asset=0.0,
            amortization_r_and_d=0.0,
        )
        adj_inputs = AdjustmentInputs()

        result = compute_cashflow_and_growth(
            adjusted, raw_current, adj_inputs, cost_of_capital, raw_prior
        )

        assert result.fcfe == pytest.approx(150.0 - result.reinvestment_equity, rel=1e-6)
