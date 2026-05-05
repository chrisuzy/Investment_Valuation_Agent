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

import difflib
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


# ---------------------------------------------------------------------------
# 1b. Deterministic fallback — keyword-set matching + difflib suggestion
# ---------------------------------------------------------------------------
#
# The regex list above is strict by design (case-sensitive prefix match), so
# minor rewording from CIQ — "Capital Expenditures" → "CapEx", pluralization,
# punctuation drift — silently drops headers onto the unmapped list.
#
# To handle realistic renames WITHOUT an LLM:
#   1. `parse_ciq_header` first tries the regex fast path (no behavior change).
#   2. If unmatched, it tokenizes the header (lowercase, punct stripped,
#      bracket/paren content removed) and checks whether any required
#      token-set below is a SUBSET of the header's tokens. Among matching
#      rules, the one whose required token-set is LARGEST (most specific)
#      wins — so "operating income" prefers the EBIT rule over an imaginary
#      "income" catch-all.
#   3. If no rule matches, `suggest_variables_for_header` (used by the
#      ingester's report) offers the operator 2-3 closest candidate fields
#      via stdlib's difflib — purely as a hint for manual triage. No
#      auto-assignment is ever done from a fuzzy score.

# Each rule: (variable_name, list-of-alternative-required-token-sets, currency_semantics).
# A header's normalized token set must contain every token in at least one
# alternative set for the rule to match.
FUZZY_KEYWORD_RULES: list[tuple[str, list[frozenset[str]], str]] = [
    # --- Income statement ---
    ('revenues', [
        frozenset({'revenue'}),
        frozenset({'revenues'}),
        frozenset({'sales', 'total'}),
        frozenset({'sales', 'net'}),
    ], 'reporting'),
    ('ebit', [
        frozenset({'ebit'}),
        frozenset({'operating', 'income'}),
        frozenset({'operating', 'profit'}),
    ], 'reporting'),
    ('ebitda', [frozenset({'ebitda'})], 'reporting'),
    ('net_income', [
        frozenset({'net', 'income'}),
        frozenset({'net', 'earnings'}),
    ], 'reporting'),
    ('interest_expense', [frozenset({'interest', 'expense'})], 'reporting'),
    ('capex', [
        frozenset({'capital', 'expenditure'}),
        frozenset({'capital', 'expenditures'}),
        frozenset({'capex'}),
    ], 'reporting'),
    ('d_a', [
        frozenset({'depreciation', 'amortization'}),
        frozenset({'depreciation', 'amort'}),
        frozenset({'da'}),
    ], 'reporting'),
    ('earnings_before_tax', [
        frozenset({'ebt'}),
        frozenset({'earnings', 'before', 'tax'}),
        frozenset({'pretax', 'income'}),
    ], 'reporting'),
    ('total_tax_expense', [
        frozenset({'income', 'tax', 'expense'}),
        frozenset({'tax', 'expense', 'total'}),
    ], 'reporting'),
    ('operating_lease_expense', [
        frozenset({'operating', 'lease', 'payments'}),
        frozenset({'operating', 'lease', 'expense'}),
    ], 'reporting'),
    ('r_and_d_expense', [
        frozenset({'rd'}),
        frozenset({'r', 'd', 'expense'}),    # "R&D Expense" / "R D Expense"
        frozenset({'r', 'd', 'exp'}),        # "R&D Exp." / "R & D Exp."
        frozenset({'research', 'development'}),
    ], 'reporting'),

    # --- Balance sheet ---
    ('cash_and_marketable_securities', [
        frozenset({'cash', 'st', 'investments'}),
        frozenset({'cash', 'short', 'term', 'investments'}),
        frozenset({'cash', 'marketable', 'securities'}),
    ], 'reporting'),
    ('cross_holdings', [
        frozenset({'longterm', 'investments'}),
        frozenset({'long', 'term', 'investments'}),
    ], 'reporting'),
    ('bv_debt', [
        frozenset({'total', 'debt'}),
    ], 'reporting'),
    ('bv_equity', [
        frozenset({'total', 'equity'}),
        frozenset({'stockholders', 'equity'}),
        frozenset({'shareholders', 'equity'}),
    ], 'reporting'),
    ('shares_outstanding', [
        frozenset({'total', 'shares', 'out'}),
        frozenset({'total', 'shares', 'outstanding'}),
        frozenset({'shares', 'outstanding', 'filing'}),
    ], 'none'),
    ('minority_interests', [
        frozenset({'minority', 'interest'}),
        frozenset({'noncontrolling', 'interest'}),
        frozenset({'non', 'controlling', 'interest'}),
    ], 'reporting'),

    # --- Market snapshot (LISTING currency) ---
    ('stock_price', [
        frozenset({'day', 'close', 'price'}),
        frozenset({'closing', 'price'}),
    ], 'listing'),
    ('mv_equity_listing', [
        frozenset({'market', 'capitalization'}),
        frozenset({'market', 'cap'}),
    ], 'listing'),
    ('options_avg_strike', [
        frozenset({'options', 'strike', 'price'}),
        frozenset({'options', 'avg', 'strike'}),
    ], 'listing'),
    ('options_outstanding', [
        frozenset({'options', 'out'}),
        frozenset({'options', 'outstanding'}),
    ], 'none'),

    # --- Non-currency snapshot fields ---
    ('effective_tax_rate_ciq', [
        frozenset({'effective', 'tax', 'rate'}),
    ], 'none'),
    ('actual_rating_fc', [
        frozenset({'issuer', 'credit', 'rating', 'foreign'}),
    ], 'none'),
    ('actual_rating_lc', [
        frozenset({'issuer', 'credit', 'rating', 'local'}),
    ], 'none'),

    # --- Identifiers ---
    ('company_name', [frozenset({'company', 'name'})], 'none'),
    ('ticker', [
        frozenset({'exchange', 'ticker'}),
        frozenset({'ticker'}),
    ], 'none'),
    ('company_type', [frozenset({'company', 'type'})], 'none'),
    ('primary_exchange', [
        frozenset({'exchanges', 'primary'}),
        frozenset({'primary', 'listing'}),
    ], 'none'),
    ('secondary_exchanges', [
        frozenset({'exchanges', 'secondary'}),
        frozenset({'secondary', 'listings'}),
    ], 'none'),
    ('reporting_currency', [
        frozenset({'filing', 'currency'}),
        frozenset({'reporting', 'currency'}),
    ], 'none'),
    ('period_date_annual', [
        frozenset({'period', 'date', 'annual'}),
    ], 'none'),
    ('period_date_quarterly', [
        frozenset({'period', 'date', 'quarter'}),
    ], 'none'),

    # --- Operating-lease commitments ---
    ('lease_commitment_yr1', [frozenset({'operating', 'lease', 'commitment', '1'})], 'reporting'),
    ('lease_commitment_yr2', [frozenset({'operating', 'lease', 'commitment', '2'})], 'reporting'),
    ('lease_commitment_yr3', [frozenset({'operating', 'lease', 'commitment', '3'})], 'reporting'),
    ('lease_commitment_yr4', [frozenset({'operating', 'lease', 'commitment', '4'})], 'reporting'),
    ('lease_commitment_yr5', [frozenset({'operating', 'lease', 'commitment', '5'})], 'reporting'),
    ('lease_commitment_beyond', [
        frozenset({'operating', 'lease', 'commitment', 'next', '5', 'yrs'}),
        frozenset({'operating', 'lease', 'commitment', 'beyond'}),
    ], 'reporting'),

    # --- Geographic segments ---
    ('geographic_segments_revenue_detail', [
        frozenset({'geographic', 'segments', 'details', 'revenue'}),
    ], 'reporting'),
    ('geographic_segments_pct_detail', [
        frozenset({'geographic', 'segments', 'details', 'revenue', 'pct'}),
    ], 'none'),
    ('geographic_segments_revenue_total', [
        frozenset({'geographic', 'segments', 'revenue'}),
    ], 'reporting'),
    ('geographic_segments_pct_total', [
        frozenset({'geographic', 'segments', 'revenue', 'pct'}),
    ], 'none'),
]


