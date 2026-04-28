"""
Module 0: Data Fetch — orchestrates Capital IQ + Damodaran lookups into CompanyValuationInput.

Given a ticker, fetches company financials from CapIQ, maps to Damodaran industry,
and retrieves industry/country data from the Damodaran store.
"""

from __future__ import annotations

import logging

from .data_dictionary import CompanyValuationInput, MacroInputs, ValuationAssumptions
from data_sources.capiq_adapter import CapIQAdapter, CapIQResult
from data_sources.damodaran_store import DamodaranStore
from data_sources.industry_mapper import IndustryMapper

logger = logging.getLogger(__name__)


def fetch_company_data(
    ticker: str,
    capiq_adapter: CapIQAdapter,
    damodaran_store: DamodaranStore,
    industry_mapper: IndustryMapper,
    risk_free_rate: float = 0.04,
    region: str = "US",
    industry_override: str | None = None,
) -> CompanyValuationInput:
    """
    Fetch all data needed for a full valuation.

    Args:
        ticker: Company ticker symbol (e.g., "AAPL").
        capiq_adapter: CapIQ data fetcher.
        damodaran_store: Pre-loaded Damodaran datasets.
        industry_mapper: Ticker → industry/country mapper.
        risk_free_rate: Current risk-free rate (user or external source).
        region: Damodaran data region ("US", "Global", "China").
        industry_override: Override auto-detected industry name.

    Returns:
        CompanyValuationInput with all data needed for the pipeline.
    """
    # 1. Fetch company financials from CapIQ
    capiq_result: CapIQResult = capiq_adapter.fetch_via_com(ticker)
    if capiq_result.warnings:
        for w in capiq_result.warnings:
            logger.warning(f"CapIQ warning for {ticker}: {w}")

    # 2. Map ticker to industry and country
    company_info = industry_mapper.lookup(ticker)
    company_name = company_info.company_name if company_info else None
    country = company_info.country if company_info else "United States"
    industry_name = industry_override or (company_info.industry_group if company_info else None)

    if not industry_name:
        raise ValueError(f"Could not determine industry for ticker '{ticker}'. Provide industry_override.")

    # 3. Look up industry data from Damodaran
    industry_data = damodaran_store.lookup_industry(industry_name, region=region)
    if industry_data is None:
        raise ValueError(f"Industry '{industry_name}' not found in Damodaran {region} data.")

    # 4. Look up country macro data
    macro = damodaran_store.lookup_country(country)
    if macro is None:
        # Fall back to mature market defaults
        erp = damodaran_store.get_mature_market_erp() or 0.05
        macro = MacroInputs(
            risk_free_rate=risk_free_rate,
            equity_risk_premium=erp,
            tax_rate_marginal=0.21,  # Default US
        )
    else:
        macro.risk_free_rate = risk_free_rate

    return CompanyValuationInput(
        ticker=ticker,
        company_name=company_name,
        country=country,
        raw_financials=capiq_result.raw_financials,
        adjustment_inputs=capiq_result.adjustment_inputs,
        macro_inputs=macro,
        industry_data=industry_data,
        option_inputs=capiq_result.option_inputs,
        valuation_assumptions=ValuationAssumptions(),
    )
