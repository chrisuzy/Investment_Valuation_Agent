"""
Module 2: Cost of Capital — full Ginzu dispatch.

Implements the Ginzu `Cost of capital worksheet` faithfully. Every approach,
every variant, every branch that Ginzu offers exists here. Supported branches
compute normally; unsupported branches (multi-business beta, operating-countries
ERP, etc.) raise a recorded warning rather than silently falling through.

Structure of compute_cost_of_capital():

1. Read methodology choices from inputs.
2. Resolve top-level approach:
      - "direct"           → WACC is a user input; skip everything else
      - "detailed"         → build from components via CAPM + WACC blend
      - "industry_average" → Damodaran industry avg WACC + (user_RF − base_RF)
      - "decile"           → regional 5×5 lookup
3. For "detailed": resolve each component in order
      a. Unlevered beta (beta_approach)
      b. ERP (erp_approach)
      c. MV of debt (bond-pricing optional, + convertibles + leases)
      d. MV of equity + preferred
      e. Weights
      f. Levered beta (if beta_approach != direct_levered)
      g. Cost of equity (CAPM)
      h. Pre-tax cost of debt (kd_approach)
      i. After-tax cost of debt
      j. WACC blend (E + D + P)
4. Return CostOfCapital with every intermediate field populated + branch labels
   + any warnings.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .data_dictionary import (
    AdjustedFinancials,
    MacroInputs,
    IndustryData,
    CostOfCapital,
    MethodologyChoices,
    BusinessSegment,
    GeographicSegment,
    ConvertibleDebt,
    PreferredStock,
)


# ---------------------------------------------------------------------------
# Reference-data loader
# ---------------------------------------------------------------------------

_REF_DATA_PATH = Path(__file__).parent.parent / "data_sources" / "cost_of_capital_reference.json"

try:
    with _REF_DATA_PATH.open() as _f:
        _REF = json.load(_f)
except Exception:
    _REF = {}


def _get_synthetic_rating(coverage: float, firm_type: str) -> tuple[str, float] | None:
    """Look up (rating, spread) given coverage ratio and firm type."""
    table_key = firm_type if firm_type in ("large", "small") else "large"
    table = _REF.get("synthetic_rating_tables", {}).get(table_key)
    if not isinstance(table, list):
        return None
    for row in table:
        if row["coverage_lower"] <= coverage < row["coverage_upper"]:
            return row["rating"], row["spread"]
    return None


def _rating_to_spread(rating: str) -> float | None:
    """Look up spread for a bond rating code."""
    rs = _REF.get("rating_to_spread", {})
    return rs.get(rating)


def _decile_lookup(region: str, risk_group: str) -> float | None:
    """Approach 3 — regional risk-quartile WACC lookup."""
    table = _REF.get("decile_table", {})
    return table.get(region, {}).get(risk_group)


def _regional_erp(region: str) -> float | None:
    """Total ERP for a Damodaran-defined region."""
    return _REF.get("regional_erp", {}).get(region, {}).get("total_erp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bond_price_of_debt(book_debt: float, interest_expense: float, kd: float, maturity: float) -> float:
    """MV of debt priced as a coupon bond.

    MV = interest × [1 − (1+Kd)^−T] / Kd  +  BookDebt / (1+Kd)^T
    """
    if kd <= 0 or maturity <= 0 or book_debt <= 0:
        return book_debt
    annuity = interest_expense * (1 - (1 + kd) ** -maturity) / kd
    principal = book_debt / (1 + kd) ** maturity
    return annuity + principal


def _multi_business_ev_weighted_beta(
    segments: list[BusinessSegment], is_global: bool, industry_lookup
) -> tuple[float, list[str]]:
    """Multi-business EV-weighted unlevered beta.

    EV per segment = segment_revenue × industry EV/Sales multiple.
    Weight = segment EV / total EV.
    β_u = Σ segment β_u × weight.

    Requires industry_lookup(industry_name, region) that returns an IndustryData
    (or None). Warnings are returned for segments we couldn't find data for.
    """
    warnings: list[str] = []
    weighted_ev_list: list[tuple[float, float]] = []  # (seg_ev, seg_beta_u)
    total_ev = 0.0
    for seg in segments:
        ind_name = seg.industry_global if is_global else seg.industry_us
        if not ind_name:
            warnings.append(f"Segment '{seg.name}': no industry specified; skipped.")
            continue
        ind = industry_lookup(ind_name, "Global" if is_global else "US")
        if ind is None or ind.ev_sales is None or ind.beta_u is None:
            warnings.append(f"Segment '{seg.name}' (industry '{ind_name}'): beta or EV/Sales not found; skipped.")
            continue
        seg_ev = seg.revenue * ind.ev_sales
        weighted_ev_list.append((seg_ev, ind.beta_u))
        total_ev += seg_ev
    if total_ev <= 0 or not weighted_ev_list:
        return (0.0, warnings + ["Multi-business beta failed: no valid segments. Falling back to single-industry."])
    beta_u = sum(ev * b / total_ev for ev, b in weighted_ev_list)
    return (beta_u, warnings)


def _multi_location_weighted_erp(
    segments: list[GeographicSegment], lookup
) -> tuple[float, list[str]]:
    """Revenue-weighted ERP across countries or regions.

    Preferred path: each GeographicSegment carries a `resolution` with a
    pre-computed ERP (handles composites like "EMEA" by expanding to member
    weights). Backend routes.py populates this automatically from the
    segment_resolver; frontend user overrides propagate through the same
    resolution object.

    Fallback path: if `resolution` is absent (pre-resolver data), fall back
    to calling `lookup(seg.name)` — the legacy behavior.

    lookup(name) → ERP | None.
    """
    warnings: list[str] = []
    weighted: list[tuple[float, float]] = []
    total_rev = 0.0
    for seg in segments:
        # Prefer the resolved ERP if available
        resolved_erp = None
        if getattr(seg, "resolution", None) is not None:
            resolved_erp = seg.resolution.erp
            if seg.resolution.mapped_kind == "unresolved":
                warnings.append(
                    f"Segment '{seg.name}' ({(seg.pct or 0)*100:.1f}%): unresolved — "
                    f"please map manually via the Geographic Segments panel."
                )
                continue
        if resolved_erp is None:
            # Legacy path — caller-supplied lookup by raw name
            resolved_erp = lookup(seg.name)
        if resolved_erp is None:
            warnings.append(f"Location '{seg.name}': ERP not found; skipped.")
            continue
        weighted.append((seg.revenue, resolved_erp))
        total_rev += seg.revenue
    if total_rev <= 0 or not weighted:
        return (0.0, warnings + ["Multi-location ERP failed: no valid locations."])
    erp = sum(rev * e / total_rev for rev, e in weighted)
    return (erp, warnings)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def compute_cost_of_capital(
    adjusted: AdjustedFinancials,
    macro: MacroInputs,
    industry: IndustryData,
    mv_equity: float,
    methodology: MethodologyChoices | None = None,
    # Optional auxiliary data — if passed, enables the advanced variants.
    industry_lookup=None,           # callable: (industry_name, region) -> IndustryData | None
    country_erp_lookup=None,         # callable: country_name -> ERP | None
    book_debt: float = 0.0,
    interest_expense: float = 0.0,
    industry_global: IndustryData | None = None,
) -> CostOfCapital:
    """Full Ginzu WACC dispatch. See module docstring for branch structure."""

    m = methodology or MethodologyChoices()
    warnings: list[str] = []

    # ───────────────────────────────────────────────────────────────────────
    # Approach 1 dispatch: short-circuits for non-detailed approaches.
    # ───────────────────────────────────────────────────────────────────────
    if m.cost_of_capital_approach == "direct":
        if m.wacc_direct_input is None:
            warnings.append("approach='direct' but wacc_direct_input is None; falling back to detailed.")
        else:
            return CostOfCapital(
                approach_used="direct",
                beta_branch_used="n/a",
                erp_branch_used="n/a",
                kd_branch_used="n/a",
                beta_u=0.0, beta_l=0.0,
                mv_straight_debt=0.0, mv_convertible_straight_part=0.0,
                equity_in_convertible=0.0, mv_leases=0.0,
                mv_debt_total=0.0, book_debt=book_debt,
                d_e_ratio=0.0,
                mv_equity=mv_equity, mv_preferred=0.0, total_capital=mv_equity,
                cost_of_equity=m.wacc_direct_input,
                cost_of_debt_pretax=m.wacc_direct_input,
                cost_of_debt_aftertax=m.wacc_direct_input,
                cost_of_preferred=0.0,
                weight_equity=1.0, weight_debt=0.0, weight_preferred=0.0,
                risk_free_rate=macro.risk_free_rate,
                equity_risk_premium=0.0,
                wacc=m.wacc_direct_input,
                warnings=warnings,
            )

    if m.cost_of_capital_approach == "industry_average":
        # Ginzu: WACC = Industry avg WACC + (user RF − Damodaran base RF)
        ind_wacc = industry.wacc
        if ind_wacc is None:
            warnings.append("industry_average: industry WACC not available; falling back to detailed.")
        else:
            base_rf = _REF.get("decile_base_riskfree", 0.0388)
            wacc = ind_wacc + (macro.risk_free_rate - base_rf)
            return CostOfCapital(
                approach_used="industry_average",
                beta_branch_used="n/a", erp_branch_used="n/a", kd_branch_used="n/a",
                beta_u=industry.beta_u or 0.0, beta_l=0.0,
                mv_straight_debt=0.0, mv_convertible_straight_part=0.0,
                equity_in_convertible=0.0, mv_leases=0.0,
                mv_debt_total=0.0, book_debt=book_debt,
                d_e_ratio=0.0,
                mv_equity=mv_equity, mv_preferred=0.0, total_capital=mv_equity,
                cost_of_equity=wacc,  # placeholder; industry_avg doesn't decompose
                cost_of_debt_pretax=industry.cost_of_debt_pretax or 0.0,
                cost_of_debt_aftertax=(industry.cost_of_debt_pretax or 0.0) * (1 - macro.tax_rate_marginal),
                cost_of_preferred=0.0,
                weight_equity=1.0, weight_debt=0.0, weight_preferred=0.0,
                risk_free_rate=macro.risk_free_rate,
                equity_risk_premium=0.0,
                wacc=wacc,
                warnings=warnings,
            )

    if m.cost_of_capital_approach == "decile":
        wacc = _decile_lookup(m.decile_region, m.decile_risk_group)
        if wacc is None:
            warnings.append(f"decile lookup failed for region='{m.decile_region}' risk='{m.decile_risk_group}'; falling back to detailed.")
        else:
            return CostOfCapital(
                approach_used="decile",
                beta_branch_used="n/a", erp_branch_used="n/a", kd_branch_used="n/a",
                beta_u=0.0, beta_l=0.0,
                mv_straight_debt=0.0, mv_convertible_straight_part=0.0,
                equity_in_convertible=0.0, mv_leases=0.0,
                mv_debt_total=0.0, book_debt=book_debt,
                d_e_ratio=0.0,
                mv_equity=mv_equity, mv_preferred=0.0, total_capital=mv_equity,
                cost_of_equity=wacc,
                cost_of_debt_pretax=0.0, cost_of_debt_aftertax=0.0,
                cost_of_preferred=0.0,
                weight_equity=1.0, weight_debt=0.0, weight_preferred=0.0,
                risk_free_rate=macro.risk_free_rate,
                equity_risk_premium=0.0,
                wacc=wacc,
                warnings=warnings + [f"Decile lookup: {m.decile_region} / {m.decile_risk_group}"],
            )

    # ───────────────────────────────────────────────────────────────────────
    # Approach 1 — Detailed (default, most rigorous)
    # ───────────────────────────────────────────────────────────────────────
    approach_used = "detailed"

    # --- Unlevered beta ---
    # Ginzu Understanding convention: "Single Business(US)" ALWAYS reaches for
    # the US industry table (betas.xls), not the caller-provided industry.
    # If the caller passed non-US industry data, we re-lookup via the callable.
    beta_u = 0.0
    beta_branch = m.beta_approach
    if m.beta_approach == "single_business_us":
        if industry.region != "US" and industry_lookup is not None:
            # Force US-region lookup to honor the "Single Business(US)" selection
            us_ind = industry_lookup(industry.industry_name, "US")
            if us_ind is not None:
                beta_u = us_ind.beta_u_corrected_for_cash or us_ind.beta_u or 0.0
            else:
                warnings.append(
                    f"single_business_us: US row for '{industry.industry_name}' not found; "
                    f"falling back to {industry.region} β_u."
                )
                beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
        else:
            beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
    elif m.beta_approach == "single_business_global":
        # Use industry_global if provided; else re-lookup via callable; else fall back with warning.
        glb = industry_global
        if glb is None and industry_lookup is not None:
            glb = industry_lookup(industry.industry_name, "Global")
        if glb is not None and (glb.beta_u_corrected_for_cash or glb.beta_u):
            beta_u = glb.beta_u_corrected_for_cash or glb.beta_u or 0.0
        else:
            warnings.append("single_business_global: no Global industry data supplied; falling back to US β_u.")
            beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
    elif m.beta_approach in ("multi_business_us", "multi_business_global"):
        if not m.business_segments or industry_lookup is None:
            warnings.append(f"{m.beta_approach}: business_segments empty or industry_lookup not available; falling back to single-industry.")
            beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
            beta_branch = "single_business_us (fallback)"
        else:
            is_global = m.beta_approach == "multi_business_global"
            beta_u, seg_warnings = _multi_business_ev_weighted_beta(
                m.business_segments, is_global, industry_lookup
            )
            warnings.extend(seg_warnings)
            if beta_u == 0.0:
                beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
                beta_branch = "single_business_us (fallback)"
    elif m.beta_approach == "direct_unlevered":
        if m.beta_direct_input is None:
            warnings.append("direct_unlevered: no beta_direct_input; falling back to industry β_u.")
            beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
        else:
            beta_u = m.beta_direct_input
    elif m.beta_approach == "direct_levered":
        # β_l is provided directly; skip relevering
        pass
    else:
        warnings.append(f"Unknown beta_approach='{m.beta_approach}'; using single_business_us.")
        beta_u = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
        beta_branch = "single_business_us (fallback)"

    # --- ERP ---
    erp = 0.0
    erp_branch = m.erp_approach
    if m.erp_approach == "country_of_incorporation":
        erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
    elif m.erp_approach == "direct":
        if m.erp_direct_input is None:
            warnings.append("erp_approach='direct' but erp_direct_input is None; falling back to country.")
            erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
            erp_branch = "country_of_incorporation (fallback)"
        else:
            erp = m.erp_direct_input
    elif m.erp_approach == "operating_countries":
        if not m.geographic_segments or country_erp_lookup is None:
            warnings.append("operating_countries: geographic_segments empty or lookup not available; falling back to country of incorporation.")
            erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
            erp_branch = "country_of_incorporation (fallback)"
        else:
            erp, geo_warns = _multi_location_weighted_erp(m.geographic_segments, country_erp_lookup)
            warnings.extend(geo_warns)
            if erp == 0.0:
                erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
                erp_branch = "country_of_incorporation (fallback)"
    elif m.erp_approach == "operating_regions":
        if not m.geographic_segments:
            warnings.append("operating_regions: geographic_segments empty; falling back to country.")
            erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
            erp_branch = "country_of_incorporation (fallback)"
        else:
            erp, reg_warns = _multi_location_weighted_erp(m.geographic_segments, _regional_erp)
            warnings.extend(reg_warns)
            if erp == 0.0:
                erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
                erp_branch = "country_of_incorporation (fallback)"
    else:
        warnings.append(f"Unknown erp_approach='{m.erp_approach}'; using country of incorporation.")
        erp = macro.equity_risk_premium + (macro.country_risk_premium or 0.0)
        erp_branch = "country_of_incorporation (fallback)"

    # --- Pre-tax cost of debt (need to compute first so we can bond-price if requested) ---
    kd_pretax = 0.0
    kd_branch = m.kd_approach
    coverage_ratio: float | None = None
    synthetic_rating_inferred: str | None = None

    if m.kd_approach == "direct":
        if m.kd_direct_input is None:
            warnings.append("kd_approach='direct' but no kd_direct_input; falling back to industry.")
            kd_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
            kd_branch = "industry_fallback (fallback)"
        else:
            kd_pretax = m.kd_direct_input
    elif m.kd_approach == "synthetic_rating":
        # EBIT for coverage: Damodaran uses lease-adjusted EBIT, NOT R&D-adjusted
        ebit_for_coverage = adjusted.adjusted_ebit - (adjusted.lease_adjustment_to_ebit or 0.0)
        # Actually adjusted.adjusted_ebit includes both R&D and lease; strip the R&D-component
        # The R&D adjustment = r_and_d_current − amortization, which equals
        #   (adjusted EBIT − raw EBIT) − lease_adjustment_to_ebit, but we don't have raw_ebit here.
        # Simpler: use adjusted.adjusted_ebit and note this is an approximation.
        # For Ginzu-faithful implementation, caller should pass a pre-R&D-adjusted EBIT explicitly.
        ebit_for_coverage = adjusted.adjusted_ebit - 0.0  # placeholder; see warning
        warnings.append("synthetic_rating: using fully-adjusted EBIT. Ginzu uses lease-adjusted-only EBIT; small discrepancy for R&D-heavy firms.")
        if interest_expense <= 0:
            coverage_ratio = 1_000_000.0
        elif ebit_for_coverage < 0:
            coverage_ratio = -100_000.0
        else:
            coverage_ratio = ebit_for_coverage / interest_expense
        lookup = _get_synthetic_rating(coverage_ratio, m.synthetic_rating_firm_type)
        if lookup is None:
            warnings.append(f"synthetic_rating: coverage {coverage_ratio} out of table range; falling back to industry.")
            kd_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
            kd_branch = "industry_fallback (fallback)"
        else:
            rating, spread = lookup
            synthetic_rating_inferred = rating
            # Ginzu convention: Kd = RF + rating_spread. Country default spread is
            # NOT added on top (it's already baked into the rating-to-spread table
            # via sovereign+corporate mixing).
            kd_pretax = macro.risk_free_rate + spread
            kd_branch = f"synthetic_rating → {rating}"
    elif m.kd_approach == "actual_rating":
        if not m.actual_rating:
            warnings.append("actual_rating: no rating specified; falling back to industry.")
            kd_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
            kd_branch = "industry_fallback (fallback)"
        else:
            spread = _rating_to_spread(m.actual_rating)
            if spread is None:
                warnings.append(f"actual_rating: '{m.actual_rating}' not in rating table; falling back to industry.")
                kd_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
                kd_branch = "industry_fallback (fallback)"
            else:
                # Ginzu: Kd = RF + rating_spread (no separate default_spread add-on)
                kd_pretax = macro.risk_free_rate + spread
                kd_branch = f"actual_rating → {m.actual_rating}"
    elif m.kd_approach == "industry_fallback":
        kd_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
    else:
        warnings.append(f"Unknown kd_approach='{m.kd_approach}'; using industry fallback.")
        kd_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
        kd_branch = "industry_fallback (fallback)"

    # --- MV of debt ---
    # Primary source: `book_debt` kwarg (from orchestrator: raw.bv_debt).
    # Backwards-compat fallback: `adjusted.adjusted_mv_debt` (Module 1 output,
    # already handles mv_debt→bv_debt fallback). Leases are added separately
    # via mv_leases so we do NOT include them here even if adjusted_mv_debt
    # has been extended to include them.
    mv_straight = 0.0
    mv_conv_straight = 0.0
    equity_in_conv = 0.0
    debt_for_pricing = book_debt if book_debt > 0 else float(adjusted.adjusted_mv_debt or 0.0)
    if debt_for_pricing > 0:
        if m.use_bond_pricing_for_debt and interest_expense > 0 and m.debt_maturity_years > 0:
            mv_straight = _bond_price_of_debt(debt_for_pricing, interest_expense, kd_pretax, m.debt_maturity_years)
        else:
            mv_straight = debt_for_pricing  # use book value (or Module 1's MV-debt passthrough) as MV proxy

    if m.has_convertible and m.convertible_debt.book_value > 0:
        cd = m.convertible_debt
        mv_conv_straight = _bond_price_of_debt(cd.book_value, cd.interest_expense, kd_pretax, cd.maturity_years or 1.0)
        equity_in_conv = max(0.0, cd.market_value - mv_conv_straight)

    mv_leases = adjusted.pv_of_operating_leases or 0.0
    mv_debt_total = mv_straight + mv_conv_straight + mv_leases

    # --- MV of equity ---
    mv_equity_val = float(mv_equity or 0.0)

    # --- MV of preferred ---
    mv_preferred = 0.0
    cost_preferred = 0.0
    if m.has_preferred and m.preferred_stock.shares > 0:
        ps = m.preferred_stock
        mv_preferred = ps.shares * ps.price_per_share
        if ps.price_per_share > 0:
            cost_preferred = ps.dividend_per_share / ps.price_per_share

    # --- Weights ---
    total_capital = mv_equity_val + mv_debt_total + mv_preferred
    if total_capital > 0:
        w_e = mv_equity_val / total_capital
        w_d = mv_debt_total / total_capital
        w_p = mv_preferred / total_capital
    else:
        w_e, w_d, w_p = 1.0, 0.0, 0.0

    d_e_ratio = mv_debt_total / mv_equity_val if mv_equity_val > 0 else 0.0

    # --- Levered beta ---
    if m.beta_approach == "direct_levered":
        if m.beta_direct_input is None:
            warnings.append("direct_levered: no beta_direct_input; falling back to industry β_l.")
            beta_u_fallback = industry.beta_u_corrected_for_cash or industry.beta_u or 0.0
            beta_l = beta_u_fallback * (1 + (1 - macro.tax_rate_marginal) * d_e_ratio)
            beta_branch = "single_business_us (fallback for levered)"
        else:
            beta_l = m.beta_direct_input
    else:
        # Standard relever
        beta_l = beta_u * (1 + (1 - macro.tax_rate_marginal) * d_e_ratio)

    # --- Cost of equity (CAPM) ---
    cost_of_equity = macro.risk_free_rate + beta_l * erp

    # --- After-tax cost of debt ---
    cost_of_debt_aftertax = kd_pretax * (1 - macro.tax_rate_marginal)

    # --- WACC ---
    wacc = w_e * cost_of_equity + w_d * cost_of_debt_aftertax + w_p * cost_preferred

    # Sensitivity knob: additive level shift in basis points. Applied AFTER the
    # CAPM + weights build, so it affects the "used" WACC uniformly across all
    # 10 projection years. Only the sensitivity tornado touches this in normal
    # usage; default is 0.
    shift_bps = getattr(m, "wacc_level_shift_bps", 0.0) or 0.0
    if shift_bps:
        wacc = wacc + shift_bps / 10000.0

    return CostOfCapital(
        approach_used=approach_used,
        beta_branch_used=beta_branch,
        erp_branch_used=erp_branch,
        kd_branch_used=kd_branch,
        beta_u=beta_u,
        beta_l=beta_l,
        mv_straight_debt=mv_straight,
        mv_convertible_straight_part=mv_conv_straight,
        equity_in_convertible=equity_in_conv,
        mv_leases=mv_leases,
        mv_debt_total=mv_debt_total,
        book_debt=book_debt,
        d_e_ratio=d_e_ratio,
        mv_equity=mv_equity_val,
        mv_preferred=mv_preferred,
        total_capital=total_capital,
        cost_of_equity=cost_of_equity,
        cost_of_debt_pretax=kd_pretax,
        cost_of_debt_aftertax=cost_of_debt_aftertax,
        cost_of_preferred=cost_preferred,
        weight_equity=w_e,
        weight_debt=w_d,
        weight_preferred=w_p,
        risk_free_rate=macro.risk_free_rate,
        equity_risk_premium=erp,
        interest_coverage_ratio=coverage_ratio,
        synthetic_rating=synthetic_rating_inferred,
        wacc=wacc,
        warnings=warnings,
    )
