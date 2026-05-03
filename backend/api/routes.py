"""All API endpoints in one file."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine.data_dictionary import (
    CompanyValuationInput, MacroInputs, ValuationAssumptions,
    RawFinancials, AdjustmentInputs, OptionInputs,
)
from engine.orchestrator import run_full_valuation
from engine.source_tracker import SourceTracker
from data_sources.damodaran_store import DamodaranStore
from data_sources.industry_mapper import IndustryMapper
from data_sources.exchange_currency_map import get_stock_price_currency
from .session_store import create_session, get_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ginzu Understanding convention: the primary "industry data" payload attached
# to every valuation is the US industry table (betas.xls, wacc.xls, margin.xls).
# The frontend Cost-of-Capital methodology selector then lets the analyst pick:
#   - "Single Business(US)"     → use the US industry data (default; matches Ginzu)
#   - "Single Business(Global)" → switch to the Global industry table
#   - "Multi-business(US/Global)" → user-supplied EV-weighted segments
#   - "Direct Input"            → user-supplied β
#
# Regional tables (China / Emerging / Europe / Japan / India / Rest) are still
# available in the DamodaranStore but are NOT used for single-business β lookups.
# They're retained because `ctryprem` country ERPs aggregate to region-level
# ERPs for the "Operating Regions" ERP branch in module_2_risk.py.
#
# This function is kept for backward-compat with a few UI-only callers that
# display which region a company is "classified into" — but it no longer drives
# industry-data selection.
def _country_to_region_display(country: str) -> str:
    """Display-only region hint for a country. Does NOT drive industry lookup."""
    if not country:
        return "US"
    c = country.lower()
    if any(k in c for k in ("china", "hong kong", "macau", "taiwan")):
        return "China"
    if "india" in c:
        return "India"
    if "japan" in c:
        return "Japan"
    if any(k in c for k in ("kingdom", "germany", "france", "italy", "spain",
                            "netherlands", "switzerland", "sweden", "norway",
                            "denmark", "finland", "belgium", "austria", "ireland",
                            "portugal", "greece")):
        return "Europe"
    if any(k in c for k in ("united states", "america", "canada")):
        return "US"
    return "Global"


# Alias for callers that still reference the old name. Kept to avoid churn;
# always returns "US" so industry-data lookups default to Ginzu's convention.
def _country_to_region(country: str) -> str:
    """Always returns 'US' — industry-data region is decided by the analyst's
    methodology_choices.beta_approach selector, not by the company's country.
    This matches Ginzu's default behavior (Single Business(US))."""
    return "US"

router = APIRouter(prefix="/api")

# Pre-load Damodaran data and industry mapper at startup
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base"
_damodaran_store: DamodaranStore | None = None
_industry_mapper: IndustryMapper | None = None


def _get_damodaran_store() -> DamodaranStore:
    global _damodaran_store
    if _damodaran_store is None:
        dam_dir = _DATA_DIR / "damodaran"
        if dam_dir.exists():
            _damodaran_store = DamodaranStore.from_directory(str(dam_dir))
            logger.info(f"Loaded Damodaran store: {_damodaran_store.industries_loaded}")
        else:
            raise HTTPException(status_code=503, detail=f"Damodaran data not found at {dam_dir}")
    return _damodaran_store


def _build_lookups(store: DamodaranStore):
    """Build the industry_lookup + country_erp_lookup callables that enable
    multi-business β and operating-countries ERP branches in M2."""

    def _industry_lookup(industry_name: str, region: str):
        return store.lookup_industry(industry_name, region=region)

    def _country_erp_lookup(country_name: str):
        m = store.lookup_country(country_name)
        if m is None:
            return None
        return (m.equity_risk_premium or 0.0) + (m.country_risk_premium or 0.0)

    return _industry_lookup, _country_erp_lookup


# ISO 4217 currency codes (common subset) — used as options in manual-entry
# dropdowns when the exchange prefix is unknown.
_ISO_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "CNY", "HKD", "CHF", "CAD", "AUD", "NZD",
    "SEK", "NOK", "DKK", "SGD", "KRW", "TWD", "INR", "THB", "MYR", "IDR",
    "PHP", "VND", "ILS", "SAR", "AED", "QAR", "KWD", "BHD", "OMR", "JOD",
    "EGP", "ZAR", "NGN", "KES", "GHS", "MAD", "TND", "BRL", "MXN", "CLP",
    "ARS", "COP", "PEN", "PLN", "CZK", "HUF", "RON", "BGN", "HRK", "TRY",
    "RUB", "UAH", "PKR", "BDT", "LKR",
]


