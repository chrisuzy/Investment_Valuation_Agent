# US + CN + HK Dataset → Database Integration — Plan

**Date:** 2026-05-04
**Status:** Plan for user review — no code beyond the inspection script yet.
**Related:** `backend/tools/inspect_us_cn_hk_dataset.py` (produced the structural summary this plan is built on).

---

## 1. What's in the dataset

Four `.xls` files in `US_CN_HK_dataset/`, totaling ~40 MB:

| File | Sheet | Rows × Cols | Role |
|---|---|---|---|
| `ginzu_cc_1_1.xls` | Screening | 10008 × 150 | Screener 1, part 1 |
| `ginzu_cc_1_2.xls` | Screening | 2921 × 150 | Screener 1, part 2 |
| `ginzu_cc_2_1.xls` | Screening | 10008 × 143 | Screener 2, part 1 |
| `ginzu_cc_2_2.xls` | Screening | 2920 × 143 | Screener 2, part 2 |

- Two screeners; each split in half because CIQ capped the export at ~10k rows.
- Screener 1 = **12,929** companies × **150** columns.
- Screener 2 = **12,928** companies × **143** columns.
- Joined on `Exchange:Ticker` the two screeners cover ~13k distinct companies across NasdaqGS, NasdaqGM, NasdaqCM, NYSE, SEHK, SHSE, SZSE.
- Non-Screening sheets (`Aggregates`, `Screen Criteria`) are metadata — ignored for ingestion.

Rows 0–6 are spacer/title rows. **Row 7 = headers, row 8+ = data.** The ingester must skip the preamble.

## 2. Column mapping — CIQ screener → internal variable

Both screeners together fully cover our `CompanyValuationInput` schema with four known gaps. All CIQ headers use the pattern `"<Metric> [<Period>] (<Scale/Currency>)"`. Period tokens: `Latest Annual` = FY-0, `Latest Annual - N` = FY-N, `Latest Quarter - N` = FQ-N, `Latest` = current snapshot.

### Identifier columns (present in both screeners)
| CIQ Header | Internal | Notes |
|---|---|---|
| `Company Name` | `company_name` | |
| `Exchange:Ticker` | `ticker` | Primary key for joining screener 1 and 2 |
| `Company Type` | — | Always "Public Company"; unused |
| `Exchanges [Primary Listing]` | `primary_exchange` | Format: `Nasdaq Global Select (NasdaqGS)`. Extract parenthesized code for our exchange map. |
| `Exchanges [Secondary Listings]` (screener 1 only) | — (optional) | Comma-separated list; useful for ADRs |
| `Filing Currency [Latest Annual]` (screener 2) | `reporting_currency` | "US Dollar" / "Chinese Renminbi (Yuan)" / "Hong Kong Dollar" → normalize to ISO codes (USD/CNY/HKD) |

### Income-statement fields — 18 periods each (FY-9..FY-0 + FQ-7..FQ-0)
All columns are `(Reported Currency)`.

| CIQ Header | Internal | From screener |
|---|---|---|
| `Total Revenue` | `revenues` | 1 |
| `EBIT` | `ebit` | 1 |
| `EBITDA` | `ebitda` | 1 |
| `Net Income` | `net_income` | 1 |
| `Interest Expense` | `interest_expense` | 1 |
| `Capital Expenditure` | `capex` | 2 |
| `Depreciation & Amort., Total` | `d_a` | 2 |
| `EBT Excl Unusual Items` | `earnings_before_tax` | 2 |
| `Income Tax Expense` | `total_tax_expense` | 2 |
| `Operating Lease Payments` | `operating_lease_expense` | 2 |
| `R&D Exp.` | `r_and_d_expense` | 2 |

### Balance-sheet fields — 11 periods each (FY-9..FY-0 + FQ-0)
| CIQ Header | Internal | From screener |
|---|---|---|
| `Total Cash & ST Investments` | `cash_and_marketable_securities` | 1 |
| `Long-term Investments` | `cross_holdings` | 1 |
| `Total Debt` | `bv_debt` | 1 |
| `Total Equity` | `bv_equity` | 1 |
| `Total Shares Out. on Filing Date (mm)` | `shares_outstanding` | 1 |
| `Minority Interest` | `minority_interests` | 2 |

### Current-snapshot fields (`Latest Annual` or `Latest` only)
| CIQ Header | Internal | From screener |
|---|---|---|
| `Effective Tax Rate [Latest Annual] (%)` | `effective_tax_rate_ciq` | 2 — divide by 100 (14.9 → 0.149) |
| `Day Close Price [Latest]` | `stock_price_reporting` | 2 |
| `Market Capitalization [My Setting] [Latest]` | `mv_equity_reporting` | 2 |
| `S&P Credit Rating — Foreign Currency LT` | `actual_rating_fc` | 2 — dash "-" means missing |
| `S&P Credit Rating — Local Currency LT` | `actual_rating_lc` | 2 |
| `Period Date, Income Statement [Latest Annual]` | `period_date_annual` | 2 — Excel serial, decode to ISO |
| `Period Date, Income Statement [Latest Quarter]` | `period_date_quarterly` | 2 |
| `Total Options Out. at End of Year (mm)` | `options_outstanding` | 2 |
| `Options W/Avg. Strike Price of Out.` | `options_avg_strike` | 2 |

