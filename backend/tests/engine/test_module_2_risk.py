"""
Tests for Module 2: Risk & Cost of Capital.

Hand-calculated expected values for beta, cost of equity, WACC.
"""

import pytest

from engine.data_dictionary import AdjustedFinancials, MacroInputs, IndustryData, CostOfCapital
from engine.module_2_risk import compute_cost_of_capital


@pytest.fixture
def us_macro():
    """Typical US macro inputs."""
    return MacroInputs(
        risk_free_rate=0.04,       # 4% T-bond
        equity_risk_premium=0.05,  # 5% ERP
        country_risk_premium=0.0,
        tax_rate_marginal=0.21,    # 21% US corporate tax
    )


@pytest.fixture
def tech_industry():
    """Tech industry averages."""
    return IndustryData(
        industry_name="Software (System & Application)",
        region="US",
        beta_u=1.05,
        beta_u_corrected_for_cash=1.20,
        cost_of_debt_pretax=0.055,  # 5.5%
    )


class TestCostOfCapital:

    def test_all_equity_firm(self, us_macro, tech_industry):
        """
        All-equity firm: D/E=0, Beta_L=Beta_U, WACC=Ke.

        Beta_L = 1.20 * (1 + 0) = 1.20
        Ke = 0.04 + 1.20 * 0.05 = 0.10
        WACC = 0.10 * 1.0 + 0 = 0.10
        """
        adjusted = AdjustedFinancials(
            adjusted_ebit=100.0,
            adjusted_mv_debt=0.0,
        )

        result = compute_cost_of_capital(adjusted, us_macro, tech_industry, mv_equity=1000.0)

        assert result.d_e_ratio == pytest.approx(0.0)
        assert result.beta_l == pytest.approx(1.20)
        assert result.cost_of_equity == pytest.approx(0.10)
        assert result.weight_equity == pytest.approx(1.0)
        assert result.weight_debt == pytest.approx(0.0)
        assert result.wacc == pytest.approx(0.10)

    def test_levered_firm(self, us_macro, tech_industry):
        """
        D=400, E=1000 → D/E=0.4
        Beta_L = 1.20 * (1 + (1-0.21)*0.4) = 1.20 * 1.316 = 1.5792
        Ke = 0.04 + 1.5792 * 0.05 = 0.04 + 0.07896 = 0.11896
        Kd_at = 0.055 * (1-0.21) = 0.04345
        We = 1000/1400 = 0.71429, Wd = 400/1400 = 0.28571
        WACC = 0.11896 * 0.71429 + 0.04345 * 0.28571 = 0.08497 + 0.01241 = 0.09739
        """
        adjusted = AdjustedFinancials(
            adjusted_ebit=100.0,
            adjusted_mv_debt=400.0,
        )

        result = compute_cost_of_capital(adjusted, us_macro, tech_industry, mv_equity=1000.0)

        assert result.d_e_ratio == pytest.approx(0.4)
        assert result.beta_l == pytest.approx(1.20 * (1 + 0.79 * 0.4), rel=1e-4)
        assert result.cost_of_equity == pytest.approx(0.04 + result.beta_l * 0.05, rel=1e-6)
        assert result.cost_of_debt_aftertax == pytest.approx(0.055 * 0.79, rel=1e-4)
        assert result.weight_equity == pytest.approx(1000 / 1400, rel=1e-4)
        assert result.weight_debt == pytest.approx(400 / 1400, rel=1e-4)

        # WACC sanity: cost_of_debt_aftertax < wacc < cost_of_equity
        assert result.cost_of_debt_aftertax < result.wacc < result.cost_of_equity

    def test_country_risk_premium(self, tech_industry):
        """CRP adds to the effective ERP."""
        macro = MacroInputs(
            risk_free_rate=0.04,
            equity_risk_premium=0.05,
            country_risk_premium=0.03,  # Emerging market
            tax_rate_marginal=0.25,
        )
        adjusted = AdjustedFinancials(adjusted_ebit=100.0, adjusted_mv_debt=0.0)

        result = compute_cost_of_capital(adjusted, macro, tech_industry, mv_equity=1000.0)

        # Ke = 0.04 + 1.20 * (0.05 + 0.03) = 0.04 + 0.096 = 0.136
        assert result.cost_of_equity == pytest.approx(0.136)

    def test_fallback_cost_of_debt(self, us_macro):
        """When industry cost_of_debt_pretax is None, use Rf + default_spread."""
        macro = MacroInputs(
            risk_free_rate=0.04,
            equity_risk_premium=0.05,
            country_risk_premium=0.0,
            tax_rate_marginal=0.21,
            default_spread=0.02,
        )
        industry = IndustryData(
            industry_name="Test",
            beta_u=1.0,
            cost_of_debt_pretax=None,
        )
        adjusted = AdjustedFinancials(adjusted_ebit=100.0, adjusted_mv_debt=500.0)

        result = compute_cost_of_capital(adjusted, macro, industry, mv_equity=1000.0)

        # Cost of debt = 0.04 + 0.02 = 0.06
        assert result.cost_of_debt_pretax == pytest.approx(0.06)
        assert result.cost_of_debt_aftertax == pytest.approx(0.06 * 0.79, rel=1e-4)

    def test_uses_cash_corrected_beta(self, us_macro):
        """Should prefer beta_u_corrected_for_cash over beta_u."""
        industry = IndustryData(
            industry_name="Test",
            beta_u=0.80,
            beta_u_corrected_for_cash=1.10,
            cost_of_debt_pretax=0.05,
        )
        adjusted = AdjustedFinancials(adjusted_ebit=100.0, adjusted_mv_debt=0.0)

        result = compute_cost_of_capital(adjusted, us_macro, industry, mv_equity=1000.0)

        # Should use 1.10, not 0.80
        assert result.beta_l == pytest.approx(1.10)

    def test_weights_sum_to_one(self, us_macro, tech_industry):
        """Equity + debt weights should sum to 1.0."""
        adjusted = AdjustedFinancials(adjusted_ebit=100.0, adjusted_mv_debt=600.0)
        result = compute_cost_of_capital(adjusted, us_macro, tech_industry, mv_equity=400.0)
        assert result.weight_equity + result.weight_debt == pytest.approx(1.0)

    def test_wacc_between_ke_and_kd(self, us_macro, tech_industry):
        """WACC should always be between cost_of_debt_aftertax and cost_of_equity."""
        for debt in [100, 500, 1000, 2000]:
            adjusted = AdjustedFinancials(adjusted_ebit=100.0, adjusted_mv_debt=float(debt))
            result = compute_cost_of_capital(adjusted, us_macro, tech_industry, mv_equity=1000.0)
            assert result.cost_of_debt_aftertax <= result.wacc <= result.cost_of_equity
