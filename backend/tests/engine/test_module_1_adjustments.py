"""
Tests for Module 1: Financial Adjustments.

Hand-calculated expected values for R&D capitalization and operating lease conversion.
"""

import pytest

from engine.data_dictionary import RawFinancials, AdjustmentInputs, AdjustedFinancials
from engine.module_1_adjustments import (
    capitalize_r_and_d,
    capitalize_operating_leases,
    compute_adjustments,
)


# ─── R&D Capitalization Tests ───────────────────────────────────────────────


class TestCapitalizeRandD:
    """Test R&D capitalization formula with hand-calculated values."""

    def test_basic_uniform_rd(self):
        """
        Uniform R&D of 100 per year, n=5.
        Past expenses: [100, 100, 100, 100, 100] (t=1..5)

        Unamortized = 100*(4/5) + 100*(3/5) + 100*(2/5) + 100*(1/5) + 100*(0/5)
                     = 80 + 60 + 40 + 20 + 0 = 200

        Amortization = 100/5 * 5 = 100

        Value of research asset = 100 (current) + 200 = 300
        """
        unamortized, amortization, value = capitalize_r_and_d(
            r_and_d_expense_current=100.0,
            r_and_d_expense_past=[100.0, 100.0, 100.0, 100.0, 100.0],
            amortization_period_n=5,
        )
        assert unamortized == pytest.approx(200.0)
        assert amortization == pytest.approx(100.0)
        assert value == pytest.approx(300.0)

    def test_growing_rd(self):
        """
        Growing R&D: current=150, past=[120, 100, 80, 60, 50], n=5.

        Unamortized = 120*(4/5) + 100*(3/5) + 80*(2/5) + 60*(1/5) + 50*(0/5)
                     = 96 + 60 + 32 + 12 + 0 = 200

        Amortization = 120/5 + 100/5 + 80/5 + 60/5 + 50/5
                     = 24 + 20 + 16 + 12 + 10 = 82

        Value = 150 + 200 = 350
        """
        unamortized, amortization, value = capitalize_r_and_d(
            r_and_d_expense_current=150.0,
            r_and_d_expense_past=[120.0, 100.0, 80.0, 60.0, 50.0],
            amortization_period_n=5,
        )
        assert unamortized == pytest.approx(200.0)
        assert amortization == pytest.approx(82.0)
        assert value == pytest.approx(350.0)

    def test_shorter_amortization_period(self):
        """
        n=3, past=[100, 80, 60], current=120.

        Unamortized = 100*(2/3) + 80*(1/3) + 60*(0/3)
                     = 66.667 + 26.667 + 0 = 93.333

        Amortization = 100/3 + 80/3 + 60/3
                     = 33.333 + 26.667 + 20 = 80

        Value = 120 + 93.333 = 213.333
        """
        unamortized, amortization, value = capitalize_r_and_d(
            r_and_d_expense_current=120.0,
            r_and_d_expense_past=[100.0, 80.0, 60.0],
            amortization_period_n=3,
        )
        assert unamortized == pytest.approx(93.333, abs=0.01)
        assert amortization == pytest.approx(80.0)
        assert value == pytest.approx(213.333, abs=0.01)

    def test_no_past_rd(self):
        """No past R&D: only current year counts."""
        unamortized, amortization, value = capitalize_r_and_d(
            r_and_d_expense_current=100.0,
            r_and_d_expense_past=[],
            amortization_period_n=5,
        )
        assert unamortized == 0.0
        assert amortization == 0.0
        assert value == 100.0

    def test_zero_amortization_period(self):
        """Edge case: n=0 should return zero unamortized/amortization."""
        unamortized, amortization, value = capitalize_r_and_d(
            r_and_d_expense_current=100.0,
            r_and_d_expense_past=[50.0, 60.0],
            amortization_period_n=0,
        )
        assert unamortized == 0.0
        assert amortization == 0.0
        assert value == 100.0

    def test_fewer_past_years_than_n(self):
        """
        n=5 but only 3 years of past data: [100, 80, 60].
        Only uses available data, doesn't assume zeros for missing years.

        Unamortized = 100*(4/5) + 80*(3/5) + 60*(2/5)
                     = 80 + 48 + 24 = 152

        Amortization = 100/5 + 80/5 + 60/5 = 20 + 16 + 12 = 48
        """
        unamortized, amortization, value = capitalize_r_and_d(
            r_and_d_expense_current=120.0,
            r_and_d_expense_past=[100.0, 80.0, 60.0],
            amortization_period_n=5,
        )
        assert unamortized == pytest.approx(152.0)
        assert amortization == pytest.approx(48.0)
        assert value == pytest.approx(272.0)  # 120 + 152


# ─── Operating Lease Capitalization Tests ────────────────────────────────────


