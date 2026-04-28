# Frontend Design — React Spreadsheet UI

## Overview

A single-page React application with a tab-per-module spreadsheet interface. The user enters a ticker, the system fetches data, and every input/output is displayed in editable grids. When the user changes a value, the backend recomputes and the UI updates.

## Tech Stack

| Library | Purpose |
|---------|---------|
| React 18+ (TypeScript) | SPA framework |
| AG Grid Community | Spreadsheet/data grid component |
| Recharts | Charts (valuation bridge, sensitivity) |
| Axios | HTTP client for API calls |
| React Router | Tab navigation (optional — could use local state) |
| TailwindCSS or CSS Modules | Styling |

---

## Page Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER                                                          │
│  [Logo] Investment Valuation System    [Ticker: AAPL ▼] [Fetch] │
├──────────────────────────────────────────────────────────────────┤
│  TAB BAR                                                         │
│  [Data Input] [Adjustments] [Risk/WACC] [CF/Growth]             │
│  [DCF] [Multiples] [Options] [Summary]                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TAB CONTENT (AG Grid spreadsheet)                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Variable Name        │ Value      │ Source    │ Status    │ │
│  │  ─────────────────────┼────────────┼──────────┼────────── │ │
│  │  Revenue              │ 394,328    │ CapIQ    │ Fetched   │ │
│  │  EBIT                 │ 118,658    │ CapIQ    │ Fetched   │ │
│  │  R&D Expense          │  29,915    │ CapIQ    │ Fetched   │ │
│  │  Adjusted EBIT        │ 134,521    │ Calc     │ ●         │ │
│  │  Beta_U               │   1.28     │ Damodaran│ Fetched   │ │
│  │  ...                  │ ...        │ ...      │ ...       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  STATUS BAR                                                      │
│  Last computed: 2s ago | Modules: M1 ● M2 ● M3 ● M4 ● M5 ● M6●│
└──────────────────────────────────────────────────────────────────┘
```

---

## Tab Details

### Tab 0: Data Input
Shows all raw fetched data (CapIQ + Damodaran), organized by category:
- Company financial data (multi-year grid: columns = fiscal years)
- R&D and lease adjustment inputs
- Macro inputs (ERP, Risk-Free Rate, Tax Rate)
- Industry data (Beta_U, D/E Ratio, Industry Name selector)

All cells are editable. Changes trigger override tracking.

### Tab 1: Adjustments (Module 1 Output)
Two sections:
1. **R&D Capitalization** — Shows the amortization schedule, unamortized R&D, and the adjustment flow: EBIT → +R&D Current → -Amortization → Adjusted EBIT
2. **Operating Lease Conversion** — Lease commitment schedule, PV calculation, debt adjustment

Outputs: `Adjusted_EBIT`, `Adjusted_Net_Income`, `Adjusted_BV_Equity`, `Adjusted_MV_Debt`

### Tab 2: Risk / WACC (Module 2 Output)
Single calculation grid:
- D/E Ratio → Beta_L → Cost of Equity
- Cost of Debt (pre/post tax)
- Weight Equity / Weight Debt → WACC

Key editable inputs: `Beta_U`, `Risk_Free_Rate`, `Equity_Risk_Premium`, `Tax_Rate_Marginal`

### Tab 3: Cash Flow & Growth (Module 3 Output)
Two sections:
1. **Reinvestment & Free Cash Flow** — Adjusted CapEx, Adjusted D&A, Reinvestment, FCFF, FCFE
2. **Return & Growth** — ROIC, ROE, Reinvestment Rates, Expected Growth (fundamental)

### Tab 4: DCF (Module 4 Output)
- **Projection table** — Year-by-year FCFF projections (high-growth period)
- **Terminal value** — Stable growth assumptions, RIR_stable, Terminal Value
- **Valuation bridge** — Operating Assets → +Cash → -Debt → Equity Value → Per Share

Key editable: `Stable_Growth_Rate`, `Projection_Years`, growth rate override

### Tab 5: Multiples (Module 5 Output)
Comparison table:
```
Multiple          │ Intrinsic │ Market │ Over/Under
──────────────────┼───────────┼────────┼──────────
PE (Forward)      │   22.5    │  28.3  │ Overvalued
PBV               │    8.2    │  12.1  │ Overvalued
EV/EBITDA         │   18.9    │  22.4  │ Overvalued
EV/Sales          │    6.8    │   7.9  │ Overvalued
```

### Tab 6: Options (Module 6 Output)
- BSM inputs: S, K, t, σ², r, y
- BSM intermediate: d1, d2, N(d1), N(d2)
- Call value per option, total options value
- Final adjustment: Equity Value → -Options → /Shares → **Final Value Per Share**

### Tab 7: Summary
Full valuation summary page:
- **Valuation bridge chart** (waterfall: Operating Assets → Cash → Debt → Options → Per Share)
- **Final answer**: Intrinsic Value Per Share vs. Current Market Price → % Upside/Downside
- **Key assumptions table** (all user-editable assumptions in one place)
- **Multiples comparison** (compact table)

---

## Cell Behavior & Color Coding

| Cell Type | Color | Editable? | Description |
|-----------|-------|-----------|-------------|
| Fetched data | White | Yes | Auto-fetched from CapIQ or Damodaran |
| Calculated value | Light blue | Read-only* | Computed by engine modules |
| User override | Yellow highlight | Yes | User has manually overridden this value |
| Assumption | Light green | Yes | User-adjustable assumptions (growth rate, projection years) |

*Calculated cells can be force-overridden by double-clicking and entering a value. They then become yellow (override).

## Edit → Recompute Flow

```
User edits cell (e.g., Beta_U = 1.35)
    │
    ▼
Frontend: PATCH /api/valuation/{session_id}
    body: { overrides: [{ variable: "beta_u", value: 1.35, module: 2 }] }
    │
    ▼
Backend: Applies override, recomputes M2 → M3 → M4 → M5 → M6
    Returns: updated module outputs + affected_modules: [2,3,4,5,6]
    │
    ▼
Frontend: Updates AG Grid data for tabs 2, 3, 4, 5, 6
    Tabs 2-6 show brief "Updated" flash indicator
```

---

## Component Structure

```
src/
├── App.tsx                    # Main layout, routing
├── components/
│   ├── Header.tsx             # Ticker input, Fetch button
│   ├── TabBar.tsx             # Module tab navigation
│   ├── ModuleGrid.tsx         # Reusable AG Grid wrapper for each tab
│   ├── ValuationBridge.tsx    # Waterfall chart component
│   ├── MultiplesComparison.tsx
│   ├── SummaryPage.tsx
│   └── DamodaranUpload.tsx    # Admin: upload Damodaran datasets
├── hooks/
│   ├── useValuationSession.ts # Session state management
│   └── useModuleData.ts       # Per-module data fetching and updates
├── api/
│   └── client.ts              # Axios instance + typed API functions
├── types/
│   └── valuation.ts           # TypeScript types mirroring Pydantic models
└── utils/
    └── formatting.ts          # Number formatting, percentage display
```
