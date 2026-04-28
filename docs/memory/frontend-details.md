# Frontend Details

## Tech Stack
- Vite + React 18 + TypeScript
- Tailwind CSS for styling
- Recharts for charts
- Custom spreadsheet components (NOT AG Grid — we built our own)
- Axios for API calls

## Pages (13 total, in frontend/src/pages/)

### InputSheet.tsx
Main data entry page. Sections:
1. Company Info (name, ticker, country, industry)
2. Base Year Financials (LTM vs Last 10K columns)
3. Adjustments (R&D toggle, lease toggle)
4. Balance Sheet (cash, cross holdings, minority interests, shares, stock price)
5. Tax Rates (effective, marginal)
6. Value Drivers (revenue growth, margins, sales/capital)
7. Market Numbers (risk-free rate, ERP, WACC)
8. Employee Options (count, strike, maturity, std dev, dividend yield)
9. Default Assumptions (stable growth, failure prob, distress proceeds, etc.)

**Known issues:**
- Cross Holdings hardcoded to `num(0)` — needs `fin0?.cross_holdings`
- Minority Interests hardcoded to `num(0)` — needs `fin0?.minority_interests`

### ValuationOutput.tsx
DCF output with revenue/EBIT/FCFF projections, terminal value, PV summation, equity bridge.

### Diagnostics.tsx
Comparison of company metrics vs industry averages.

### SyntheticRating.tsx
Interest coverage → synthetic bond rating → default spread table.

### CostOfCapital.tsx
Levered beta, cost of equity, cost of debt, WACC calculation breakdown.

### FailureRate.tsx
Failure probability estimation based on company characteristics.

### RDConverter.tsx
R&D capitalization worksheet — past expenses, amortization, research asset value.

### LeaseConverter.tsx
Operating lease conversion — commitment schedule, PV calculation, debt equivalent.

### TrailingTwelveMonth.tsx
TTM calculation from quarterly data.

### StoriesToNumbers.tsx
Maps qualitative narrative to quantitative assumptions.

### ValuationPicture.tsx
Visual bridge from operating assets → equity value → per-share value (Recharts bar chart).

### AnswerKeys.tsx
Reference values and sanity checks.

### OptionValue.tsx
Black-Scholes option pricing for employee stock options.

## Components (7 shared, in frontend/src/components/)

### SpreadsheetCell.tsx
Core cell component. Props:
- `value: string` — display value
- `type: 'label' | 'financial' | 'hypothesis' | 'calc' | 'reference' | 'hint' | 'header'`
- `editable?: boolean` — whether user can edit
- `width?: string` — column width

Color coding:
- label: white background, bold text
- financial: light blue (#EBF5FB) — data from CIQ/Damodaran
- hypothesis: light green (#E8F8F5) — user-editable assumptions
- calc: light gray (#F2F3F4) — computed values
- reference: light orange (#FEF5E7) — industry reference data
- hint: light yellow (#FEF9E7) — helper text
- header: dark gray (#2C3E50), white text

### SpreadsheetGrid.tsx
Table wrapper with title bar. Renders `<table>` with children (thead/tbody).

### ColorLegend.tsx
Shows color key for cell types at top of page.

### Sidebar.tsx
Navigation sidebar with links to all 13 pages. Ticker input at top.

### MetricCard.tsx, DataTable.tsx, SectionCard.tsx
Earlier components from initial scaffold, may still be used in some pages.

## Types (frontend/src/types/valuation.ts)
Mirrors all 13 Pydantic schemas from data_dictionary.py:
- MacroInputs, RawFinancials, AdjustmentInputs, AdjustedFinancials
- IndustryData, CostOfCapital, CashFlowMetrics, ValuationAssumptions
- DCFResult, MultiplesResult, OptionInputs, FinalValuation
- CompanyValuationInput, ValuationResponse

**NEEDS:** cross_holdings and minority_interests added to RawFinancials interface

## API Client (frontend/src/api/client.ts)
- `createValuation(ticker)` → POST /api/valuation
- `getValuation(id)` → GET /api/valuation/{id}
- `updateValuation(id, patch)` → PATCH /api/valuation/{id}