# Strip bracket/paren content (period tokens, currency modifiers) + punctuation,
# then lowercase + tokenize. Returns the normalized token set used for keyword
# matching AND the normalized bare string used for difflib suggestions.
_BRACKET_RE = re.compile(r'[\[\(].*?[\]\)]')       # remove [...] and (...) content
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")           # everything except lowercase alnum → space
_PERCENT_TOKEN = re.compile(r'%|percent|pct', re.IGNORECASE)


def _normalize_header(header: str) -> tuple[frozenset[str], str]:
    """Return (tokens, bare_normalized) for a CIQ header.

    - Strips `[...]` and `(...)` content so period/currency metadata doesn't
      pollute the token set.
    - Normalizes `%` and "percent" to the token 'pct' for consistent matching.
    - Lowercases and collapses punctuation. Returns a frozen token set and a
      single-space-joined bare string.
    """
    stripped = _BRACKET_RE.sub(' ', header)
    stripped = _PERCENT_TOKEN.sub(' pct ', stripped)
    lowered = stripped.lower()
    normalized = _NON_WORD_RE.sub(' ', lowered).strip()
    tokens = frozenset(t for t in normalized.split() if t)
    return tokens, normalized


def _keyword_match(tokens: frozenset[str]) -> tuple[str | None, str]:
    """Return (variable_name, currency_semantics) for the most specific rule
    whose required-token set is a subset of `tokens`. If multiple rules tie
    on specificity, returns None (ambiguous — better to log than guess)."""
    best_variable: str | None = None
    best_currency = 'none'
    best_size = 0
    tied = False
    for variable, alternatives, currency in FUZZY_KEYWORD_RULES:
        for alt in alternatives:
            if alt.issubset(tokens):
                size = len(alt)
                if size > best_size:
                    best_variable = variable
                    best_currency = currency
                    best_size = size
                    tied = False
                elif size == best_size and variable != best_variable:
                    tied = True
                break  # stop checking more alternatives for this variable
    if tied:
        return None, 'none'
    return best_variable, best_currency