def _build_unresolved_fields(
    inputs,
    store: "DamodaranStore",
    current: dict | None = None,
    industry_resolved: bool = True,
) -> list[dict]:
    """Scan the valuation inputs for fields that couldn't be auto-resolved.

    The frontend reads this list and presents manual-entry UI so the user can
    fix gaps (e.g., industry missing from indname, effective tax #N/A, etc.)
    instead of having the engine silently default.
    """
    unresolved: list[dict] = []

    # --- Industry ---
    ind = inputs.industry_data
    if not industry_resolved:
        # Industry couldn't be auto-looked-up; a placeholder was applied so the
        # pipeline could run. Surface so user picks from the 94-industry dropdown.
        unresolved.append({
            "path": "industry_data.industry_name",
            "kind": "enum",
            "reason": (
                f"Ticker not found in Damodaran's indname.xlsx or supplemental_companies.json. "
                f"Placeholder industry '{ind.industry_name if ind else '?'}' applied so the valuation can run — "
                f"please pick the correct industry."
            ),
            "options": store.list_industries("US"),
            "current_value": ind.industry_name if ind else None,
            "required": True,
        })
    elif ind is None or not ind.industry_name:
        unresolved.append({
            "path": "industry_data.industry_name",
            "kind": "enum",
            "reason": "Industry not set.",
            "options": store.list_industries("US"),
            "current_value": None,
            "required": True,
        })
    elif ind.beta_u is None or ind.beta_u == 0:
        unresolved.append({
            "path": "industry_data.industry_name",
            "kind": "enum",
            "reason": f"Industry '{ind.industry_name}' classified but beta data is missing.",
            "options": store.list_industries("US"),
            "current_value": ind.industry_name,
            "required": True,
        })

    # --- Country ---
    macro = inputs.macro_inputs
    countries = store.list_countries()
    if not inputs.country or inputs.country not in countries:
        unresolved.append({
            "path": "country",
            "kind": "country",
            "reason": (
                f"Country '{inputs.country}' not found in Damodaran country-risk dataset."
                if inputs.country else
                "CIQ did not return a country for this ticker."
            ),
            "options": countries,
            "current_value": inputs.country,
            "required": True,
        })

    # --- Tax rates ---
    if macro.tax_rate_marginal is None or macro.tax_rate_marginal == 0:
        unresolved.append({
            "path": "macro_inputs.tax_rate_marginal",
            "kind": "percentage",
            "reason": "Marginal tax rate couldn't be looked up from countrytaxrates.xls.",
            "current_value": macro.tax_rate_marginal,
            "suggestion": 0.25,
            "required": True,
        })
    if inputs.effective_tax_rate_ciq is None:
        unresolved.append({
            "path": "effective_tax_rate_ciq",
            "kind": "percentage",
            "reason": "CIQ returned no effective tax rate (often #N/A for firms with negative EBT).",
            "current_value": None,
            "suggestion": macro.tax_rate_marginal,
            "required": False,
        })

    # --- Stock price currency ---
    if not inputs.stock_price_currency:
        unresolved.append({
            "path": "stock_price_currency",
            "kind": "currency",
            "reason": "Exchange prefix not recognized in exchange_currency_map.py.",
            "options": _ISO_CURRENCIES,
            "current_value": None,
            "required": True,
        })

    # --- FX rate unavailable + currencies differ ---
    if (
        inputs.reporting_currency
        and inputs.stock_price_currency
        and inputs.reporting_currency != inputs.stock_price_currency
        and inputs.fx_rate is None
    ):
        unresolved.append({
            "path": "fx_rate",
            "kind": "number",
            "reason": (
                f"Currencies differ ({inputs.stock_price_currency} listing vs {inputs.reporting_currency} "
                "reporting) but CIQ template didn't supply stock_price_reporting. "
                "Re-run the CIQ template OR enter FX rate manually."
            ),
            "current_value": None,
            "required": True,
        })

    # --- Shares outstanding ---
    if inputs.raw_financials and not inputs.raw_financials[0].shares_outstanding:
        unresolved.append({
            "path": "raw_financials.0.shares_outstanding",
            "kind": "number",
            "reason": "Shares outstanding missing from CIQ (no IQ_BASIC_WEIGHT value).",
            "current_value": None,
            "required": True,
        })

    return unresolved


def _get_industry_mapper() -> IndustryMapper:
    global _industry_mapper
    if _industry_mapper is None:
        lookup_file = _DATA_DIR / "industry_lookup" / "indname.xlsx"
        if lookup_file.exists():
            _industry_mapper = IndustryMapper.from_file(str(lookup_file))
            logger.info(f"Loaded industry mapper: {_industry_mapper.total_companies} companies")
        else:
            raise HTTPException(status_code=503, detail=f"Industry lookup not found at {lookup_file}")
    return _industry_mapper


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ValuationRequest(BaseModel):
    """POST body: full CompanyValuationInput as JSON."""
    inputs: CompanyValuationInput


class OverrideRequest(BaseModel):
    """PATCH body: partial overrides to recompute.

    Keys are dot-paths like "macro_inputs.risk_free_rate" or
    "valuation_assumptions.high_growth_years". Values can be scalars or
    structured objects — e.g. overriding
    "methodology_choices.geographic_segments" requires a list of segment
    dicts, each carrying its own `resolution` object for the user's
    manual country/region mapping.
    """
    # Accept any JSON-serializable value. Pydantic will coerce nested
    # structures when CompanyValuationInput is rebuilt in patch_valuation.
    overrides: dict[str, object | None]


def _report_to_dict(session) -> dict:
    """Serialize a session to a JSON-friendly dict."""
    r = session.report
    # Attach industry statistical distributions (Q1/Median/Q3 benchmarks) if available
    industry_stats = None
    try:
        store = _get_damodaran_store()
        ind_name = session.inputs.industry_data.industry_name if session.inputs.industry_data else None
        if ind_name:
            industry_stats = store.lookup_industry_stats(ind_name)
    except Exception:
        industry_stats = None

    ltm_dump = r.ltm_financials.model_dump() if r.ltm_financials else None
    result = {
        "id": session.id,
        "ticker": r.ticker,
        "inputs": session.inputs.model_dump(),
        "ltm_financials": ltm_dump,
        "adjusted": r.adjusted.model_dump() if r.adjusted else None,
        "cost_of_capital": r.cost_of_capital.model_dump() if r.cost_of_capital else None,
        "cashflow": r.cashflow.model_dump() if r.cashflow else None,
        "dcf": r.dcf.model_dump() if r.dcf else None,
        "multiples": r.multiples.model_dump() if r.multiples else None,
        "final": r.final.model_dump() if r.final else None,
        "warnings": r.warnings,
        "source_metadata": session.source_tracker.to_dict() if session.source_tracker else {},
        "industry_stats": industry_stats,
        "unresolved_fields": getattr(session, "unresolved_fields", []) or [],
    }
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/search")
def search_companies(q: str, max_results: int = 20):
    """Search companies by ticker, name, or exchange code. Returns candidates for confirmation."""
    mapper = _get_industry_mapper()
    results = mapper.search(q, max_results=max_results)
    return {
        "query": q,
        "count": len(results),
        "results": [
            {
                "exchange_ticker": r.exchange_ticker,
                "company_name": r.company_name,
                "country": r.country,
                "industry": r.industry_group,
                "exchange": r.exchange_ticker.split(":")[0] if ":" in r.exchange_ticker else "",
                "symbol": r.exchange_ticker.split(":")[-1] if ":" in r.exchange_ticker else r.exchange_ticker,
                "region": _country_to_region(r.country),
            }
            for r in results
        ],
    }