### Operating-lease commitments (`Latest Annual` only)
| CIQ Header | Internal |
|---|---|
| `Operating Lease Commitment Due +1` | `lease_commitment_yr1` |
| `Operating Lease Commitment Due +2` | `lease_commitment_yr2` |
| `Operating Lease Commitment Due +3` | `lease_commitment_yr3` |
| `Operating Lease Commitment Due +4` | `lease_commitment_yr4` |
| `Operating Lease Commitment Due +5` | `lease_commitment_yr5` |
| `Operating Lease Commitment Due, Next 5 Yrs` | `lease_commitment_beyond` |

### Geographic segments
| CIQ Header | Internal |
|---|---|
| `Geographic Segments (Screen by Sum): Revenue` | (top-level total) |
| `Geographic Segments (Screen by Sum): % of Revenue` | |
| `Geographic Segments (Screen by Sum) (Details): Revenue` | (segment-level detail) |
| `Geographic Segments (Screen by Sum) (Details): % of Revenue` | |

Current template stores geographic segments as a structured list (`GeographicSegment[]`). The screener flattens them into single-number columns + a separate "Details" column that's likely a semicolon-delimited string. We'll parse on ingest.

### Gaps (in template, NOT in screener)
| Field | Template mnemonic | Impact |
|---|---|---|
| `r_and_d_expense_fn` | `IQ_RD_EXP_FN` | Footnote fallback only. Primary R&D is in the screener; we won't miss much. |
| `options_avg_maturity` | `IQ_OPTIONS_AVG_LIFE` | Default to 5-year assumption when DB path is used. |
| `stock_price` (listing currency) | `IQ_CLOSEPRICE` (no REPORTED) | Only reporting-ccy variant present. For cross-listed firms the listing-ccy price won't be in the DB path — fine for valuation math (uses reporting ccy) but the UI will only have one price to show. |
| `mv_equity` (listing currency) | `IQ_MARKETCAP` (no REPORTED) | Same as above. |

These are cosmetic gaps, not blockers. The DB path can fall back to "same as reporting currency" for listing-currency fields and default `options_avg_maturity = 5` — the valuation math is unaffected.

## 3. Architectural proposal

```
┌─────────────────────────────────────────────────────────────┐
│ US_CN_HK_dataset/                                            │
│   ginzu_cc_1_1.xls, cc_1_2.xls, cc_2_1.xls, cc_2_2.xls      │
└─────────────────────────────────────────────────────────────┘
                        │
                        │  (quarterly re-run by user, files replaced)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Ingestion                                                     │
│   CLI: python -m tools.ingest_us_cn_hk_dataset              │
│   Admin: POST /api/admin/refresh-database → invokes CLI      │
│                                                               │
│   - Stream each .xls via xlrd (row-by-row, never full load)  │
│   - Parse headers via CIQ_HEADER_PATTERNS map                │
│   - Join screener 1 + 2 by Exchange:Ticker                   │
│   - Normalize: currencies → ISO codes, ratings dash → None,   │
│                Excel dates → ISO, % → decimal                 │
│   - Write to SQLite (drop+recreate tables per refresh)        │
│   - Report: n_companies ingested, n_rejected, unmapped headers│
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ SQLite: backend/data_sources/us_cn_hk.sqlite                 │
│                                                               │
│   companies (                                                 │
│     ticker TEXT PRIMARY KEY,                                  │
│     company_name TEXT,                                        │
│     exchange TEXT,                                            │
│     filing_currency TEXT,                                     │
│     effective_tax_rate REAL,                                  │
│     actual_rating_fc TEXT, actual_rating_lc TEXT,             │
│     stock_price_reporting REAL, mv_equity_reporting REAL,     │
│     period_date_annual TEXT, period_date_quarterly TEXT,      │
│     lease_commitment_yr1..yr5 REAL, lease_commitment_beyond   │
│     options_outstanding REAL, options_avg_strike REAL,        │
│     geographic_segments_json TEXT,                            │
│     data_as_of TEXT,    -- when the .xls was ingested         │
│     -- updated timestamps for audit                            │
│   );                                                          │
│                                                               │
│   financials_annual (                                         │
│     ticker TEXT, fy_offset INTEGER,  -- 0..9                  │
│     revenues REAL, ebit REAL, ebitda REAL, net_income REAL,   │
│     interest_expense REAL, capex REAL, d_a REAL,              │
│     earnings_before_tax REAL, total_tax_expense REAL,         │
│     operating_lease_expense REAL, r_and_d_expense REAL,       │
│     cash_and_marketable_securities REAL, cross_holdings REAL, │
│     bv_debt REAL, bv_equity REAL, shares_outstanding REAL,    │
│     minority_interests REAL,                                  │
│     PRIMARY KEY (ticker, fy_offset)                           │
│   );                                                          │
│                                                               │
│   financials_quarterly (                                      │
│     ticker TEXT, fq_offset INTEGER,  -- 0..7                  │
│     revenues REAL, ebit REAL, ebitda REAL, net_income REAL,   │
│     interest_expense REAL, capex REAL, d_a REAL,              │
│     earnings_before_tax REAL, total_tax_expense REAL,         │
│     operating_lease_expense REAL, r_and_d_expense REAL,       │
│     cash_and_marketable_securities REAL,  -- FQ-0 only        │
│     bv_debt REAL, bv_equity REAL, shares_outstanding REAL,    │
│     minority_interests REAL,  -- FQ-0 only                    │
│     PRIMARY KEY (ticker, fq_offset)                           │
│   );                                                          │
│                                                               │
│   ingest_log (timestamp, n_companies, n_rejected, notes)      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend API (new endpoints)                                   │
│                                                               │
│   GET /api/database/search?q=X                                │
│      → [{ticker, company_name, exchange, match_quality}, …]  │
│      LIKE query on company_name, ticker, filtered to ≤ 20     │
│                                                               │
│   GET /api/database/company/<ticker>                          │
│      → returns assembled CompanyValuationInput-compatible     │
│        object (not yet run through the engine)                │
│                                                               │
│   POST /api/valuation/from-database { ticker }                │
│      → builds CompanyValuationInput, runs full pipeline       │
│        through run_full_valuation (same orchestrator as       │
│        template-upload path), creates session, returns same   │
│        ValuationResponse shape as /fetch-from-file            │
│                                                               │
│   POST /api/admin/refresh-database                            │
│      → invokes ingestion CLI, returns summary                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Frontend — OnboardingWizard extension                         │
│                                                               │
│ Step 1 (Find company) — existing, but now also checks DB     │
│   When a company is selected, backend returns                 │
│   { in_database: bool, data_as_of: date | null }              │
│                                                               │
│ Step 2 — branch based on in_database:                         │
│   - If in DB: prominent "Value from Database" button + "Data  │
│     as of YYYY-MM-DD" badge. Secondary: "Or download template │
│     and fill manually" for overriding with fresh CIQ data.    │
│   - If not in DB: existing template flow as primary.          │
│                                                               │
│ No changes to Steps 3/4 (they're only reached on template     │
│ path). DB path skips directly to the valuation result.        │
└─────────────────────────────────────────────────────────────┘
```

