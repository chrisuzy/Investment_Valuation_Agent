# Data Dictionary — Typed Variable Schema

## Purpose

The Data Dictionary is the **single source of truth** for all variable names in the system. Every module imports Pydantic models from `engine/data_dictionary.py`. No module may introduce variables outside this dictionary.

## Implementation

All schemas are Pydantic `BaseModel` classes with strict typing. Variable names match the PRD exactly (snake_case with underscores). All financial values are `float`. Counts are `int`. Arrays use `list[float]`.

## Schema Definitions

### A. MacroInputs — Macro & Risk Variables

| Variable | Type | Description |
|----------|------|-------------|
| `risk_free_rate` | `float` | 10/20/30-year treasury yield |
| `equity_risk_premium` | `float` | Equity Risk Premium (ERP) |
| `country_risk_premium` | `float` | Country Risk Premium (CRP) |
| `tax_rate_marginal` | `float` | Marginal/statutory tax rate |
| `tax_rate_effective` | `float` | Effective tax rate |
| `default_spread` | `float` | Corporate debt default spread |

Source: Damodaran datasets (by country/region).

### B. RawFinancials — Company Financial Data from Capital IQ

| Variable | Type | Description |
|----------|------|-------------|
| `revenues` | `float` | Total revenue |
| `ebit` | `float` | Earnings before interest & taxes |
| `ebitda` | `float` | EBITDA |
| `net_income` | `float` | Net income |
| `interest_expense` | `float` | Interest expense |
| `capex` | `float` | Capital expenditures |
| `d_a` | `float` | Depreciation & amortization |
| `noncash_wc` | `float` | Non-cash working capital |
| `change_in_noncash_wc` | `float` | Change in non-cash WC |
| `net_debt_issued` | `float` | Net debt issuance |
| `cash_and_marketable_securities` | `float` | Cash + marketable securities |
| `bv_equity` | `float` | Book value of equity |
| `bv_debt` | `float` | Book value of debt |
| `mv_equity` | `float` | Market value of equity (market cap) |
| `mv_debt` | `float` | Market value of debt |
| `shares_outstanding` | `int` | Primary shares outstanding |

Source: Capital IQ Excel plugin. Multi-year data stored as `list[RawFinancials]` (one per fiscal year).

### C. AdjustmentInputs — R&D and Lease Inputs

| Variable | Type | Description |
|----------|------|-------------|
| `amortization_period_n` | `int` | R&D amortization period (3, 5, or 10 years) |
| `r_and_d_expense_current` | `float` | Current year R&D expense |
| `r_and_d_expense_past_t` | `list[float]` | Past t years R&D expenses (t=1..n) |
| `operating_lease_expense_current` | `float` | Current operating lease expense |
| `operating_lease_commitment_t` | `list[float]` | Future lease commitments by year |

Source: Capital IQ Excel plugin.

### D. AdjustedFinancials — Module 1 Output

| Variable | Type | Description |
|----------|------|-------------|
| `unamortized_r_and_d` | `float` | Unamortized R&D asset value |
| `amortization_r_and_d` | `float` | Current period R&D amortization |
| `pv_of_operating_leases` | `float` | PV of operating lease debt |
| `adjusted_ebit` | `float` | EBIT adjusted for R&D + leases |
| `adjusted_net_income` | `float` | Net income adjusted for R&D |
| `adjusted_bv_equity` | `float` | Book equity + research asset |
| `adjusted_mv_debt` | `float` | Market debt + lease PV |

### E. IndustryData — Damodaran Lookup Result

| Variable | Type | Description |
|----------|------|-------------|
| `beta_u` | `float` | Unlevered beta (industry average) |
| `industry_d_e_ratio` | `float` | Industry average D/E ratio |
| `industry_name` | `str` | Damodaran industry classification |

Source: Damodaran "Betas by Industry" dataset.

### F. CostOfCapital — Module 2 Output

