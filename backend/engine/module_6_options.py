"""
Module 6: Options Pricing & Final Value — Black-Scholes + dilution-adjusted value per share.

Prices employee stock options using Black-Scholes, then adjusts the DCF equity value
for option dilution to produce the final value per share.
"""

from __future__ import annotations

import math

from .data_dictionary import DCFResult, OptionInputs, FinalValuation, MacroInputs


def black_scholes_call(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    y: float = 0.0,
) -> float:
    """
    Black-Scholes call option price.

    Args:
        S: Current stock price (or value per share).
        K: Strike price.
        T: Time to maturity in years.
        r: Risk-free rate (continuous compounding).
        sigma: Annualized volatility (std dev of stock returns).
        y: Dividend yield (continuous).

    Returns:
        Call option value.
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return max(S - K, 0.0)  # Intrinsic value only

    d1 = (math.log(S / K) + (r - y + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    call = S * math.exp(-y * T) * _normal_cdf(d1) - K * math.exp(-r * T) * _normal_cdf(d2)
    return max(call, 0.0)


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using math.erfc (no scipy dependency)."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


def compute_options_and_final_value(
    dcf_result: DCFResult,
    option_inputs: OptionInputs,
    macro: MacroInputs,
) -> FinalValuation:
    """
    Price employee options with Ginzu-style dilution-adjusted Black-Scholes
    (fixed-point iteration) and compute final value per share.

    Ginzu's Option value sheet closes the circular reference:
        Adjusted_S = (S_seed × shares + call_value × warrants) / (shares + warrants)
        call_value = BSM(Adjusted_S, K, T, r, σ, y)

    We iterate until call_value stabilizes, then subtract total option value from
    the pre-options equity value and divide by shares to get final per-share.
    """
    value_of_equity_pre = dcf_result.value_of_equity or 0.0
    value_per_share_pre = dcf_result.value_per_share_pre_options or 0.0

    if (not option_inputs.has_options
        or option_inputs.number_of_options <= 0
        or value_per_share_pre <= 0):
        return FinalValuation(
            call_value_per_option=0.0,
            value_of_all_options=0.0,
            value_per_share=value_per_share_pre,
        )

    # Derive share count from the pre-options equity / per-share identity.
    shares = value_of_equity_pre / value_per_share_pre if value_per_share_pre > 0 else 1.0
    warrants = option_inputs.number_of_options

    # Iteration seed: intrinsic pre-options per-share value.
    # (Ginzu uses current market price; we use intrinsic per-share for consistency
    # with a self-contained valuation where market price is an OUTPUT to compare,
    # not an INPUT into the computation.)
    S_seed = value_per_share_pre

    K = option_inputs.average_strike_price
    T = option_inputs.average_maturity
    r = macro.risk_free_rate
    sigma = option_inputs.stock_price_std_dev
    y = option_inputs.dividend_yield

    # Fixed-point iteration
    call_value = 0.0
    for _ in range(20):
        adjusted_S = (S_seed * shares + call_value * warrants) / (shares + warrants)
        new_call = black_scholes_call(adjusted_S, K, T, r, sigma, y)
        if abs(new_call - call_value) < 0.01:
            call_value = new_call
            break
        call_value = new_call

    total_option_value = call_value * warrants
    adjusted_equity = value_of_equity_pre - total_option_value
    value_per_share = adjusted_equity / shares if shares > 0 else 0.0

    return FinalValuation(
        call_value_per_option=call_value,
        value_of_all_options=total_option_value,
        value_per_share=value_per_share,
    )
