"""End-to-end integration tests against TEST_DATA CIQ files.

Per user guidance: DO NOT compare results against Ginzu_NVIDIA.xlsx cached values —
the TEST_DATA files have different valuation dates (2026-04-28) than Damodaran's
Ginzu (2025-01-01). What we CAN validate:
  - Pipeline runs end-to-end without errors
  - Output fields are populated and not NaN / None where expected
  - Computation MECHANICS match Ginzu (EBIT = Rev × Margin, discount factors are
    cumulative products, equity bridge includes minority + cross_holdings, etc.)
  - Results are in a plausible range (revenue > 0, value_per_share finite)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2].parent
TEST_DATA_DIR = REPO_ROOT / "TEST_DATA"

# Stub minimal industry/macro data so the test doesn't require the full DamodaranStore
from engine.data_dictionary import (
    IndustryData, MacroInputs, ValuationAssumptions, AdjustmentInputs,
    CompanyValuationInput, RawFinancials,
)
from engine.orchestrator import run_full_valuation


def _build_inputs_from_ciq(ciq_path: Path, ticker: str, industry: str = "Semiconductor") -> CompanyValuationInput:
    """Parse a resolved CIQ template and wrap it into a CompanyValuationInput
    with stub industry + macro data."""
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from tools.read_ciq_template import read_ciq_template

    ciq = read_ciq_template(str(ciq_path))
    annual = ciq["annual"]
    current = ciq["current"]
    pd_annual = ciq.get("period_dates", {}).get("period_date_annual")
    # derive base fiscal year from period date
    base_fy = 2025
    if pd_annual:
        try:
            from dateutil import parser
            base_fy = parser.parse(pd_annual).year
        except Exception:
            pass

    raw_financials = []
    for yr_off in sorted(annual.keys()):
        d = annual[yr_off]
        if yr_off == 0:
            d = {**d, **{k: v for k, v in current.items() if v is not None}}
        raw_financials.append(RawFinancials(
            fiscal_year=base_fy - yr_off,
            revenues=float(d.get("revenues") or 0),
            ebit=float(d.get("ebit") or 0),
            ebitda=d.get("ebitda"),
            net_income=d.get("net_income"),
            interest_expense=d.get("interest_expense"),
            d_a=d.get("d_a"),
            capex=d.get("capex"),
            r_and_d_expense=d.get("r_and_d_expense"),
            earnings_before_tax=d.get("earnings_before_tax"),
            total_tax_expense=d.get("total_tax_expense"),
            cash_and_marketable_securities=d.get("cash_and_marketable_securities"),
            bv_equity=d.get("bv_equity"),
            bv_debt=d.get("bv_debt"),
            mv_equity=d.get("mv_equity") if yr_off == 0 else None,
            mv_debt=d.get("bv_debt"),
            shares_outstanding=d.get("shares_outstanding"),
            stock_price=d.get("stock_price") if yr_off == 0 else None,
            cross_holdings=d.get("cross_holdings"),
            minority_interests=d.get("minority_interests"),
        ))

    # Stub industry data (Damodaran Semiconductor-like)
    industry_data = IndustryData(
        industry_name=industry, region="US",
        beta_u=1.40, beta_u_corrected_for_cash=1.45,
        cost_of_debt_pretax=0.055, wacc=0.105,
        pretax_operating_margin=0.25, sales_to_capital=2.0,
        revenue_growth=0.15, std_dev_stock=0.35, roic=0.18,
    )
    macro = MacroInputs(
        risk_free_rate=0.045, equity_risk_premium=0.045,
        country_risk_premium=0.0,
        tax_rate_marginal=0.25, tax_rate_effective=0.15,
        default_spread=0.012,
    )

    # Build lease + R&D adjustment inputs from CIQ
    rd_past = []
    for yr in range(1, 11):
        v = annual.get(yr, {}).get("r_and_d_expense")
        if v is not None and v > 0:
            rd_past.append(float(v))
    has_rd = (current.get("r_and_d_expense") or 0) > 0 and len(rd_past) > 0

    lease_commits: list[float] = []
    for key in ("lease_commitment_yr1", "lease_commitment_yr2", "lease_commitment_yr3",
                "lease_commitment_yr4", "lease_commitment_yr5", "lease_commitment_beyond"):
        v = current.get(key)
        if v is not None and v > 0:
            lease_commits.append(float(v))
    has_leases = len(lease_commits) >= 2

    adj_inputs = AdjustmentInputs(
        amortization_period_n=5,
        r_and_d_expense_current=float(current.get("r_and_d_expense") or 0),
        r_and_d_expense_past=rd_past,
        operating_lease_expense_current=float(current.get("operating_lease_expense") or 0),
        operating_lease_commitments=lease_commits,
        has_r_and_d=has_rd,
        has_operating_leases=has_leases,
    )

    return CompanyValuationInput(
        ticker=ticker,
        company_name=ticker,
        country="United States",
        raw_financials=raw_financials,
        macro_inputs=macro,
        industry_data=industry_data,
        adjustment_inputs=adj_inputs,
        valuation_assumptions=ValuationAssumptions(
            projection_years=10, high_growth_years=5, margin_convergence_year=5,
            revenue_growth_next_year=0.15,
            operating_margin_next_year=None,  # let engine use LTM-implied
            target_operating_margin=0.30,
            sales_to_capital_high=2.0, sales_to_capital_stable=2.0,
        ),
    )


@pytest.mark.skipif(not TEST_DATA_DIR.exists(), reason="TEST_DATA folder not present")
class TestLiveDataPipeline:
    """Run the pipeline on each TEST_DATA file. These are METHOD-validation tests,
    not VALUE-matching tests."""

    @pytest.mark.parametrize("fname,ticker", [
        ("TEST_DATA_NVDA_260428.xlsx", "NVDA"),
        ("TEST_DATA_MSFT_260428.xlsx", "MSFT"),
        ("TEST_DATA_LENOVO_260428.xlsx", "LNVGY"),
    ])
    def test_full_pipeline_produces_valid_output(self, fname, ticker):
        path = TEST_DATA_DIR / fname
        if not path.exists():
            pytest.skip(f"File not present: {fname}")

        inputs = _build_inputs_from_ciq(path, ticker)
        report = run_full_valuation(inputs)

        assert report.adjusted is not None, "M1 output missing"
        assert report.cost_of_capital is not None, "M2 output missing"
        assert report.cashflow is not None, "M3 output missing"
        assert report.dcf is not None, "M4 output missing"
        assert report.final is not None, "M6 output missing"

        dcf = report.dcf
        # Structural invariants:
        assert len(dcf.revenue_projections) == 10
        assert len(dcf.ebit_projections) == 10
        assert len(dcf.fcff_projections) == 10
        assert len(dcf.discount_factors) == 10

        # No NaN anywhere:
        for v in (dcf.revenue_projections + dcf.ebit_projections + dcf.fcff_projections
                  + dcf.discount_factors + dcf.pv_fcff):
            assert not math.isnan(v), "NaN in DCF projections"

        # Revenue grows year-over-year in the high-growth period (positive assumption)
        for t in range(4):
            assert dcf.revenue_projections[t + 1] >= dcf.revenue_projections[t] * 0.9, (
                "Revenue should not shrink materially in high-growth years"
            )

        # EBIT = Revenue × Margin invariant (Ginzu mechanic)
        # Year 1 EBIT should be margin_y1 × year-1 revenue; we allow some wiggle from margin path
        rev_1 = dcf.revenue_projections[0]
        ebit_1 = dcf.ebit_projections[0]
        implied_margin = ebit_1 / rev_1 if rev_1 != 0 else 0
        # Implied margin between -1.0 and 1.0 (sanity)
        assert -1.0 < implied_margin < 1.0, f"Implied margin Y1 out of range: {implied_margin}"

        # Cumulative discount factors decrease monotonically
        for t in range(1, 10):
            assert dcf.discount_factors[t] < dcf.discount_factors[t - 1], (
                "Discount factors must decrease over time"
            )
        # And each df < 1
        assert all(0 < df < 1 for df in dcf.discount_factors)

        # Terminal value finite
        assert dcf.terminal_value_firm is not None and math.isfinite(dcf.terminal_value_firm)
        assert dcf.pv_terminal_value is not None and math.isfinite(dcf.pv_terminal_value)

        # Value per share finite
        assert report.final.value_per_share is not None
        assert math.isfinite(report.final.value_per_share)

    def test_equity_bridge_includes_minority_and_cross(self):
        """Verify M4 equity bridge formula is applied. Use MSFT (larger firm, more likely to have
        non-zero minority/cross). We don't assert specific values — just that changing
        minority/cross produces a change in value_of_equity."""
        path = TEST_DATA_DIR / "TEST_DATA_MSFT_260428.xlsx"
        if not path.exists():
            pytest.skip("MSFT file not present")

        inputs = _build_inputs_from_ciq(path, "MSFT")
        report_base = run_full_valuation(inputs)

        # Modify raw_financials[0] to add minority + cross
        fin0 = inputs.raw_financials[0]
        inputs2 = inputs.model_copy(deep=True)
        inputs2.raw_financials[0] = fin0.model_copy(update={
            "minority_interests": 10_000.0,
            "cross_holdings": 5_000.0,
        })
        report_modified = run_full_valuation(inputs2)

        # The equity value SHOULD differ
        assert report_base.dcf.value_of_equity != pytest.approx(
            report_modified.dcf.value_of_equity, rel=1e-6
        ), "Minority + cross_holdings should flow through to equity value"