## 4. File-by-file work breakdown

### Backend
| File | Change | Approx lines |
|---|---|---|
| `backend/data_sources/us_cn_hk_mapping.py` | **NEW.** `CIQ_HEADER_PATTERNS` mapping table + period parser. | ~100 |
| `backend/tools/ingest_us_cn_hk_dataset.py` | **NEW.** Streaming .xls reader, dedupes ticker, writes SQLite. | ~250 |
| `backend/data_sources/us_cn_hk_db.py` | **NEW.** Query helpers: `search_companies()`, `fetch_company()`. | ~80 |
| `backend/api/routes.py` | Three new endpoints (search, company, from-database, admin-refresh). | ~120 |
| `backend/data_sources/us_cn_hk.sqlite` | **NEW.** SQLite file (gitignored — large, binary). | — |
| `backend/tests/test_us_cn_hk_ingest.py` | **NEW.** Test one screener slice end-to-end. | ~80 |

### Frontend
| File | Change | Approx lines |
|---|---|---|
| `frontend/src/api/client.ts` | Add `searchDatabase`, `valueFromDatabase` API calls. | ~30 |
| `frontend/src/components/OnboardingWizard.tsx` | Step 2 branch: "Value from Database" vs "Download template". Pulls `data_as_of` for the badge. | ~80 |
| `frontend/src/components/DatabaseSearch.tsx` | **NEW.** Autocomplete component for step 1 DB lookup. | ~100 |

**Total: ~840 lines backend + frontend.** Plus one new ~20 MB SQLite file (ingested from the .xls files on refresh).

## 5. Open questions — need your call before I code

<ol>

<li><b>Missing-data policy.</b> When a user searches a company and it's in the DB but some fields are blank ("-" from CIQ), what's the expected behavior?

<ul>
<li><b>a)</b> Proceed with valuation; surface missing fields in the existing UnresolvedFields panel (same UX as the template path). <b>Recommended.</b></li>
<li>b) Block DB path for that company, force template path.</li>
</ul>
</li>

<li><b>Damodaran industry classification.</b> The screener does NOT include a Damodaran industry name. Two options:

<ul>
<li>a) Keep our existing `indname.xlsx` lookup-by-ticker (unchanged). If ticker isn't in the lookup → surface as UnresolvedField as today. <b>Recommended — no new work.</b></li>
<li>b) Enrich the DB with Damodaran industry at ingest time (requires running each ticker through the mapper during ingestion).</li>
</ul>
</li>

