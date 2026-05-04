"""
SQLite database layer for the US/CN/HK (and future regions) company dataset.

Schema-as-code: three tables + ingest log. Idempotent — the ingester drops
and recreates tables on refresh, so re-running is always safe. Every write
is a single transaction; partial failures don't leave the DB inconsistent.

Public surface:
  - get_connection()            open a connection (creates the DB file if absent)
  - init_schema()               drop + recreate tables (called at start of every refresh)
  - insert_companies()          bulk-insert companies table
  - insert_annual_financials()  bulk-insert financials_annual
  - insert_quarterly_financials() bulk-insert financials_quarterly
  - log_ingest()                append a row to ingest_log
  - search_companies()          GET /api/database/search — LIKE on name + exact-prefix on ticker
  - fetch_company()             GET /api/database/company/<ticker> — fully-assembled dict
  - latest_ingest_summary()     GET /api/admin/dataset-status — last refresh report
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parent / "us_cn_hk.sqlite"


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_db_path() -> Path:
    """Override via env var US_CN_HK_DB_PATH (useful for tests)."""
    env = os.environ.get("US_CN_HK_DB_PATH")
    return Path(env) if env else DB_PATH


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with sensible defaults for a read-mostly,
    single-writer app. Always commits or rolls back on exit."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # readers never block writers
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_COMPANIES_DDL = """
CREATE TABLE IF NOT EXISTS companies (
    ticker                  TEXT PRIMARY KEY,
    company_name            TEXT NOT NULL,
    company_type            TEXT,
    exchange_code           TEXT,
    primary_exchange        TEXT,
    secondary_exchanges     TEXT,
    region                  TEXT,
    filing_currency         TEXT,
    listing_currency        TEXT,
    fx_listing_to_reporting REAL,          -- derived at ingest when possible
    fx_rate_source          TEXT,          -- 'same currency' | 'unset' | 'manual' | …
    effective_tax_rate      REAL,          -- /100 already applied
    stock_price_listing     REAL,
    mv_equity_listing       REAL,
    actual_rating_fc        TEXT,
    actual_rating_lc        TEXT,
    options_outstanding     REAL,
    options_avg_strike      REAL,          -- listing currency
    period_date_annual      TEXT,
    period_date_quarterly   TEXT,
    lease_commitment_yr1    REAL,
    lease_commitment_yr2    REAL,
    lease_commitment_yr3    REAL,
    lease_commitment_yr4    REAL,
    lease_commitment_yr5    REAL,
    lease_commitment_beyond REAL,
    geographic_segments_json TEXT,         -- list[{name, revenue, pct}]
    data_as_of              TEXT           -- ISO date of the ingest
);
"""

_FINANCIALS_ANNUAL_DDL = """
CREATE TABLE IF NOT EXISTS financials_annual (
    ticker                          TEXT NOT NULL,
    fy_offset                       INTEGER NOT NULL,   -- 0 = FY-0 (most recent)
    revenues                        REAL,
    ebit                            REAL,
    ebitda                          REAL,
    net_income                      REAL,
    interest_expense                REAL,
    capex                           REAL,
    d_a                             REAL,
    earnings_before_tax             REAL,
    total_tax_expense               REAL,
    operating_lease_expense         REAL,
    r_and_d_expense                 REAL,
    cash_and_marketable_securities  REAL,
    cross_holdings                  REAL,
    bv_debt                         REAL,
    bv_equity                       REAL,
    shares_outstanding              REAL,
    minority_interests              REAL,
    PRIMARY KEY (ticker, fy_offset),
    FOREIGN KEY (ticker) REFERENCES companies(ticker) ON DELETE CASCADE
);
"""

_FINANCIALS_QUARTERLY_DDL = """
CREATE TABLE IF NOT EXISTS financials_quarterly (
    ticker                          TEXT NOT NULL,
    fq_offset                       INTEGER NOT NULL,   -- 0 = FQ-0 (most recent)
    revenues                        REAL,
    ebit                            REAL,
    ebitda                          REAL,
    net_income                      REAL,
    interest_expense                REAL,
    capex                           REAL,
    d_a                             REAL,
    earnings_before_tax             REAL,
    total_tax_expense               REAL,
    operating_lease_expense         REAL,
    r_and_d_expense                 REAL,
    cash_and_marketable_securities  REAL,           -- FQ-0 only on balance-sheet
    cross_holdings                  REAL,
    bv_debt                         REAL,
    bv_equity                       REAL,
    shares_outstanding              REAL,
    minority_interests              REAL,
    PRIMARY KEY (ticker, fq_offset),
    FOREIGN KEY (ticker) REFERENCES companies(ticker) ON DELETE CASCADE
);
"""

_INGEST_LOG_DDL = """
CREATE TABLE IF NOT EXISTS ingest_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc   TEXT NOT NULL,
    n_companies     INTEGER NOT NULL,
    n_rejected      INTEGER NOT NULL,
    n_files         INTEGER NOT NULL,
    file_manifest   TEXT,     -- JSON: [{name, size, mtime}, …]
    unmapped_columns TEXT,    -- JSON list
    unmapped_exchanges TEXT,  -- JSON list
    warnings        TEXT,     -- JSON list of strings
    duration_ms     INTEGER
);
"""

_INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(company_name COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_companies_exchange ON companies(exchange_code)",
    "CREATE INDEX IF NOT EXISTS idx_companies_region ON companies(region)",
]


def init_schema(conn: sqlite3.Connection, drop_existing: bool = True) -> None:
    """Create all tables (optionally dropping first, which is what a refresh does)."""
    if drop_existing:
        for table in ("financials_annual", "financials_quarterly", "companies"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        # ingest_log is preserved across refreshes — it's the audit trail.
    conn.execute(_COMPANIES_DDL)
    conn.execute(_FINANCIALS_ANNUAL_DDL)
    conn.execute(_FINANCIALS_QUARTERLY_DDL)
    conn.execute(_INGEST_LOG_DDL)
    for ddl in _INDEX_DDL:
        conn.execute(ddl)


# ---------------------------------------------------------------------------
# Bulk inserts — use executemany for speed. All columns explicit to catch
# schema drift at write time.
# ---------------------------------------------------------------------------

_COMPANIES_COLS = [
    "ticker", "company_name", "company_type", "exchange_code", "primary_exchange",
    "secondary_exchanges", "region", "filing_currency", "listing_currency",
    "fx_listing_to_reporting", "fx_rate_source", "effective_tax_rate",
    "stock_price_listing", "mv_equity_listing", "actual_rating_fc", "actual_rating_lc",
    "options_outstanding", "options_avg_strike", "period_date_annual",
    "period_date_quarterly", "lease_commitment_yr1", "lease_commitment_yr2",
    "lease_commitment_yr3", "lease_commitment_yr4", "lease_commitment_yr5",
    "lease_commitment_beyond", "geographic_segments_json", "data_as_of",
]

_ANNUAL_COLS = [
    "ticker", "fy_offset", "revenues", "ebit", "ebitda", "net_income",
    "interest_expense", "capex", "d_a", "earnings_before_tax", "total_tax_expense",
    "operating_lease_expense", "r_and_d_expense", "cash_and_marketable_securities",
    "cross_holdings", "bv_debt", "bv_equity", "shares_outstanding", "minority_interests",
]

_QUARTERLY_COLS = list(_ANNUAL_COLS)
_QUARTERLY_COLS[1] = "fq_offset"  # replace fy_offset


def _executemany_from_dicts(conn: sqlite3.Connection, table: str, columns: list[str],
                             rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    placeholders = ",".join("?" for _ in columns)
    cols_sql = ",".join(columns)
    sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})"
    tuples = [tuple(r.get(c) for c in columns) for r in rows]
    conn.executemany(sql, tuples)


def insert_companies(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    _executemany_from_dicts(conn, "companies", _COMPANIES_COLS, rows)


def insert_annual_financials(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    _executemany_from_dicts(conn, "financials_annual", _ANNUAL_COLS, rows)


def insert_quarterly_financials(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    _executemany_from_dicts(conn, "financials_quarterly", _QUARTERLY_COLS, rows)


def log_ingest(conn: sqlite3.Connection, *, timestamp_utc: str, n_companies: int,
               n_rejected: int, n_files: int, file_manifest: list,
               unmapped_columns: list, unmapped_exchanges: list,
               warnings: list, duration_ms: int) -> None:
    conn.execute("""
        INSERT INTO ingest_log (timestamp_utc, n_companies, n_rejected, n_files,
            file_manifest, unmapped_columns, unmapped_exchanges, warnings, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp_utc, n_companies, n_rejected, n_files,
        json.dumps(file_manifest), json.dumps(unmapped_columns),
        json.dumps(unmapped_exchanges), json.dumps(warnings), duration_ms,
    ))


