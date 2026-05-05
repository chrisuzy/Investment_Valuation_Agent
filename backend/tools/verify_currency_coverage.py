"""
tools/verify_currency_coverage.py

Verify currency + FX-rate coverage across every company in the US/CN/HK DB.

Checks three categories (all required for a complete valuation):
  1. Reporting currency  — where DCF math runs. In this schema = filing_currency
                           (CIQ reports financials in the filer's home currency;
                           our orchestrator treats that as the reporting ccy).
  2. Listing currency    — where the stock trades. Used for user-facing price.
  3. Filing currency     — the CIQ "Reported Currency" column (redundant with
                           reporting ccy today, but surfaced separately because
                           some CIQ exports put "-" in this column).

For every company, verify:
  - All three currency codes resolve to valid ISO 4217
  - If listing ≠ filing, an FX rate is available (stored or derivable from the
    USD-anchor table)

Pure Python, zero LLM tokens. Runs in ~5 seconds for 35k companies.

Usage:
  python -m tools.verify_currency_coverage                        # full DB
  python -m tools.verify_currency_coverage --sample 100 --seed 1  # random 100
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from data_sources.us_cn_hk_mapping import normalize_filing_currency  # noqa: E402
from tools.ingest_us_cn_hk_dataset import _USD_PER_CCY, default_fx_rate  # noqa: E402

# Exchange name (or code in parens) → listing ISO 4217
# Keyed by a substring that uniquely identifies the exchange.
_EXCHANGE_TO_CCY: dict[str, str] = {
    "NasdaqGS": "USD", "NasdaqGM": "USD", "NasdaqCM": "USD",
    "NYSE)": "USD", "NYSEAM": "USD", "OTCPK": "USD", "OTCBB": "USD",
    "SEHK": "HKD",
    "SHSE": "CNY", "SZSE": "CNY",
    "BSE)": "INR", "NSEI": "INR",
    "TSE)": "JPY",
    "ASX": "AUD",
    "TSX": "CAD", "TSXV": "CAD",
    "LSE)": "GBP", "AIM": "GBP",
    "XTRA": "EUR", "DB)": "EUR", "ENXTPA": "EUR", "ENXTBR": "EUR",
    "ENXTAM": "EUR", "ENXTLS": "EUR", "BIT)": "EUR", "BME)": "EUR",
    "HLSE": "EUR", "ICSE": "EUR", "TLSE": "EUR", "RISE": "EUR",
    "NSEL": "EUR",  # Vilnius (EUR since 2015)
    "OM)": "SEK",
    "CPSE": "DKK",
    "SWX": "CHF",
    "BOVESPA": "BRL",
    "BMV": "MXN",
    "SET": "THB",
    "IDX": "IDR",
    "SGX": "SGD",
    "TWSE": "TWD",
    "KOSE": "KRW", "KOSDAQ": "KRW",
    "JMSE": "JMD",  # Jamaica (not in USD-anchor table)
}


def infer_currency_from_exchange(exchange: str | None) -> str | None:
    """Best-effort: match the first exchange-substring that appears in the name."""
    if not exchange:
        return None
    for key, ccy in _EXCHANGE_TO_CCY.items():
        if key in exchange:
            return ccy
    return None


def _missing(v) -> bool:
    """A value is missing if it's None, empty string, '-', 'n/a', or whitespace."""
    if v is None:
        return True
    s = str(v).strip().lower()
    return s in ("", "-", "n/a", "na", "null", "none")


def check_company(ticker: str, filing_raw: str, listing_raw: str,
                  stored_fx: float | None,
                  exchange: str | None = None,
                  use_exchange_fallback: bool = False) -> dict:
    """Run all three currency checks on one company.

    Returns dict with:
      - filing_ok, listing_ok, fx_ok  (bools)
      - filing_norm, listing_norm     (ISO 4217 or None)
      - fx_rate, fx_source            (float, source-label)
      - failure_reasons               (list of str — empty = full coverage)
    """
    reasons: list[str] = []

    # Filing currency
    if _missing(filing_raw):
        filing_norm = None
        reasons.append("filing_missing")
        filing_ok = False
    else:
        filing_norm = normalize_filing_currency(filing_raw)
        if filing_norm is None:
            reasons.append(f"filing_unresolvable:{filing_raw!r}")
            filing_ok = False
        else:
            filing_ok = True

    # Listing currency (with optional exchange-based fallback)
    if _missing(listing_raw):
        if use_exchange_fallback:
            inferred = infer_currency_from_exchange(exchange)
            if inferred:
                listing_norm = inferred
                listing_ok = True
                reasons.append("listing_inferred_from_exchange")
            else:
                listing_norm = None
                reasons.append("listing_missing")
                listing_ok = False
        else:
            listing_norm = None
            reasons.append("listing_missing")
            listing_ok = False
    else:
        listing_norm = normalize_filing_currency(listing_raw)
        if listing_norm is None:
            reasons.append(f"listing_unresolvable:{listing_raw!r}")
            listing_ok = False
        else:
            listing_ok = True

    # Filing fallback: if filing is '-' but listing resolved via fallback, many
    # CIQ exports have filing == listing for single-country companies.
    if use_exchange_fallback and not filing_ok and listing_ok:
        inferred = infer_currency_from_exchange(exchange)
        if inferred:
            filing_norm = inferred
            filing_ok = True
            reasons.append("filing_inferred_from_exchange")

    # FX rate (only required if listing ≠ filing)
    fx_ok = False
    fx_rate: float | None = None
    fx_source = "unset"
    if filing_ok and listing_ok:
        if filing_norm == listing_norm:
            fx_ok = True
            fx_rate = 1.0
            fx_source = "same_currency"
        elif stored_fx is not None and stored_fx > 0:
            fx_ok = True
            fx_rate = float(stored_fx)
            fx_source = "stored"
        else:
            rate, src = default_fx_rate(listing_norm, filing_norm)
            if rate is not None:
                fx_ok = True
                fx_rate = rate
                fx_source = src
            else:
                reasons.append(f"fx_rate_missing:{listing_norm}->{filing_norm}")
    elif not filing_ok or not listing_ok:
        reasons.append("fx_not_checkable")

    return {
        "ticker": ticker,
        "filing_raw": filing_raw,
        "filing_norm": filing_norm,
        "filing_ok": filing_ok,
        "listing_raw": listing_raw,
        "listing_norm": listing_norm,
        "listing_ok": listing_ok,
        "fx_rate": fx_rate,
        "fx_source": fx_source,
        "fx_ok": fx_ok,
        "reasons": reasons,
    }