<li><b>Listing-currency price/mv (IQ_CLOSEPRICE, IQ_MARKETCAP without REPORTED override).</b> Screener only has reporting-currency variants. For cross-listed firms (e.g. SEHK tickers), the listing-currency value is missing. Fix:

<ul>
<li>a) DB path shows only reporting-currency values. The `stock_price` / `mv_equity` fields stay None in the DB path. The P/V ratio uses `stock_price_reporting` (already the convention per CLAUDE.md). <b>Recommended.</b></li>
<li>b) Compute listing-ccy price by inverting fx_rate at ingest. Fragile — we'd need the same FX rate the user's CIQ instance used.</li>
</ul>
</li>

<li><b>Database file location.</b> Proposed `backend/data_sources/us_cn_hk.sqlite`. Alternative: keep it outside the repo at `~/.ad_cc_pilot_data/us_cn_hk.sqlite` so it never risks being committed. <b>Recommendation: inside backend/data_sources/ with an explicit `.gitignore` entry.</b>

</li>

<li><b>Refresh trigger.</b> I proposed three layers (CLI, admin endpoint, optional filesystem watcher). Which do you want?

<ul>
<li>a) CLI only — most conservative; you run it after each refresh.</li>
<li>b) CLI + admin endpoint — same as (a) plus a button/curl to trigger. <b>Recommended.</b></li>
<li>c) (a) + (b) + filesystem watcher — auto-ingest whenever the .xls files change.</li>
</ul>
</li>

<li><b>Ingest validation policy.</b> Screener 1 and 2 join on `Exchange:Ticker`. What if screener 2 has a ticker not in screener 1 (or vice versa)? Options:

<ul>
<li>a) Inner join — only keep tickers in both. Miss some data but guarantee completeness for retained rows. <b>Recommended.</b></li>
<li>b) Outer join — keep all tickers, fill missing side with nulls. Maximum coverage, more UnresolvedField churn downstream.</li>
</ul>
</li>

<li><b>Data-as-of date.</b> Where does it come from?

<ul>
<li>a) File modification time of the .xls (simplest, but can be wrong if files were copied).</li>
<li>b) `Period Date, Income Statement [Latest Annual]` from screener 2 per-company (accurate per ticker, but varies by fiscal year).</li>
<li>c) <b>Both.</b> Store the file-mtime as global `data_as_of` on the `ingest_log`; store the per-ticker `period_date_annual` on the `companies` table. <b>Recommended.</b></li>
</ul>
</li>

</ol>

## 6. What I won't build

- A new valuation engine. The DB path ends at `CompanyValuationInput` and feeds the existing `run_full_valuation` orchestrator. Zero changes to M1–M6.
- User authentication for the admin endpoint. Refresh-DB is assumed to be operator-only; bind it to localhost or protect with a simple token in a later iteration.
- Historical-revision tracking (e.g. "this company was in the DB a quarter ago with different numbers"). Each refresh overwrites.

## 6a. Revision — currency-semantics correction (verified against 5 tickers on 2026-05-04)

CIQ's "Reported Currency" screener modifier is **silently inert** for four columns:
- `Day Close Price [Latest] (Reported Currency)` — actually LISTING currency
- `Market Capitalization [Latest] (Reported Currency)` — actually LISTING currency
- `Options W/Avg. Strike Price of Out. [Latest Annual] (Reported Currency)` — actually LISTING currency
- `Total Options Out. at End of Year (mm)` — unit (no currency), but included for completeness

**Verified with:** Lenovo SEHK:992 (USD-filed, HKD-listed → price 11.63 = HKD), Tencent SEHK:700 (CNY/HKD), BABA NYSE (CNY/USD → $295B MCap = USD). Single-currency firms AAPL and Moutai can't distinguish and are consistent with either.

**Ingest mapping change:**
- `Day Close Price → stock_price` (listing) — NOT `stock_price_reporting`
- `Market Capitalization → mv_equity_listing` (listing) — NOT `mv_equity_reporting`
- `Options W/Avg. Strike Price → options_avg_strike_listing` (listing)

**Derived fields** (at read time, not stored):
- `stock_price_reporting = stock_price × fx_rate`
- `mv_equity_reporting = mv_equity_listing × fx_rate`

Where `fx_rate` is (listing ccy → reporting ccy multiplier). Sources, in priority order:
1. User override (editable Currency Info panel in UI)
2. Derived from CIQ template when both listing and reporting variants are fetched (template path only — not available from screener)
3. External FX feed (not in scope for first iteration)
4. `None` → surface as UnresolvedField, valuation math uses listing currency throughout until user fills it

**New UI: Currency Information panel.** Placed at the top of InputSheet (and echoed on Stories to Numbers header), shows three badges:
```
Filing: USD    Listing: HKD    FX: 0.128  [editable, shows fx_rate_source]
```
Editing the FX cell PATCHes `inputs.fx_rate` + sets `fx_rate_source = "manual"`. Orchestrator re-derives stock_price_reporting and mv_equity_reporting on next run.

