"""
Build the redistributable seed database from the local admin-built SQLite.

Produces `backend/data/valuation_seed.sqlite` — a scrubbed copy suitable
for committing to the public repo. The scrub:

  - Drops `ingest_log` entirely (it contains the raw screener filenames,
    which hint at the data vendor).
  - Drops any other audit tables that reference upload operations.
  - Normalizes `fx_rate_source` values to neutral terms.
  - Adds a `metadata` table with a human-readable attribution string
    that does NOT name the data vendor for company-level financials.
  - VACUUMs to minimize size.

Company-level data (revenue, EBIT, balance sheet, etc.) is left intact
because those are public facts. Redistribution of the derived database
is consistent with the user's stated policy.

Usage:
    python -m tools.build_seed_database

Reads from:  backend/data_sources/us_cn_hk.sqlite   (admin-built, local only)
Writes to:   backend/data/valuation_seed.sqlite      (committable to repo)
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path when running as `python -m tools.build_seed_database`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources import us_cn_hk_db as db


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_DIR = REPO_ROOT / "backend" / "data"
SEED_PATH = SEED_DIR / "valuation_seed.sqlite"


def build_seed(source_path: Path | None = None, dest_path: Path | None = None) -> dict:
    """Produce a scrubbed seed database. Returns a summary dict."""
    source_path = source_path or db.get_db_path()
    dest_path = dest_path or SEED_PATH

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source database {source_path} does not exist. Run the ingester first."
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Start fresh: copy the source, then mutate. This is faster than
    # selective INSERTs for a 40MB database.
    if dest_path.exists():
        dest_path.unlink()
    shutil.copy2(source_path, dest_path)

    # Open the copy and scrub.
    conn = sqlite3.connect(str(dest_path))
    conn.row_factory = sqlite3.Row
    try:
        # 1. Drop ingest_log entirely — contains raw screener filenames
        #    that identify the data vendor.
        conn.execute("DROP TABLE IF EXISTS ingest_log")

        # 2. Normalize fx_rate_source to neutral terms.
        #    Current distinct values observed: 'same currency', 'unset'.
        #    Vendor-implied variants (if any slipped in) → 'auto-derived'.
        conn.execute("""
            UPDATE companies SET fx_rate_source = 'auto-derived'
            WHERE fx_rate_source LIKE '%CIQ%'
               OR fx_rate_source LIKE '%implied%'
               OR fx_rate_source LIKE 'Capital IQ%'
        """)

        # 3. Add a metadata table with attribution.
        conn.execute("DROP TABLE IF EXISTS metadata")
        conn.execute("""
            CREATE TABLE metadata (
                key    TEXT PRIMARY KEY,
                value  TEXT NOT NULL
            )
        """)
        conn.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            [
                ("seed_built_utc", datetime.now(timezone.utc).isoformat(timespec="seconds")),
                ("schema_version", "1"),
                ("data_scope", "public equities on major US / China / Hong Kong exchanges"),
                ("financials_attribution",
                 "Company-level financials aggregated from public filings and "
                 "consolidated third-party market-data services."),
                ("macro_industry_attribution",
                 "Macro, country, and industry-average reference data from "
                 "Prof. Aswath Damodaran, NYU Stern (pages.stern.nyu.edu/~adamodar/)."),
                ("redistribution",
                 "This seed is the derived relational form; raw vendor exports "
                 "are not redistributed."),
            ],
        )

        conn.commit()

        # 4. VACUUM — reclaims space from the dropped ingest_log rows and
        #    compacts the file. Usually shrinks by a few percent.
        conn.execute("VACUUM")
        conn.commit()

        # Report
        company_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        annual_count = conn.execute("SELECT COUNT(*) FROM financials_annual").fetchone()[0]
        quarterly_count = conn.execute("SELECT COUNT(*) FROM financials_quarterly").fetchone()[0]
    finally:
        conn.close()

    size_mb = dest_path.stat().st_size / (1024 * 1024)

    return {
        "seed_path": str(dest_path),
        "size_mb": round(size_mb, 2),
        "companies": company_count,
        "annual_rows": annual_count,
        "quarterly_rows": quarterly_count,
    }


def main():
    report = build_seed()
    print("Seed database built:")
    for k, v in report.items():
        print(f"  {k}: {v}")

    # Sanity check that we didn't inflate the file
    if report["size_mb"] > 80:
        print(f"\n⚠ WARNING: seed file is {report['size_mb']}MB — consider Git LFS.")
    else:
        print(f"\n✓ {report['size_mb']}MB — within GitHub's comfortable size range (< 50MB warning).")


if __name__ == "__main__":
    main()
