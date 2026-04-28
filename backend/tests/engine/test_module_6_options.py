"""
Tests for Module 6: Options Pricing & Final Value (Black-Scholes).
"""

import math
import pytest

from engine.data_dictionary import DCFResult, OptionInputs, MacroInputs
from engine.module_6_options import black_scholes_call, compute_options_and_final_value


class TestBlackScholes:

    def test_atm_call(self):
        """At-the-money call: S=K=100, T=1, r=5%, sigma=20%, no dividends.

        d1 = (ln(1) + (0.05 + 0.02)*1) / (0.20*1) = 0.07/0.20 = 0.35
        d2 = 0.35 - 0.20 = 0.15
        C = 100*N(0.35) - 100*e^(-0.05)*N(0.15)
          = 100*0.6368 - 95.123*0.5596
          = 63.68 - 53.23 = 10.45
        """
        call = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.20)
        assert call == pytest.approx(10.45, abs=0.1)

    def test_deep_itm(self):
        """Deep in-the-money: call ≈ S - K*e^(-rT)."""
        call = black_scholes_call(S=200, K=100, T=1, r=0.05, sigma=0.20)
        # Should be very close to 200 - 100*e^(-0.05) = 200 - 95.12 = 104.88
        assert call > 100

    def test_deep_otm(self):
        """Deep out-of-the-money: call ≈ 0."""
        call = black_scholes_call(S=50, K=200, T=1, r=0.05, sigma=0.20)
        assert call < 1.0

    def test_zero_volatility(self):
        """Zero vol: intrinsic value only."""
        call = black_scholes_call(S=110, K=100, T=1, r=0.05, sigma=0.0)
        assert call == pytest.approx(10.0)  # max(110-100, 0)

    def test_zero_time(self):
        """Zero time to expiry: intrinsic value."""
        call = black_scholes_call(S=110, K=100, T=0, r=0.05, sigma=0.20)
        assert call == pytest.approx(10.0)

    def test_with_dividend_yield(self):
        """Dividend yield reduces call value."""
        no_div = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.20, y=0.0)
        with_div = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.20, y=0.02)
        assert with_div < no_div

    def test_higher_vol_higher_value(self):
        """Higher volatility → higher call value (all else equal)."""
        low_vol = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.15)
        high_vol = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.40)
        assert high_vol > low_vol


class TestOptionsAndFinalValue:

    def test_no_options(self):
        """No options: value per share = pre-option value."""
        dcf = DCFResult(
            value_of_equity=5000.0,
            value_per_share_pre_options=100.0,
        )
        options = OptionInputs(has_options=False)
        macro = MacroInputs(risk_free_rate=0.04, equity_risk_premium=0.05, tax_rate_marginal=0.21)

        result = compute_options_and_final_value(dcf, options, macro)

        assert result.call_value_per_option == 0.0
        assert result.value_of_all_options == 0.0
        assert result.value_per_share == pytest.approx(100.0)

    def test_with_options_reduces_value(self):
        """Options reduce per-share value."""
        dcf = DCFResult(
            value_of_equity=5000.0,
            value_per_share_pre_options=100.0,
        )
        options = OptionInputs(
            number_of_options=10.0,
            average_strike_price=80.0,
            average_maturity=3.0,
            stock_price_std_dev=0.30,
            has_options=True,
        )
        macro = MacroInputs(risk_free_rate=0.04, equity_risk_premium=0.05, tax_rate_marginal=0.21)

        result = compute_options_and_final_value(dcf, options, macro)

        assert result.call_value_per_option > 0
        assert result.value_of_all_options > 0
        assert result.value_per_share < 100.0  # Options dilute value

    def test_deep_otm_options_minimal_impact(self):
        """Deep OTM options have minimal impact on value."""
        dcf = DCFResult(
            value_of_equity=5000.0,
            value_per_share_pre_options=100.0,
        )
        options = OptionInputs(
            number_of_options=10.0,
            average_strike_price=300.0,  # Way OTM
            average_maturity=1.0,
            stock_price_std_dev=0.20,
            has_options=True,
        )
        macro = MacroInputs(risk_free_rate=0.04, equity_risk_premium=0.05, tax_rate_marginal=0.21)

        result = compute_options_and_final_value(dcf, options, macro)

        # Should barely reduce value
        assert result.value_per_share > 99.0
