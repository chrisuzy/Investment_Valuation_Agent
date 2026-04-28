# Brainstorming Session — Investment Valuation Automation System
**Date:** 2026-03-13

---

## PRD Analysis

The PRD (`PRD.md`) defines a comprehensive **Investment Valuation Automation System** (投资估值自动化系统) with 6 modules covering the complete Damodaran-style valuation workflow:

1. **Module 1: Financial Adjustments** — R&D capitalization, operating lease debt conversion
2. **Module 2: Risk & Cost of Capital** — Beta, Cost of Equity, WACC calculation
3. **Module 3: Cash Flow & Growth** — FCFF, FCFE, ROIC, fundamental growth rates
4. **Module 4: Intrinsic Valuation (DCF)** — Terminal value, firm-to-equity bridge
5. **Module 5: Relative Valuation (Multiples)** — PE, PBV, EV/EBITDA, EV/Sales intrinsic multiples
6. **Module 6: Options Pricing & Per-Share Value** — Black-Scholes for employee stock options dilution

The PRD also defines a **Global Data Dictionary** with 60+ strictly-typed variable names and mandates TDD with real Capital IQ data (AAPL, MSFT, TSLA, KO, CSCO).

---

## Decision Log

### Q1: Programming Language
**Question:** What programming language and runtime do you want this system built in?
**Options:**
- Python (Recommended) — Best ecosystem for financial modeling
- TypeScript/Node.js — JS-based stack
- Python + Excel/Jupyter — Python core with Excel/Jupyter presentation

**Decision: Python (Recommended)**
> Best ecosystem for financial modeling — pandas, numpy, scipy (for BSM), strong Capital IQ SDK support.

---

### Q2: Usage Mode
**Question:** How will this system be used?
**Options:**
- CLI / Script
- Jupyter Notebook
- Web API Service
- All of the above

**Decision: Full-stack app with backend and frontend**
> User specified a full-stack web application with both backend and frontend.

---

### Q3: Frontend Style
**Question:** What should the frontend look like?
**Options:**
- Dashboard-style SPA — React/Next.js valuation dashboard with charts
- Form-based wizard — Step-by-step wizard flow
- Spreadsheet-like UI — Excel-like grid where analysts see and edit calculations

**Decision: Spreadsheet-like UI**
> Familiar Excel-like grid interface where analysts can see and edit all the intermediate calculations, like a smart spreadsheet.

---

### Q4: Data Source / Capital IQ Access
**Question:** What is your Capital IQ data access method?
**Options:**
- Capital IQ Excel Plugin / CSV export
- Capital IQ API (REST/SDK)
- Mock / Manual input first

**Decision: Capital IQ Excel Plugin / CSV export**
> Data is exported from Capital IQ via Excel plugin. No API access available.

---

### Q5: Backend Framework
**Question:** For the backend framework, which do you prefer?
**Options:**
- FastAPI (Recommended) — Modern async, auto-OpenAPI docs, Pydantic validation
- Django + DRF — Batteries-included, heavier
- Flask — Lightweight, more manual work

**Decision: FastAPI (Recommended)**
> Natural fit for a computation-heavy service with great type validation via Pydantic.

---

### Q6: Architecture Approach
**Question:** Which architecture approach do you prefer?

**Approach A: Monolith with Embedded Engine (Recommended)**
- Single FastAPI app with valuation engine as internal Python package
- React SPA frontend with AG Grid spreadsheet
- Pros: Simple deployment, engine testable independently, clean separation
- Cons: Engine and API must deploy together

**Approach B: Microservices — Separate Engine Service**
- Valuation engine as its own gRPC/REST service + API gateway
- Pros: Engine scales independently
- Cons: Overkill, deployment complexity, inter-service latency

**Approach C: Jupyter-Backed Computation**
- Frontend → FastAPI → Jupyter kernel for computation
- Pros: Analysts can open notebooks directly
- Cons: Stateful kernels, brittle in production

**Decision: Approach A — Monolith with Embedded Engine**
> Simple, testable, clean separation between calculation logic and HTTP layer.

---

### Q7: Data Sources Clarification
**User clarification (unprompted):**
> There are two types of data required as inputs for investment valuation:
> 1. **Company financial data** — fetched via Capital IQ Excel plug-in
> 2. **Industrial data and macro economic data** (ERP, industrial average, etc.) — from Professor Aswath Damodaran's website, released annually, downloadable in Excel format: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html

This led to the **two-source data architecture** design with separate parsers for each source.

---

### Q8: Two-Source Data Architecture Approval
**Question:** Does this two-source data architecture (Capital IQ + Damodaran) correctly capture your workflow?

**Decision: Yes, continue**

