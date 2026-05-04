"""
Deterministic, LLM-free mapping/parsing utilities for the US+CN+HK CIQ
screener dataset.

Every function in this module is pure Python — no model calls, no network.
Safe to run as part of an automated ingest pipeline (cron, admin button,
filesystem watcher) without any Claude / LLM involvement.

Contents:
  - CIQ_HEADER_PATTERNS: regex patterns that route CIQ screener column
    headers to our internal variable names + period tokens.
  - parse_ciq_header(): apply the patterns to a raw header string.
  - parse_geographic_segments(): split the semicolon/newline-delimited
    segment cells into structured records.
  - normalize_filing_currency(): CIQ verbose currency names → ISO codes.
  - parse_exchange_code(): extract the parenthesized abbreviation.
  - normalize_effective_tax_rate(): /100 from percent to decimal.

All functions are tested against real screener samples — see spot-check
output in the DB-integration plan §6a.
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# 1. Column header → (variable, period) mapping
# ---------------------------------------------------------------------------

# Pattern syntax: (header_prefix_regex, variable_name, currency_semantics).
#   currency_semantics:
#     'reporting'   — value is in company's filing currency (Reported Currency
#                     modifier works as advertised)
#     'listing'     — value is in trading currency regardless of modifier
#                     (CIQ's silent-ignore bug — see plan §6a)
#     'none'        — no currency (share count, %, date, rating text)
#
# Each pattern matches the *start* of a CIQ header. Period is pulled from the
# `[...]` bracket in the header by a separate regex.
CIQ_HEADER_PATTERNS: list[tuple[str, str, str]] = [
    # --- Identifiers ---
    (r'^Company Name$', 'company_name', 'none'),
    (r'^Exchange:Ticker$', 'ticker', 'none'),
    (r'^Company Type$', 'company_type', 'none'),
    (r'^Exchanges \[Primary Listing\]', 'primary_exchange', 'none'),
    (r'^Exchanges \[Secondary Listings\]', 'secondary_exchanges', 'none'),
    (r'^Filing Currency', 'reporting_currency', 'none'),
    (r'^Period Date, Income Statement \[Latest Annual\]', 'period_date_annual', 'none'),
    (r'^Period Date, Income Statement \[Latest Quarter\]', 'period_date_quarterly', 'none'),

    # --- Income statement (reporting currency, 18 periods: 10 annual + 8 quarterly) ---
    (r'^Total Revenue ', 'revenues', 'reporting'),
    (r'^EBIT ', 'ebit', 'reporting'),
    (r'^EBITDA ', 'ebitda', 'reporting'),
    (r'^Net Income ', 'net_income', 'reporting'),
    (r'^Interest Expense ', 'interest_expense', 'reporting'),
    (r'^Capital Expenditure ', 'capex', 'reporting'),
    (r'^Depreciation & Amort', 'd_a', 'reporting'),
    (r'^EBT Excl Unusual Items ', 'earnings_before_tax', 'reporting'),
    (r'^Income Tax Expense ', 'total_tax_expense', 'reporting'),
    (r'^Operating Lease Payments ', 'operating_lease_expense', 'reporting'),
    (r'^R&D Exp\. ', 'r_and_d_expense', 'reporting'),

    # --- Balance sheet (reporting currency, 11 periods: 10 annual + FQ-0) ---
    (r'^Total Cash & ST Investments ', 'cash_and_marketable_securities', 'reporting'),
    (r'^Long-term Investments ', 'cross_holdings', 'reporting'),
    (r'^Total Debt ', 'bv_debt', 'reporting'),
    (r'^Total Equity ', 'bv_equity', 'reporting'),
    (r'^Total Shares Out\. on Filing Date ', 'shares_outstanding', 'none'),  # in mm
    (r'^Minority Interest ', 'minority_interests', 'reporting'),

    # --- Market / snapshot (LISTING currency — the "Reported Currency" trap) ---
    (r'^Day Close Price', 'stock_price', 'listing'),                    # NOT reporting
    (r'^Market Capitalization', 'mv_equity_listing', 'listing'),        # NOT reporting
    (r'^Options W/Avg\. Strike Price', 'options_avg_strike', 'listing'),# listing (ESOs denominated in trading ccy)
    (r'^Total Options Out\. at the End of Year', 'options_outstanding', 'none'),  # shares (mm)

    # --- Current-snapshot, non-currency ---
    (r'^Effective Tax Rate \[Latest Annual\]', 'effective_tax_rate_ciq', 'none'),  # %, divide by 100 at ingest
    (r'^S&P Entity Credit Rating - Issuer Credit Rating - Foreign Currency LT',
     'actual_rating_fc', 'none'),
    (r'^S&P Entity Credit Rating - Issuer Credit Rating - Local Currency LT',
     'actual_rating_lc', 'none'),

    # --- Operating-lease commitments (Latest Annual only, reporting ccy) ---
    (r'^Operating Lease Commitment Due \+1', 'lease_commitment_yr1', 'reporting'),
    (r'^Operating Lease Commitment Due \+2', 'lease_commitment_yr2', 'reporting'),
    (r'^Operating Lease Commitment Due \+3', 'lease_commitment_yr3', 'reporting'),
    (r'^Operating Lease Commitment Due \+4', 'lease_commitment_yr4', 'reporting'),
    (r'^Operating Lease Commitment Due \+5', 'lease_commitment_yr5', 'reporting'),
    (r'^Operating Lease Commitment Due, Next 5 Yrs', 'lease_commitment_beyond', 'reporting'),

    # --- Geographic segments ---
    (r'^Geographic Segments \(Screen by Sum\) \(Details\): Revenue',
     'geographic_segments_revenue_detail', 'reporting'),
    (r'^Geographic Segments \(Screen by Sum\) \(Details\): % of Revenue',
     'geographic_segments_pct_detail', 'none'),
    (r'^Geographic Segments \(Screen by Sum\): Revenue',
     'geographic_segments_revenue_total', 'reporting'),
    (r'^Geographic Segments \(Screen by Sum\): % of Revenue',
     'geographic_segments_pct_total', 'none'),
]

_COMPILED_PATTERNS = [(re.compile(p), v, c) for (p, v, c) in CIQ_HEADER_PATTERNS]

# Period extraction: `[Latest Annual - 3]` → ('Latest Annual - 3', 'annual', 3)
_PERIOD_RE = re.compile(r'\[(Latest Annual(?: - (\d+))?|Latest Quarter(?: - (\d+))?|Latest|LTM|My Setting)\]')


def parse_ciq_header(header: str) -> dict[str, Any] | None:
    """Parse a CIQ screener column header.

    Returns a dict with keys:
      - variable: internal variable name (or None if unmapped)
      - currency_semantics: 'reporting' | 'listing' | 'none'
      - period_kind: 'annual' | 'quarterly' | 'latest' | 'ltm' | None
      - period_offset: int | None   (0 = FY-0 / FQ-0; None for non-periodic)

    Returns None only if the header is empty/blank.
    An unmapped non-blank header returns variable=None so the ingester can
    log it for operator review.
    """
    if not header or not header.strip():
        return None

    variable = None
    currency_semantics = 'none'
    for regex, var, ccy in _COMPILED_PATTERNS:
        if regex.match(header):
            variable = var
            currency_semantics = ccy
            break

    # Headers can carry TWO bracket pairs — e.g.
    #   'Market Capitalization [My Setting] [Latest] (Reported Currency)'
    # We want the time-period token, not the config token. Prefer the
    # last period-like bracket; skip 'My Setting'.
    period_kind = None
    period_offset = None
    for m in _PERIOD_RE.finditer(header):
        tok = m.group(1)
        if tok == 'My Setting':
            continue
        if tok.startswith('Latest Annual'):
            period_kind = 'annual'
            period_offset = int(m.group(2)) if m.group(2) else 0
        elif tok.startswith('Latest Quarter'):
            period_kind = 'quarterly'
            period_offset = int(m.group(3)) if m.group(3) else 0
        elif tok == 'Latest':
            period_kind = 'latest'
            period_offset = 0
        elif tok == 'LTM':
            period_kind = 'ltm'
            period_offset = 0
        # Keep iterating — last match wins when there are multiple.

    return {
        'variable': variable,
        'currency_semantics': currency_semantics,
        'period_kind': period_kind,
        'period_offset': period_offset,
        'raw_header': header,
    }


# ---------------------------------------------------------------------------
# 2. Geographic segments parser
# ---------------------------------------------------------------------------

# Pattern: one segment entry = "<name>: <revenue> (<pct>%)"
#   name can contain spaces, parens, dots, commas, slashes, apostrophes
#   revenue: digits with optional commas and decimal point; "-" or empty → None
#   percent: digits and one decimal point
# Separators between entries: ';' followed by optional whitespace/newline.
_SEGMENT_RE = re.compile(
    r'''
    \s*                          # leading whitespace
    (?P<name>[^:;]+?)            # segment name (lazy, no ':' or ';')
    \s*:\s*
    (?P<revenue>[\d,.]+|-)       # revenue (digits/commas/decimal) or literal '-'
    \s*\(\s*
    (?P<pct>[\d.]+)              # percent
    \s*%\s*\)
    \s*
    ''',
    re.VERBOSE,
)


def parse_geographic_segments(cell: Any) -> list[dict[str, Any]]:
    """Parse a CIQ 'Geographic Segments (Details)' cell.

    Input formats we handle (all verified against real data):
      - ''  or  '-'                              → empty list
      - float/int                                → empty list (single-segment firms
                                                   return a plain number in the
                                                   top-level column; we ignore)
      - 'Asia Pacific (AP): 12,942.1 (18.7%);\\nAmericas (AG): 23,297.4 (33.7%);'
      - 'Mainland China: 662,119.0 (88.1%);\\nOthers: 89,647.0 (11.9%)'
      - "People's Republic of China (PRC): 996,347.0 (100.0%)"

    Returns a list of dicts:
      [{'name': 'Asia Pacific (AP)', 'revenue': 12942.1, 'pct': 0.187}, …]

    Percent is returned as decimal (0.187, not 18.7). Revenue is a float;
    '-' or unparseable → None. Segments are returned in the order they
    appear in the cell.
    """
    if cell is None or cell == '' or cell == '-':
        return []
    if not isinstance(cell, str):
        return []

    segments: list[dict[str, Any]] = []
    for m in _SEGMENT_RE.finditer(cell):
        name = m.group('name').strip()
        rev_raw = m.group('revenue').strip()
        if rev_raw == '-':
            revenue: float | None = None
        else:
            try:
                revenue = float(rev_raw.replace(',', ''))
            except ValueError:
                revenue = None
        try:
            pct = float(m.group('pct')) / 100.0
        except ValueError:
            pct = 0.0
        segments.append({'name': name, 'revenue': revenue, 'pct': pct})
    return segments


# ---------------------------------------------------------------------------
# 3. Small normalizers
# ---------------------------------------------------------------------------

_CURRENCY_NAME_TO_ISO = {
    'US Dollar': 'USD',
    'Chinese Renminbi (Yuan)': 'CNY',
    'Hong Kong Dollar': 'HKD',
    'Japanese Yen': 'JPY',
    'Euro': 'EUR',
    'British Pound': 'GBP',
    'Singapore Dollar': 'SGD',
    'Taiwan New Dollar': 'TWD',
    'Korean Won': 'KRW',
    'Indian Rupee': 'INR',
    'Australian Dollar': 'AUD',
    'Canadian Dollar': 'CAD',
    'New Taiwan Dollar': 'TWD',
}


def normalize_filing_currency(raw: Any) -> str | None:
    """'US Dollar' → 'USD'. Unknown → raw (passthrough so operator can see it)."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw = raw.strip()
    return _CURRENCY_NAME_TO_ISO.get(raw, raw)


