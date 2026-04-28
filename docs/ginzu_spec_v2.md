# Ginzu Specification v2 — Reconciled End-to-End Valuation Framework

**Authority:** this document is ground-truth, synthesized directly from the formulas in `knowledge_base/Ginzu_NVIDIA.xlsx` (extracted by `backend/tools/extract_ginzu_formulas.py` into `docs/brainstorm_cache/ginzu_extracted.json` — 1,675 formulas across 18 sheets).

**Scope:** canonical single-segment Damodaran FCFF valuation. Multi-segment overlays (e.g. NVIDIA's AI/Auto segments) are NVIDIA-specific extensions and are **out of scope** for this spec.

**Purpose:** replaces `docs/brainstorm_cache/methods_in_details.md`. Where this document conflicts with `docs/valuation_framework_textbook.md`, this document wins — see `docs/textbook_corrections.md` for the per-item discrepancy list.

**How to use:** read top-to-bottom in stage order to implement a new valuation system. Each stage lists (a) inputs, (b) variable-linked formulas, (c) outputs, (d) known Ginzu quirks. Full findings backing this synthesis live in `docs/brainstorm_cache/stage_{1..6}_findings.md`.

---

## Table of Contents

1. [Inputs](#1-inputs)
2. [LTM Normalization](#2-ltm-normalization)
3. [R&D Capitalization](#3-rd-capitalization)
4. [Operating Lease Conversion](#4-operating-lease-conversion)
5. [Cost of Capital (4 Approaches)](#5-cost-of-capital)
6. [10-Year DCF Projection](#6-10-year-dcf-projection)
7. [Terminal Value](#7-terminal-value)
8. [Discounting to Present Value](#8-discounting-to-present-value)
9. [Failure Probability Overlay](#9-failure-probability-overlay)
10. [Equity Bridge and Per-Share Value](#10-equity-bridge-and-per-share-value)
11. [Options Dilution (Iterative Black-Scholes)](#11-options-dilution)
12. [Invested Capital and ROIC Path](#12-invested-capital-and-roic-path)
13. [Diagnostics](#13-diagnostics)
14. [Feedback Loops](#14-feedback-loops)
15. [Ginzu Quirks to Not Replicate](#15-ginzu-quirks-to-not-replicate)

---

## 1. Inputs

Canonical user inputs fed to the valuation (Input sheet, rows 3–83 of Ginzu):

### A. Company identification
- `valuation_date`, `company_name`, `country_of_incorporation`, `industry_us`, `industry_global`

### B. Base-year financial data (this year + last year in parallel columns)
- `revenues`, `operating_income_ebit`, `interest_expense`, `book_value_of_equity`, `book_value_of_debt`
- `has_rd_to_capitalize`, `has_operating_leases` (Yes/No flags)
- `cash_and_marketable_securities`, `cross_holdings`, `minority_interests`
- `shares_outstanding`, `current_stock_price`
- `effective_tax_rate`, `marginal_tax_rate`

### C. Story inputs (growth and profitability)
- `revenue_growth_next_year` — year 1 growth
- `revenue_growth_years_2_5` — years 2–5 growth (**default = `revenue_growth_next_year`**)
- `operating_margin_next_year` — year 1 margin
- `target_pretax_operating_margin` — margin at maturity
- `year_of_convergence_for_margin` — integer 1–10
- `sales_to_capital_ratio_years_1_5` — capital efficiency high-growth
- `sales_to_capital_ratio_years_6_10` — capital efficiency transition

### D. Macro + market
- `riskfree_rate` — risk-free rate in reporting currency
- `initial_cost_of_capital` — computed from §5, echoed onto Input sheet for display

### E. Options (if applicable)
- `has_options_outstanding` (Yes/No)
- `options_outstanding`, `options_avg_strike`, `options_avg_maturity`, `stock_price_std_dev`

### F. Override flags + paired values
Each override has a Yes/No flag cell + 1-3 associated value cells. When flag = "Yes", the override value is active. Default behavior applies when flag is "No" or blank.

| Override | Flag | Value(s) | Default behavior |
|---|---|---|---|
| `override_cost_of_capital_stable` | B56 | B57 | terminal WACC = `riskfree_rate + mature_market_erp` |
| `override_roic_stable` | B59 | B60 | terminal ROIC = terminal WACC (no excess returns) |
| `override_failure_probability` | B62 | B63 | p = 0 |
| *failure tie-to* | — | B64 ("B" or "V") | "V" |
| *distress proceeds pct* | — | B65 | 0.5 |
| `override_reinvestment_lag` | B67 | B68 (0, 2, 3) | lag = 1 year |
| `override_tax_convergence` | B70 | — | tax converges to marginal by year 11 |
| `override_nol` | B72 | B73 | NOL_0 = 0 |
| `override_riskfree` | B75 | B76 | RF unchanged after year 10 |
| `override_growth_perpetuity` | B78 | B79 | g_terminal = RF |
| `override_trapped_cash` | B81 | B82, B83 | cash_usable = cash |

**Case sensitivity quirk:** every flag cell expects literal "Yes" EXCEPT the trapped cash flag (B81) which Ginzu checks for literal "YES" (all caps). Our engine should accept case-insensitively.

---

## 2. LTM Normalization

**Purpose:** bring stale 10-K flows up to date using most recent 10-Q data.

**Inputs per flow item:** `last_10k_value`, `prior_year_ytd_value`, `current_year_ytd_value`.

**Formula (flow items only):**
```
ltm_value = last_10k_value + current_year_ytd_value - prior_year_ytd_value
```

**Balance sheet items:** no LTM — use most recent 10-Q point-in-time.

**Ginzu note:** the `Trailing 12 month` sheet is a standalone calculator in Ginzu (the analyst computes LTM separately and types the result into Input!B10..B23). Our backend automates this via `backend/engine/ltm_calculator.py`.

---

## 3. R&D Capitalization

**Inputs:** `amortization_period_n`, `r_and_d_expense_current`, `r_and_d_expense_past_t` for t = 1..N (where t=1 is one year ago).

**Per-year derivation (t = 1..N):**
```
unamortized_fraction_t = (N - t) / N
unamortized_value_t    = r_and_d_expense_past_t × unamortized_fraction_t
amortization_t         = r_and_d_expense_past_t / N
```

**Aggregates:**
```
value_of_research_asset    = r_and_d_expense_current + Σ_{t=1..N} unamortized_value_t
amortization_r_and_d_total = Σ_{t=1..N} amortization_t
adjustment_to_ebit_from_rd = r_and_d_expense_current - amortization_r_and_d_total
```

**Applied to:**
```
adjusted_ebit       += adjustment_to_ebit_from_rd        # pre-tax
adjusted_net_income += adjustment_to_ebit_from_rd        # pre-tax
adjusted_bv_equity  += value_of_research_asset
```

---

## 4. Operating Lease Conversion

**Inputs:** `operating_lease_expense_current`, `operating_lease_commitment_yr_t` for t = 1..5, `operating_lease_commitment_beyond_yr5`, `cost_of_debt_pretax`.

**Derived:**
```
n_additional = ROUND(commitment_beyond_yr5 / AVERAGE(commitment_yr1..5), 0)   # may be 0

annuity_amount =
  IF n_additional > 0:  commitment_beyond_yr5 / n_additional
  ELSE:                 commitment_beyond_yr5  (treat as single lump in year 6)
```

**Present values:**
```
pv_yr_1_to_5 = Σ_{t=1..5} commitment_yr_t / (1 + kd)^t

pv_beyond_yr5 =
  IF n_additional > 0:
    [ annuity_amount × (1 - (1 + kd)^(-n_additional)) / kd ] × (1 + kd)^(-5)
  ELSE:
    commitment_beyond_yr5 × (1 + kd)^(-6)

debt_value_of_operating_leases = pv_yr_1_to_5 + pv_beyond_yr5
```

**Restated financials:**
```
total_lease_years                  = 5 + n_additional        # 5 when n_additional = 0
depreciation_on_lease_asset        = debt_value_of_leases / total_lease_years
adjustment_to_ebit_from_leases     = lease_expense_current - depreciation_on_lease_asset
adjustment_to_depreciation         = debt_value_of_leases / total_lease_years  # = depreciation_on_lease_asset
```

**Applied to:**
```
adjusted_ebit  += adjustment_to_ebit_from_leases
adjusted_debt  += debt_value_of_operating_leases
adjusted_d_a   += adjustment_to_depreciation                # used in §6.7 reinvestment diagnostics
```

---

## 5. Cost of Capital

Four approaches selected by `cost_of_capital_approach` ∈ {"I will input", "Detailed", "Industry Average", "Decile"}. Dispatch:

```
wacc_initial =
  IF approach == "I will input":           direct_cost_of_capital_input
  ELIF approach == "Detailed":              E62 (Approach 1 output)
  ELIF approach == "Industry Average":      B67 (Approach 2 output)
  ELSE:                                     B72 (Approach 3 output)
```

### 5.1 Approach 1 — Detailed

**Five beta variants** (selector `beta_estimation_approach`):
- "Single Business(US)": `unlevered_beta = VLOOKUP(industry_us, Industry_Averages_US, col=7)`
- "Multibusiness(US)": `unlevered_beta = EV-weighted average across business segments using Industry_Averages_US`
- "Single Business(Global)": `unlevered_beta = VLOOKUP(industry_global, Industry_Averages_Global, col=7)`
- "Multibusiness(Global)": `unlevered_beta = EV-weighted average, Global`
- "Direct Input": `unlevered_beta = direct_unlevered_beta_input`; OR `levered_beta = direct_levered_beta_input` (see §5.1.C)

EV-weighted multi-business beta:
```
for each segment i:
    segment_ev_i = segment_revenue_i × industry_ev_to_sales_multiple_i  (col 15)
    segment_unlevered_beta_i = industry_unlevered_beta_i  (col 7)

weighted_unlevered_beta = Σ_i (segment_unlevered_beta_i × segment_ev_i / Σ_j segment_ev_j)
```

**Four ERP variants** (selector `erp_estimation_approach`):
- "Country of Incorporation": `erp = VLOOKUP(country, Country_ERP_Table, col=4)` — total ERP (mature + country)
- "Operating Countries": revenue-weighted blend per country
- "Operating Regions": revenue-weighted blend per region (10 regions at Country_ERP rows 201–210)
- "Will Input": `erp = direct_erp_input`

Operating countries / regions:
```
weighted_erp = Σ_i (erp_i × revenue_i / total_revenue)
```

**Three pre-tax Kd variants** (selector `cost_of_debt_approach`):
- "Direct Input": `kd_pretax = direct_cost_of_debt_pretax`
- "Synthetic Rating": `kd_pretax = Synthetic_rating!D16` (see §5.2)
- "Actual Rating": `kd_pretax = riskfree_rate + VLOOKUP(rating, Rating_Spread_Table, col=2)`

**MV of debt (bond pricing):**
```
mv_straight_debt =
  interest_expense × (1 - (1 + kd)^(-maturity)) / kd
  + book_value_of_debt / (1 + kd)^maturity

mv_straight_debt_in_convertible =
  conv_interest × (1 - (1 + kd)^(-conv_maturity)) / kd
  + conv_book / (1 + kd)^conv_maturity

equity_in_convertible = conv_market_value - mv_straight_debt_in_convertible

mv_debt_total = mv_straight_debt + mv_straight_debt_in_convertible + debt_value_of_operating_leases
```

**MV of equity:**
```
mv_equity = shares_outstanding × current_stock_price
```

**MV of preferred:**
```
mv_preferred = number_of_preferred_shares × preferred_price_per_share
```

**Weights:**
```
mv_total   = mv_equity + mv_debt_total + mv_preferred
w_equity   = mv_equity / mv_total
w_debt     = mv_debt_total / mv_total
w_preferred = mv_preferred / mv_total
```

**Levered beta:**
```
levered_beta =
  IF beta_approach == "Direct Input":
    direct_levered_beta_input
  ELSE:
    unlevered_beta × (1 + (1 - tax_rate_marginal) × (mv_debt_total / mv_equity))
```

**Component costs:**
```
cost_of_equity_capm    = riskfree_rate + levered_beta × erp
cost_of_debt_aftertax  = kd_pretax × (1 - tax_rate_marginal)
cost_of_preferred      = preferred_dividend_per_share / preferred_price_per_share
```

**WACC (Approach 1 output):**
```
wacc = w_equity × cost_of_equity_capm + w_debt × cost_of_debt_aftertax + w_preferred × cost_of_preferred
```

### 5.2 Synthetic rating

Inputs: `firm_type` (1=large mfg, 2=small/risky, 3=financial), `adjusted_ebit_for_coverage`, `adjusted_interest_for_coverage`, `riskfree_rate`.

**Important:** `adjusted_ebit_for_coverage` uses **lease-adjusted EBIT only** (NOT R&D-adjusted). `adjusted_interest_for_coverage` = `reported_interest + lease_pv × kd_pretax`.

```
interest_coverage_ratio =
  IF interest == 0:    1_000_000  (proxy for infinite)
  IF ebit < 0:         -100_000   (proxy for distress)
  ELSE:                ebit / interest

rating = VLOOKUP(coverage, coverage_rating_table[firm_type], col=3)
company_spread = VLOOKUP(coverage, coverage_rating_table[firm_type], col=4)
country_spread = VLOOKUP(country_of_incorporation, Country_ERP, col=3)

synthetic_kd_pretax = riskfree_rate + company_spread + country_spread
```

### 5.3 Approach 2 — Industry average adjusted
```
wacc =
  industry_wacc_for_selection                # VLOOKUP on industry + col 13
  + (riskfree_rate - mature_market_riskfree) # mature_market_riskfree is a time-sensitive constant, currently 3.88% in Ginzu 2023 edition; refresh annually from Damodaran dataset
```

### 5.4 Approach 3 — Regional decile
```
wacc = VLOOKUP(region, region_quartile_table, col_index(risk_group))
```
Returns a flat rate from a 5×5 table (regions × {First Decile, First Quartile, Median, Third Quartile, Ninth Decile}). **No RF adjustment** (inconsistent with Approach 2; design choice).

---

## 6. 10-Year DCF Projection

Canonical single-segment. `t` indexes year: t=1..10 explicit, t=11 is terminal.

### 6.1 Revenue path
```
g_revenue_year_t:
  t == 1:             revenue_growth_next_year
  t == 2:             revenue_growth_years_2_5        # defaults to year-1 growth if user didn't set
  3 ≤ t ≤ 5:          revenue_growth_years_2_5        # flat
  6 ≤ t ≤ 10:         g_5 - (g_5 - g_terminal) × (t - 5) / 5
  Terminal:           g_terminal

revenue_year_t = revenue_year_{t-1} × (1 + g_revenue_year_t)
revenue_year_0 = base_year_rest_revenue  (adjusted EBIT base; for canonical single-segment = raw.revenues)

g_terminal:
  IF override_growth_perpetuity:  growth_perpetuity_rate
  ELIF override_riskfree:         riskfree_after_yr10
  ELSE:                           riskfree_rate
```

### 6.2 Operating margin path
```
operating_margin_year_t:
  t == 1:                                 operating_margin_next_year
  1 < t ≤ margin_convergence_year_K:      target - (target - margin_1) × (K - t) / K
  t > margin_convergence_year_K:          target_pretax_operating_margin
  Terminal:                               target_pretax_operating_margin
```

### 6.3 Operating income
```
operating_income_year_t = revenue_year_t × operating_margin_year_t
```

Base year:
```
operating_income_base = reported_ebit
                      + (has_leases ? adjustment_to_ebit_from_leases : 0)
                      + (has_rd ? adjustment_to_ebit_from_rd : 0)
```

### 6.4 Tax rate path
```
tax_rate_year_t:
  1 ≤ t ≤ 5:                          effective_tax_rate
  5 < t ≤ 10:                         tax_rate_year_{t-1} + (tax_terminal - effective) / 5
  Terminal:                           IF override_tax_convergence: effective_tax_rate
                                       ELSE: marginal_tax_rate
```

### 6.5 NOL carryforward (dynamic)
```
nol_start_year_1 = IF override_nol: nol_amount  ELSE: 0

For t = 1..10, terminal:
  nol_end_year_t =
    IF operating_income_year_t < 0:
      nol_end_{t-1} - operating_income_year_t           # grows by loss
    ELIF nol_end_{t-1} > operating_income_year_t:
      nol_end_{t-1} - operating_income_year_t           # partial consumption
    ELSE:
      0                                                   # fully consumed
```

### 6.6 NOPAT (NOL-aware)
```
nopat_year_t:
  IF operating_income_year_t > 0:
    IF operating_income_year_t < nol_end_{t-1}:
      operating_income_year_t                          # zero tax
    ELSE:
      operating_income_year_t - (operating_income_year_t - nol_end_{t-1}) × tax_rate_year_t
  ELSE:
    operating_income_year_t                            # operating loss, no tax
```

Equivalently: `taxable_income_year_t = max(0, operating_income_year_t - nol_end_{t-1})`; `tax = taxable × rate`; `nopat = operating_income - tax`.

### 6.7 Reinvestment (Sales-to-Capital with lag)

```
k = reinvestment_lag_years
    (default = 1 unless override_reinvestment_lag, in which case user's B68 value ∈ {0, 2, 3})

sales_to_capital_year_t:
  1 ≤ t ≤ 5:    sales_to_capital_ratio_years_1_5
  6 ≤ t ≤ 10:   sales_to_capital_ratio_years_6_10

For t = 1..10:
  reinvestment_year_t =
    IF k == 0:  (revenue_year_t - revenue_year_{t-1}) / sales_to_capital_year_t
    IF k == 1:  (revenue_year_{t+1} - revenue_year_t) / sales_to_capital_year_t
    IF k == 2:  (revenue_year_{t+2} - revenue_year_{t+1}) / sales_to_capital_year_t
    IF k == 3:  (revenue_year_{t+3} - revenue_year_{t+2}) / sales_to_capital_year_t

# Edge case: for k ≥ 2 in years 9 or 10, we need revenue past year 11.
# Extrapolate at terminal growth:
#   revenue_year_11 = revenue_year_terminal = revenue_year_10 × (1 + g_terminal)
#   revenue_year_12 = revenue_year_11 × (1 + g_terminal)
#   revenue_year_13 = revenue_year_12 × (1 + g_terminal)
```

### 6.8 Terminal reinvestment
```
reinvestment_terminal =
  IF g_terminal > 0:
    (g_terminal / roic_terminal) × nopat_terminal      # RIR × NOPAT
  ELSE:
    0
```

### 6.9 FCFF
```
fcff_year_t = nopat_year_t - reinvestment_year_t
fcff_terminal = nopat_terminal - reinvestment_terminal
```

---

## 7. Terminal Value

Gordon growth formula applied at end of year 10:
```
terminal_value = fcff_terminal / (wacc_terminal - g_terminal)
```

**Requires:** `wacc_terminal > g_terminal` (else undefined / infinite). Enforce `g_terminal ≤ riskfree_rate` upstream.

---

## 8. Discounting to Present Value

**WACC path:**
```
wacc_year_t:
  1 ≤ t ≤ 5:     wacc_initial                                          (from §5)
  6 ≤ t ≤ 10:    prev_wacc - (wacc_year_5 - wacc_terminal) / 5
  Terminal:      wacc_terminal

wacc_terminal:
  IF override_cost_of_capital_stable:   cost_of_capital_stable_override
  ELIF override_riskfree:               riskfree_after_yr10 + mature_market_erp
  ELSE:                                 riskfree_rate + mature_market_erp
```

Where `mature_market_erp` is the Damodaran base US ERP (Country ERP!B1), currently ~4.33% at 2023 calibration. Refresh annually from dataset.

**Cumulative discount factor (year-by-year product, NOT closed form):**
```
cumulative_discount_factor_year_0 = 1
cumulative_discount_factor_year_t = cumulative_discount_factor_year_{t-1} × 1 / (1 + wacc_year_t)
```

**Present values:**
```
pv_fcff_year_t = fcff_year_t × cumulative_discount_factor_year_t    for t = 1..10
pv_terminal    = terminal_value × cumulative_discount_factor_year_10

value_as_going_concern = Σ_{t=1..10} pv_fcff_year_t + pv_terminal
```

---

## 9. Failure Probability Overlay

**Applied to `value_as_going_concern` BEFORE the equity bridge** (not after).

```
p_failure = IF override_failure_probability: failure_probability  ELSE: 0

distress_proceeds =
  IF failure_tie_to == "B":
    (bv_equity_reported + bv_debt_reported) × distress_proceeds_pct
  ELSE:  # "V" or default
    value_as_going_concern × distress_proceeds_pct

value_of_operating_assets =
  value_as_going_concern × (1 - p_failure)
  + distress_proceeds × p_failure
```

**Probability selection:** analyst reads the Failure Rate worksheet (rating-based or age+industry-based reference tables, BLS data) and manually enters `failure_probability` into Input!B63. No automated derivation.

---

## 10. Equity Bridge and Per-Share Value

```
debt_total = bv_debt + (has_leases ? debt_value_of_operating_leases : 0)

cash_usable =
  IF override_trapped_cash (case-insensitive "YES" / "Yes"):
    cash_and_marketable_securities - trapped_cash_amount × (tax_rate_marginal - trapped_cash_tax_rate)
  ELSE:
    cash_and_marketable_securities

value_of_equity =
  value_of_operating_assets
  - debt_total
  - minority_interests
  + cash_usable
  + cross_holdings

value_of_all_options =
  IF has_options_outstanding:
    value_from_dilution_adjusted_bsm       # §11
  ELSE:
    0

value_of_equity_in_common = value_of_equity - value_of_all_options

value_per_share = value_of_equity_in_common / shares_outstanding
```

---

## 11. Options Dilution

Iterative dilution-adjusted Black-Scholes. Converges in 3–5 iterations typically.

```
# Initial seed
stock_price_seed = current_stock_price    # Ginzu uses MARKET price, not intrinsic
                                           # (our engine currently uses intrinsic pre-options; see §15)
adjusted_K = strike_price                  # no adjustment to strike
variance = stddev_stock_price^2

# Fixed-point iteration
call_value = initial_guess                 # 0 is fine; converges quickly
repeat until |call_value_new - call_value_old| < tolerance:
  adjusted_S = (stock_price_seed × shares_outstanding + call_value × n_warrants)
               / (shares_outstanding + n_warrants)
  d1 = [ ln(adjusted_S / adjusted_K) + (riskfree_rate - dividend_yield + variance/2) × T ]
       / (stddev × sqrt(T))
  d2 = d1 - stddev × sqrt(T)
  call_value = adjusted_S × exp(-dividend_yield × T) × N(d1)
             - adjusted_K × exp(-riskfree_rate × T) × N(d2)

value_of_all_options = call_value × n_warrants
```

---

## 12. Invested Capital and ROIC Path

**Invested capital base:**
```
invested_capital_base =
  bv_equity
  + bv_debt
  - cash_and_marketable_securities
  + (has_leases ? debt_value_of_operating_leases : 0)
  + (has_rd    ? value_of_research_asset         : 0)
```

**Year-by-year:**
```
invested_capital_year_t = invested_capital_year_{t-1} + reinvestment_year_t    for t = 1..10
```

**ROIC path:**
```
roic_year_0 = operating_income_base × (1 - effective_tax_rate) / invested_capital_base
roic_year_t = nopat_year_t / invested_capital_year_{t-1}                         for t = 1..10

roic_terminal:
  IF override_roic_stable:  roic_stable_override
  ELSE:                     wacc_terminal          # no excess returns in stable growth
```

---

## 13. Diagnostics

Metrics helpful for sanity-checking a valuation:

```
pv_of_nopat_10yr              = Σ_{t=1..10} nopat_year_t × cumulative_discount_factor_t
pv_of_fcff_10yr               = Σ_{t=1..10} fcff_year_t × cumulative_discount_factor_t
value_effect_of_reinvestment  = pv_of_nopat_10yr - pv_of_fcff_10yr

growth_rate_1yr               = revenue_year_0 / revenue_year_{-1} - 1
growth_rate_5yr_cagr          = (revenue_year_0 / revenue_year_{-5})^(1/5) - 1
```

Sanity invariants (per textbook Section 15):
- `g_terminal ≤ riskfree_rate`
- `wacc_terminal > g_terminal`
- `roic_terminal ≥ wacc_terminal` (if excess returns are expected at maturity)
- `cost_of_debt_aftertax < wacc < cost_of_equity`
- `pv_of_terminal_value / value_as_going_concern ∈ [0.4, 0.85]` (terminal tail sanity)

---

## 14. Feedback Loops

Three circular references must be handled:

**Loop 1 — Synthetic rating ↔ Kd ↔ WACC:**
- Adjusted EBIT → interest coverage → synthetic rating → company spread → Kd → WACC
- Adjusted EBIT does not depend on WACC in canonical single-pass, so this loop is one-way (no iteration strictly required). BUT if synthetic rating is active, WACC and Kd must be re-derived when adjusted EBIT changes.

**Loop 2 — Option dilution ↔ equity per share:**
- Call value → adjusted stock price → call value (§11 iterative block).
- Required fixed-point iteration.

**Loop 3 — Cost of debt ↔ lease conversion:**
- Lease PV uses `cost_of_debt_pretax` as discount rate.
- Lease PV affects adjusted EBIT (via depreciation), which is used in synthetic rating.
- If synthetic rating is active, this creates a second-order loop. Typically converges in 1–2 iterations.

Ginzu closes all three via Excel's iterative calculation. Our engine must implement them explicitly.

---

## 15. Ginzu Quirks to NOT Replicate

Found during Stage 4 walk, these are errors or awkward design choices in the NVIDIA Ginzu workbook. Do NOT copy them:

1. **Margin formula D4 bug:** references `$C$15` (AI segment margin, in the NVIDIA-specific overlay) instead of `$C$4` (canonical year-1 margin). Masked in NVIDIA sample because both equal 0.65. **Our implementation must use `operating_margin_next_year` universally.**

2. **Terminal ROIC default #REF! error (M59):** when `override_roic_stable = "No"`, Ginzu's formula references a broken cell. Masked in NVIDIA sample because the override was "Yes". **Our default should be `wacc_terminal` (no excess returns).**

3. **"YES" vs "Yes" case inconsistency:** trapped cash flag (B81) checks for `"YES"` (all caps); all other override flags check for `"Yes"`. **Our engine accepts case-insensitively.**

4. **S/C path off-by-one (G57):** year 5 reads `sales_to_capital_ratio_years_6_10` instead of years_1_5. Masked when both values are equal. **Our implementation:** years 1–5 use `sales_to_capital_ratio_years_1_5`, years 6–10 use `sales_to_capital_ratio_years_6_10`.

5. **Beta dispatch missing Direct Input branch (B23):** "Direct Input" for unlevered beta falls through to Multibusiness(Global) computation. **Our implementation must properly handle the Direct Input option for unlevered beta (in addition to the levered beta Direct Input path which does work).**

6. **Hard-coded 3.88% in Approach 2:** represents the Damodaran 2023-edition base US RF. **Our implementation must refresh this annually from the Damodaran dataset metadata, not hard-code.**

7. **Approach 3 lacks RF adjustment:** Approach 2 subtracts the Damodaran-base RF then adds the user's RF, but Approach 3 does neither. **Apply the same RF adjustment pattern to Approach 3 when implementing — document as deviation from Ginzu.**

---

## Appendix: Canonical compute formula count

Derived from the canonical single-segment paths across all stages:

| Stage | Compute formulas |
|---|---:|
| §1 Inputs | 1 (B27 default) |
| §2 LTM | 1 per flow item (multiply out by ~10 items) |
| §3 R&D | ~45 (N iterations × fields) |
| §4 Leases | ~20 |
| §5 WACC Approach 1 | ~50 |
| §6 DCF | ~110 (10 years × 11 rows) |
| §7 Terminal | 1 |
| §8 PV | ~30 (10 years × 3) |
| §9 Failure | 4 |
| §10 Bridge | 10 |
| §11 Options (iterative, ~5 iters × 8 cells) | 40 |
| §12 IC + ROIC | ~30 |
| §13 Diagnostics | ~6 |
| **Total canonical** | **≈ 350 formulas** |

**This is the minimum complete Damodaran FCFF valuation.** Our engine currently implements approximately 30% of this correctly (§§2, 3, 4, 5.1 basic, 7, 10 partial, 11 non-iterative). Phase 1 of `project_plan_v2.md` closes the §6 (DCF projection) and §9, §10 completion gaps. Phase 2 closes §11 (iteration) and §5.2 (synthetic rating). Phase 3 closes §5.1 full variants.

---

*End of `ginzu_spec_v2.md`. See `docs/textbook_corrections.md` for textbook-vs-Ginzu delta and `docs/project_plan_v2.md` for the implementation roadmap.*
