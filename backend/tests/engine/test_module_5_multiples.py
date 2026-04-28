"""
Tests for Module 5: Relative Valuation (Multiples).
"""

import pytest

from engine.data_dictionary import (
    AdjustedFinancials, RawFinancials, CashFlowMetrics,
    CostOfCapital, ValuationAssumptions, MacroInputs,
)
from engine.module_5_multiples import compute_multiples


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
        d_e_ratio=0.3, beta_l=1.1,
        cost_of_equity=0.10, cost_of_debt_pretax=0.055,
        cost_of_debt_aftertax=0.04345, weight_equity=0.77,
        weight_debt=0.23, wacc=0.0832,
    )


class TestMultiples:

    def test_pe_intrinsic(self, macro, cost_of_capital):
        """PE = payout_ratio / (Ke - g)."""
        adjusted = AdjustedFinancials(adjusted_ebit=200.0, adjusted_net_income=150.0)
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0,
                            ebitda=250.0, d_a=50.0, mv_equity=2000.0, net_income=150.0)
        cf = CashFlowMetrics(
            adjusted_capex=80.0, adjusted_d_a=40.0,
            reinvestment_firm=50.0, fcff=100.0,
            rir_firm=0.35, rir_equity=0.20, roe=0.15,
        )
        assumptions = ValuationAssumptions()

        result = compute_multiples(adjusted, raw, cf, cost_of_capital, assumptions, macro)

        # PE = (1 - 0.20) / (0.10 - 0.04) = 0.80 / 0.06 = 13.33
        assert result.pe_ratio_intrinsic == pytest.approx(0.80 / 0.06, rel=1e-3)

    def test_pbv_intrinsic(self, macro, cost_of_capital):
        """PBV = (ROE - g) / (Ke - g)."""
        adjusted = AdjustedFinancials(adjusted_ebit=200.0, adjusted_net_income=150.0)
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0,
                            ebitda=250.0, d_a=50.0, mv_equity=2000.0, net_income=150.0)
        cf = CashFlowMetrics(
            adjusted_capex=80.0, adjusted_d_a=40.0,
            reinvestment_firm=50.0, fcff=100.0,
            rir_firm=0.35, rir_equity=0.20, roe=0.15,
        )
        assumptions = ValuationAssumptions()

        result = compute_multiples(adjusted, raw, cf, cost_of_capital, assumptions, macro)

        # PBV = (0.15 - 0.04) / (0.10 - 0.04) = 0.11 / 0.06 = 1.833
        assert result.pbv_ratio_intrinsic == pytest.approx(0.11 / 0.06, rel=1e-3)

    def test_ev_sales_intrinsic(self, macro, cost_of_capital):
        """EV/Sales = after_tax_margin * (1 - rir) / (WACC - g)."""
        adjusted = AdjustedFinancials(adjusted_ebit=200.0)
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0, ebitda=250.0, d_a=50.0)
        cf = CashFlowMetrics(
            adjusted_capex=80.0, adjusted_d_a=40.0,
            reinvestment_firm=50.0, fcff=100.0, rir_firm=0.35,
        )
        assumptions = ValuationAssumptions()

        result = compute_multiples(adjusted, raw, cf, cost_of_capital, assumptions, macro)

        # after_tax_margin = 200 * 0.79 / 1000 = 0.158
        # EV/Sales = 0.158 * (1 - 0.35) / (0.0832 - 0.04) = 0.158 * 0.65 / 0.0432 = 2.377
        margin = 200 * 0.79 / 1000
        expected = margin * 0.65 / (0.0832 - 0.04)
        assert result.ev_sales_intrinsic == pytest.approx(expected, rel=1e-3)

    def test_pe_market(self, macro, cost_of_capital):
        """Market PE = MV Equity / adjusted net income."""
        adjusted = AdjustedFinancials(adjusted_ebit=200.0, adjusted_net_income=150.0)
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0,
                            mv_equity=2000.0, net_income=150.0)
        cf = CashFlowMetrics(
            adjusted_capex=80.0, adjusted_d_a=40.0,
            reinvestment_firm=50.0, fcff=100.0, rir_firm=0.35,
        )
        assumptions = ValuationAssumptions()

        result = compute_multiples(adjusted, raw, cf, cost_of_capital, assumptions, macro)

        assert result.pe_ratio_market == pytest.approx(2000.0 / 150.0, rel=1e-3)

    def test_no_mv_equity_pe_market_none(self, macro, cost_of_capital):
        """No market cap → market PE is None."""
        adjusted = AdjustedFinancials(adjusted_ebit=200.0, adjusted_net_income=150.0)
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0, mv_equity=None)
        cf = CashFlowMetrics(
            adjusted_capex=80.0, adjusted_d_a=40.0,
            reinvestment_firm=50.0, fcff=100.0, rir_firm=0.35,
        )
        assumptions = ValuationAssumptions()

        result = compute_multiples(adjusted, raw, cf, cost_of_capital, assumptions, macro)
        assert result.pe_ratio_market is None