class FetchRequest(BaseModel):
    """POST body for ticker-based fetch."""
    ticker: str
    region: str = "US"
    risk_free_rate: float = 0.0425
    industry_override: str | None = None


@router.post("/valuation/fetch")
def fetch_and_run(req: FetchRequest):
    """Look up ticker in Damodaran/industry data, build inputs, run full pipeline."""
    store = _get_damodaran_store()
    mapper = _get_industry_mapper()

    # 1. Look up company → industry + country
    company_info = mapper.lookup(req.ticker)
    if company_info is None and not req.industry_override:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{req.ticker}' not found in industry lookup. "
                   f"Try the full Exchange:Ticker format (e.g. NasdaqGS:AAPL) or provide industry_override.",
        )

    company_name = company_info.company_name if company_info else req.ticker
    country = (company_info.country if company_info else None) or "United States"
    industry_name = req.industry_override or (company_info.industry_group if company_info else None)

    if not industry_name:
        raise HTTPException(status_code=422, detail=f"Could not determine industry for '{req.ticker}'.")

    # 2. Industry lookup — ALWAYS use US region as the primary payload
    # (Ginzu convention: Single Business(US) is the default regardless of firm
    # location). Regional data is available through methodology_choices at runtime.
    primary_region = "US"
    industry_data = store.lookup_industry(industry_name, region=primary_region)
    if industry_data is None:
        # Last-resort fallback: try Global
        industry_data = store.lookup_industry(industry_name, region="Global")
        if industry_data:
            primary_region = "Global"
    if industry_data is None:
        available = store.list_industries("US")
        raise HTTPException(
            status_code=422,
            detail=f"Industry '{industry_name}' not found. Available ({len(available)}): {available[:20]}...",
        )

    # 3. Look up country macro data
    macro = store.lookup_country(country)
    if macro is None:
        erp = store.get_mature_market_erp() or 0.05
        macro = MacroInputs(
            risk_free_rate=req.risk_free_rate,
            equity_risk_premium=erp,
            tax_rate_marginal=0.21,
        )
    else:
        macro.risk_free_rate = req.risk_free_rate

    # 3b. Always show Global as comparison
    industry_data_global = None
    if primary_region != "Global":
        industry_data_global = store.lookup_industry(industry_name, region="Global")

    # 3c. Determine currencies — use exchange_ticker (e.g. "NasdaqGS:NVDA") not bare ticker
    stock_price_currency = get_stock_price_currency(company_info.exchange_ticker) if company_info else None

    # 4. Build skeleton inputs (no CapIQ data yet — user will fill financials manually
    #    or we can try CapIQ COM automation)
    inputs = CompanyValuationInput(
        ticker=req.ticker,
        company_name=company_name,
        country=country,
        stock_price_currency=stock_price_currency,
        raw_financials=[],  # Empty — frontend will show "needs financial data"
        macro_inputs=macro,
        industry_data=industry_data,
        industry_data_global=industry_data_global,
        valuation_assumptions=ValuationAssumptions(),
    )

    # 5. Prepare CIQ template and open in Excel for the user
    #    COM automation can't connect to Excel from the web server due to Windows security.
    #    Instead: prepare the template with the ticker, open it, and tell the user to save.
    #    The user then uploads the saved file via the "Upload CIQ File" button.
    capiq_warnings: list[str] = []
    try:
        import openpyxl as _oxl

        ciq_dir = _DATA_DIR / "ciq_fetches"
        template_file = ciq_dir / "CIQ_Fetch_Template.xlsx"

        if template_file.exists():
            # Prepare template with ticker in B1
            work_copy = ciq_dir / f"_active_fetch.xlsx"
            twb = _oxl.load_workbook(str(template_file))
            twb["CIQ_Data"]["B1"] = req.ticker
            twb.save(str(work_copy))
            twb.close()

            # Open in Excel (like double-clicking) — Windows only
            import os, sys
            if sys.platform == "win32" and hasattr(os, "startfile"):
                os.startfile(str(work_copy))
                capiq_warnings.append(
                    f"CIQ template opened in Excel for {req.ticker}. "
                    f"Wait for data to load, then save (Ctrl+S) and upload the file."
                )
            else:
                # Linux / Mac: can't auto-open Excel. User must download template and resolve on a Windows machine.
                capiq_warnings.append(
                    f"CIQ template prepared at {work_copy.name}. "
                    f"Download via /api/valuation/generate-template, resolve on a Windows machine with the CIQ plugin, "
                    f"and upload the saved file via /api/valuation/fetch-from-file."
                )
        else:
            capiq_warnings.append("CIQ template not found. Please upload CIQ file manually.")
    except Exception as e:
        capiq_warnings.append(f"Could not open CIQ template: {e}. Please upload CIQ file manually.")

    # 6. Run pipeline if we have financials
    if inputs.raw_financials:
        ind_lookup, cerp_lookup = _build_lookups(store)
        report = run_full_valuation(inputs, industry_lookup=ind_lookup, country_erp_lookup=cerp_lookup)
    else:
        from engine.orchestrator import ValuationReport
        report = ValuationReport(
            ticker=req.ticker,
            warnings=capiq_warnings + ["No financial data — enter manually or upload CapIQ export."],
        )

    session = create_session(inputs, report)
    result = _report_to_dict(session)
    result["capiq_warnings"] = capiq_warnings
    result["company_name"] = company_name
    result["country"] = country
    result["industry_name"] = industry_name
    return result


