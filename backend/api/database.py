"""
Public database-backed endpoints.

These are NOT gated by admin auth — anyone using the app can search for a
company and run a valuation from the ingested database. The raw CIQ .xls
files are not exposed here; only the derived tables.

Endpoints:
  GET  /api/database/search?q=<query>            autocomplete
  GET  /api/database/company/<ticker>            full structured snapshot
  GET  /api/database/company-exists/<ticker>     lightweight existence check
  POST /api/valuation/from-database {ticker}     run full pipeline, create session
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources import us_cn_hk_db as db

router = APIRouter(prefix="/database", tags=["database"])


# ---------------------------------------------------------------------------
# Search + lookup
# ---------------------------------------------------------------------------

@router.get("/search")
def search(q: str = "", limit: int = 20) -> dict:
    """Case-insensitive substring on company_name + exact-prefix on ticker.
    Returns up to `limit` (default 20). Empty q → empty results."""
    if not q.strip():
        return {"query": q, "results": []}
    try:
        with db.get_connection() as conn:
            rows = db.search_companies(conn, q, limit=limit)
    except Exception:
        # If the DB file doesn't exist yet (no admin has uploaded), return empty.
        rows = []
    return {"query": q, "results": rows}


@router.get("/company-exists/{ticker:path}")
def company_exists(ticker: str) -> dict:
    """Lightweight existence check — the onboarding wizard uses this to
    decide whether to offer the 'Value from Database' option."""
    try:
        with db.get_connection() as conn:
            row = db.fetch_company(conn, ticker)
    except Exception:
        row = None
    return {
        "ticker": ticker,
        "in_database": row is not None,
        "data_as_of": row["company"].get("data_as_of") if row else None,
    }


@router.get("/company/{ticker:path}")
def company(ticker: str) -> dict:
    """Full company snapshot — identifiers + snapshot fields + annual + quarterly
    financials. Raises 404 if the ticker isn't in the DB."""
    try:
        with db.get_connection() as conn:
            row = db.fetch_company(conn, ticker)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")
    if row is None:
        raise HTTPException(status_code=404, detail=f"Ticker not in database: {ticker}")
    return row


# ---------------------------------------------------------------------------
# Valuation from database — builds CompanyValuationInput from the DB record
# and runs through the existing orchestrator.
# ---------------------------------------------------------------------------

# Imports pulled in at request time to avoid circular imports with routes.py.

class FromDatabaseRequest(BaseModel):
    ticker: str
    risk_free_rate: float = 0.0425
    industry_override: str | None = None


# Mount this endpoint on a SEPARATE router with /valuation prefix so it lives
# next to the existing template-upload endpoint under the same URL tree.
valuation_router = APIRouter(prefix="/valuation", tags=["valuation"])