class TestCapitalizeOperatingLeases:
    """Test PV of operating leases using Damodaran annuity method."""

    def test_basic_lease_pv_annuity(self):
        """
        Commitments: [100, 100, 100, 100, 100, 200] at 5%.
        avg(yr1..yr5) = 100, n_additional = round(200/100) = 2
        annuity = 200/2 = 100 at years 6, 7.

        PV = sum(100/1.05^i for i=1..5) + 100/1.05^6 + 100/1.05^7
        """
        pv, n_add, total = capitalize_operating_leases(
            operating_lease_commitments=[100.0, 100.0, 100.0, 100.0, 100.0, 200.0],
            cost_of_debt_pretax=0.05,
        )
        expected = (
            sum(100 / 1.05**i for i in range(1, 6))
            + 100 / 1.05**6
            + 100 / 1.05**7
        )
        assert pv == pytest.approx(expected, rel=1e-6)
        assert n_add == 2
        assert total == 7

    def test_no_commitments(self):
        """No commitments → PV = 0."""
        pv, n_add, total = capitalize_operating_leases([], 0.05)
        assert pv == 0.0
        assert n_add == 0
        assert total == 0

    def test_zero_discount_rate(self):
        """Zero discount rate → PV = 0 (guarded edge case)."""
        pv, n_add, total = capitalize_operating_leases([100.0, 100.0], 0.0)
        assert pv == 0.0

    def test_single_year_commitment(self):
        """Single year, no beyond: PV = 100/1.06."""
        pv, n_add, total = capitalize_operating_leases([100.0], 0.06)
        assert pv == pytest.approx(100.0 / 1.06, rel=1e-6)
        assert n_add == 0
        assert total == 1

    def test_high_discount_rate(self):
        """High discount rate (20%) with no beyond amount."""
        pv, n_add, total = capitalize_operating_leases(
            [100.0, 100.0, 100.0], 0.20
        )
        expected = 100 / 1.20 + 100 / 1.20**2 + 100 / 1.20**3
        assert pv == pytest.approx(expected, rel=1e-6)
        assert n_add == 0
        assert total == 3

    def test_nvidia_ground_truth(self):
        """
        Nvidia 2025 ground truth from Damodaran's Operating Lease Converter.
        Commitments: [287, 235, 194, 151, 98, 605], cost_of_debt = 6.12%
        avg(yr1..yr5) = 193.0, n_additional = round(605/193) = 3
        annuity = 605/3 = 201.667 at years 6, 7, 8
        total_years = 8
        Expected PV ≈ 1233 (ground truth)
        """
        pv, n_add, total = capitalize_operating_leases(
            operating_lease_commitments=[287.0, 235.0, 194.0, 151.0, 98.0, 605.0],
            cost_of_debt_pretax=0.0612,
        )
        assert n_add == 3
        assert total == 8
        assert pv == pytest.approx(1233.0, abs=1.0)


# ─── Full compute_adjustments Integration Tests ─────────────────────────────


