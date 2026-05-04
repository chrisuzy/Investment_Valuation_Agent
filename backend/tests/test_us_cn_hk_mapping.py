"""
Regression tests for us_cn_hk_mapping.py — guards against CIQ format drift.

These assertions encode the exact real-world samples observed from
US_CN_HK_dataset on 2026-05-04. If any of them fail, one of the input
files probably changed format; investigate before adjusting the tests.
"""
from __future__ import annotations

import pytest

from data_sources.us_cn_hk_mapping import (
    parse_ciq_header,
    parse_geographic_segments,
    normalize_effective_tax_rate,
    normalize_filing_currency,
    parse_exchange_code,
)


# ---------------------------------------------------------------------------
# parse_ciq_header
# ---------------------------------------------------------------------------

def test_header_income_annual_with_offset():
    r = parse_ciq_header('Total Revenue [Latest Annual - 3] (Reported Currency)')
    assert r is not None
    assert r['variable'] == 'revenues'
    assert r['currency_semantics'] == 'reporting'
    assert r['period_kind'] == 'annual'
    assert r['period_offset'] == 3


def test_header_income_annual_current():
    r = parse_ciq_header('EBIT [Latest Annual] (Reported Currency)')
    assert r['variable'] == 'ebit'
    assert r['period_kind'] == 'annual'
    assert r['period_offset'] == 0


def test_header_quarterly():
    r = parse_ciq_header('Total Revenue [Latest Quarter - 2] (Reported Currency)')
    assert r['variable'] == 'revenues'
    assert r['period_kind'] == 'quarterly'
    assert r['period_offset'] == 2


def test_header_listing_currency_market_fields():
    """Critical: the three market columns must route to LISTING-ccy schema
    fields, despite CIQ labeling them '(Reported Currency)'."""
    r1 = parse_ciq_header('Day Close Price [Latest] (Reported Currency)')
    assert r1['variable'] == 'stock_price'
    assert r1['currency_semantics'] == 'listing'

    r2 = parse_ciq_header('Market Capitalization [My Setting] [Latest] (Reported Currency)')
    assert r2['variable'] == 'mv_equity_listing'
    assert r2['currency_semantics'] == 'listing'
    # Dual-bracket header: must skip 'My Setting' and pick 'Latest'.
    assert r2['period_kind'] == 'latest'

    r3 = parse_ciq_header('Options W/Avg. Strike Price of Out. [Latest Annual] (Reported Currency)')
    assert r3['variable'] == 'options_avg_strike'
    assert r3['currency_semantics'] == 'listing'


def test_header_identifier_fields():
    assert parse_ciq_header('Company Name')['variable'] == 'company_name'
    assert parse_ciq_header('Exchange:Ticker')['variable'] == 'ticker'
    assert parse_ciq_header('Filing Currency [Latest Annual]')['variable'] == 'reporting_currency'


def test_header_blank_returns_none():
    assert parse_ciq_header('') is None
    assert parse_ciq_header('   ') is None


def test_header_unmapped_returns_variable_none():
    """A header we don't know yet returns variable=None so the ingester
    can log it for operator review, without crashing."""
    r = parse_ciq_header('Some Brand New Column [Latest Annual]')
    assert r is not None
    assert r['variable'] is None


# ---------------------------------------------------------------------------
# parse_geographic_segments
# ---------------------------------------------------------------------------

def test_geo_lenovo():
    """4 segments, multiple regions with parenthesized abbreviations."""
    cell = (
        'Asia Pacific (AP): 12,942.1 (18.7%);\n'
        'Americas (AG): 23,297.4 (33.7%);\n'
        'Europe-Middle East-Africa (EMEA): 16,936.3 (24.5%);\n'
        'China: 15,901.2 (23.0%)'
    )
    segs = parse_geographic_segments(cell)
    assert len(segs) == 4
    names = [s['name'] for s in segs]
    assert 'Asia Pacific (AP)' in names
    assert 'Europe-Middle East-Africa (EMEA)' in names
    assert segs[0]['revenue'] == pytest.approx(12942.1)
    assert segs[0]['pct'] == pytest.approx(0.187)
    # All pct values in decimal form
    assert all(0 <= s['pct'] <= 1.01 for s in segs)


def test_geo_single_segment():
    """BABA: one segment spanning all revenue."""
    segs = parse_geographic_segments("People's Republic of China (PRC): 996,347.0 (100.0%)")
    assert len(segs) == 1
    assert segs[0]['name'] == "People's Republic of China (PRC)"
    assert segs[0]['pct'] == pytest.approx(1.00)


def test_geo_empty_inputs():
    assert parse_geographic_segments('') == []
    assert parse_geographic_segments('-') == []
    assert parse_geographic_segments(None) == []
    assert parse_geographic_segments(12345.0) == []  # single-value cells


# ---------------------------------------------------------------------------
# normalize_effective_tax_rate
# ---------------------------------------------------------------------------

def test_eff_tax_rate_divides_by_100():
    """CIQ gives percent (14.9); schema stores decimal (0.149)."""
    assert normalize_effective_tax_rate(14.9) == pytest.approx(0.149)
    assert normalize_effective_tax_rate(1.28) == pytest.approx(0.0128)
    assert normalize_effective_tax_rate(0) == 0.0


def test_eff_tax_rate_missing():
    assert normalize_effective_tax_rate(None) is None
    assert normalize_effective_tax_rate('') is None
    assert normalize_effective_tax_rate('-') is None
    assert normalize_effective_tax_rate('not a number') is None


# ---------------------------------------------------------------------------
# normalize_filing_currency
# ---------------------------------------------------------------------------

def test_filing_currency_known_names():
    assert normalize_filing_currency('US Dollar') == 'USD'
    assert normalize_filing_currency('Chinese Renminbi (Yuan)') == 'CNY'
    assert normalize_filing_currency('Hong Kong Dollar') == 'HKD'


def test_filing_currency_unknown_passthrough():
    """Unknown names pass through so operator can see what CIQ returned."""
    assert normalize_filing_currency('Zimbabwean Dollar') == 'Zimbabwean Dollar'


def test_filing_currency_empty():
    assert normalize_filing_currency('') is None
    assert normalize_filing_currency(None) is None


# ---------------------------------------------------------------------------
# parse_exchange_code
# ---------------------------------------------------------------------------

def test_exchange_code_extracts_parenthesized():
    assert parse_exchange_code('Nasdaq Global Select (NasdaqGS)') == 'NasdaqGS'
    assert parse_exchange_code('The Stock Exchange of Hong Kong Ltd. (SEHK)') == 'SEHK'
    assert parse_exchange_code('Shanghai Stock Exchange (SHSE)') == 'SHSE'
    assert parse_exchange_code('New York Stock Exchange (NYSE)') == 'NYSE'


def test_exchange_code_preserves_mixed_case():
    """Important: NasdaqGS (mixed case) must round-trip for the
    EXCHANGE_CURRENCY lookup to work."""
    assert parse_exchange_code('Nasdaq (NasdaqGS)') == 'NasdaqGS'


def test_exchange_code_missing():
    assert parse_exchange_code('No parens here') is None
    assert parse_exchange_code(None) is None
    assert parse_exchange_code('') is None