# Canonical alias strings used ONLY by suggest_variables_for_header for
# difflib-based suggestions. Never used for auto-assignment. Keep each entry
# short and normalized (lowercase, spaces only).
_SUGGESTION_ALIASES: dict[str, list[str]] = {
    'revenues': ['total revenue', 'revenues', 'total sales', 'net sales'],
    'ebit': ['ebit', 'operating income', 'operating profit'],
    'ebitda': ['ebitda'],
    'net_income': ['net income', 'net earnings'],
    'interest_expense': ['interest expense'],
    'capex': ['capital expenditure', 'capital expenditures', 'capex'],
    'd_a': ['depreciation amortization', 'depreciation and amortization'],
    'earnings_before_tax': ['earnings before tax', 'ebt excl unusual items', 'pretax income'],
    'total_tax_expense': ['income tax expense'],
    'operating_lease_expense': ['operating lease payments', 'operating lease expense'],
    'r_and_d_expense': ['r d expense', 'research and development expense'],
    'cash_and_marketable_securities': ['total cash and st investments', 'cash and short term investments'],
    'cross_holdings': ['long term investments'],
    'bv_debt': ['total debt'],
    'bv_equity': ['total equity', 'stockholders equity'],
    'shares_outstanding': ['total shares outstanding on filing date'],
    'minority_interests': ['minority interest', 'noncontrolling interest'],
    'stock_price': ['day close price', 'closing price'],
    'mv_equity_listing': ['market capitalization'],
    'options_avg_strike': ['options weighted avg strike price'],
    'options_outstanding': ['total options outstanding'],
    'effective_tax_rate_ciq': ['effective tax rate'],
    'actual_rating_fc': ['s p issuer credit rating foreign currency'],
    'actual_rating_lc': ['s p issuer credit rating local currency'],
}