_EXCHANGE_CODE_RE = re.compile(r'\(([A-Za-z]+)\)\s*$')


def parse_exchange_code(primary_listing: Any) -> str | None:
    """'Nasdaq Global Select (NasdaqGS)' → 'NasdaqGS'.

    Uses the parenthesized abbreviation at the end, which matches the
    `EXCHANGE_CURRENCY` lookup in exchange_currency_map.py. Mixed case
    preserved (NasdaqGS, not NASDAQGS) to match CIQ's conventions.
    """
    if not isinstance(primary_listing, str):
        return None
    m = _EXCHANGE_CODE_RE.search(primary_listing)
    return m.group(1) if m else None


def normalize_effective_tax_rate(raw: Any) -> float | None:
    """CIQ screener's Effective Tax Rate column is in PERCENT (e.g. 14.9).
    Our schema stores effective_tax_rate as a DECIMAL (0.149). Divide by 100.

    Handles '-' as missing → None.
    """
    if raw is None or raw == '' or raw == '-':
        return None
    try:
        return float(raw) / 100.0
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 4. Self-test (run directly to verify against the real screener samples)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # Geographic segments samples captured from the US_CN_HK_dataset on 2026-05-04.
    SAMPLES = [
        # (ticker, cell, expected_n_segments, expected_first_name)
        ('SEHK:992',
         'Asia Pacific (AP): 12,942.1 (18.7%);\nAmericas (AG): 23,297.4 (33.7%);\n'
         'Europe-Middle East-Africa (EMEA): 16,936.3 (24.5%);\nChina: 15,901.2 (23.0%)',
         4, 'Asia Pacific (AP)'),
        ('NasdaqGS:AAPL',
         'Greater China: 64,377.0 (15.5%);\nUnited States (U.S.): 151,790.0 (36.5%);\n'
         'Other Countries: 199,994.0 (48.1%)',
         3, 'Greater China'),
        ('SEHK:700',
         'Mainland China: 662,119.0 (88.1%);\nOthers: 89,647.0 (11.9%)',
         2, 'Mainland China'),
        ('SHSE:600519',
         'Foreign: 4,858.1 (2.9%);\nChina: 163,980.0 (97.1%)',
         2, 'Foreign'),
        ('NYSE:BABA',
         "People's Republic of China (PRC): 996,347.0 (100.0%)",
         1, "People's Republic of China (PRC)"),
        # Edge cases
        ('_none', '', 0, None),
        ('_dash', '-', 0, None),
        ('_number', 1234.5, 0, None),
    ]

    print('Geographic segment parser self-test:')
    for tkr, cell, expected_n, expected_first in SAMPLES:
        out = parse_geographic_segments(cell)
        ok = len(out) == expected_n and (expected_first is None or (out and out[0]['name'] == expected_first))
        status = 'PASS' if ok else 'FAIL'
        print(f'  {status}  {tkr:22s}  got {len(out)} segments')
        for seg in out:
            print(f'         {seg["name"]:40s}  rev={seg["revenue"]}  pct={seg["pct"]:.3f}')
    print()

    # Effective tax rate
    print('Effective tax rate normalizer:')
    for raw in [1.28, 15.6, 22.0, 0.0, '-', None, '']:
        print(f'  {raw!r:10s} → {normalize_effective_tax_rate(raw)}')
    print()

    # Filing currency
    print('Filing currency normalizer:')
    for raw in ['US Dollar', 'Chinese Renminbi (Yuan)', 'Hong Kong Dollar', 'Zimbabwean Dollar', '']:
        print(f'  {raw!r:30s} → {normalize_filing_currency(raw)!r}')
    print()

    # Exchange code
    print('Exchange code parser:')
    for raw in ['Nasdaq Global Select (NasdaqGS)', 'The Stock Exchange of Hong Kong Ltd. (SEHK)',
                'Shanghai Stock Exchange (SHSE)', 'New York Stock Exchange (NYSE)', '']:
        print(f'  {raw!r:50s} → {parse_exchange_code(raw)!r}')
    print()

    # Header parser — spot check
    print('Header parser spot check:')
    for h in [
        'Total Revenue [Latest Annual - 3] (Reported Currency)',
        'Day Close Price [Latest] (Reported Currency)',
        'Market Capitalization [My Setting] [Latest] (Reported Currency)',
        'Effective Tax Rate [Latest Annual] (%)',
        'Geographic Segments (Screen by Sum) (Details): Revenue (Reported Currency) [Latest Annual]',
        'Company Name',
    ]:
        print(f'  {h[:60]:60s} → {parse_ciq_header(h)}')