def iter_rows(db_path: str, sample: int | None = None, seed: int | None = None):
    """Yield (ticker, filing, listing, fx_listing_to_reporting, exchange)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT ticker, filing_currency, listing_currency, "
                "fx_listing_to_reporting, primary_exchange FROM companies")
    rows = cur.fetchall()
    conn.close()
    if sample:
        import random
        rng = random.Random(seed)
        rows = rng.sample(rows, min(sample, len(rows)))
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(_REPO_ROOT / "backend/data_sources/us_cn_hk.sqlite"))
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--top", type=int, default=15, help="Top N problem values to show")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--fallback", action="store_true",
                   help="Use primary_exchange to infer missing listing/filing currencies")
    args = p.parse_args()

    rows = iter_rows(args.db, sample=args.sample, seed=args.seed)
    n = len(rows)

    all_ok = 0
    filing_fails = 0
    listing_fails = 0
    fx_fails = 0
    reason_freq: Counter = Counter()
    filing_raw_bad: Counter = Counter()
    listing_raw_bad: Counter = Counter()
    fx_pair_bad: Counter = Counter()
    ticker_examples: dict[str, list[str]] = {}

    for ticker, filing_raw, listing_raw, stored_fx, exchange in rows:
        r = check_company(ticker, filing_raw or "", listing_raw or "", stored_fx,
                          exchange=exchange, use_exchange_fallback=args.fallback)
        if args.verbose:
            print(f"{r['ticker']:<20}  filing={r['filing_raw']!r:<15}→{r['filing_norm']}  "
                  f"listing={r['listing_raw']!r:<10}→{r['listing_norm']}  "
                  f"fx={r['fx_rate']} ({r['fx_source']})  ok={r['filing_ok'] and r['listing_ok'] and r['fx_ok']}")
        if not r["filing_ok"]:
            filing_fails += 1
            filing_raw_bad[str(filing_raw)] += 1
        if not r["listing_ok"]:
            listing_fails += 1
            listing_raw_bad[str(listing_raw)] += 1
        if not r["fx_ok"]:
            fx_fails += 1
            if r["filing_ok"] and r["listing_ok"]:
                fx_pair_bad[f"{r['listing_norm']}→{r['filing_norm']}"] += 1
        if r["filing_ok"] and r["listing_ok"] and r["fx_ok"]:
            all_ok += 1
        for reason in r["reasons"]:
            tag = reason.split(":")[0]
            reason_freq[tag] += 1
            ticker_examples.setdefault(tag, []).append(r["ticker"])

    label = f"SAMPLE (n={args.sample}, seed={args.seed})" if args.sample else "FULL DB"
    print(f"\n{'=' * 65}\n{label}\n{'=' * 65}")
    print(f"Companies checked:            {n:,}")
    print(f"  all three checks pass:      {all_ok:,}  ({all_ok/max(n,1)*100:.1f}%)")
    print(f"  filing currency fails:      {filing_fails:,}  ({filing_fails/max(n,1)*100:.1f}%)")
    print(f"  listing currency fails:     {listing_fails:,}  ({listing_fails/max(n,1)*100:.1f}%)")
    print(f"  FX rate fails:              {fx_fails:,}  ({fx_fails/max(n,1)*100:.1f}%)")

    print(f"\nFailure reasons:")
    for tag, cnt in reason_freq.most_common():
        print(f"  {tag:<25} {cnt:>8,}")

    if filing_raw_bad:
        print(f"\nTop {args.top} unresolvable filing_currency values:")
        for val, cnt in filing_raw_bad.most_common(args.top):
            print(f"  {cnt:5d}×  {val!r}")
    if listing_raw_bad:
        print(f"\nTop {args.top} unresolvable listing_currency values:")
        for val, cnt in listing_raw_bad.most_common(args.top):
            print(f"  {cnt:5d}×  {val!r}")
    if fx_pair_bad:
        print(f"\nTop {args.top} unresolvable FX pairs (listing→filing):")
        for pair, cnt in fx_pair_bad.most_common(args.top):
            print(f"  {cnt:5d}×  {pair}")

    print(f"\n{'=' * 65}\nSUMMARY")
    print(f"{'=' * 65}")
    print(f"Currencies in USD-anchor table: {len(_USD_PER_CCY)}")
    print(f"Overall coverage:               {all_ok/max(n,1)*100:.2f}%")


if __name__ == "__main__":
    main()