**Why `stock_price` not `stock_price_reporting` is the right ingest target:** the listing-currency value is the authoritative source (what CIQ gave us, verified price against the exchange snap). The reporting-currency value is always derivable from listing × fx, so we store the primary and derive the alias. Avoids the two-sources-of-truth bug where CIQ's `stock_price_reporting` would disagree with `stock_price × fx_rate_user_override`.

## 6b. Multi-region extensibility (new requirement)

The ingester must be region-agnostic — drop a new regional screener file in `US_CN_HK_dataset/` (or a renamed `markets_dataset/` folder) and re-run; the pipeline should merge rows into the same `companies` / `financials_*` tables without code changes.

**Design:**
- Ingester takes a `--data-dir` pointing to any folder; scans `*.xls` in it.
- Each file must expose `Screening` sheet with row-7 headers; the `CIQ_HEADER_PATTERNS` map is shared across all files.
- Join on `Exchange:Ticker` — naturally unique across regions (exchange prefix differentiates).
- Region is inferred from the exchange prefix, stored in `companies.region`. Supported regions auto-expand as new prefixes appear. Unknown prefixes → flagged in the `ingest_log.unmapped_exchanges` row, user can patch the exchange map.
- Rename `US_CN_HK_dataset/` → `markets_dataset/` (or keep `US_CN_HK_dataset` as a legacy alias) once a second regional set exists.

**Implementation implication:** one SQLite, one schema, many regions. Zero code change per new region — just add the file.

## 6c. Knowledge-base auto-refresh (new requirement)

Annual Damodaran data refresh follows the same pattern:
- `knowledge_base/damodaran/` currently holds betas, capex, margin, WACC, country premium files split across 8 regional variants (Global, US, China, India, Europe, Emerg, Japan, Rest) — plus a `_catalog.json` index.
- `knowledge_base/industry_lookup/indname.xlsx` maps tickers to Damodaran industry.

**New admin endpoint:** `POST /api/admin/refresh-knowledge-base` — re-reads:
- All `knowledge_base/damodaran/*.xls*` files → refreshes the in-memory `DamodaranStore` singleton (`backend/data_sources/damodaran_store.py`)
- `knowledge_base/industry_lookup/indname.xlsx` → refreshes the `IndustryMapper` singleton
- Rebuilds `_catalog.json` if it exists

**Detection options:**
- a) Admin endpoint only (user triggers after drop) — **Recommended; lowest-effort**
- b) File watcher (inotify via `watchdog`) — auto-triggers on file change
- c) Startup-time cache invalidation — checks file mtimes on every lookup; too chatty

For a yearly refresh cadence, (a) is sufficient. File watcher is a nice-to-have later.

**Consolidated refresh endpoint:** `POST /api/admin/refresh-all` invokes both the markets-dataset refresh and the knowledge-base refresh in sequence. Operator convenience.

## 6d. Hard constraint — zero LLM / Claude Code involvement during refresh

Refresh must be **purely deterministic Python**. The operator's workflow is:

```
1. Download new CIQ screener files / new Damodaran release
2. Drop them into the designated folder
3. Run `python -m tools.refresh_all` OR hit the admin endpoint OR (optional) let the watcher fire
4. Done. No Claude, no LLM, no human review of the mapping.
```

**Design implications:**

- **Mapping logic lives in code or config — not prompt.** The `CIQ_HEADER_PATTERNS` table in `backend/data_sources/us_cn_hk_mapping.py` (plus a YAML override at `config/header_overrides.yaml` for future edits) handles header → internal-variable routing via regex match. If CIQ's labels drift slightly, the operator can edit the YAML without touching Python.

- **Fail-loud guarantees.** The ingester surfaces:
  - Unmapped column headers (listed in `ingest_log.unmapped_columns`)
  - Unknown exchange prefixes (listed in `ingest_log.unmapped_exchanges`)
  - Per-column null rates (warn when > 50%)
  - Row-level rejections (malformed tickers, duplicate primary keys)

  Output is a human-readable report (stdout + logged JSON); no LLM parsing required.

- **Schema changes need a code release, not a refresh.** If CIQ adds a new column type our schema doesn't know about, the operator will see it in `unmapped_columns` and can either:
  - Ignore it (safe default — column dropped from ingest)
  - Edit `config/header_overrides.yaml` to route it to an existing field
  - File a ticket for a code release to add a new schema field

  The ingester itself never "invents" a schema from what it sees.

- **Idempotence.** Re-running the ingester on the same files produces an identical database. No accumulated state. Safe to re-run after a crash.

- **Watchdog mode (optional, deferred).** A `watchdog`-based file-change listener can trigger the ingester automatically. Initially not implemented because:
  - Quarterly refresh cadence makes it low-value
  - Adds a background process that complicates deployment
  - The `tools.refresh_all` CLI + admin endpoint already cover the manual path cleanly

  If adopted later, it's a small addition: one `watchdog.Observer` spawned at backend startup, watching `US_CN_HK_dataset/` and `knowledge_base/` for `*.xls*` file-close events.

## 6d.1. Geographic Segments parser — verified