@router.post("/valuation/generate-template")
def generate_template(ticker: str = "NVDA"):
    """Generate a CIQ template Excel file and return it for download."""
    from tools.generate_ciq_template import generate_template as gen_tmpl
    output_path = gen_tmpl(ticker)
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"CIQ_Fetch_Template.xlsx",
    )


class FileUploadFetchRequest(BaseModel):
    region: str = "US"
    risk_free_rate: float = 0.0425
    industry_override: str | None = None


@router.post("/valuation/fetch-from-file")
async def fetch_from_file(
    file: UploadFile = File(...),
    region: str = Form("US"),
    risk_free_rate: float = Form(0.0425),
    industry_override: str | None = Form(None),
):
    """
    Read a resolved CIQ template Excel file and run the valuation pipeline.

    The file should be a CIQ_Fetch_Template.xlsx that was:
    1. Generated by /api/valuation/generate-template
    2. Opened in Excel with CIQ plugin
    3. Saved after all formulas resolved
    """
    from tools.read_ciq_template import read_ciq_template
    import tempfile, shutil

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        ciq_data = read_ciq_template(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read CIQ file: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    ticker = ciq_data["ticker"]
    if not ticker:
        raise HTTPException(status_code=422, detail="No ticker found in B1 of the uploaded file.")

    # Hoist CIQ dict sections so they're in scope for the whole function
    # (industry fallback path needs `current` for primary_exchange lookup).
    current = ciq_data.get("current") or {}

    store = _get_damodaran_store()
    mapper = _get_industry_mapper()

    # Look up company info
    company_info = mapper.lookup(ticker)
    company_name = company_info.company_name if company_info else ticker
    country = company_info.country if company_info else "United States"
    industry_name = industry_override or (company_info.industry_group if company_info else None)

    # Industry lookup — ALWAYS use US region (Ginzu convention: Single Business(US)).
    # Analyst can override via methodology_choices.beta_approach on the frontend.
    # GRACEFUL DEGRADATION: if industry can't be resolved, use a placeholder and
    # surface via unresolved_fields so the user can manually select from the
    # dropdown of 94 Damodaran industries. Don't block the upload.
    primary_region = "US"
    industry_resolved = False
    industry_data = store.lookup_industry(industry_name, region=primary_region) if industry_name else None
    if industry_data is None and industry_name:
        industry_data = store.lookup_industry(industry_name, region="Global")
        if industry_data:
            primary_region = "Global"
    if industry_data is not None:
        industry_resolved = True
    else:
        # Last-resort placeholder — use a safe default so the pipeline can run.
        # The unresolved_fields list will flag this so the user picks an industry.
        placeholder_name = industry_name or "Semiconductor"
        industry_data = store.lookup_industry(placeholder_name, region="US")
        if industry_data is None:
            available = store.list_industries("US")
            industry_data = store.lookup_industry(available[0], region="US") if available else None
        if industry_data is None:
            raise HTTPException(status_code=422, detail="Damodaran industry store is empty; cannot build valuation.")

    macro = store.lookup_country(country)
    if macro is None:
        erp = store.get_mature_market_erp() or 0.05
        macro = MacroInputs(risk_free_rate=risk_free_rate, equity_risk_premium=erp, tax_rate_marginal=0.21)
    else:
        macro.risk_free_rate = risk_free_rate

    # Always show Global as comparison (unless primary is already Global)
    # Use the resolved industry name (may differ from original if fallback was applied)
    resolved_industry = industry_data.industry_name if industry_data else industry_name
    industry_data_global = store.lookup_industry(resolved_industry, region="Global") if (primary_region != "Global" and resolved_industry) else None

    # Determine stock price currency: try exchange_ticker first, then CIQ primary_exchange
    stock_price_currency = None
    if company_info and company_info.exchange_ticker:
        stock_price_currency = get_stock_price_currency(company_info.exchange_ticker)
    if not stock_price_currency:
        # Try CIQ primary_exchange field (e.g., "HKSE" → look up currency)
        ciq_exchange = current.get("primary_exchange")
        if ciq_exchange and isinstance(ciq_exchange, str):
            from data_sources.exchange_currency_map import EXCHANGE_CURRENCY
            stock_price_currency = EXCHANGE_CURRENCY.get(ciq_exchange.strip())

    # Compute effective tax rate from CIQ EBT and tax expense
    yr0_ciq = ciq_data["annual"].get(0, {})
    ebt = _fval_or_none(yr0_ciq, "earnings_before_tax")
    tax_exp = _fval_or_none(yr0_ciq, "total_tax_expense")
    if ebt and tax_exp and ebt > 0:
        macro.tax_rate_effective = abs(tax_exp) / abs(ebt)

    # Build RawFinancials from the parsed CIQ data
    annual = ciq_data["annual"]
    # `current` already hoisted above; this keeps the code readable at the usage site
    period_dates = ciq_data.get("period_dates", {})

    # Derive base fiscal year from period_date_annual (FY-0)
    # e.g., "Mar 31, 2025" → 2025; "Jan 26, 2026" → 2026
    base_fy_year = datetime.now().year  # fallback
    fy0_date_str = period_dates.get("period_date_annual")
    if fy0_date_str:
        try:
            from dateutil import parser as dateparser
            fy0_date = dateparser.parse(fy0_date_str)
            if fy0_date:
                base_fy_year = fy0_date.year
        except Exception:
            pass

    raw_financials = []
    for fy_offset in sorted(annual.keys()):
        data = annual[fy_offset]
        if fy_offset == 0:
            data.update({k: v for k, v in current.items()
                         if k not in ("reporting_currency", "primary_exchange")
                         and v is not None})
        # Currency handling (FY0 only — market/listing data doesn't exist for prior years):
        # - `mv_equity` is populated with the REPORTING-currency value for WACC math.
        #   If the <FILING>-override field is missing (e.g., CIQ template hasn't been
        #   regenerated with the new fields yet), fall back to the listing-currency
        #   mv_equity as the math payload. This degrades gracefully: the Phase-2
        #   fallback UI will flag it.
        # - `mv_equity_listing` preserves the as-traded (listing-ccy) value for UI display.
        # - `stock_price` stays as the listing-ccy price (UI continuity with brokers).
        # - `stock_price_reporting` is the same price converted to reporting ccy.
        if fy_offset == 0:
            mv_listing   = _fval_or_none(data, "mv_equity")              # always listing ccy
            mv_reporting = _fval_or_none(data, "mv_equity_reporting")    # None if old template
            # Fallback: derive reporting-currency mv_equity via the derived
            # fx_rate when the CIQ template didn't supply mv_equity_reporting
            # directly. Prevents the downstream currency-mixing bug where
            # mv_for_math ends up in listing currency but bv_debt / cash stay
            # in reporting, corrupting EV and the market multiples.
            if mv_reporting is None and mv_listing is not None and fx_rate is not None:
                mv_reporting = mv_listing * fx_rate
            mv_for_math  = mv_reporting if mv_reporting is not None else mv_listing
            sp_listing   = _fval_or_none(data, "stock_price")
            sp_reporting = _fval_or_none(data, "stock_price_reporting")
        else:
            mv_listing = mv_reporting = mv_for_math = None
            sp_listing = sp_reporting = None
        rf = RawFinancials(
            fiscal_year=base_fy_year - fy_offset,
            revenues=_fval(data, "revenues"),
            ebit=_fval(data, "ebit"),
            ebitda=_fval_or_none(data, "ebitda"),
            net_income=_fval_or_none(data, "net_income"),
            interest_expense=_fval_or_none(data, "interest_expense"),
            capex=_fval_or_none(data, "capex"),
            d_a=_fval_or_none(data, "d_a"),
            noncash_wc=_fval_or_none(data, "noncash_wc"),
            change_in_noncash_wc=_fval_or_none(data, "change_in_noncash_wc"),
            net_debt_issued=_fval_or_none(data, "net_debt_issued"),
            cash_and_marketable_securities=_fval_or_none(data, "cash_and_marketable_securities"),
            bv_equity=_fval_or_none(data, "bv_equity"),
            bv_debt=_fval_or_none(data, "bv_debt"),
            mv_equity=mv_for_math if fy_offset == 0 else _fval_or_none(data, "mv_equity"),
            mv_equity_listing=mv_listing,
            mv_debt=_fval_or_none(data, "mv_debt"),
            shares_outstanding=_fval_or_none(data, "shares_outstanding"),
            stock_price=sp_listing if fy_offset == 0 else _fval_or_none(data, "stock_price"),
            stock_price_reporting=sp_reporting,
            cross_holdings=_fval_or_none(data, "cross_holdings"),
            minority_interests=_fval_or_none(data, "minority_interests"),
            r_and_d_expense=_fval_or_none(data, "r_and_d_expense"),
            earnings_before_tax=_fval_or_none(data, "earnings_before_tax"),
            total_tax_expense=_fval_or_none(data, "total_tax_expense"),
        )
        raw_financials.append(rf)

    # Build quarterly financials
    quarterly = ciq_data["quarterly"]
    quarterly_financials = []
    for q_offset in sorted(quarterly.keys()):
        qdata = quarterly[q_offset]
        qrf = RawFinancials(
            fiscal_year=q_offset,
            revenues=_fval(qdata, "revenues"),
            ebit=_fval(qdata, "ebit"),
            ebitda=_fval_or_none(qdata, "ebitda"),
            net_income=_fval_or_none(qdata, "net_income"),
            interest_expense=_fval_or_none(qdata, "interest_expense"),
            capex=_fval_or_none(qdata, "capex"),
            d_a=_fval_or_none(qdata, "d_a"),
            noncash_wc=_fval_or_none(qdata, "noncash_wc"),
            change_in_noncash_wc=_fval_or_none(qdata, "change_in_noncash_wc"),
            net_debt_issued=_fval_or_none(qdata, "net_debt_issued"),
            cash_and_marketable_securities=_fval_or_none(qdata, "cash_and_marketable_securities"),
            bv_equity=_fval_or_none(qdata, "bv_equity"),
            bv_debt=_fval_or_none(qdata, "bv_debt"),
            shares_outstanding=_fval_or_none(qdata, "shares_outstanding"),
            cross_holdings=_fval_or_none(qdata, "cross_holdings"),
            minority_interests=_fval_or_none(qdata, "minority_interests"),
            r_and_d_expense=_fval_or_none(qdata, "r_and_d_expense"),
            earnings_before_tax=_fval_or_none(qdata, "earnings_before_tax"),
            total_tax_expense=_fval_or_none(qdata, "total_tax_expense"),
        )
        quarterly_financials.append(qrf)

    # Extract currencies
    reporting_currency = None
    rc = current.get("reporting_currency")
    if rc and isinstance(rc, str):
        reporting_currency = rc

    # Build R&D past expenses
    r_and_d_past = []
    for yr in range(1, 11):
        yr_data = annual.get(yr, {})
        rd = _fval_or_none(yr_data, "r_and_d_expense")
        r_and_d_past.append(rd or 0.0)

    yr0_data = annual.get(0, {})
    lease_commitments = []
    for key in ["lease_commitment_yr1", "lease_commitment_yr2", "lease_commitment_yr3",
                 "lease_commitment_yr4", "lease_commitment_yr5", "lease_commitment_beyond"]:
        val = _fval_or_none(current, key) or _fval_or_none(yr0_data, key)
        lease_commitments.append(val or 0.0)

    # Damodaran industry-specific R&D amortization period recommendation.
    # Shorter horizons for fast-moving tech/consumer; longer for pharma/aerospace.
    # Source: Damodaran R&D amortization appendix (industry defaults).
    _AMORT_PERIOD_BY_INDUSTRY = {
        # 3 years — short payoff horizon
        "Retail (Online)": 3, "Software (Internet)": 3, "Software (Entertainment)": 3,
        # 5 years — default for most industries including general tech / software / semi
        # (leave as 5 via the default below)
        # 10 years — long-horizon research
        "Drugs (Pharmaceutical)": 10, "Drugs (Biotechnology)": 10,
        "Aerospace/Defense": 10, "Healthcare Products": 10,
        "Chemical (Basic)": 10, "Chemical (Diversified)": 10, "Chemical (Specialty)": 10,
        "Oil/Gas (Integrated)": 10, "Oil/Gas (Production and Exploration)": 10,
    }
    amort_default = _AMORT_PERIOD_BY_INDUSTRY.get(industry_name, 5)

    adj_inputs = AdjustmentInputs(
        amortization_period_n=amort_default,
        r_and_d_expense_current=_fval(yr0_data, "r_and_d_expense"),
        r_and_d_expense_past=r_and_d_past,
        operating_lease_expense_current=_fval(yr0_data, "operating_lease_expense"),
        operating_lease_commitments=lease_commitments,
        has_r_and_d=_fval(yr0_data, "r_and_d_expense") > 0,
        has_operating_leases=_fval(yr0_data, "operating_lease_expense") > 0,
    )

    option_inputs = OptionInputs(
        number_of_options=_fval(current, "options_outstanding"),
        average_strike_price=_fval(current, "options_avg_strike"),
        average_maturity=_fval(current, "options_avg_maturity"),
        has_options=_fval(current, "options_outstanding") > 0,
    )

    # Extract period dates (period_dates already extracted above)
    period_date_10k = period_dates.get("period_date_annual") or period_dates.get("period_date_10k")
    period_date_10q = period_dates.get("period_date_quarterly") or period_dates.get("period_date_10q")

    # Compute quarters_since_10k from period dates
    quarters_since = 0
    if period_date_10k and period_date_10q:
        try:
            from dateutil import parser as dateparser
            d10k = dateparser.parse(period_date_10k)
            d10q = dateparser.parse(period_date_10q)
            if d10k and d10q:
                months_diff = (d10q.year - d10k.year) * 12 + (d10q.month - d10k.month)
                quarters_since = max(0, round(months_diff / 3))
        except Exception:
            pass

    # Build per-year period dates map: {"0": "46047", "1": "45661", ...}
    period_dates_annual: dict[str, str | None] = {}
    for key, val in period_dates.items():
        if key.startswith("period_date_annual_fy"):
            fy_off = key.replace("period_date_annual_fy", "")
            period_dates_annual[fy_off] = val

    # Get CIQ-fetched effective tax rate (from current/market data)
    effective_tax_rate_ciq_val = _fval_or_none(current, "effective_tax_rate_ciq")

    # Derive FX rate (listing → reporting) from the two CIQ stock-price variants.
    # Only valid when BOTH are present and non-zero. Otherwise mark unavailable
    # and downstream math falls back to listing-currency mv_equity (with warning).
    fx_rate = None
    fx_rate_source = "unknown"
    sp_listing = _fval_or_none(current, "stock_price")
    sp_reporting = _fval_or_none(current, "stock_price_reporting")
    if reporting_currency and stock_price_currency and reporting_currency == stock_price_currency:
        fx_rate = 1.0
        fx_rate_source = "same currency"
    elif sp_listing and sp_reporting and sp_listing > 0:
        fx_rate = sp_reporting / sp_listing
        fx_rate_source = "CIQ implied"
    elif sp_listing and sp_reporting is None:
        fx_rate_source = "unavailable (CIQ template missing stock_price_reporting)"

    # Geographic segments: run through the resolver (exact → alias → composite →
    # weak default → unresolved). Each segment arrives with a SegmentResolution
    # embedded. Frontend can show the raw data + resolver suggestion, and user
    # can override via the segment-mapping UI.
    from engine.segment_resolver import resolve_segments
    from engine.data_dictionary import GeographicSegment, SegmentResolution, SegmentMember, MethodologyChoices
    raw_geo = ciq_data.get("geo_segments") or []
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

    # Actual credit rating from CIQ — when present and valid, auto-switch
    # kd_approach to 'actual_rating' so the WACC uses the rating-implied
    # spread. Empty / NA / zero → leave kd_approach at its default, user
    # can still override via the WACC-page dropdown.
    rating_raw = current.get("actual_rating") if current else None
    parsed_rating = _clean_rating(rating_raw)

    methodology_kwargs: dict = {"geographic_segments": geo_segments_input}
    if parsed_rating is not None:
        methodology_kwargs["actual_rating"] = parsed_rating
        methodology_kwargs["kd_approach"] = "actual_rating"
    methodology = MethodologyChoices(**methodology_kwargs)

    inputs = CompanyValuationInput(
        ticker=ticker,
        company_name=company_name,
        country=country,
        reporting_currency=reporting_currency,
        stock_price_currency=stock_price_currency,
        fx_rate=fx_rate,
        fx_rate_source=fx_rate_source,
        fx_rate_date=period_date_10k or period_date_10q,
        raw_financials=raw_financials,
        quarterly_financials=quarterly_financials,
        period_date_10k=period_date_10k,
        period_date_10q=period_date_10q,
        period_dates_annual=period_dates_annual,
        effective_tax_rate_ciq=effective_tax_rate_ciq_val,
        quarters_since_10k=quarters_since,
        adjustment_inputs=adj_inputs,
        macro_inputs=macro,
        industry_data=industry_data,
        industry_data_global=industry_data_global,
        option_inputs=option_inputs,
        valuation_assumptions=ValuationAssumptions(),
        methodology_choices=methodology,
    )

    if inputs.raw_financials:
        ind_lookup, cerp_lookup = _build_lookups(store)
        report = run_full_valuation(inputs, industry_lookup=ind_lookup, country_erp_lookup=cerp_lookup)
    else:
        from engine.orchestrator import ValuationReport
        report = ValuationReport(ticker=ticker, warnings=["No financial data in uploaded file."])

    # Build the unresolved_fields list — places where auto-resolve failed and
    # the user should manually override. Each entry describes what to show.
    unresolved = _build_unresolved_fields(inputs, store, current, industry_resolved=industry_resolved)

    session = create_session(inputs, report, unresolved_fields=unresolved)
    result = _report_to_dict(session)
    result["company_name"] = company_name
    result["country"] = country
    result["industry_name"] = industry_name
    return result


def _fval(data: dict, key: str) -> float:
    """Get float value from dict, default 0.0."""
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) else 0.0


