# Data-Fetch Template Schema

This document specifies the Excel workbook schema the backend expects
when you upload company-level financial data. Build your own template
using whatever data source you have access to (Capital IQ plug-in,
Bloomberg, FactSet, your firm's data warehouse) — as long as the final
xlsx matches this structure, the backend will parse it.

No prebuilt template is shipped with this repo. The reasons and
alternatives are described in the project's main [README](../README.md).

---

## Workbook layout

A compliant workbook has **two sheets**:

| Sheet | Purpose |
|---|---|
| `CIQ_Data`     | The data-fetch formulas + their resolved values |
| `_RowMap`       | Metadata: which row holds which variable |

The sheet name `CIQ_Data` is legacy (the project started with Capital
IQ as the first data source). You can use the same name with any data
provider; the name is just a label.

---

## `CIQ_Data` sheet

### Row 1: ticker

| Cell | Contents |
|---|---|
| `A1` | Label `"Ticker:"` |
| `B1` | Ticker string (e.g., `"NasdaqGS:MSFT"`, `"SEHK:992"`, `"NYSE:BABA"`). Every fetch formula in the sheet references `$B$1`. Change B1, all formulas re-resolve. |

### Rows 4+: data rows

Each data row has this column structure:

| Column | Contents |
|---|---|
| `A` | Variable name (e.g., `revenues`, `ebit`, `stock_price`) |
| `B` | Period label (e.g., `IQ_FY-0`, `IQ_FQ-2`, `current`) |
| `C` | Fetch formula (typically `=CIQ(...)` or equivalent) |
| `D` | Resolved value (formula `=C{row}` so it always equals column C's value) |
| `E` | Human-readable description |

The backend reads the **resolved value** from column D. Which formula you
use to populate C (and thus D) is up to you — CIQ, Bloomberg, FactSet,
or an entirely manual typed value all work.

### Section conventions

Organized into these sections (labels in column A, merged across cells):

- `INCOME STATEMENT (Annual)` — for FY-0 through FY-10
- `INCOME STATEMENT (Quarterly — for LTM)` — for FQ-0 through FQ-7
- `BALANCE SHEET (Annual)` — for FY-0 through FY-10
- `BALANCE SHEET (Quarterly — latest 10-Q)` — for FQ-0 only
- `MARKET DATA (Current)` — stock price, market cap, filing currency, etc.
- `EMPLOYEE OPTIONS (Current)` — options outstanding, strike, maturity
- `OPERATING LEASE COMMITMENTS (Current)` — year 1–5 + beyond
- `PERIOD DATES` — most recent 10-K and 10-Q period-end dates
- `GEOGRAPHIC REVENUE SEGMENTS (top 10 by revenue, latest FY)` — ranked 1..10

---

## Required variable names

### Income statement (per fiscal year `IQ_FY-0` through `IQ_FY-10`)

| Variable | Semantic |
|---|---|
| `revenues` | Total revenue |
| `ebit` | Operating income |
| `ebitda` | EBITDA |
| `net_income` | Net income (attributable to shareholders) |
| `interest_expense` | Interest expense (positive; backend wraps with ABS) |
| `d_a` | Depreciation & amortization (from cash-flow statement) |
| `r_and_d_expense` | R&D expense (primary). Fetch for FY-0 through FY-10 so the R&D converter has a 10-year history. |
| `capex` | Capital expenditures (positive) |
| `operating_lease_expense` | Current-period operating lease rent |
| `earnings_before_tax` | Pre-tax income |
| `total_tax_expense` | Income tax expense |

### Income statement (quarterly `IQ_FQ-0` through `IQ_FQ-7`)

Same variables as above — needed to compute LTM via the Ginzu formula:
```
LTM = FY-0 − Prior_YTD + Current_YTD
```
where `Prior_YTD = Σ FQ-4..FQ-(K+3)` and `Current_YTD = Σ FQ-0..FQ-(K-1)`
for K quarters since the last 10-K filing.

### Balance sheet (per fiscal year `IQ_FY-0` through `IQ_FY-10`, plus `IQ_FQ-0`)

| Variable | Semantic |
|---|---|
| `cash_and_marketable_securities` | Cash + ST investments |
| `bv_equity` | Total stockholders' equity |
| `bv_debt` | Total debt (short + long) |
| `shares_outstanding` | Diluted / weighted shares outstanding at filing date |
| `cross_holdings` | Long-term investments (equity method / minority stakes) |
| `minority_interests` | Non-controlling interests |

### Market data (period = `"current"`)

| Variable | Semantic | Currency |
|---|---|---|
| `stock_price` | Last close | **Listing** currency |
| `stock_price_reporting` | Last close | **Reporting** (filing) currency — see [Currency handling](#currency-handling) |
| `mv_equity` | Market capitalization | **Listing** currency |
| `mv_equity_reporting` | Market capitalization | **Reporting** (filing) currency |
| `reporting_currency` | ISO 4217 code of the financial statements (e.g., `"USD"`, `"CNY"`) | n/a |
| `primary_exchange` | Exchange prefix (e.g., `"SEHK"`, `"NasdaqGS"`) | n/a |
| `effective_tax_rate_ciq` | Effective tax rate (already divided by 100, so `0.15` not `15`) | n/a |

### Employee options (period = `"current"`)

| Variable | Semantic |
|---|---|
| `options_outstanding` | Total outstanding options |
| `options_avg_strike` | Weighted-average strike price |
| `options_avg_maturity` | Weighted-average remaining life (years) |

### Operating lease commitments (period = `"current"`)

| Variable | Semantic |
|---|---|
| `lease_commitment_yr1` | Commitment due in year 1 |
| `lease_commitment_yr2` | Commitment due in year 2 |
| `lease_commitment_yr3` | Commitment due in year 3 |
| `lease_commitment_yr4` | Commitment due in year 4 |
| `lease_commitment_yr5` | Commitment due in year 5 |
| `lease_commitment_beyond` | Aggregate commitment beyond year 5 |

### Period dates

| Variable | Semantic |
|---|---|
| `period_date_annual` | Most recent 10-K period end date |
| `period_date_quarterly` | Most recent 10-Q period end date |

### Geographic revenue segments (ranked 1..10 by revenue, latest FY)

| Variable pattern | Semantic |
|---|---|
| `geo_seg_name_{rank}` | Segment name as reported (e.g., `"China"`, `"EMEA"`, `"Americas"`) for `rank` in 1..10 |
| `geo_seg_rev_{rank}` | Segment revenue for the same rank |

Companies typically report 3–10 real segments; the backend filters out
zero-revenue rows plus common corporate/unallocated labels
(`"Headquarters"`, `"Unallocated *"`, `"Eliminations"`, etc.).

---

## Currency handling

The engine distinguishes two currencies:

- **Reporting currency** (`reporting_currency` field) — the currency of
  the financial statements. All DCF math (WACC, VPS, bridge) runs in
  this currency.
- **Listing currency** — the currency the stock trades in on its
  primary exchange. Only the stock price and market cap (the `stock_price`
  and `mv_equity` fields) are in this currency.

For firms where the two match (e.g., MSFT on Nasdaq in USD, reports USD),
no conversion happens. For firms where they differ — e.g. Lenovo reports
in USD but trades on SEHK in HKD — the backend derives the FX rate from
the ratio of the `_reporting` vs `_listing` price/mv variants, and uses
the reporting-currency values for WACC math.

### Capital IQ users specifically

The `=CIQ(...)` function has a 4th positional argument for currency
scope: `"TRADED"` (default, listing currency) or `"REPORTED"` (filing
currency). So:

```excel
stock_price              =CIQ($B$1, "IQ_CLOSEPRICE")                      ← listing ccy
stock_price_reporting    =CIQ($B$1, "IQ_CLOSEPRICE", "", "REPORTED")      ← reporting ccy
mv_equity                =CIQ($B$1, "IQ_MARKETCAP")                       ← listing ccy
mv_equity_reporting      =CIQ($B$1, "IQ_MARKETCAP",  "", "REPORTED")      ← reporting ccy
```

If your data source uses different syntax (Bloomberg `BDP` with a
currency override, etc.), adapt accordingly. The backend doesn't care
how column D's value was resolved, only that it's correct.

---

## `_RowMap` sheet

Tabular metadata the reader uses to locate each variable:

| Column | Contents |
|---|---|
| `A` | Row number in `CIQ_Data` where this variable lives |
| `B` | Variable name (e.g., `revenues`) |
| `C` | Period label (`IQ_FY-0`, `IQ_FQ-2`, `current`, `rank_1`, etc.) |
| `D` | Mnemonic / formula identifier (free text — for reference) |

One row per variable × period combination. Generated automatically by
`backend/tools/generate_ciq_template.py`.

---

## Generating a blank template

The backend ships a generator that emits the full layout with formula
cells as `=CIQ(...)` stubs:

```bash
cd backend && source .venv/bin/activate
python -m tools.generate_ciq_template NVDA
```

Output: `knowledge_base/ciq_fetches/CIQ_Fetch_Template.xlsx`

You can hand-edit column C of any row to replace the `=CIQ(...)` formula
with your data source's equivalent (e.g., a Bloomberg `=BDP(...)`
formula, or a literal typed-in value if you're valuing a small firm
where the financials come from a PDF). The `_RowMap` tells the backend
where to find each variable regardless of the formula used.

---

## Minimum working data

For a DCF to produce a non-trivial result, you need at least:

- 2 fiscal years of revenue + EBIT (the most recent + one prior)
- `stock_price`, `mv_equity`, `shares_outstanding`, `reporting_currency`,
  `primary_exchange`
- `bv_debt`, `bv_equity`, `cash_and_marketable_securities`
- `interest_expense`, `earnings_before_tax`, `total_tax_expense`
- `period_date_annual` and (if applicable) `period_date_quarterly`

Everything else is optional. R&D and lease data enable the capitalization
adjustments; geographic segments enable the operating-countries ERP
approach; quarterly data enables LTM rotation. When a field is missing
the backend uses safe defaults and surfaces the gap via the frontend
`UnresolvedFieldsPanel` so you can fix it manually.

---

## Field mapping reference

The code-level truth for variable names is in
[`backend/data_sources/capiq_formula_map.py`](../backend/data_sources/capiq_formula_map.py)
(the `CIQField` definitions). If you change the schema, start there.
