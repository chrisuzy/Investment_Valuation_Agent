# AD_CC_pilot — Project Context for Claude Code

## What this system is

A full Damodaran Ginzu DCF valuation tool. The user uploads an Excel workbook populated by Capital IQ (CIQ) formulas, the backend reads it, runs the full M0→M6 pipeline, and the frontend displays every module as an audit-grade spreadsheet.

**Stack:** FastAPI + Pydantic v2 (backend) · React 18 + Vite + TypeScript + Tailwind (frontend) · openpyxl (Excel reading/writing)

---

## Pipeline architecture

```
M0  Data fetch      tools/read_ciq_template.py  → CompanyValuationInput
M1  Adjustments     engine/module_1_adjustments  → AdjustedFinancials   (R&D capitalisation, lease PV)
M2  Risk / WACC     engine/module_2_risk         → CostOfCapital        (β, ERP, Kd, WACC)
M3  Cashflow        engine/module_3_cashflow     → CashFlowMetrics      (FCFF, ROIC, reinvestment)
M4  DCF             engine/module_4_dcf          → DCFResult            (PV FCFF, terminal value, VPS)
M5  Multiples       engine/module_5_multiples    → MultiplesResult      (intrinsic PE/PBV/EV ratios)
M6  Options/Final   engine/module_6_options      → FinalValuation       (BSM option value, VPS net)
```

Orchestrator: `backend/engine/orchestrator.py::run_full_valuation()`.
Every PATCH (user edits a driver) re-runs ALL modules — partial re-run is not implemented. The orchestrator always overwrites all derived fields; never skip overwriting a field just because it's non-null.

API entry points: `backend/api/routes.py`  
Session store: `backend/api/session_store.py` (in-memory dict keyed by session UUID)

---

## CIQ template — critical architecture

### Template generator
`backend/tools/generate_ciq_template.py`  
Copies the user's authoritative template file and writes a `_RowMap` sheet listing `(row, variable_name, period, mnemonic)` for every CIQ-formula row. **Do not rebuild formulas from scratch** — always copy the user's template unchanged and append only the `_RowMap`.

### Template reader  
`backend/tools/read_ciq_template.py`  
Opens the workbook **twice**:
- `data_only=False` — to read the live formula strings in column C  
- `data_only=True` — to read cached numeric values

Routing is driven by parsing the actual CIQ formula, not by the `_RowMap` period field (which can be stale). The parser handles all four call forms:
```
=CIQ($B$1,"IQ_TOTAL_REV","IQ_FY-0")
=_xll.ciqfunctions.udf.CIQ($B$1,"IQ_EFFECT_TAX_RATE","IQ_FY")/100
=ABS(CIQ($B$1,"IQ_CAPEX","IQ_FY-0"))
=CIQ($B$1,"IQ_CLOSEPRICE")          ← no period arg → "current"
```

Period routing logic:
- `IQ_FY` (no offset) → `current` (effective_tax_rate_ciq and similar single-period fields)
- `IQ_FY-0`, `IQ_FY-1`, … → `annual[0]`, `annual[1]`, …
- `IQ_FQ-0`, `IQ_FQ-1`, … → `quarterly[0]`, `quarterly[1]`, …

### Do not trust the _RowMap period field for routing
The generator may write `period="current"` but the formula itself is the authority. Always parse `parse_ciq_formula()` to get the true period.

---

## Critical conventions — must always respect

### Base year (LTM)
All frontend pages and backend NOPAT/ROIC calculations use the **LTM (last twelve months)** rotated base year, not `raw_financials[0]`.

Frontend: always use `baseYear(data)` from `frontend/src/lib/baseYear.ts`:
```typescript
export function baseYear(data: ValuationResponse): RawFinancials | undefined {
  return data.ltm_financials ?? data.inputs.raw_financials[0];
}
```
Never reference `data.inputs.raw_financials[0]` directly in display code.

Backend: use `ltm_then_prior` (LTM prepended to the raw_financials list) when computing company_metrics.

### Tax rate — effective vs marginal
- **Effective tax** (`macro_inputs.tax_rate_effective`): use for base-year NOPAT, ROIC, and intrinsic multiples (M3, M5)
- **Marginal tax** (`macro_inputs.tax_rate_marginal`): use for DCF projection years (M4) and Kd after-tax (M2)
- `effective_tax_rate_ciq` is fetched from `IQ_EFFECT_TAX_RATE / IQ_FY` — single-period current fetch. The reader routes this to `macro_inputs.tax_rate_effective`. Do not use `tax_rate_marginal` as a substitute for base-year calculations.

