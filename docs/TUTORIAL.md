# Tutorial — Value Microsoft in 5 minutes

This walkthrough takes you from a fresh clone to a complete DCF valuation
of Microsoft in roughly 5 minutes. It assumes you've already run the
[Quickstart](../README.md#-quickstart) — backend on `:8000`, frontend on
`:5173`, Damodaran reference data under `knowledge_base/damodaran/`.

No S&P Capital IQ subscription required for this tutorial — we'll hand-
populate a minimal workbook with values sourced from Microsoft's public
10-K filing.

---

## Step 1 — Generate a blank template (30 s)

From the repo root:

```bash
cd backend && source .venv/bin/activate
python -m tools.generate_ciq_template MSFT
```

Output: `knowledge_base/ciq_fetches/CIQ_Fetch_Template.xlsx`. Open it in
Excel. You'll see:

- **Row 1:** `Ticker:` in A1, `MSFT` in B1 (yellow highlighted)
- **Rows 4+:** every variable the backend expects, one per row, with a
  `=CIQ(...)` formula in column C and a `=C{row}` mirror in column D
  (the backend reads column D)
- **`_RowMap` sheet:** metadata the backend uses to locate each variable

Without a Capital IQ plug-in the `=CIQ(...)` formulas won't resolve — they'll
show `#NAME?`. That's fine. We'll type the values directly into column D,
which is what the backend actually reads.

---

## Step 2 — Populate the minimum working set (3 min)

You need these values (sourced from Microsoft's latest 10-K, available
on [microsoft.com/investor](https://www.microsoft.com/en-us/Investor/)).
Numbers below are illustrative — use whatever the latest 10-K says.

**Find the row in `_RowMap` for each variable; paste the value into column D
of the matching row on `CIQ_Data`.**

| Variable | Period | Value | Source |
|---|---|---|---|
| `revenues` | `IQ_FY-0` | 281724 | 10-K income statement, total revenue (in millions USD) |
| `revenues` | `IQ_FY-1` | 245122 | prior-year revenue |
| `ebit` | `IQ_FY-0` | 128528 | operating income |
| `ebit` | `IQ_FY-1` | 109433 | prior-year operating income |
| `interest_expense` | `IQ_FY-0` | 2425 | interest expense (positive number) |
| `cash_and_marketable_securities` | `IQ_FY-0` | 30242 | cash + ST investments |
| `bv_equity` | `IQ_FY-0` | 343479 | total stockholders' equity |
| `bv_debt` | `IQ_FY-0` | 112184 | total debt (short + long) |
| `shares_outstanding` | `IQ_FY-0` | 7433.17 | basic shares (millions) |
| `cross_holdings` | `IQ_FY-0` | 15405 | LT investments |
| `minority_interests` | `IQ_FY-0` | 0 | none for MSFT |
| `earnings_before_tax` | `IQ_FY-0` | 128967 | |
| `total_tax_expense` | `IQ_FY-0` | 21795 | |
| `r_and_d_expense` | `IQ_FY-0` | 32488 | optional; enables R&D capitalization |
| `stock_price` | `current` | 424.82 | latest close — listing currency (USD) |
| `stock_price_reporting` | `current` | 424.82 | same value; MSFT lists and reports in USD |
| `mv_equity` | `current` | 3157757 | shares × price, in millions |
| `mv_equity_reporting` | `current` | 3157757 | same as mv_equity for USD-only firms |
| `reporting_currency` | `current` | USD | ISO code |
| `primary_exchange` | `current` | NasdaqGS | exchange prefix |
| `period_date_annual` | `IQ_FY-0` | Jun 30, 2025 | 10-K period end |
| `period_date_quarterly` | `IQ_FQ-0` | Jun 30, 2025 | or the latest 10-Q date |

> ⚡ **Pro tip:** If you don't want to hand-populate every row, skip R&D and
> lease data — the backend will still produce a valid (if less precise)
> valuation using the minimum core set.

**Save** the xlsx.

---

## Step 3 — Upload (30 s)

Make sure both services are running:

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn api.main:app --port 8000

# Frontend (new terminal)
cd frontend && npm run dev
```

Go to `http://localhost:5173/`. Click "Upload CIQ File" → pick your
populated xlsx.

Within a second or two, the Input Sheet will populate.

---

## Step 4 — Navigate the valuation (1 min)

### 4a. Input Sheet (`/`)

Verify the base-year numbers look right. Hover any cell to see its
provenance. Any unexpected zeros? Check the corresponding `_RowMap` entry
and column D value.

### 4b. Cost of Capital (`/wacc`)

The crown jewel. You'll see:

- A panel of **4 dropdowns** (Approach / β / ERP / Kd)
- Under them, the **computed WACC components** — β_u, β_L, D/E, weights,
  Ke, Kd, and the final WACC
- An **industry reference sidebar** with Damodaran's industry averages

For MSFT on default settings (`Detailed` / `Single Business(US)` /
`Country of incorporation` / `Industry fallback`) you should see:

- β_u ≈ 1.25 (Software System & Application)
- β_L ≈ 1.28 (levered at MSFT's low debt ratio)
- Ke ≈ 10.3%
- Kd pre-tax ≈ 5.3% (Damodaran's industry Kd)
- WACC ≈ 10.0%

**Try this:** change the ERP approach dropdown to `Operating countries`
(assuming you populated geographic segment data). WACC should tick up
slightly since Microsoft earns revenue globally.

### 4c. Summary Sheet (`/summary`)

The 10-year projection:

| Year | Revenue | Growth | EBIT margin | EBIT | Reinvest | FCFF |
|------|---------|--------|-------------|------|----------|------|
| 1 | 309,896 | 10.0% | 45.6% | 141,381 | … | … |
| 2 | 334,688 | 8.0% | … | … | … | … |
| … | | | | | | |
| Terminal | 4.25% ≤ RF | target margin | | | | |

Plus the final equity bridge:

```
V_operating    = sum PV(FCFF) + PV(terminal)
  − Debt
  − Minority interests
  + Cash
  + Cross-holdings
= V_equity
  − Options (iterative BSM)
= V_equity_common
÷ Shares
= Value per Share (reporting ccy)
```

### 4d. Compare to market price

At the bottom of the Summary sheet, Price / Value ratio shows whether
MSFT is trading at a premium (ratio > 1) or discount (< 1) to its DCF
intrinsic value on the assumptions you picked.

---

## Step 5 — Tweak an assumption, watch everything recompute (30 s)

Go to the Input Sheet. Find **"Revenue growth, next year"** — it's a
hypothesis cell (yellow). Double-click, type a new value (say, `0.12`
instead of `0.10`), press Enter.

Under the hood:
1. Frontend PATCHes `valuation_assumptions.revenue_growth_next_year` to `0.12`
2. Backend re-runs the full M1-M6 pipeline
3. All 15 pages reflect the new state within ~200 ms

Watch revenue projections rise, EBIT compound higher, FCFF scale, and the
final VPS go up. This is the **provenance model** in action — change one
input, every downstream number traces to it.

---

## What next

- **Methodology deep-dive:** read
  [`docs/Ginzu understanding/module_04_cost_of_capital.md`](Ginzu%20understanding/module_04_cost_of_capital.md)
  to learn why WACC has 4 approaches in the first place.
- **Try a non-US firm:** value Lenovo (SEHK:992) or Alibaba (NYSE:BABA).
  You'll see the currency banner activate and the FX conversion between
  listing and reporting currencies.
- **Try a harder case:** a firm not in Damodaran's industry classification
  file — the `UnresolvedFieldsPanel` will guide you through manual
  industry selection.
- **Reconcile against Damodaran:** run the comparison harness in
  `docs/experiments/` to verify this engine matches his published numbers
  for NVIDIA within ~0% on WACC.

Happy valuing.
