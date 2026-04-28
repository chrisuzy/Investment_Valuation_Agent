# Session History & Decision Log

## Session 1 — 2026-03-13: Architecture & Design

### Decisions Made (Brainstorming)
1. **Language:** Python (backend) + TypeScript (frontend) — best ecosystem for financial modeling
2. **Usage mode:** Full-stack web app with backend and frontend
3. **Frontend style:** Spreadsheet-like UI (Excel-like grid, not dashboard, not wizard)
4. **Data source:** Capital IQ Excel plugin (no API access — user only has web access + Excel plugin)
5. **Backend framework:** FastAPI — async, auto-OpenAPI docs, Pydantic validation
6. **Architecture:** Approach A — Monolith (FastAPI + React + embedded Python engine)
7. **Data sources:** Two sources — Capital IQ (company financials via COM) + Damodaran (industry/macro from annual Excel downloads)
8. **Module 0 added:** User only provides ticker — system fetches everything automatically
9. **CapIQ automation:** pywin32 COM to drive Excel + CIQ plugin, with manual fallback
10. **Testing:** Damodaran's fcffsimpleginzu.xlsx as formula-level oracle (read only relevant cells per test, not entire workbook)

### Design Documents Produced
- `docs/architecture/00-system-overview.md` — High-level architecture
- `docs/architecture/01-data-dictionary.md` — All variable schemas
- `docs/architecture/02-data-sources.md` — CapIQ + Damodaran integration
- `docs/architecture/03-engine-modules.md` — M0-M6 with all formulas
- `docs/architecture/04-api-design.md` — FastAPI endpoints
- `docs/architecture/05-frontend-design.md` — React spreadsheet UI
- `docs/architecture/06-testing-strategy.md` — TDD approach
- `docs/architecture/brainstorm-session-2026-03-13.md` — Full decision log

## Session 2 — 2026-03-13 to 2026-03-14: Backend Implementation

### What Was Built
- `backend/engine/data_dictionary.py` — 13 Pydantic schemas
- `backend/engine/module_1_adjustments.py` through `module_6_options.py` — All engine modules
- `backend/engine/orchestrator.py` — Pipeline runner
- `backend/data_sources/capiq_excel_automation.py` — COM driver
- `backend/data_sources/capiq_formula_map.py` — CIQ mnemonics
- `backend/data_sources/capiq_adapter.py` — Adapter layer
- `backend/data_sources/damodaran_parsers/` — 6 parsers
- `backend/data_sources/damodaran_store.py` — Lookup service
- `backend/data_sources/industry_mapper.py` — Ticker → industry
- `backend/api/` — FastAPI app (main, routes, session_store)
- 64 tests all passing

## Session 3 — 2026-03-16: Frontend + Integration + CIQ Issues

### Frontend Built
- 13 pages matching GT spreadsheet tabs (InputSheet, ValuationOutput, Diagnostics, etc.)
- Custom SpreadsheetCell component with 6 cell types (label, financial, hypothesis, calc, reference, hint, header)
- Color-coded cells: blue=financial data, green=hypothesis/editable, gray=calculated, orange=reference, yellow=hint
- SpreadsheetGrid, ColorLegend, Sidebar components
- Vite + React + TypeScript + Tailwind CSS + Recharts

### Backend-Frontend Integration
- Server runs on localhost:8000
- Frontend built to frontend/dist/
- CORS configured
- POST/GET/PATCH /api/valuation endpoints working

### CIQ Data Comparison (Major Discovery)
Ran comprehensive comparison of CIQ-fetched data vs ground truth. Found 22 mismatched fields.
See [ciq-data-issues.md](ciq-data-issues.md) for full details.

**Critical issues:**
- BV Equity: CIQ returns total equity (incl. minority) vs GT wants stockholders' equity only
- BV Debt: CIQ returns only interest-bearing debt vs GT uses broader definition
- Cash: CIQ returns only cash equivalents vs GT includes investments/deposits
- Shares Outstanding: CIQ formula fails entirely
- Stock Price: Date/currency mismatch
- Effective Tax Rate: CIQ formula returns nothing

### User's Proposed Fix Workflow
User proposed: generate an Excel file with CIQ formulas + GT comparison. User opens in Excel with CIQ plugin, fixes wrong formulas, saves back. We read corrected file.

### Stalling Problem Identified
Claude kept stopping mid-task during this session:
1. Said "let me do it" then stopped without writing code
2. Repeated 3+ times
3. Root cause: response boundaries after tool results, over-planning before execution
4. User explicitly called this out and demanded diagnosis
5. Eventually identified that COM automation timeouts (90s commands with 30s poll timeouts) caused cascading stalls
6. Also identified excessive verbose analysis between actions burning context

### Plan Created (Not Yet Executed)
Plan for CIQ fetch spreadsheet with GT comparison:
1. `backend/tools/generate_almarai_fetch.py` → generates `knowledge_base/ciq_fetches/SASE_2280_fetch.xlsx`
2. Add cross_holdings + minority_interests to data_dictionary.py, valuation.ts, InputSheet.tsx
3. Update COM driver with save_path + new CIQ formulas

### Files Modified in Session 3
- frontend/src/components/SpreadsheetCell.tsx (created)
- frontend/src/components/SpreadsheetGrid.tsx (created)
- frontend/src/components/ColorLegend.tsx (created)
- frontend/src/pages/SyntheticRating.tsx (created)
- frontend/src/pages/FailureRate.tsx (created)
- frontend/src/pages/TrailingTwelveMonth.tsx (created)
- frontend/src/pages/StoriesToNumbers.tsx (created)
- frontend/src/pages/ValuationPicture.tsx (created)
- frontend/src/pages/AnswerKeys.tsx (created)
- frontend/src/components/Sidebar.tsx (modified)
- frontend/src/App.tsx (modified)

## Session 4 — 2026-03-16 (Current): Memory Save Before Upgrade

User wants to upgrade Claude Code from v2.1.76 to latest.
Requested comprehensive memory save before upgrade:
1. MEMORY.md — project context (this file is the index)
2. ciq-data-issues.md — all 22 mismatched fields with GT values
3. formulas-and-modules.md — every formula, CIQ mapping, module relationships
4. session-history.md — this file (chronological decisions)
5. frontend-details.md — all 13 pages and components
6. CLAUDE.md — lessons learned and interaction philosophy