The `Geographic Segments (Screen by Sum) (Details): Revenue` column packs multiple segments into one cell as `Name: Revenue (Pct%)` entries separated by `;` + `\n`. Written as a deterministic regex parser in `backend/data_sources/us_cn_hk_mapping.py::parse_geographic_segments`. Self-test against 5 real cells (Lenovo 4 segments, AAPL 3, Tencent 2, Moutai 2, BABA 1) all pass; edge cases (empty, `-`, numeric) return empty list.

Example output for Lenovo:
```
[
  {'name': 'Asia Pacific (AP)',               'revenue': 12942.1, 'pct': 0.187},
  {'name': 'Americas (AG)',                   'revenue': 23297.4, 'pct': 0.337},
  {'name': 'Europe-Middle East-Africa (EMEA)','revenue': 16936.3, 'pct': 0.245},
  {'name': 'China',                           'revenue': 15901.2, 'pct': 0.230},
]
```

LLM writes the parser once; runtime is pure regex. Operator can run `python -m data_sources.us_cn_hk_mapping` to re-verify after any future CIQ format drift.

## 6d.2. Effective Tax Rate — divide by 100

CIQ screener's `Effective Tax Rate [Latest Annual] (%)` column returns percent as a number (e.g. `1.28`, `15.6`). Our schema stores decimal (`0.0128`, `0.156`). The ingester must call `normalize_effective_tax_rate()` which handles this (plus `-`/`None` → `None`).

Verified against template-path values: Lenovo screener 1.28 → 0.0128 matches Lenovo template's 0.0127 (1bp rounding difference due to fiscal-year vs LTM slicing).

## 6d.3. Compliance — raw screener files NEVER committed

Hard rule baked into `.gitignore`:
```
US_CN_HK_dataset/
markets_dataset/
ginzu_cc_*.xls
ginzu_cc_*.xlsx
backend/data_sources/*.sqlite
```

The raw exports are the user's data asset; the open-source repo must not carry them. The ingested SQLite is also local-build-only — regenerable from the source files at any time via the admin refresh endpoint.

