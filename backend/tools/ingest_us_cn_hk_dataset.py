"""
Ingester — reads CIQ screener .xls files from a designated folder and loads
them into the SQLite database at backend/data_sources/us_cn_hk.sqlite.

Pure Python. Zero LLM at runtime. Idempotent — drops & recreates the
companies / financials_annual / financials_quarterly tables on every run.
Persists ingest_log rows across runs for audit.

Usage:
    python -m tools.ingest_us_cn_hk_dataset [--data-dir PATH]

Default data-dir: repository-root/US_CN_HK_dataset/

Behavior:
  - Finds all ginzu_cc_*.xls in the folder.
  - Groups files by stem prefix (cc_1_* vs cc_2_*); concatenates the rows
    of each group (cc_1_1 + cc_1_2 → screener 1; cc_2_1 + cc_2_2 → screener 2).
  - Joins screener 1 and screener 2 on Exchange:Ticker (inner join — only
    keep tickers present in both).
  - Per-row: routes each cell through the CIQ_HEADER_PATTERNS map to the
    correct destination. Unknown headers logged to unmapped_columns.
  - Derives region + listing_currency from exchange prefix via the existing
    EXCHANGE_CURRENCY map. Filing currency normalized from CIQ's verbose
    name (e.g. 'US Dollar' → 'USD').
  - Computes fx_listing_to_reporting when listing == filing (→ 1.0). For
    cross-currency firms, leaves None — the user supplies it via the
    Currency Info panel in the app.
  - Writes the report to ingest_log.

Fails loud but not fatal: unknown headers, unknown exchanges, missing
rows → all captured in the report. Never crashes mid-ingest.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import xlrd

# Ensure backend/ is on sys.path when running as `python -m tools.ingest_...`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources import us_cn_hk_db as db
from data_sources.us_cn_hk_mapping import (
    parse_ciq_header,
    parse_geographic_segments,
    normalize_effective_tax_rate,
    normalize_filing_currency,
    parse_exchange_code,
)
from data_sources.exchange_currency_map import EXCHANGE_CURRENCY

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "US_CN_HK_dataset"
HEADER_ROW = 7  # zero-indexed; row 7 is the CIQ screener's actual header row
FIRST_DATA_ROW = 8


# ---------------------------------------------------------------------------
# Region inference
# ---------------------------------------------------------------------------

_REGION_BY_EXCHANGE_PREFIX = {
    # US
    "NasdaqGS": "US", "NasdaqGM": "US", "NasdaqCM": "US",
    "NYSE": "US", "NYSEAM": "US", "NYSEArca": "US", "OTCPK": "US", "OTCBB": "US",
    # Greater China
    "SEHK": "HK",
    "SHSE": "CN", "SZSE": "CN",
    # Extend as new regions onboard. Unknown prefixes land in 'UNKNOWN' and are logged.
}


def region_from_exchange(exchange_code: str | None) -> str:
    if not exchange_code:
        return "UNKNOWN"
    return _REGION_BY_EXCHANGE_PREFIX.get(exchange_code, "UNKNOWN")


# ---------------------------------------------------------------------------
# .xls readers — streaming, no bulk-data retention
# ---------------------------------------------------------------------------

def read_sheet_rows(path: Path) -> tuple[list[str], list[list[Any]]]:
    """Return (headers, data_rows) from a screener .xls.
    data_rows is a list of lists — memory-mapped but contains the full
    sheet, which for 12k-row screeners is ~tens of MB in Python lists.
    Acceptable: this runs server-side at ingest time, not during user calls.
    """
    wb = xlrd.open_workbook(str(path), on_demand=True)
    sh = wb.sheet_by_name("Screening")
    headers = [str(sh.cell_value(HEADER_ROW, c)).strip() for c in range(sh.ncols)]
    data_rows: list[list[Any]] = []
    for r in range(FIRST_DATA_ROW, sh.nrows):
        data_rows.append([sh.cell_value(r, c) for c in range(sh.ncols)])
    wb.release_resources()
    return headers, data_rows


def _group_files(data_dir: Path) -> dict[str, list[Path]]:
    """Group ginzu_cc_*.xls files by their leading screener id.

    'ginzu_cc_1_1.xls', 'ginzu_cc_1_2.xls' → screener '1'
    'ginzu_cc_2_1.xls', 'ginzu_cc_2_2.xls' → screener '2'
    Supports future 'ginzu_cc_3_1.xls' etc. — any new prefix gets its own group.
    """
    groups: dict[str, list[Path]] = {}
    pat = re.compile(r"^ginzu_cc_(\d+)_\d+\.xlsx?$", re.IGNORECASE)
    for f in sorted(data_dir.glob("ginzu_cc_*.xls*")):
        m = pat.match(f.name)
        if m:
            groups.setdefault(m.group(1), []).append(f)
    return groups


def _parsed_excel_date(value: Any, datemode: int = 0) -> str | None:
    """Excel serial → ISO date string. Passes through strings as-is."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and 40000 < value < 80000:
        try:
            return xlrd.xldate_as_datetime(value, datemode).date().isoformat()
        except Exception:
            return None
    return str(value)