---

### Q9: Module 0 — Data Fetch Automation
**User feedback:**
> Where is the data fetch module? You need to fetch the data for me. The only input will be a company's name or ticker. You need to run through Capital IQ Excel plug-in to get financial data, and look up into Damodaran's spreadsheets (I can pull them down on an annual basis, as a dictionary sort of data, but you have to look up).

This led to adding **Module 0: Data Fetch** as the system entry point — user provides only a ticker, system handles everything.

---

### Q10: Capital IQ Automation Method
**Question:** Does the automated Excel COM approach (pywin32) for Capital IQ data fetching work for you?
**Options:**
- Yes, automate via Excel COM — pywin32 to drive Excel + CapIQ plugin
- Keep manual upload as primary
- Both: auto with manual fallback

**Decision: Both — auto with manual fallback**
> Try COM automation first (pywin32 drives Excel + CapIQ plugin automatically). Fall back to manual upload if it fails.

**Key requirement:** User does NOT have Capital IQ API access, only web access and the Excel plugin. System must automate through the Excel plugin via COM so the user doesn't have to manually open/upload files.

---

### Q11: Frontend Design Approval
**Question:** Does this spreadsheet-like frontend design match what you had in mind?

**Decision: Yes, looks great**
> Tab-per-module layout with AG Grid, color-coded cells, editable overrides with incremental recomputation.

---

### Q12: API & Session Management Approval
**Question:** Does this API design and session management approach work for you?

**Decision: Yes, finalize the design**

---

## Final Architecture Summary

| Aspect | Decision |
|--------|----------|
| **Language** | Python 3.11+ (backend), TypeScript (frontend) |
| **Architecture** | Monolith: FastAPI + React SPA + embedded pure-Python engine |
| **Backend** | FastAPI, Pydantic v2, NumPy, SciPy |
| **Frontend** | React 18+, AG Grid Community (spreadsheet), Recharts (charts) |
| **Data: Company** | Capital IQ Excel plugin via pywin32 COM automation (manual fallback) |
| **Data: Industry/Macro** | Damodaran annual Excel datasets (user downloads, system parses & indexes) |
| **Storage** | In-memory sessions (no database initially), JSON files for Damodaran data |
| **Testing** | TDD with pytest, real company data fixtures (AAPL, MSFT, TSLA, KO, CSCO) |

## Module Pipeline

```
M0 (Data Fetch: CapIQ + Damodaran)
  → M1 (Financial Adjustments: R&D + Leases)
    → M2 (Risk / WACC)
      → M3 (Cash Flow & Growth)
        → M4 (DCF)         ─┐
        → M5 (Multiples)    ├→ Final Value Per Share
        → M6 (Options/BSM) ─┘
```

## Testing Decision: Damodaran Ginzu Spreadsheet as Formula-Level Oracle

**File:** `knowledge_base/fcffsimpleginzu.xlsx` (Damodaran's FCFF Simple Ginzu valuation calculator)

**17 sheets**, pre-filled with Almarai (Saudi food company) data. Contains hundreds of interconnected formulas across sheets.

**Key decision:** Do NOT try to read/parse the entire workbook at once — context window will run out. Instead:
- When implementing each individual function, read **only the 5-15 relevant cells** from the corresponding Excel sheet
- Use those cell values as input/expected-output pairs for that function's unit test
- Each Excel sheet maps to a specific module (see `06-testing-strategy.md` for the mapping table)

**Sheet → Module mapping (quick reference):**
- `R& D converter` → M1 R&D capitalization
- `Operating lease converter` → M1 lease conversion
- `Cost of capital worksheet` → M2 WACC
- `Industry Averages(US/Global)` → M2 beta/ERP lookup
- `Country equity risk premiums` → M2 ERP/CRP
- `Valuation output` → M3 cash flow + M4 DCF
- `Option value` → M6 Black-Scholes

---

## Design Documents Produced

| File | Content |
|------|---------|
| `docs/architecture/00-system-overview.md` | High-level architecture, tech stack, dependency graph |
| `docs/architecture/01-data-dictionary.md` | All 60+ variable definitions with Pydantic types (schemas A–L) |
| `docs/architecture/02-data-sources.md` | Capital IQ COM automation + Damodaran dataset management |
| `docs/architecture/03-engine-modules.md` | Detailed M0–M6 design with all formulas and function signatures |
| `docs/architecture/04-api-design.md` | FastAPI endpoints, session management, error handling, CORS |
| `docs/architecture/05-frontend-design.md` | React + AG Grid tab layout, cell behavior, component structure |
| `docs/architecture/06-testing-strategy.md` | TDD with real company fixtures, constraint checks, coverage targets |