**Open-source scrubbing (future requirement).** When the DB-backed valuation system is eventually open-sourced:
- Rename `parse_ciq_header` → `parse_vendor_header` and similar identifiers
- Strip "Capital IQ" / "CIQ" references from user-facing comments and docs
- Retain mnemonic strings like `IQ_TOTAL_REV` as opaque vendor field codes (they're public API identifiers, not CIQ trademarks)
- Rename the `capiq_formula_map.py` module to `vendor_formula_map.py`
- The `backend/data_sources/us_cn_hk_mapping.py` module already uses neutral names externally (e.g. `parse_ciq_header` is the only internal ref); rename at open-source time.

This scrubbing is out of scope for the current iteration but must precede any public release.

## 6e. Frontend refresh trigger (new requirement)

An operator-facing **Admin / Data Sources** page. Linked from the sidebar under a "⚙ Admin" item (only shown when env var `AD_CC_ADMIN=1` is set, so it's hidden in normal sessions).

**What it shows:**

```
┌─ Markets Dataset ──────────────────────────────────────┐
│ Folder: /home/chriszhang/.../US_CN_HK_dataset/         │
│   ginzu_cc_1_1.xls    15.7 MB   modified 2026-05-04 22:22 │
│   ginzu_cc_1_2.xls    4.7 MB    modified 2026-05-04 22:22 │
│   ginzu_cc_2_1.xls    16.0 MB   modified 2026-05-04 22:22 │
│   ginzu_cc_2_2.xls    4.8 MB    modified 2026-05-04 22:22 │
│ Database last ingested: 2026-05-04 23:40                 │
│ Companies in database: 12,929                            │
│ [↻ Refresh Database]                                     │
└────────────────────────────────────────────────────────┘

┌─ Knowledge Base ───────────────────────────────────────┐
│ Folder: /home/chriszhang/.../knowledge_base/damodaran/ │
│   24 files, oldest modified 2025-07-01                  │
│ Industry lookup: /home/chriszhang/.../industry_lookup/  │
│   indname.xlsx  modified 2026-03-15                     │
│ Last refresh: 2026-05-04 23:40                          │
│ [↻ Refresh Knowledge Base]                              │
└────────────────────────────────────────────────────────┘

[↻ Refresh Everything]   (runs both in sequence)
```

**Workflow the operator follows:**
1. Replace the .xls files in the folder (via their OS file manager, scp, etc.)
2. Open the Admin page in the browser
3. Inspect the file list (timestamps confirm the drop worked)
4. Click "Refresh"
5. Button shows spinner; backend returns summary (n_companies, n_rejected, unmapped warnings)
6. Page re-renders with new timestamps

**Implementation pieces:**
- `GET /api/admin/dataset-status` — returns the two folders' manifests (files + mtimes + sizes) + last-ingest timestamps from `ingest_log`
- `POST /api/admin/refresh-database` — triggers the markets-dataset ingest; returns JSON summary
- `POST /api/admin/refresh-knowledge-base` — triggers the KB rebuild; returns summary
- `POST /api/admin/refresh-all` — both in sequence
- `frontend/src/pages/Admin.tsx` — the page shown above

**No LLM in this loop.** The backend script is deterministic Python; the UI button just invokes it. Operator never needs to open Claude Code, provide prompts, or interpret output beyond the summary counts.

**Path to fully-automated (later):** the watcher option from §6d becomes the "auto" version of this same button. Drop files → watcher detects → runs the same ingest code → UI shows updated timestamps automatically. The UI is unchanged; the button just becomes optional.

## 6f. UI-driven file uploads (new requirement)

Operator never needs SSH or CLI access. The admin page in §6e gets drop zones alongside the manifest lists:

**New endpoints** (beyond the refresh endpoints in §6e):
- `POST /api/admin/upload/markets-dataset` — multipart upload, accepts `.xls`/`.xlsx`, saves to `US_CN_HK_dataset/`, returns filename + size + saved path.
- `POST /api/admin/upload/damodaran` — multipart upload, filename determines which file it replaces (e.g. `betaGlobal.xls` → `knowledge_base/damodaran/betaGlobal.xls`). Unknown filenames rejected with a clear error.
- `POST /api/admin/upload/industry-lookup` — replaces `knowledge_base/industry_lookup/indname.xlsx`.

**Workflow:** Drag .xls onto the drop zone → frontend POSTs multipart → backend saves + auto-triggers ingest for that section only → response carries the refresh-summary JSON → UI renders the summary inline.

**Safety:** each upload replaces the target file atomically (write to `.tmp`, rename). If the subsequent ingest fails, the previous database snapshot is retained (see §6g); the operator sees the error in the summary and can re-upload or add an override.

## 6g. Error tolerance — four layers (new requirement)

Damodaran reformats their tables most years; CIQ occasionally renames a column or adds one. The ingester must survive both and produce a report the operator can act on — **never crash, never produce an empty database from a partial failure.**

### Layer 1 — Permissive header matching (already in the parser module)

`CIQ_HEADER_PATTERNS` uses prefix regex, so `"Total Revenue "` matches all of:
- `Total Revenue [LTM] (Reported Currency)`
- `Total Revenue [Latest Annual - 3] (Reported Currency)`
- `Total Revenue [Latest Annual - 3]` (if CIQ drops the currency suffix)

Patterns use `?` for optional trailing characters where CIQ's pluralization or spacing tends to drift (e.g. `^Total Revenues?`). Widened as specific drifts are observed.

### Layer 2 — Operator-editable YAML overrides

File: `config/header_overrides.yaml`. Zero-code, zero-LLM.

```yaml
overrides:
  - header_prefix: "Revenues, Net"
    variable: revenues
    currency: reporting
  - header_prefix: "EBITDA, Normalized"
    variable: ebitda
    currency: reporting
```

Ingester checks the YAML file AFTER the hardcoded patterns — the operator can override or extend without touching Python. Edit the YAML, re-run refresh, done.

### Layer 3 — Unknown columns skipped, NEVER crash

- Unknown CIQ column headers → logged in `ingest_log.unmapped_columns`; column dropped from ingest; neighbouring data ingested normally.
- Unknown exchange prefixes → logged in `ingest_log.unmapped_exchanges`; the company still lands in `companies` table with `listing_currency = None`; operator can patch `exchange_currency_map.py` later.
- Unexpected cell values (malformed numbers, unexpected strings in numeric columns) → logged per-row; cell value becomes `None`.
- Empty mandatory fields (ticker missing, company name missing) → row rejected; counted in summary; other rows proceed.

### Layer 4 — Damodaran: dynamic header-row detection

Existing Damodaran loader uses fixed row offsets (row 8 = header). If Damodaran adds a cover page, this breaks. Replace with:

```python
def find_header_row(sheet, required_tokens=('Industry Name', 'Number of firms')):
    """Scan first 30 rows for the one containing all required tokens."""
    for r in range(min(sheet.nrows, 30)):
        cells = [str(sheet.cell_value(r, c)).lower() for c in range(sheet.ncols)]
        if all(any(tok.lower() in cell for cell in cells) for tok in required_tokens):
            return r
    return None  # surface as warning; retain previous snapshot
```

Tokens differ per file (countrystats.xls looks for `'Country'`; capex.xls for `'Industry Name'` + `'Sales/Capital'`). If the header row isn't found, the loader logs the failure, **retains the previously-cached parsed data**, and surfaces the error in the UI — operator sees exactly which file needs attention. The rest of the refresh proceeds.

### What the operator sees after every refresh

A human-readable report in the UI:

```
Markets Dataset Refresh  · 2026-05-04 23:40:12
  ✓ 12,929 companies ingested
  ✓ 0 rows rejected
  ⚠ 2 unknown column headers (skipped; see below)
  ⚠ 1 unknown exchange prefix (SGX — 4 tickers have listing_currency=None)
  Unknown headers:
    • 'Dividend Yield [Latest Annual] (%)' — not in mapping; add entry to
      config/header_overrides.yaml if wanted
    • 'Free Cash Flow [Latest Annual]' — same

Damodaran Refresh  · 2026-05-04 23:40:14
  ✓ 24 of 26 files reloaded
  ✗ betaGlobal.xls: header row not found (searched rows 0–29 for
      'Industry Name' + 'Number of firms')
      → Check Damodaran's latest layout; may need to edit
        config/damodaran_overrides.yaml or open a ticket
      → Previous snapshot from 2025-07-01 is still active

Industry Lookup Refresh
  ✓ 847 tickers loaded (+12 new since last upload)
```

**Graceful degradation:** a failure in any single file doesn't corrupt the system. Previous successful data stays loaded; next refresh can retry.

## 6h. Access control — admin-only upload; public open-source, private data

**Requirement:** the Data Sources page (§6e, §6f) must be restricted to the instance administrator. When others clone the open-source repo and deploy, the page is empty until THEY upload their own data — they become the admin for their instance. The raw CIQ .xls files are confidential; the admin's uploads must not be visible or downloadable by non-admin users of the same instance.

**Mechanism (simple, no full auth system):**

- Server-side config: `AD_CC_ADMIN_TOKEN` environment variable. Any non-empty string the admin chooses. No value set → admin features disabled entirely (all admin endpoints return 404; sidebar item hidden).
- Client-side: admin navigates to `/admin`, enters the token once; stored in `localStorage`. Subsequent requests to admin endpoints send the token in header `X-Admin-Token`.
- Backend middleware: `@require_admin` decorator on admin endpoints checks `X-Admin-Token == os.environ['AD_CC_ADMIN_TOKEN']`. Mismatch/missing → 401.
- Frontend sidebar: the `⚙ Data Sources` item renders only if `localStorage.ad_cc_admin_token` is set AND a lightweight `/api/admin/whoami` returns OK. Unauthenticated users never see the link.

**What's protected vs public:**

| Endpoint | Access | Rationale |
|---|---|---|
| `GET /api/database/search?q=` | Public | Search is the primary user-facing feature; no proprietary data leaks (ticker + company name are public facts). |
| `GET /api/database/company/<ticker>` | Public | Returns derived financial data assembled from the (derived) DB. Consistent with "the DB is open-sourceable" rule. |
| `POST /api/valuation/from-database` | Public | User-facing valuation. |
| `GET /api/admin/dataset-status` | **Admin only** | Lists raw filenames + sizes + mtimes — reveals what files exist on the server. |
| `POST /api/admin/upload/*` | **Admin only** | Write access to the data layer. |
| `POST /api/admin/refresh-*` | **Admin only** | Rebuilds the DB from raw files. |
| `GET /api/admin/download/*` | **Admin only — but we won't build this** | No reason to ever serve the raw .xls files back to the browser. Omit entirely so the confidentiality guarantee is structural, not policy. |

**Confidentiality guarantee:** raw CIQ .xls files never leave the server. No endpoint streams them back. Even the admin UI shows filenames + sizes + mtimes — never contents. To download, the admin goes in via SSH (out of scope for the app).

**Open-source ship-ability:**

- Code ships with no admin token set → admin features are dormant
- Code ships with no raw CIQ files (gitignored, §6d.3)
- Code ships with an empty SQLite DB (gitignored; built on first admin upload)
- Anyone cloning the repo gets a working app with:
  - Template-upload path (works immediately with their own CIQ plugin)
  - DB search path returns empty results until admin uploads
  - Data Sources page accessible by setting their own `AD_CC_ADMIN_TOKEN`

**Future multi-user extension (out of scope for this iteration):**

The user mentioned allowing multiple people to upload without letting them see existing files. This requires full auth (sessions, per-user folders, role-based views). Implementable as a follow-up: per-user upload folder `user_data/<user_id>/`, existing SQLite shared read-only across users, admin's files remain admin-only. Not building this now — the single-admin model above satisfies the current confidentiality requirement.

## 7. Success criteria

1. Running `python -m tools.ingest_us_cn_hk_dataset` populates the SQLite file with ~13,000 companies in under 60 seconds.
2. A search for "Tencent" in the frontend returns results from the DB; clicking the result takes the user straight to the valuation page without touching Excel.
3. Replacing the four .xls files with a new snapshot and running the CLI (or hitting the admin endpoint) fully refreshes the database.
4. The template-upload path continues to work unchanged — it's the fallback for firms outside the three regions and for overriding stale DB data.
5. For a ticker present in both paths (e.g., Lenovo SEHK:992), DB-path valuation and template-upload valuation produce the **same `value_per_share`** within rounding tolerance (0.1%).

---

## Appendix — inspection output reference

- `backend/tools/inspect_us_cn_hk_dataset.py` — the tool I wrote and ran.
- `/tmp/us_cn_hk_inspection.json` (107 KB) — structured summary: per-file, per-sheet, row/col counts, top 25 rows.
- This plan uses only that summary; the bulk data stayed out of the LLM context.