def _db_record_to_company_input(record: dict, risk_free_rate: float, industry_override: str | None):
    """Translate a DB record into the CompanyValuationInput shape that the
    orchestrator expects. Reuses the same helpers (industry lookup, country
    ERP lookup, macro setup) as the /fetch-from-file path so the valuation
    math is identical."""
    from engine.data_dictionary import (
        CompanyValuationInput, RawFinancials, MacroInputs, AdjustmentInputs,
        OptionInputs, ValuationAssumptions, MethodologyChoices, TaxHistory,
        GeographicSegment, SegmentResolution, SegmentMember,
    )
    from engine.segment_resolver import resolve_segments
    from api.routes import _get_damodaran_store, _get_industry_mapper, _clean_rating

    co = record["company"]
    annual_rows = record["financials_annual"]
    quarterly_rows = record["financials_quarterly"]

    # Industry / macro resolution — mirrors routes.py::fetch_from_file lines 542–587
    ticker = co["ticker"]
    store = _get_damodaran_store()
    mapper = _get_industry_mapper()
    company_info = mapper.lookup(ticker)
    country = company_info.country if company_info else co.get("region") or "United States"
    industry_name = industry_override or (company_info.industry_group if company_info else None)

    primary_region = "US"
    industry_data = store.lookup_industry(industry_name, region=primary_region) if industry_name else None
    if industry_data is None and industry_name:
        industry_data = store.lookup_industry(industry_name, region="Global")
        if industry_data:
            primary_region = "Global"
    if industry_data is None:
        # Graceful fallback — same as template path
        available = store.list_industries("US")
        industry_data = store.lookup_industry(available[0], region="US") if available else None
    industry_data_global = (
        store.lookup_industry(industry_data.industry_name, region="Global")
        if industry_data and primary_region != "Global" else None
    )

    macro = store.lookup_country(country)
    if macro is None:
        erp = store.get_mature_market_erp() or 0.05
        macro = MacroInputs(risk_free_rate=risk_free_rate, equity_risk_premium=erp, tax_rate_marginal=0.21)
    else:
        macro.risk_free_rate = risk_free_rate
    if co.get("effective_tax_rate") is not None:
        macro.tax_rate_effective = co["effective_tax_rate"]

    # Build per-year RawFinancials. The DB has 10 annual + 8 quarterly rows.
    # Base fiscal year: infer from period_date_annual (YYYY-MM-DD).
    base_fy_year = datetime.now().year
    pda = co.get("period_date_annual")
    if pda:
        try:
            base_fy_year = datetime.fromisoformat(pda[:10]).year
        except ValueError:
            pass

    raw_financials: list[RawFinancials] = []
    # Map fy_offset → fiscal_year (offset 0 → base, offset 1 → base-1, etc.)
    annual_by_offset = {r["fy_offset"]: r for r in annual_rows}
    for offset in sorted(annual_by_offset.keys()):
        r = annual_by_offset[offset]
        is_current = (offset == 0)
        rf = RawFinancials(
            fiscal_year=base_fy_year - offset,
            revenues=r.get("revenues"),
            ebit=r.get("ebit"),
            ebitda=r.get("ebitda"),
            net_income=r.get("net_income"),
            interest_expense=r.get("interest_expense"),
            d_a=r.get("d_a"),
            r_and_d_expense=r.get("r_and_d_expense"),
            capex=r.get("capex"),
            operating_lease_expense=r.get("operating_lease_expense"),
            earnings_before_tax=r.get("earnings_before_tax"),
            total_tax_expense=r.get("total_tax_expense"),
            bv_equity=r.get("bv_equity"),
            bv_debt=r.get("bv_debt"),
            cash_and_marketable_securities=r.get("cash_and_marketable_securities"),
            cross_holdings=r.get("cross_holdings"),
            minority_interests=r.get("minority_interests"),
            shares_outstanding=r.get("shares_outstanding"),
            # Listing-currency snapshots land on the current-year row only
            stock_price=co.get("stock_price_listing") if is_current else None,
            mv_equity_listing=co.get("mv_equity_listing") if is_current else None,
        )
        raw_financials.append(rf)

    # Quarterly
    quarterly_financials: list[RawFinancials] = []
    q_by_offset = {r["fq_offset"]: r for r in quarterly_rows}
    for offset in sorted(q_by_offset.keys()):
        r = q_by_offset[offset]
        quarterly_financials.append(RawFinancials(
            fiscal_year=base_fy_year,  # CIQ quarterly is current-year slice; precise FY offsets aren't critical here
            revenues=r.get("revenues"),
            ebit=r.get("ebit"),
            ebitda=r.get("ebitda"),
            net_income=r.get("net_income"),
            interest_expense=r.get("interest_expense"),
            d_a=r.get("d_a"),
            r_and_d_expense=r.get("r_and_d_expense"),
            capex=r.get("capex"),
            operating_lease_expense=r.get("operating_lease_expense"),
            earnings_before_tax=r.get("earnings_before_tax"),
            total_tax_expense=r.get("total_tax_expense"),
            bv_equity=r.get("bv_equity"),
            bv_debt=r.get("bv_debt"),
            cash_and_marketable_securities=r.get("cash_and_marketable_securities"),
            cross_holdings=r.get("cross_holdings"),
            minority_interests=r.get("minority_interests"),
            shares_outstanding=r.get("shares_outstanding"),
        ))

    # Option inputs — disable BSM when data is incomplete. Lenovo is the
    # typical case: options_outstanding = 132M but options_avg_strike = 0
    # (CIQ screener's Reported Currency bug returned 0 for strike on some
    # tickers); without a strike, BSM divides by zero. Safer to skip
    # option dilution and surface as UnresolvedField than crash.
    num_opts = co.get("options_outstanding") or 0.0
    avg_strike = co.get("options_avg_strike") or 0.0
    has_opts = num_opts > 0 and avg_strike > 0
    option_inputs = OptionInputs(
        number_of_options=num_opts,
        average_strike_price=avg_strike,
        average_maturity=5.0,  # screener doesn't include maturity — plan §2 acceptable default
        stock_price_std_dev=(industry_data.std_dev_stock if industry_data and industry_data.std_dev_stock else 0.35),
        dividend_yield=0.0,
        has_options=has_opts,
    )

    # Adjustment inputs — R&D / lease past-year arrays populated from annual data
    adj_inputs = AdjustmentInputs()
    # Pull past R&D values from older annual rows for the R&D capitalization
    past_rd: list[float] = []
    for offset in range(1, 11):
        r = annual_by_offset.get(offset)
        if r and r.get("r_and_d_expense") is not None:
            past_rd.append(float(r["r_and_d_expense"]))
    adj_inputs.r_and_d_expense_past = past_rd
    if annual_by_offset.get(0) and annual_by_offset[0].get("r_and_d_expense"):
        adj_inputs.r_and_d_expense_current = float(annual_by_offset[0]["r_and_d_expense"])
        adj_inputs.has_r_and_d = True
    # Lease commitments from snapshot fields — schema uses
    # operating_lease_commitments: list[float] + separate has_leases flag.
    # Append the beyond-5-yr bucket as an optional 6th entry (matches the
    # template upload's AdjustmentInputs shape).
    lease_yrs = [co.get(f"lease_commitment_yr{i}") or 0.0 for i in range(1, 6)]
    beyond = float(co.get("lease_commitment_beyond") or 0.0)
    commitments = [float(v) for v in lease_yrs]
    if beyond > 0:
        commitments.append(beyond)
    adj_inputs.operating_lease_commitments = commitments
    # Current-year lease expense isn't captured on the company snapshot;
    # infer from the FY-0 annual row if available.
    if annual_by_offset.get(0) and annual_by_offset[0].get("operating_lease_expense"):
        adj_inputs.operating_lease_expense_current = float(annual_by_offset[0]["operating_lease_expense"])
    # Match the template path's convention: has_operating_leases is driven by
    # current-year lease EXPENSE, not merely the presence of commitment rows.
    # Screener snapshots may include multi-year commitments even when the firm
    # doesn't break out a separate lease expense — in that case the template
    # leaves leases disabled (the commitments are discounted elsewhere).
    adj_inputs.has_operating_leases = adj_inputs.operating_lease_expense_current > 0

    # FX defaults: 1.0 if currencies match; None otherwise (user supplies manually)
    fx_rate = co.get("fx_listing_to_reporting")
    fx_source = co.get("fx_rate_source") or "unset"
    if fx_rate is None and co.get("filing_currency") == co.get("listing_currency"):
        fx_rate = 1.0
        fx_source = "same currency"

    # Compute quarters_since_10k from period dates so the LTM rotation
    # pulls the correct number of quarters forward. E.g. Lenovo's
    # FY-0 ends Mar 31, 2025 and FQ-0 ends Dec 31, 2025 → 3 quarters.
    quarters_since = 0
    pda = co.get("period_date_annual")
    pdq = co.get("period_date_quarterly")
    if pda and pdq:
        try:
            d_a = datetime.fromisoformat(pda[:10])
            d_q = datetime.fromisoformat(pdq[:10])
            months = (d_q.year - d_a.year) * 12 + (d_q.month - d_a.month)
            quarters_since = max(0, min(4, round(months / 3)))
        except ValueError:
            quarters_since = 0

    # Build methodology choices. If CIQ-sourced S&P issuer rating is
    # available, wire it to actual_rating + kd_approach='actual_rating'
    # so Module 2 uses the actual rating instead of industry fallback.
    # Geographic segments — run the ingested screener segments through the
    # same resolver the template path uses so Cost-of-Capital can blend the
    # country ERPs and show the mapped/unresolved state on the segment UI.
    raw_geo = co.get("geographic_segments") or []
    geo_segments_input: list[GeographicSegment] = []
    for s in resolve_segments(raw_geo, store):
        r = s["resolution"]
        geo_segments_input.append(GeographicSegment(
            name=s["name"],
            revenue=s["revenue"],
            pct=s.get("pct"),
            resolution=SegmentResolution(
                raw_name=r["raw_name"],
                mapped_to=r.get("mapped_to"),
                mapped_kind=r.get("mapped_kind", "unresolved"),
                erp=r.get("erp"),
                members=[SegmentMember(**m) for m in (r.get("members") or [])],
                confidence=r.get("confidence", 0.0),
                source=r.get("source", "auto"),
                note=r.get("note"),
            ),
        ))

    methodology_kwargs: dict = {"geographic_segments": geo_segments_input}
    rating_raw = co.get("actual_rating_fc") or co.get("actual_rating_lc")
    # Normalize CIQ S&P/Moody's labels ("BBB", "A-", "Baa2"…) to the compound
    # bucket key used by the rating-spread table (e.g. "Baa2/BBB"). Without
    # this, module_2 falls back to industry spread with a warning.
    rating = _clean_rating(rating_raw)
    if rating:
        methodology_kwargs["actual_rating"] = rating
        methodology_kwargs["kd_approach"] = "actual_rating"
    methodology = MethodologyChoices(**methodology_kwargs)

    # Assemble
    inputs = CompanyValuationInput(
        ticker=ticker,
        company_name=co.get("company_name"),
        country=country,
        reporting_currency=co.get("filing_currency"),
        stock_price_currency=co.get("listing_currency"),
        fx_rate=fx_rate,
        fx_rate_source=fx_source,
        fx_rate_date=co.get("period_date_annual"),
        raw_financials=raw_financials,
        quarterly_financials=quarterly_financials,
        quarters_since_10k=quarters_since,
        period_date_10k=co.get("period_date_annual"),
        period_date_10q=co.get("period_date_quarterly"),
        effective_tax_rate_ciq=co.get("effective_tax_rate"),
        adjustment_inputs=adj_inputs,
        macro_inputs=macro,
        industry_data=industry_data,
        industry_data_global=industry_data_global,
        option_inputs=option_inputs,
        valuation_assumptions=ValuationAssumptions(),
        methodology_choices=methodology,
    )
    return inputs