def suggest_variables_for_header(header: str, top_n: int = 3, min_ratio: float = 0.55) -> list[dict[str, Any]]:
    """Offer ranked candidate variables for an unmapped header.

    Uses stdlib difflib.SequenceMatcher — deterministic, no dependencies,
    no network. Result is a list of {variable, alias, ratio} dicts sorted
    best-first. Only suggestions at or above `min_ratio` are returned so
    obviously-unrelated columns (e.g. dates, free-text notes) get an empty
    list rather than a misleading "nearest-neighbor" guess.
    """
    if not header or not header.strip():
        return []
    _, bare = _normalize_header(header)
    if not bare:
        return []
    scored: list[tuple[float, str, str]] = []
    for variable, aliases in _SUGGESTION_ALIASES.items():
        for alias in aliases:
            r = difflib.SequenceMatcher(None, bare, alias).ratio()
            if r >= min_ratio:
                scored.append((r, variable, alias))
    scored.sort(reverse=True)
    # Dedupe by variable (keep highest-scoring alias per variable) then cap
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r, v, a in scored:
        if v in seen:
            continue
        seen.add(v)
        out.append({'variable': v, 'closest_alias': a, 'ratio': round(r, 3)})
        if len(out) >= top_n:
            break
    return out


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
    match_source = 'unmapped'
    # Fast path: exact regex prefix match (unchanged from the original impl
    # so files that ingested correctly before keep ingesting identically).
    for regex, var, ccy in _COMPILED_PATTERNS:
        if regex.match(header):
            variable = var
            currency_semantics = ccy
            match_source = 'regex'
            break
    # Fallback: deterministic keyword-set matching after normalization. Only
    # runs when the regex list found nothing, so no existing behavior changes.
    if variable is None:
        tokens, _ = _normalize_header(header)
        kw_var, kw_ccy = _keyword_match(tokens)
        if kw_var is not None:
            variable = kw_var
            currency_semantics = kw_ccy
            match_source = 'keyword'

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
        'match_source': match_source,   # 'regex' | 'keyword' | 'unmapped'
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

# ISO 4217 code → list of name/alias strings that should all resolve to it.
# Covers the 30+ major global currencies used by companies on the exchanges
# we ingest. Lookup is case/punctuation-insensitive (see _normalize_ccy_key),
# so "south korean won", "South Korean Won", "KRW" all map to "KRW".
_CURRENCY_ALIASES: dict[str, list[str]] = {
    # North America
    'USD': ['US Dollar', 'United States Dollar', 'U.S. Dollar', 'USD'],
    'CAD': ['Canadian Dollar', 'CAD'],
    'MXN': ['Mexican Peso', 'MXN'],
    # Europe
    'EUR': ['Euro', 'EUR'],
    'GBP': ['British Pound', 'Pound Sterling', 'UK Pound', 'GBP'],
    'CHF': ['Swiss Franc', 'CHF'],
    'SEK': ['Swedish Krona', 'SEK'],
    'NOK': ['Norwegian Krone', 'NOK'],
    'DKK': ['Danish Krone', 'DKK'],
    'PLN': ['Polish Zloty', 'Polish Złoty', 'PLN'],
    'CZK': ['Czech Koruna', 'CZK'],
    'HUF': ['Hungarian Forint', 'HUF'],
    'RON': ['Romanian Leu', 'New Romanian Leu', 'RON'],
    'TRY': ['Turkish Lira', 'New Turkish Lira', 'TRY'],
    'RUB': ['Russian Ruble', 'Russian Rouble', 'RUB'],
    # Asia-Pacific
    'JPY': ['Japanese Yen', 'Yen', 'JPY'],
    'CNY': ['Chinese Renminbi (Yuan)', 'Chinese Yuan', 'Renminbi', 'Yuan', 'CNY', 'RMB'],
    'HKD': ['Hong Kong Dollar', 'HKD'],
    'TWD': ['Taiwan New Dollar', 'New Taiwan Dollar', 'Taiwan Dollar', 'TWD'],
    'KRW': ['South Korean Won', 'Korean Won', 'Won', 'KRW'],
    'INR': ['Indian Rupee', 'Rupee', 'INR'],
    'SGD': ['Singapore Dollar', 'SGD'],
    'AUD': ['Australian Dollar', 'AUD'],
    'NZD': ['New Zealand Dollar', 'NZD'],
    'IDR': ['Indonesian Rupiah', 'Rupiah', 'IDR'],
    'MYR': ['Malaysian Ringgit', 'Ringgit', 'MYR'],
    'PHP': ['Philippine Peso', 'Philippines Peso', 'PHP'],
    'THB': ['Thai Baht', 'Baht', 'THB'],
    'VND': ['Vietnamese Dong', 'Dong', 'VND'],
    'PKR': ['Pakistani Rupee', 'PKR'],
    'BDT': ['Bangladeshi Taka', 'BDT'],
    # Middle East / Africa
    'AED': ['UAE Dirham', 'Emirati Dirham', 'AED'],
    'SAR': ['Saudi Riyal', 'SAR'],
    'QAR': ['Qatari Riyal', 'Qatari Rial', 'QAR'],
    'KWD': ['Kuwaiti Dinar', 'KWD'],
    'BHD': ['Bahraini Dinar', 'BHD'],
    'OMR': ['Omani Rial', 'OMR'],
    'ILS': ['Israeli Shekel', 'Israeli New Shekel', 'Shekel', 'ILS', 'NIS'],
    'EGP': ['Egyptian Pound', 'EGP'],
    'ZAR': ['South African Rand', 'Rand', 'ZAR'],
    'NGN': ['Nigerian Naira', 'Naira', 'NGN'],
    # Latin America
    'BRL': ['Brazilian Real', 'Real', 'BRL'],
    'ARS': ['Argentine Peso', 'Argentinian Peso', 'ARS'],
    'CLP': ['Chilean Peso', 'CLP'],
    'COP': ['Colombian Peso', 'COP'],
    'PEN': ['Peruvian Sol', 'Nuevo Sol', 'PEN'],
}