# ---------------------------------------------------------------------------
# Public read APIs
# ---------------------------------------------------------------------------

def search_companies(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Case-insensitive substring on company_name OR exact-prefix on ticker.
    Results sorted: exact ticker match first, then ticker prefix, then name
    prefix, then name substring — alphabetical within each group."""
    if not query or not query.strip():
        return []
    q = query.strip()
    rows = conn.execute("""
        SELECT ticker, company_name, exchange_code, region, filing_currency,
               listing_currency, period_date_annual,
               CASE
                 WHEN ticker = ? COLLATE NOCASE THEN 0
                 WHEN ticker LIKE ? COLLATE NOCASE THEN 1
                 WHEN company_name LIKE ? COLLATE NOCASE THEN 2
                 ELSE 3
               END AS match_rank
        FROM companies
        WHERE ticker LIKE ? COLLATE NOCASE OR company_name LIKE ? COLLATE NOCASE
        ORDER BY match_rank, company_name COLLATE NOCASE
        LIMIT ?
    """, (q, f"{q}%", f"{q}%", f"%{q}%", f"%{q}%", limit)).fetchall()
    return [dict(r) for r in rows]


def fetch_company(conn: sqlite3.Connection, ticker: str) -> dict | None:
    """Return the full company snapshot — identifiers + snapshot fields +
    list of annual + list of quarterly financials. Returns None if not found."""
    co = conn.execute("SELECT * FROM companies WHERE ticker = ?", (ticker,)).fetchone()
    if co is None:
        return None
    co_dict = dict(co)
    # Inflate geographic_segments_json back into a list.
    gs = co_dict.pop("geographic_segments_json", None)
    try:
        co_dict["geographic_segments"] = json.loads(gs) if gs else []
    except (json.JSONDecodeError, TypeError):
        co_dict["geographic_segments"] = []

    annual = conn.execute(
        "SELECT * FROM financials_annual WHERE ticker = ? ORDER BY fy_offset",
        (ticker,),
    ).fetchall()
    quarterly = conn.execute(
        "SELECT * FROM financials_quarterly WHERE ticker = ? ORDER BY fq_offset",
        (ticker,),
    ).fetchall()

    return {
        "company": co_dict,
        "financials_annual": [dict(r) for r in annual],
        "financials_quarterly": [dict(r) for r in quarterly],
    }


def latest_ingest_summary(conn: sqlite3.Connection) -> dict | None:
    """Most recent ingest_log row, with JSON-decoded fields."""
    row = conn.execute(
        "SELECT * FROM ingest_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    for k in ("file_manifest", "unmapped_columns", "unmapped_exchanges", "warnings"):
        try:
            d[k] = json.loads(d.get(k) or "[]")
        except json.JSONDecodeError:
            d[k] = []
    return d


def company_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM companies").fetchone()
    return int(row["n"]) if row else 0