### Currency — two stock price fields
```
fin.stock_price              # listing currency  — show to user, matches broker screens
fin.stock_price_reporting    # reporting currency — use for P/V ratio and DCF bridge
fin.mv_equity                # reporting currency — use for WACC math and EV computation
fin.mv_equity_listing        # listing currency   — display only
```
The P/V ratio requires `stock_price_reporting / value_per_share` (both in reporting ccy). Never divide `stock_price` (listing) by `value_per_share` (reporting) — this gives a wrong ratio for cross-listed companies.

`fx_rate` = listing-ccy → reporting-ccy multiplier. Defined at top of the raw_financials loop in routes.py; must be computed before entering the loop.

### WACC geographic mix
Industry β lookups default to US (Ginzu convention: `beta_approach = "single_business_us"`). The user's methodology selector in the frontend can override to Global, multi-business, or direct-input. Regional tables (China, India, Europe, etc.) are retained only for `ctryprem` ERP calculations, not for β lookups. `_country_to_region()` always returns "US" for this reason.

---

## Frontend page map

| Page | File | What it shows |
|------|------|---------------|
| Input Sheet | `pages/InputSheet.tsx` | All uploaded raw inputs + adjustment toggles |
| Cost of Capital | `pages/CostOfCapital.tsx` | WACC waterfall, β, ERP, Kd branches |
| Synthetic Rating | `pages/SyntheticRating.tsx` | Interest coverage → synthetic bond rating lookup |
| Stories to Numbers | `pages/StoriesToNumbers.tsx` | 8 DCF driver inputs (sensitivity panel hosts these) |
| Valuation Output | `pages/ValuationOutput.tsx` | Full DCF projection table + equity bridge |
| Valuation Picture | `pages/ValuationPicture.tsx` | Graphical summary, P/V gauge |
| Relative Valuation | `pages/RelativeValuation.tsx` | Intrinsic vs market multiples vs industry benchmarks |
| Summary Sheet | `pages/SummarySheet.tsx` | One-page executive summary |
| Answer Keys | `pages/AnswerKeys.tsx` | Damodaran-style answer key for each module |
| Diagnostics | `pages/Diagnostics.tsx` | Data quality flags, missing-field audit |
| Trailing Twelve Months | `pages/TrailingTwelveMonth.tsx` | LTM calculation detail |
| R&D Converter | `pages/RDConverter.tsx` | R&D capitalisation workings |
| Lease Converter | `pages/LeaseConverter.tsx` | Operating lease PV workings |
| Option Value | `pages/OptionValue.tsx` | BSM option dilution |
| Failure Rate | `pages/FailureRate.tsx` | Distress probability overlay |

Color convention (SpreadsheetCell types):
- `financial` = sky/blue — raw CIQ-fetched data
- `calc` = emerald/green — derived / formula output
- `label` = plain — row label
- `reference` = slate/gray — Damodaran benchmark / industry data
- `header` = dark header row

### Key shared components
- `components/SpreadsheetCell.tsx` + `SpreadsheetGrid.tsx` — the spreadsheet UI primitives
- `components/SensitivityPanel.tsx` — 8-driver sensitivity, tornado, archetype presets, **Reset-to-original**
- `components/ErrorBoundary.tsx` — wraps Routes; catches render errors; resets on navigation
- `lib/baseYear.ts` — LTM helper (use everywhere, not raw_financials[0])
- `lib/sources.ts` — tooltip helpers: `ciq()`, `formula()`, `backendField()`

---

## Sensitivity panel & archetype design

`components/SensitivityPanel.tsx`

- 8 driver inputs rendered as numeric text boxes with ▲/▼ arrows and Q1/median/Q3 chips
- Each driver maps to a `patch_path` in `ValuationAssumptions`
- **Archetype presets**: 6 cards (Disruptor / High Growth / Mature / Value / Distressed / Turnaround). Click-to-apply patches all 8 drivers.
- **Reset button**: on first mount per `sessionId`, a snapshot of the 8 driver values is taken. "↺ Reset to original inputs" reverts all 8 to snapshot. The snapshot watches only `sessionId`, NOT `data`, so archetype clicks or manual edits do not overwrite the snapshot.
- **Comparison table**: shown when an archetype is selected — Original / Current / Δ columns.

---

## Export workbook

`backend/api/export_workbook.py`