# Flat reverse lookup: normalized-alias-key → ISO code. Case/punctuation-stripped.
_NORMALIZED_TO_ISO: dict[str, str] = {}


def _normalize_ccy_key(s: str) -> str:
    """Lowercase + keep only alnum so 'South Korean Won' and 'south-korean-won'
    and 'SouthKoreanWon' all collapse to the same key."""
    return re.sub(r'[^a-z0-9]+', '', s.lower())


for _iso, _aliases in _CURRENCY_ALIASES.items():
    for _a in _aliases:
        _NORMALIZED_TO_ISO[_normalize_ccy_key(_a)] = _iso


def normalize_filing_currency(raw: Any) -> str | None:
    """Canonicalize any vendor currency string to its ISO 4217 code.

    Resolution order (deterministic, LLM-free):
      1. Exact case-insensitive alias lookup (strips punctuation/whitespace).
         "South Korean Won", "south-korean won", "KRW" → 'KRW'.
      2. 3-letter all-upper shape check: if the input is already an ISO code
         in our table, return it.
      3. Fuzzy fallback via difflib (threshold 0.88) — catches typos like
         "Koren Won" → "KRW".
      4. Passthrough: unknown string returned as-is so the operator sees it
         in the UI and can extend `_CURRENCY_ALIASES` if needed.

    Returns None only for empty/non-string inputs.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    key = _normalize_ccy_key(s)
    if not key:
        return s
    # Layer 1: exact case/punct-insensitive
    if key in _NORMALIZED_TO_ISO:
        return _NORMALIZED_TO_ISO[key]
    # Layer 2: already a known ISO?
    up = s.upper()
    if up in _CURRENCY_ALIASES:
        return up
    # Layer 3: fuzzy fallback for typos
    all_keys = list(_NORMALIZED_TO_ISO.keys())
    close = difflib.get_close_matches(key, all_keys, n=1, cutoff=0.88)
    if close:
        return _NORMALIZED_TO_ISO[close[0]]
    # Layer 4: passthrough so unknown names remain visible
    return s


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