def _num_or_none(v: Any) -> float | None:
    """Numeric cell → float; '-', '', None, and unparseable → None."""
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Per-row decoding
# ---------------------------------------------------------------------------

def decode_screener_row(
    headers: list[str],
    row: list[Any],
    decoded_headers: list[dict | None],
) -> dict[str, Any]:
    """Turn one raw row into a flat dict keyed by internal variable names,
    with period-indexed keys for annual/quarterly series.

    For period-indexed fields the key is e.g. 'revenues__annual_3' or
    'ebit__quarterly_0'. Snapshot fields use the variable name directly.
    """
    out: dict[str, Any] = {}
    for c, parsed in enumerate(decoded_headers):
        if not parsed or not parsed["variable"]:
            continue
        raw = row[c]
        var = parsed["variable"]
        pk = parsed["period_kind"]
        po = parsed["period_offset"]

        # Identifier / text-only fields
        if var in ("company_name", "ticker", "company_type",
                   "primary_exchange", "secondary_exchanges",
                   "actual_rating_fc", "actual_rating_lc"):
            s = str(raw).strip() if raw not in (None, "") else None
            if s == "-":
                s = None
            out[var] = s
            continue
        if var == "reporting_currency":
            out[var] = normalize_filing_currency(raw)
            continue
        if var in ("period_date_annual", "period_date_quarterly"):
            out[var] = _parsed_excel_date(raw)
            continue
        if var == "effective_tax_rate_ciq":
            out["effective_tax_rate"] = normalize_effective_tax_rate(raw)
            continue
        if var.startswith("geographic_segments"):
            # Only keep the (Details) variant as structured; the non-details
            # column is just an aggregate number, already captured elsewhere.
            if var == "geographic_segments_revenue_detail":
                out["geographic_segments"] = parse_geographic_segments(raw)
            continue
        if var == "options_avg_strike":
            out[var] = _num_or_none(raw)
            continue
        if var == "options_outstanding":
            out[var] = _num_or_none(raw)
            continue
        if var in ("stock_price", "mv_equity_listing"):
            # Map to listing-currency schema fields (per §6a currency correction).
            # stock_price_listing is the DB column name.
            dest = "stock_price_listing" if var == "stock_price" else var
            out[dest] = _num_or_none(raw)
            continue
        if var.startswith("lease_commitment_"):
            out[var] = _num_or_none(raw)
            continue

        # Period-indexed (income + balance sheet)
        if pk in ("annual", "quarterly"):
            key = f"{var}__{pk}_{po}"
            out[key] = _num_or_none(raw)
            continue

        # Fall-through — rare, log as string
        out[var] = raw
    return out


# ---------------------------------------------------------------------------
# Ingester core
# ---------------------------------------------------------------------------

