# AD_CC_pilot — Comprehensive Project Context

## Quick Links to Detailed Files
- [CIQ Data Issues & Ground Truth](ciq-data-issues.md) — All 22 mismatched fields, GT values, what CIQ returns, root causes
- [Formulas & Module Relationships](formulas-and-modules.md) — Every formula, module dependency, interconnections
- [Session History & Decisions](session-history.md) — Chronological record of all decisions and conversations
- [Frontend Pages & Components](frontend-details.md) — All 13 pages, components, cell types, color coding

## Project Overview
Full-stack app automating Damodaran-style equity valuation. User enters a ticker, system fetches data and runs a 6-module pipeline, presenting results in a spreadsheet-like UI.

## Architecture
- **Approach A: Monolith** — FastAPI backend + React frontend + pure Python engine
- **Backend:** FastAPI (Python 3.11+), Pydantic v2, NumPy, SciPy
- **Frontend:** React + TypeScript, Vite, Tailwind CSS, Recharts (charts), custom SpreadsheetGrid/Cell components
- **Data sources:** Capital IQ Excel plugin (pywin32 COM automation with manual fallback) + Damodaran annual Excel datasets
- **No database** — in-memory session state, JSON files for Damodaran data
- **Test company:** Almarai (SASE:2280), Saudi food company — all GT data is for this company

## Module Pipeline
M0 (Data Fetch) → M1 (Financial Adjustments) → M2 (Risk/WACC) → M3 (CF/Growth) → M4 (DCF) / M5 (Multiples) / M6 (Options) → Final Value Per Share

## Key File Map
See [frontend-details.md](frontend-details.md) for frontend specifics.

### Backend
- `backend/engine/data_dictionary.py` — 13 Pydantic schemas (central types). NEEDS: cross_holdings, minority_interests added to RawFinancials
- `backend/engine/module_[1-6]_*.py` — All implemented, 64 tests passing
- `backend/engine/orchestrator.py` — Pipeline runner M1→M6, incremental recomputation
- `backend/engine/module_0_data_fetch.py` — CapIQ + Damodaran → CompanyValuationInput
- `backend/data_sources/capiq_excel_automation.py` — COM driver. NEEDS: save_path param added
- `backend/data_sources/capiq_formula_map.py` — CIQ mnemonics. NEEDS: cross_holdings, minority_interests fields
- `backend/data_sources/capiq_adapter.py` — Adapter layer
- `backend/data_sources/damodaran_parsers/` — 6 parsers for Damodaran Excel files
- `backend/data_sources/damodaran_store.py` — Lookup service
- `backend/data_sources/industry_mapper.py` — Ticker → Damodaran industry
- `backend/api/main.py` — FastAPI app (CORS, router)
- `backend/api/routes.py` — POST/GET/PATCH /api/valuation endpoints
- `backend/api/session_store.py` — In-memory session dict

### Frontend
- `frontend/src/pages/` — 13 pages total (InputSheet, ValuationOutput, Diagnostics, SyntheticRating, CostOfCapital, FailureRate, RDConverter, TrailingTwelveMonth, StoriesToNumbers, ValuationPicture, AnswerKeys, LeaseConverter, OptionValue)
- `frontend/src/components/` — SpreadsheetCell, SpreadsheetGrid, ColorLegend, Sidebar, MetricCard, DataTable, SectionCard
- `frontend/src/api/client.ts` — Axios API calls
- `frontend/src/types/valuation.ts` — TS types mirroring Pydantic schemas. NEEDS: cross_holdings, minority_interests

### Knowledge Base
- `knowledge_base/damodaran/` — 18 Damodaran Excel files
- `knowledge_base/industry_lookup/indname.xlsx` — 48K companies for ticker→industry mapping
- `knowledge_base/groud_truth/ground_truth.xlsx` — Almarai GT (17 sheets from Damodaran's fcffsimpleginzu.xlsx)
- `knowledge_base/ciq_fetches/` — Directory created, awaiting SASE_2280_fetch.xlsx generation

### Docs
- `PRD.md` — Full PRD with formulas and test cases (Chinese)
- `docs/architecture/0[0-6]-*.md` — 7 architecture docs
- `docs/architecture/brainstorm-session-2026-03-13.md` — All initial design decisions

## Build Status (as of 2026-03-16)
- **DONE:** Data layer (CapIQ adapter + Damodaran parsers + industry mapper) — all tested
- **DONE:** Engine Modules 1-6 + orchestrator — 64 tests all passing
- **DONE:** FastAPI API (3 files: main, routes, session_store)
- **DONE:** React frontend (13 pages, 7 shared components, Tailwind CSS, Recharts charts)
- **DONE:** Backend+frontend integration working, server runs on localhost:8000
- **DONE:** GT comparison analysis — identified 22 mismatched CIQ fields (see ciq-data-issues.md)
- **IN PROGRESS:** CIQ fetch spreadsheet generation (generate_almarai_fetch.py)
- **PENDING:** Schema additions (cross_holdings, minority_interests)
- **PENDING:** COM driver save_path feature
- **PENDING:** Wire up corrected CIQ formulas after user review

## Current Active Plan
Generate `backend/tools/generate_almarai_fetch.py` that creates `knowledge_base/ciq_fetches/SASE_2280_fetch.xlsx`:
- Col A: Variable name
- Col B: CIQ formula (=CIQ("SASE:2280","MNEMONIC","PERIOD"))
- Col C: GT value (yellow background)
- Col D: Status (OK/WRONG/MISSING)
- Col E: Notes describing the issue
- Sections: Company Info, Financials, R&D, Leases, Balance Sheet, Market Data, Tax, Options
- User opens in Excel with CIQ plugin, fixes formulas, saves back for us to read

## User Preferences
- Language: Python (backend), TypeScript (frontend)
- Wants automated data fetching (no manual upload if possible)
- Capital IQ: Excel plugin only (no API access), automate via pywin32 COM
- Damodaran: Annual Excel downloads
- PRD is in Chinese, user communicates in English
- User is impatient with stalling — execute quickly, don't over-plan
