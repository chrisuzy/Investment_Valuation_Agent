# System Overview — Investment Valuation Automation

## Purpose

A full-stack web application that automates Damodaran-style equity valuation. The user enters a ticker symbol, the system fetches all required data, runs a 6-module valuation pipeline, and presents results in an interactive spreadsheet-like UI where every assumption and intermediate value can be inspected and overridden.

## Core Design Principles

1. **Single-ticker input** — The only required user input is a company ticker. All financial, industry, and macro data are fetched automatically.
2. **Strict variable typing** — Every variable in the system is defined in a central Data Dictionary (Pydantic models). Modules communicate exclusively through these typed schemas. No ad-hoc variable names.
3. **Stateless computation modules** — Each valuation module is a pure function: typed inputs in, typed outputs out, no side effects. This makes them independently testable.
4. **Incremental recomputation** — When a user overrides a value, only downstream modules re-run.
5. **Two data sources** — Company financials from Capital IQ (via Excel plugin automation), industry/macro data from Damodaran's annual datasets.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  FRONTEND (React + AG Grid)               │
│  Ticker input → Tab-per-module spreadsheet → Summary      │
└─────────────────────────┬────────────────────────────────┘
                          │ REST API (JSON)
┌─────────────────────────┴────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  API Layer  │  │ Session Mgr  │  │  Data Sources  │  │
│  │  (Routes)   │  │ (State)      │  │  (CapIQ +      │  │
│  │             │  │              │  │   Damodaran)   │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         └────────────────┼──────────────────┘            │
│                          ▼                               │
│  ┌───────────────────────────────────────────────────┐   │
│  │         VALUATION ENGINE (Pure Python)             │   │
│  │  M0: Data Fetch → M1: Adjustments → M2: Risk →   │   │
│  │  M3: Cash Flow → M4: DCF / M5: Multiples /       │   │
│  │  M6: Options → Final Value Per Share              │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + TypeScript | SPA framework |
| Spreadsheet UI | AG Grid (Community) | Editable data grids per module |
| Charts | Recharts | Valuation bridge, sensitivity charts |
| HTTP client | Axios | API communication |
| Backend | FastAPI (Python 3.11+) | REST API, validation, session management |
| Data models | Pydantic v2 | Typed schemas for Data Dictionary |
| Computation | NumPy, SciPy | Math (PV, normal CDF for BSM) |
| Excel automation | pywin32 (win32com) | Capital IQ plugin automation |
| Excel parsing | openpyxl / pandas | Parse Damodaran and CapIQ Excel files |

## Module Dependency Graph

```
M0 (Data Fetch)
  │
  ▼
M1 (Financial Adjustments)
  │
  ▼
M2 (Risk / WACC)
  │
  ▼
M3 (Cash Flow & Growth)
  │
  ├──────────────┬──────────────┐
  ▼              ▼              ▼
M4 (DCF)    M5 (Multiples)  M6 (Options)
  │                             │
  └──────────────┬──────────────┘
                 ▼
         Final Valuation
```

M4, M5, and M6 can run in parallel after M3. M6 adjusts M4's equity value for option dilution to produce the final Value Per Share.

## Related Documents

- [01-data-dictionary.md](./01-data-dictionary.md) — All variable definitions and Pydantic schema design
- [02-data-sources.md](./02-data-sources.md) — Capital IQ automation and Damodaran dataset management
- [03-engine-modules.md](./03-engine-modules.md) — Detailed design for each valuation module (M0–M6)
- [04-api-design.md](./04-api-design.md) — FastAPI endpoints, session management, recomputation logic
- [05-frontend-design.md](./05-frontend-design.md) — React spreadsheet UI, tab layout, editing behavior
- [06-testing-strategy.md](./06-testing-strategy.md) — TDD approach with real Capital IQ data validation