def ingest(data_dir: Path) -> dict[str, Any]:
    """Run the ingest pipeline. Returns a report dict (also written to ingest_log)."""
    start = time.time()
    warnings: list[str] = []
    unmapped_cols_seen: set[str] = set()
    unmapped_exchanges_seen: set[str] = set()
    file_manifest: list[dict] = []

    if not data_dir.exists():
        return {
            "status": "error",
            "error": f"Data directory does not exist: {data_dir}",
            "n_companies": 0,
        }

    groups = _group_files(data_dir)
    if not groups:
        return {
            "status": "error",
            "error": f"No ginzu_cc_*.xls files found in {data_dir}",
            "n_companies": 0,
        }

    # Record file manifest for the ingest_log.
    for g_id, files in groups.items():
        for fp in files:
            file_manifest.append({
                "file": fp.name,
                "size_bytes": fp.stat().st_size,
                "mtime": datetime.fromtimestamp(fp.stat().st_mtime).isoformat(),
                "group": g_id,
            })

    # Per-screener: concatenate rows from all files in the group.
    screener_rows: dict[str, list[dict[str, Any]]] = {}
    for g_id, files in groups.items():
        combined: list[dict[str, Any]] = []
        master_headers: list[str] | None = None
        decoded_headers: list[dict | None] | None = None
        for fp in files:
            headers, data_rows = read_sheet_rows(fp)
            if master_headers is None:
                master_headers = headers
                decoded_headers = [parse_ciq_header(h) for h in headers]
                for h, p in zip(headers, decoded_headers):
                    if p and p["variable"] is None and h.strip():
                        unmapped_cols_seen.add(h)
            elif headers != master_headers:
                warnings.append(
                    f"Header mismatch between {files[0].name} and {fp.name} — "
                    f"skipping {fp.name}. Re-export the screener to align columns."
                )
                continue
            assert decoded_headers is not None
            for row in data_rows:
                tkr = str(row[1]).strip() if len(row) > 1 and row[1] else None
                if not tkr:
                    continue
                d = decode_screener_row(headers, row, decoded_headers)
                d["__ticker"] = tkr
                combined.append(d)
        screener_rows[g_id] = combined

    # Join on __ticker (inner join).
    if len(screener_rows) < 2:
        warnings.append(
            "Fewer than 2 screener groups found; using only available group(s). "
            "This is OK for testing but the full schema needs both."
        )

    by_ticker: dict[str, dict[str, Any]] = {}
    group_ids = sorted(screener_rows.keys())
    # Seed with the first group
    for row in screener_rows[group_ids[0]]:
        by_ticker[row["__ticker"]] = dict(row)
    # Intersect with subsequent groups
    for g_id in group_ids[1:]:
        g_map = {row["__ticker"]: row for row in screener_rows[g_id]}
        new_map: dict[str, dict[str, Any]] = {}
        for tkr, merged in by_ticker.items():
            other = g_map.get(tkr)
            if other is None:
                continue  # inner join — drop
            merged.update(other)
            new_map[tkr] = merged
        by_ticker = new_map

    # Transform to DB-insertable shape.
    companies_rows: list[dict[str, Any]] = []
    annual_rows: list[dict[str, Any]] = []
    quarterly_rows: list[dict[str, Any]] = []
    n_rejected = 0
    data_as_of = datetime.now(timezone.utc).date().isoformat()

    # Period-indexed field keys we expect: each internal variable × period-kind × offset.
    # We'll scan each merged row and bucket them.
    ANNUAL_METRICS = [
        "revenues", "ebit", "ebitda", "net_income", "interest_expense", "capex",
        "d_a", "earnings_before_tax", "total_tax_expense", "operating_lease_expense",
        "r_and_d_expense", "cash_and_marketable_securities", "cross_holdings",
        "bv_debt", "bv_equity", "shares_outstanding", "minority_interests",
    ]
    QUARTERLY_METRICS = list(ANNUAL_METRICS)

    for tkr, row in by_ticker.items():
        name = row.get("company_name")
        if not name:
            n_rejected += 1
            continue

        primary = row.get("primary_exchange")
        exchange_code = parse_exchange_code(primary)
        if exchange_code is None and primary:
            unmapped_exchanges_seen.add(primary)

        listing_currency = EXCHANGE_CURRENCY.get(exchange_code) if exchange_code else None
        filing_currency = row.get("reporting_currency")

        # FX default: 1.0 when listing == filing, else None (user supplies).
        fx = None
        fx_src = "unset"
        if listing_currency and filing_currency and listing_currency == filing_currency:
            fx = 1.0
            fx_src = "same currency"

        # Geographic segments: list[dict] → JSON string for storage.
        geo = row.get("geographic_segments") or []
        geo_json = json.dumps(geo) if isinstance(geo, list) else None

        companies_rows.append({
            "ticker": tkr,
            "company_name": name,
            "company_type": row.get("company_type"),
            "exchange_code": exchange_code,
            "primary_exchange": primary,
            "secondary_exchanges": row.get("secondary_exchanges"),
            "region": region_from_exchange(exchange_code),
            "filing_currency": filing_currency,
            "listing_currency": listing_currency,
            "fx_listing_to_reporting": fx,
            "fx_rate_source": fx_src,
            "effective_tax_rate": row.get("effective_tax_rate"),
            "stock_price_listing": row.get("stock_price_listing"),
            "mv_equity_listing": row.get("mv_equity_listing"),
            "actual_rating_fc": row.get("actual_rating_fc"),
            "actual_rating_lc": row.get("actual_rating_lc"),
            "options_outstanding": row.get("options_outstanding"),
            "options_avg_strike": row.get("options_avg_strike"),
            "period_date_annual": row.get("period_date_annual"),
            "period_date_quarterly": row.get("period_date_quarterly"),
            "lease_commitment_yr1": row.get("lease_commitment_yr1"),
            "lease_commitment_yr2": row.get("lease_commitment_yr2"),
            "lease_commitment_yr3": row.get("lease_commitment_yr3"),
            "lease_commitment_yr4": row.get("lease_commitment_yr4"),
            "lease_commitment_yr5": row.get("lease_commitment_yr5"),
            "lease_commitment_beyond": row.get("lease_commitment_beyond"),
            "geographic_segments_json": geo_json,
            "data_as_of": data_as_of,
        })

        # Annual financials: bucket period-indexed keys (var__annual_N)
        for offset in range(10):
            rec = {"ticker": tkr, "fy_offset": offset}
            any_present = False
            for m in ANNUAL_METRICS:
                k = f"{m}__annual_{offset}"
                v = row.get(k)
                rec[m] = v
                if v is not None:
                    any_present = True
            if any_present:
                annual_rows.append(rec)

        # Quarterly financials: offsets 0..7
        for offset in range(8):
            rec = {"ticker": tkr, "fq_offset": offset}
            any_present = False
            for m in QUARTERLY_METRICS:
                k = f"{m}__quarterly_{offset}"
                v = row.get(k)
                rec[m] = v
                if v is not None:
                    any_present = True
            if any_present:
                quarterly_rows.append(rec)

    # Write to DB — single transaction via get_connection().
    with db.get_connection() as conn:
        db.init_schema(conn, drop_existing=True)
        db.insert_companies(conn, companies_rows)
        db.insert_annual_financials(conn, annual_rows)
        db.insert_quarterly_financials(conn, quarterly_rows)
        db.log_ingest(
            conn,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            n_companies=len(companies_rows),
            n_rejected=n_rejected,
            n_files=sum(len(v) for v in groups.values()),
            file_manifest=file_manifest,
            unmapped_columns=sorted(unmapped_cols_seen),
            unmapped_exchanges=sorted(unmapped_exchanges_seen),
            warnings=warnings,
            duration_ms=int((time.time() - start) * 1000),
        )

    return {
        "status": "ok",
        "n_companies": len(companies_rows),
        "n_rejected": n_rejected,
        "n_annual_rows": len(annual_rows),
        "n_quarterly_rows": len(quarterly_rows),
        "unmapped_columns": sorted(unmapped_cols_seen),
        "unmapped_exchanges": sorted(unmapped_exchanges_seen),
        "warnings": warnings,
        "duration_seconds": round(time.time() - start, 2),
        "file_manifest": file_manifest,
    }


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Ingest CIQ screener .xls files into SQLite.")
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                    help=f"Folder containing ginzu_cc_*.xls files (default: {DEFAULT_DATA_DIR})")
    ap.add_argument("--db-path", type=str, default=None,
                    help="SQLite path override (sets US_CN_HK_DB_PATH env var)")
    args = ap.parse_args()

    if args.db_path:
        import os
        os.environ["US_CN_HK_DB_PATH"] = args.db_path

    try:
        report = ingest(args.data_dir)
    except Exception as e:
        traceback.print_exc()
        print(f"\nFATAL: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps({k: v for k, v in report.items() if k != "file_manifest"}, indent=2))
    if report.get("unmapped_columns"):
        print(f"\n⚠ {len(report['unmapped_columns'])} unmapped columns — see JSON above.")
    if report.get("unmapped_exchanges"):
        print(f"⚠ {len(report['unmapped_exchanges'])} unmapped exchange prefixes.")
    if report.get("warnings"):
        print(f"⚠ {len(report['warnings'])} warnings.")


if __name__ == "__main__":
    main()