def _fval_or_none(data: dict, key: str) -> float | None:
    """Get float value from dict, or None."""
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) else None


# S&P label → compound Moody's/S&P key used by the module_2_risk rating
# spread table. CIQ's IQ_SP_ISSUER_RATING returns S&P labels ("A+",
# "BBB-", ...) — we map them to the table's compound form so
# `_rating_to_spread` returns a real number. The compound keys are the
# closest-neighbor buckets from Damodaran's published rating-to-spread
# lookup, so sub-labels ("AA+" / "AA-") snap to their nearest canonical
# bucket ("AA") rather than failing.
_SP_TO_COMPOUND: dict[str, str] = {
    "AAA":  "Aaa/AAA",
    "AA+":  "Aaa/AAA",   # nearest bucket
    "AA":   "Aa2/AA",
    "AA-":  "Aa2/AA",
    "A+":   "A1/A+",
    "A":    "A2/A",
    "A-":   "A3/A-",
    "BBB+": "A3/A-",     # nearest
    "BBB":  "Baa2/BBB",
    "BBB-": "Baa2/BBB",
    "BB+":  "Ba1/BB+",
    "BB":   "Ba2/BB",
    "BB-":  "Ba2/BB",
    "B+":   "B1/B+",
    "B":    "B2/B",
    "B-":   "B3/B-",
    "CCC+": "Caa/CCC",
    "CCC":  "Caa/CCC",
    "CCC-": "Caa/CCC",
    "CC":   "Ca2/CC",
    "C":    "C2/C",
    "D":    "D2/D",
}
# Moody's labels → same compound key (for CIQ responses that lead with Moody's)
_MOODYS_TO_COMPOUND: dict[str, str] = {
    "Aaa":  "Aaa/AAA",
    "Aa1":  "Aaa/AAA",
    "Aa2":  "Aa2/AA", "Aa3":  "Aa2/AA",
    "A1":   "A1/A+",  "A2":   "A2/A", "A3": "A3/A-",
    "Baa1": "A3/A-",  "Baa2": "Baa2/BBB", "Baa3": "Baa2/BBB",
    "Ba1":  "Ba1/BB+", "Ba2": "Ba2/BB", "Ba3": "Ba2/BB",
    "B1":   "B1/B+",  "B2":   "B2/B", "B3": "B3/B-",
    "Caa1": "Caa/CCC", "Caa2": "Caa/CCC", "Caa3": "Caa/CCC",
    "Ca":   "Ca2/CC",
    # ("C" is intentionally resolved via the S&P table above so
    # "C" from CIQ maps to "C2/C" rather than being ambiguous.)
}