- Generates a downloadable `.xlsx` with all modules as separate sheets
- Labels that start with `=` are relabeled with `→` prefix (e.g., `"→ Operating Assets"`) to prevent Excel interpreting them as formulas (#NAME? errors)
- `_cell()` helper: any string value starting with `=` that isn't a real formula is prepended with `'` (apostrophe = Excel text-mode marker)

---

## Known limitations / open items

1. **SyntheticRating large-firm table**: The page shows the small-firm Damodaran coverage table. When `synthetic_rating_firm_type = "large"`, the engine uses a different band table. A disclaimer banner is shown but the table itself is not dynamically switched.

2. **OptionValue.tsx currency mismatch**: Mixes listing-ccy `stock_price` with reporting-ccy BSM seed. Not yet fixed.

3. **InputSheet.tsx sales-to-capital**: Line ~533 uses raw invested capital vs the backend's adjusted IC. Minor discrepancy in the display-only input sheet.

4. **GitHub Actions CI**: `.github/workflows/tests.yml` requires `workflow` scope PAT. Currently local-only.

5. **Orphan M3 outputs**: `fcfe`, `reinvestment_equity`, `roe`, `rir_equity` are computed but not displayed anywhere.

---

## What NOT to do

- **Never modify CIQ formulas in the user's template.** The generator must copy unchanged and only append `_RowMap`. The user verifies formula correctness in Excel independently.
- **Never route by `_RowMap.period` alone.** Always parse the formula string to get the true period.
- **Never reference `raw_financials[0]` in frontend display code.** Use `baseYear(data)`.
- **Never use `tax_rate_marginal` for base-year NOPAT or ROIC.** Use `tax_rate_effective`.
- **Never divide listing-ccy stock price by reporting-ccy VPS** for P/V ratio. Both must be in the same currency.
- **Never skip overwriting derived fields in the orchestrator after a PATCH.** Always rerun all modules.
- **Never write Excel cell labels starting with `=`** — use `→` prefix instead.

---

## Running the system

```bash
# Backend
cd backend && uvicorn api.main:app --reload --port 8000

# With admin features enabled (uploads, refresh, etc.)
AD_CC_ADMIN_TOKEN=<your-secret> uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

Frontend dev server: http://localhost:5173
API: http://localhost:8000/api

---

## Markets DB (US + CN + HK company dataset)

**What it is.** ~13k companies across NasdaqGS/NasdaqGM/NasdaqCM/NYSE/SEHK/SHSE/SZSE, ingested from CIQ Screener .xls exports into SQLite.

**Two SQLite paths coexist:**
- `backend/data/valuation_seed.sqlite` — scrubbed redistributable seed. **Committed to the repo** (shipped to every clone). Loaded automatically when no admin-built DB exists.
- `backend/data_sources/us_cn_hk.sqlite` — admin-built local DB, includes `ingest_log` with upload manifest. **Gitignored.** Wins over the seed when present.

Resolution order in `us_cn_hk_db.py::get_db_path()`: env var override → admin-built → committed seed.

**Seed build pipeline:**
- Admin uploads .xls files via the `⚙ Data Sources` page → `refresh-database` builds `us_cn_hk.sqlite`.
- Operator then runs `python -m tools.build_seed_database` to emit `valuation_seed.sqlite`. The scrub drops `ingest_log`, normalizes `fx_rate_source` to vendor-neutral terms, adds a `metadata` table with neutral attribution, and VACUUMs.
- `git commit` the updated seed to publish a new snapshot to the public repo.

**Two paths coexist:**
- DB path: `/api/database/search` → `/api/valuation/from-database`. Public endpoints. Instant.
- Template path: existing `/api/valuation/fetch-from-file`. Still works for tickers outside the ingested regions.

Both paths converge at `run_full_valuation` — identical valuation math.

**Admin-gated data management** (plan §6h):
- Env var `AD_CC_ADMIN_TOKEN` — no value set → all admin endpoints return 404
- Admin UI at `/admin` (sidebar item hidden unless `adminWhoami` returns `configured: true`)
- Upload .xls files via drag-drop, then click Rebuild Database
- Raw file download intentionally not implemented — confidentiality is structural

**Key files:**
- `backend/data_sources/us_cn_hk_db.py` — schema + query helpers
- `backend/data_sources/us_cn_hk_mapping.py` — deterministic CIQ header → internal variable mapping + parsers
- `backend/tools/ingest_us_cn_hk_dataset.py` — CLI ingester (4.4s for ~13k companies)
- `backend/api/admin.py` + `backend/api/database.py` — endpoints
- `frontend/src/pages/AdminDataSources.tsx` — upload UI
- `docs/superpowers/specs/2026-05-04-us-cn-hk-database-integration-plan.md` — full design spec

**Currency-semantics gotcha** (plan §6a): CIQ Screener's "Reported Currency" modifier is silently inert for four columns (Day Close Price, Market Cap, Options Avg Strike, Options Out). Those always come through in listing currency. The ingester routes them to listing-currency schema fields (`stock_price`, `mv_equity_listing`, `options_avg_strike`). The orchestrator derives reporting-ccy variants when the user sets fx_rate manually via the Currency Info panel on Input Sheet.

**.gitignore rules:** raw CIQ .xls files never committed (`US_CN_HK_dataset/`, `ginzu_cc_*.xls*`). SQLite artifact never committed. Confidentiality is structural.

GitHub repo: https://github.com/chrisuzy/Investment_Valuation_Agent