| Variable | Type | Description |
|----------|------|-------------|
| `d_e_ratio` | `float` | Company debt-equity ratio (market values) |
| `beta_l` | `float` | Levered beta |
| `cost_of_equity` | `float` | Ke = Rf + Beta_L * ERP |
| `cost_of_debt_pretax` | `float` | Pre-tax cost of debt |
| `cost_of_debt_aftertax` | `float` | After-tax cost of debt |
| `wacc` | `float` | Weighted average cost of capital |

### G. CashFlowMetrics — Module 3 Output

| Variable | Type | Description |
|----------|------|-------------|
| `adjusted_capex` | `float` | CapEx + R&D expense |
| `adjusted_d_a` | `float` | D&A + R&D amortization |
| `reinvestment_firm` | `float` | Total firm reinvestment |
| `reinvestment_equity` | `float` | Equity reinvestment |
| `fcff` | `float` | Free cash flow to firm |
| `fcfe` | `float` | Free cash flow to equity |
| `adjusted_invested_capital` | `float` | Adjusted invested capital |
| `roic` | `float` | Return on invested capital |
| `roe` | `float` | Return on equity |
| `rir_firm` | `float` | Firm reinvestment rate |
| `rir_equity` | `float` | Equity reinvestment rate |
| `expected_growth_ebit` | `float` | Fundamental EBIT growth |
| `expected_growth_ni` | `float` | Fundamental NI growth |

### H. ValuationAssumptions — User-Adjustable DCF Inputs

| Variable | Type | Description |
|----------|------|-------------|
| `projection_years` | `int` | High-growth period length (default: 5) |
| `stable_growth_rate` | `float` | Terminal growth rate (must <= risk_free_rate) |
| `high_growth_rate_override` | `float | None` | Override for high-growth EBIT growth |
| `wacc_stable_override` | `float | None` | Override WACC for stable period |

### I. DCFResult — Module 4 Output

| Variable | Type | Description |
|----------|------|-------------|
| `fcff_projections` | `list[float]` | Projected FCFF for each year |
| `terminal_value_firm` | `float` | Terminal value |
| `value_of_operating_assets` | `float` | PV of operating assets |
| `value_of_equity` | `float` | Equity value pre-options |
| `value_per_share_pre_options` | `float` | Per-share value pre-dilution |

### J. MultiplesResult — Module 5 Output

| Variable | Type | Description |
|----------|------|-------------|
| `pe_ratio_intrinsic` | `float` | Intrinsic forward PE |
| `pbv_ratio_intrinsic` | `float` | Intrinsic PBV |
| `ev_ebitda_intrinsic` | `float` | Intrinsic EV/EBITDA |
| `ev_sales_intrinsic` | `float` | Intrinsic EV/Sales |
| `pe_ratio_market` | `float` | Actual market PE for comparison |

### K. OptionInputs — Employee Stock Option Data

| Variable | Type | Description |
|----------|------|-------------|
| `option_s` | `float` | Underlying asset value |
| `option_k` | `float` | Average strike price |
| `option_t` | `float` | Average remaining maturity |
| `option_variance` | `float` | Asset value variance (sigma^2) |
| `option_y` | `float` | Dividend yield |
| `number_of_options` | `int` | Total outstanding options |

### L. FinalValuation — Module 6 / Final Output

| Variable | Type | Description |
|----------|------|-------------|
| `call_value` | `float` | BSM call option value per option |
| `value_of_options` | `float` | Total option value |
| `value_per_share` | `float` | Final per-share intrinsic value |

## Naming Convention Rules

1. All variable names use `snake_case` in Python code
2. PRD variable names with uppercase (e.g., `FCFF`) become lowercase in Python (`fcff`)
3. List variables for time series use `_t` suffix or are typed as `list[float]`
4. All monetary values are in the company's reporting currency (assumed consistent)
5. All rates/ratios are decimal (0.05 = 5%), not percentage