def _clean_rating(raw) -> str | None:
    """Normalize a CIQ `IQ_SP_ISSUER_RATING` value into a compound rating
    bucket key (e.g. ``"Baa2/BBB"``) accepted by the module_2 spread table.

    Returns None when the cell is empty, numeric zero, a sentinel string
    like ``NR`` / ``NA`` / ``-``, or anything else we don't recognize —
    so the WACC branch falls back to the user's dropdown selection.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and raw == 0:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.upper() in {"NA", "N/A", "NR", "NOT RATED", "-", "—", "0"}:
        return None
    # Strip vendor prefix like "S&P: BB+" → "BB+"
    if ":" in s:
        s = s.split(":", 1)[1].strip()
    # Direct lookup (S&P side — exact case)
    if s in _SP_TO_COMPOUND:
        return _SP_TO_COMPOUND[s]
    if s in _MOODYS_TO_COMPOUND:
        return _MOODYS_TO_COMPOUND[s]
    # Case-insensitive S&P match (CIQ may return lowercase)
    for label, compound in _SP_TO_COMPOUND.items():
        if label.lower() == s.lower():
            return compound
    # Moody's with a trailing "+" / "-" may arrive as "Baa1+" — strip and retry
    stripped = s.rstrip("+-")
    if stripped in _MOODYS_TO_COMPOUND:
        return _MOODYS_TO_COMPOUND[stripped]
    return None


@router.get("/industries")
def list_industries(region: str = "US"):
    """List all available Damodaran industries."""
    store = _get_damodaran_store()
    return {"industries": store.list_industries(region)}


@router.get("/erp-catalog")
def list_erp_catalog():
    """Return every Damodaran country + region with its ERP, for the
    geographic-segment manual-mapping dropdown on the frontend.

    Shape:
      {
        countries: [{name, total_erp, base_erp, crp}, ...],    # 180 entries
        regions:   [{name, total_erp}, ...],                   # 10 entries
      }
    """
    import json
    from pathlib import Path
    store = _get_damodaran_store()

    countries = []
    for name, raw in (store._country_risk or {}).items():
        if name.startswith("__") or not isinstance(raw, dict):
            continue
        base = raw.get("equity_risk_premium")
        crp = raw.get("country_risk_premium") or 0
        if base is None:
            continue
        countries.append({
            "name": name,
            "base_erp": base,
            "crp": crp,
            "total_erp": base + crp,
        })
    countries.sort(key=lambda c: c["name"])

    # Regions from cost_of_capital_reference.json
    ref_path = Path(__file__).resolve().parent.parent / "data_sources" / "cost_of_capital_reference.json"
    regions = []
    if ref_path.exists():
        with ref_path.open() as f:
            ref = json.load(f)
        for region_name, data in (ref.get("regional_erp") or {}).items():
            if region_name == "description" or not isinstance(data, dict):
                continue
            erp = data.get("total_erp")
            if erp is None:
                continue
            regions.append({"name": region_name, "total_erp": erp})
        regions.sort(key=lambda r: r["name"])

    return {"countries": countries, "regions": regions}


@router.post("/valuation")
def create_valuation(req: ValuationRequest):
    """Run full valuation pipeline and return results."""
    store = _get_damodaran_store()
    ind_lookup, cerp_lookup = _build_lookups(store)
    report = run_full_valuation(req.inputs, industry_lookup=ind_lookup, country_erp_lookup=cerp_lookup)
    session = create_session(req.inputs, report)
    return _report_to_dict(session)


@router.get("/valuation/{session_id}")
def get_valuation(session_id: str):
    """Retrieve existing valuation results."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _report_to_dict(session)