@valuation_router.post("/from-database")
def from_database(req: FromDatabaseRequest) -> dict:
    """Run the full valuation pipeline starting from a DB-sourced ticker.
    Returns the same shape as /valuation/fetch-from-file."""
    try:
        with db.get_connection() as conn:
            record = db.fetch_company(conn, req.ticker)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")
    if record is None:
        raise HTTPException(status_code=404, detail=f"Ticker not in database: {req.ticker}")

    from engine.orchestrator import run_full_valuation
    from api.routes import _build_lookups, _get_damodaran_store, _report_to_dict
    from api.session_store import create_session

    inputs = _db_record_to_company_input(record, req.risk_free_rate, req.industry_override)
    store = _get_damodaran_store()
    ind_lookup, cerp_lookup = _build_lookups(store)
    report = run_full_valuation(inputs, industry_lookup=ind_lookup, country_erp_lookup=cerp_lookup)

    # Use the same session layout + serializer the template path uses so the
    # response shape is byte-identical.
    session = create_session(inputs, report)
    result = _report_to_dict(session)
    # Mirror the template-path's root-level context fields (company_name,
    # country, industry_name). Template path sets these after
    # _report_to_dict in routes.py::fetch_from_file; we replicate here so
    # the two paths return identical top-level shapes.
    result["company_name"] = inputs.company_name
    result["country"] = inputs.country
    result["industry_name"] = inputs.industry_data.industry_name if inputs.industry_data else None
    return result