class TestComputeAdjustments:
    """Test the full Module 1 pipeline."""

    @pytest.fixture
    def base_raw(self):
        """Base raw financials for testing."""
        return RawFinancials(
            fiscal_year=0,
            revenues=1000.0,
            ebit=200.0,
            net_income=150.0,
            bv_equity=500.0,
            mv_debt=300.0,
        )

    def test_rd_only(self, base_raw):
        """R&D capitalization with no leases."""
        adj_inputs = AdjustmentInputs(
            amortization_period_n=5,
            r_and_d_expense_current=100.0,
            r_and_d_expense_past=[100.0, 100.0, 100.0, 100.0, 100.0],
            has_r_and_d=True,
            has_operating_leases=False,
        )

        result = compute_adjustments(base_raw, adj_inputs, cost_of_debt_pretax=0.05)

        # Amortization = 100 (see test above)
        # Adjusted EBIT = 200 + 100 - 100 = 200
        assert result.adjusted_ebit == pytest.approx(200.0)
        # Adjusted Net Income = 150 + 100 - 100 = 150
        assert result.adjusted_net_income == pytest.approx(150.0)
        # Value of research asset = 100 + 200 = 300
        assert result.value_of_research_asset == pytest.approx(300.0)
        # Adjusted BV Equity = 500 + 300 = 800
        assert result.adjusted_bv_equity == pytest.approx(800.0)
        # No lease adjustment
        assert result.pv_of_operating_leases == 0.0
        assert result.adjusted_mv_debt == 300.0

    def test_growing_rd_increases_ebit(self, base_raw):
        """Growing R&D should increase adjusted EBIT vs raw EBIT."""
        adj_inputs = AdjustmentInputs(
            amortization_period_n=5,
            r_and_d_expense_current=150.0,
            r_and_d_expense_past=[120.0, 100.0, 80.0, 60.0, 50.0],
            has_r_and_d=True,
            has_operating_leases=False,
        )

        result = compute_adjustments(base_raw, adj_inputs, cost_of_debt_pretax=0.05)

        # Amortization = 82 (see test above)
        # Adjusted EBIT = 200 + 150 - 82 = 268
        assert result.adjusted_ebit == pytest.approx(268.0)
        assert result.adjusted_ebit > base_raw.ebit  # Growing R&D → higher adjusted EBIT

    def test_leases_only(self, base_raw):
        """Operating lease capitalization with no R&D (Damodaran method)."""
        adj_inputs = AdjustmentInputs(
            has_r_and_d=False,
            has_operating_leases=True,
            operating_lease_expense_current=50.0,
            operating_lease_commitments=[50.0, 50.0, 50.0, 50.0, 50.0, 100.0],
        )

        result = compute_adjustments(base_raw, adj_inputs, cost_of_debt_pretax=0.05)

        # avg(yr1..yr5) = 50, n_additional = round(100/50) = 2
        # annuity = 100/2 = 50 at years 6, 7.  total_years = 7
        expected_pv = sum(50 / 1.05**t for t in range(1, 6)) + 50 / 1.05**6 + 50 / 1.05**7
        assert result.pv_of_operating_leases == pytest.approx(expected_pv, rel=1e-6)
        assert result.lease_n_additional_years == 2
        assert result.lease_years_total == 7

        # Adjusted MV Debt = 300 + PV
        assert result.adjusted_mv_debt == pytest.approx(300.0 + expected_pv, rel=1e-6)

        # Damodaran: depreciation = PV / 7, EBIT adj = lease_expense - depreciation
        depreciation = expected_pv / 7
        lease_ebit_adj = 50.0 - depreciation
        assert result.depreciation_on_lease_asset == pytest.approx(depreciation, rel=1e-6)
        assert result.lease_adjustment_to_ebit == pytest.approx(lease_ebit_adj, rel=1e-6)
        assert result.adjusted_ebit == pytest.approx(200.0 + lease_ebit_adj, rel=1e-6)

        # No R&D adjustment
        assert result.unamortized_r_and_d == 0.0
        assert result.amortization_r_and_d == 0.0

    def test_both_rd_and_leases(self, base_raw):
        """Both R&D and lease adjustments combined (Damodaran method)."""
        adj_inputs = AdjustmentInputs(
            amortization_period_n=5,
            r_and_d_expense_current=150.0,
            r_and_d_expense_past=[120.0, 100.0, 80.0, 60.0, 50.0],
            has_r_and_d=True,
            has_operating_leases=True,
            operating_lease_expense_current=50.0,
            operating_lease_commitments=[50.0, 50.0, 50.0, 50.0, 50.0, 100.0],
        )

        result = compute_adjustments(base_raw, adj_inputs, cost_of_debt_pretax=0.05)

        # R&D: amortization=82, adjusted EBIT step 1 = 200 + 150 - 82 = 268
        # Lease: n_add=2, total=7, annuity=50 at yr 6,7
        expected_pv = sum(50 / 1.05**t for t in range(1, 6)) + 50 / 1.05**6 + 50 / 1.05**7
        depreciation = expected_pv / 7
        lease_ebit_adj = 50.0 - depreciation

        # Lease: adjusted EBIT step 2 = 268 + lease_ebit_adj
        assert result.adjusted_ebit == pytest.approx(268.0 + lease_ebit_adj, rel=1e-4)

        # Debt: 300 + PV of leases
        assert result.adjusted_mv_debt == pytest.approx(300.0 + expected_pv, rel=1e-4)

        # BV Equity: 500 + 350 (research asset)
        assert result.adjusted_bv_equity == pytest.approx(850.0)

    def test_no_adjustments(self, base_raw):
        """No R&D or leases: adjusted = raw."""
        adj_inputs = AdjustmentInputs(has_r_and_d=False, has_operating_leases=False)
        result = compute_adjustments(base_raw, adj_inputs, cost_of_debt_pretax=0.05)

        assert result.adjusted_ebit == base_raw.ebit
        assert result.adjusted_net_income == base_raw.net_income
        assert result.adjusted_bv_equity == base_raw.bv_equity
        assert result.adjusted_mv_debt == base_raw.mv_debt

    def test_none_net_income(self):
        """When raw net_income is None, adjusted should remain None."""
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0, net_income=None)
        adj_inputs = AdjustmentInputs(
            r_and_d_expense_current=100.0,
            r_and_d_expense_past=[80.0, 60.0],
            amortization_period_n=5,
            has_r_and_d=True,
        )
        result = compute_adjustments(raw, adj_inputs, cost_of_debt_pretax=0.05)
        assert result.adjusted_net_income is None

    def test_none_mv_debt_with_leases(self):
        """When raw mv_debt is None but leases exist, adjusted_mv_debt = PV of leases."""
        raw = RawFinancials(fiscal_year=0, revenues=1000.0, ebit=200.0, mv_debt=None)
        adj_inputs = AdjustmentInputs(
            has_operating_leases=True,
            operating_lease_expense_current=50.0,
            operating_lease_commitments=[50.0, 50.0],  # only 2 years, no beyond
        )
        result = compute_adjustments(raw, adj_inputs, cost_of_debt_pretax=0.05)
        expected_pv = 50 / 1.05 + 50 / 1.05**2
        assert result.adjusted_mv_debt == pytest.approx(expected_pv, rel=1e-6)
        assert result.lease_years_total == 2
        assert result.lease_n_additional_years == 0