@router.patch("/valuation/{session_id}")
def patch_valuation(session_id: str, req: OverrideRequest):
    """Apply overrides to inputs and recompute."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply overrides to inputs via dot-path
    inputs_dict = session.inputs.model_dump()
    for path, value in req.overrides.items():
        _set_nested(inputs_dict, path, value)

    # Rebuild inputs and recompute
    new_inputs = CompanyValuationInput(**inputs_dict)
    store = _get_damodaran_store()
    ind_lookup, cerp_lookup = _build_lookups(store)
    new_report = run_full_valuation(new_inputs, industry_lookup=ind_lookup, country_erp_lookup=cerp_lookup)
    session.inputs = new_inputs
    session.report = new_report
    return _report_to_dict(session)


@router.post("/valuation/{session_id}/sensitivity")
def sensitivity(session_id: str):
    """Run the Damodaran-style sensitivity tornado.

    For each of the 8 canonical drivers, run the full valuation pipeline
    twice — once at each end of the driver's sweep range — and return the
    resulting VPS along with the delta versus the current baseline. Session
    state is NOT mutated; the user's current inputs stay intact.
    """
    from engine.sensitivity_ranges import build_ranges

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    store = _get_damodaran_store()
    ind_lookup, cerp_lookup = _build_lookups(store)

    baseline_vps = (
        session.report.final.value_per_share
        if session.report.final and session.report.final.value_per_share is not None
        else None
    )

    driver_ranges = build_ranges(session.inputs)
    bars = []
    for dr in driver_ranges:
        endpoint_results = {}
        for kind, endpoint_val in [("lo", dr.range_lo), ("hi", dr.range_hi)]:
            trial_dict = session.inputs.model_dump()
            _set_nested(trial_dict, dr.patch_path, endpoint_val)
            # Terminal-growth requires the override flag to actually take effect.
            if dr.patch_path == "valuation_assumptions.growth_perpetuity_rate":
                _set_nested(trial_dict, "valuation_assumptions.override_growth_perpetuity", True)
            try:
                trial_inputs = CompanyValuationInput(**trial_dict)
                trial_report = run_full_valuation(
                    trial_inputs, industry_lookup=ind_lookup, country_erp_lookup=cerp_lookup
                )
                vps = trial_report.final.value_per_share if trial_report.final else None
            except Exception:
                vps = None
            endpoint_results[kind] = vps

        vps_lo = endpoint_results["lo"]
        vps_hi = endpoint_results["hi"]
        bars.append({
            "driver": dr.driver,
            "label": dr.label,
            "patch_path": dr.patch_path,
            "range_lo": dr.range_lo,
            "range_hi": dr.range_hi,
            "vps_lo": vps_lo,
            "vps_hi": vps_hi,
            "delta_lo": (vps_lo - baseline_vps) if (vps_lo is not None and baseline_vps is not None) else None,
            "delta_hi": (vps_hi - baseline_vps) if (vps_hi is not None and baseline_vps is not None) else None,
            "range_source": dr.range_source,
        })

    return {
        "baseline_vps": baseline_vps,
        "currency": session.inputs.reporting_currency,
        "bars": bars,
    }


def _set_nested(d, path: str, value) -> None:
    """Set a value in nested dicts/lists using dot-path like 'a.b.0.c'.

    Numeric segments index into the parent list (assumed to exist and be long
    enough). Missing dict keys are created as {}. Missing list slots raise.
    """
    keys = path.split(".")
    for i, key in enumerate(keys[:-1]):
        if isinstance(d, list):
            d = d[int(key)]
        else:
            next_key = keys[i + 1]
            default = [] if next_key.isdigit() else {}
            if key not in d or not isinstance(d[key], (dict, list)):
                d[key] = default
            d = d[key]
    last = keys[-1]
    if isinstance(d, list):
        d[int(last)] = value
    else:
        d[last] = value
