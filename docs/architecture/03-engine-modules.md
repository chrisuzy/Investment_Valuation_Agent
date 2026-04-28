# Valuation Engine — Module Design

## Overview

The valuation engine is a pure Python package with zero web framework dependencies. Each module is a stateless function that takes typed Pydantic inputs and returns typed outputs. The orchestrator chains them together.

```
engine/
├── __init__.py
├── data_dictionary.py       # All Pydantic model definitions
├── module_0_data_fetch.py   # Orchestrates CapIQ + Damodaran data retrieval
├── module_1_adjustments.py  # R&D capitalization + operating lease conversion
├── module_2_risk.py         # Beta, Cost of Equity, WACC
├── module_3_cashflow.py     # FCFF, FCFE, ROIC, growth rates
├── module_4_dcf.py          # Terminal value, DCF bridge
├── module_5_multiples.py    # Intrinsic multiples
├── module_6_options.py      # Black-Scholes, final per-share value
├── orchestrator.py          # Pipeline runner with incremental recomputation
└── utils.py                 # PV calculation, normal CDF, shared math
```

---

## Module 0: Data Fetch

**Purpose:** Given a ticker, retrieve all required data from Capital IQ and Damodaran.

**Function signature:**
```python
def fetch_company_data(
    ticker: str,
    capiq_driver: CapIQAdapter,      # COM automation or manual upload adapter
    damodaran_store: DamodaranStore,  # Pre-loaded Damodaran datasets
    industry_override: str | None = None  # User can override auto-mapping
) -> CompanyValuationInput:
```

**Logic:**
1. Call `capiq_driver.fetch(ticker, years=5)` → `RawFinancials[]` + `AdjustmentInputs`
2. From CapIQ data, extract SIC/GICS sector code
3. Map sector → Damodaran industry (via `industry_mapper.json`, or use `industry_override`)
4. Call `damodaran_store.lookup_industry(industry_name)` → `IndustryData`
5. Call `damodaran_store.lookup_macro(country)` → `MacroInputs`
6. Return bundled `CompanyValuationInput`

---

## Module 1: Financial Adjustments

**Purpose:** Capitalize R&D expenses as an asset. Convert operating leases to debt. Adjust EBIT, Net Income, Book Equity, and Market Debt.

**Function signature:**
```python
def compute_adjustments(
    raw: RawFinancials,
    adj_inputs: AdjustmentInputs,
    cost_of_debt_pretax: float  # Needed for lease PV discounting
) -> AdjustedFinancials:
```

**Formulas (from PRD):**

### R&D Capitalization
```
unamortized_r_and_d = Σ(r_and_d_expense_past_t[t] × (n - t) / n) for t=1..n
value_of_research_asset = r_and_d_expense_current + unamortized_r_and_d
amortization_r_and_d = Σ(r_and_d_expense_past_t[t] / n) for t=1..n
adjusted_ebit = ebit + r_and_d_expense_current - amortization_r_and_d
adjusted_net_income = net_income + r_and_d_expense_current - amortization_r_and_d
adjusted_bv_equity = bv_equity + value_of_research_asset
```

### Operating Lease Capitalization
```
pv_of_operating_leases = Σ(commitment_t / (1 + cost_of_debt_pretax)^t)
adjusted_mv_debt = mv_debt + pv_of_operating_leases
imputed_interest = pv_of_operating_leases × cost_of_debt_pretax
adjusted_ebit += operating_lease_expense_current - (operating_lease_expense_current - imputed_interest)
         (≈ adjusted_ebit += imputed_interest)
```

**Test:** For AAPL, `adjusted_ebit > ebit` (R&D add-back exceeds amortization for growing R&D).

---

## Module 2: Risk & Cost of Capital

**Purpose:** Compute levered beta, cost of equity, after-tax cost of debt, and WACC.

**Function signature:**
```python
def compute_cost_of_capital(
    adjusted: AdjustedFinancials,
    macro: MacroInputs,
    industry: IndustryData,
    mv_equity: float
) -> CostOfCapital:
```

**Formulas:**
```
d_e_ratio = adjusted_mv_debt / mv_equity
beta_l = beta_u × (1 + (1 - tax_rate_marginal) × d_e_ratio)
cost_of_equity = risk_free_rate + (beta_l × equity_risk_premium)
cost_of_debt_aftertax = cost_of_debt_pretax × (1 - tax_rate_marginal)
weight_equity = mv_equity / (mv_equity + adjusted_mv_debt)
weight_debt = adjusted_mv_debt / (mv_equity + adjusted_mv_debt)
wacc = (cost_of_equity × weight_equity) + (cost_of_debt_aftertax × weight_debt)
```

**Constraint:** `cost_of_debt_aftertax < wacc < cost_of_equity` (sanity check).

---

## Module 3: Cash Flow & Growth

**Purpose:** Compute reinvestment, free cash flows (FCFF/FCFE), return metrics (ROIC/ROE), and fundamental growth rates.

**Function signature:**
```python
def compute_cashflow_and_growth(
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    adj_inputs: AdjustmentInputs,
    cost_of_capital: CostOfCapital,
    raw_prior_year: RawFinancials  # For invested capital (beginning of period)
) -> CashFlowMetrics:
```

**Formulas:**
```
adjusted_capex = capex + r_and_d_expense_current
adjusted_d_a = d_a + amortization_r_and_d
reinvestment_firm = adjusted_capex - adjusted_d_a + change_in_noncash_wc
reinvestment_equity = reinvestment_firm - net_debt_issued

fcff = adjusted_ebit × (1 - tax_rate_marginal) - reinvestment_firm
fcfe = adjusted_net_income - reinvestment_equity

adjusted_invested_capital = adjusted_bv_equity(prior) + bv_debt(prior) - cash(prior)
roic = (adjusted_ebit × (1 - tax_rate_marginal)) / adjusted_invested_capital
roe = adjusted_net_income / adjusted_bv_equity(prior)

rir_firm = reinvestment_firm / (adjusted_ebit × (1 - tax_rate_marginal))
rir_equity = reinvestment_equity / adjusted_net_income

expected_growth_ebit = roic × rir_firm
expected_growth_ni = roe × rir_equity
```

**Constraint:** `expected_growth_ebit == roic × rir_firm` (identity check).

---

## Module 4: Intrinsic Valuation (DCF)

**Purpose:** Project future cash flows, compute terminal value, discount to present, bridge from firm value to equity value.

**Function signature:**
```python
def compute_dcf(
    cf_metrics: CashFlowMetrics,
    cost_of_capital: CostOfCapital,
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    assumptions: ValuationAssumptions
) -> DCFResult:
```

**Formulas:**

### High-growth period projection (years 1..n)
```
For each year t:
  ebit_t = ebit_{t-1} × (1 + expected_growth_ebit)
  fcff_t = ebit_t × (1 - tax_rate_marginal) × (1 - rir_firm)
```

### Terminal value
```
Constraints:
  stable_growth_rate <= risk_free_rate
  roic_stable = wacc_stable  (excess returns vanish)
  rir_firm_stable = stable_growth_rate / roic_stable

fcff_n_plus_1 = ebit_n × (1 + stable_growth_rate) × (1 - tax_rate_marginal) × (1 - rir_firm_stable)
terminal_value_firm = fcff_n_plus_1 / (wacc_stable - stable_growth_rate)
```

### Present value summation
```
value_of_operating_assets = Σ(fcff_t / (1 + wacc)^t) + terminal_value_firm / (1 + wacc)^n
value_of_equity = value_of_operating_assets + cash_and_marketable_securities - adjusted_mv_debt
value_per_share_pre_options = value_of_equity / shares_outstanding
```

---

## Module 5: Relative Valuation (Multiples)

**Purpose:** Compute intrinsic (fundamental-justified) multiples and compare with market multiples.

**Function signature:**
```python
def compute_multiples(
    adjusted: AdjustedFinancials,
    raw: RawFinancials,
    cf_metrics: CashFlowMetrics,
    cost_of_capital: CostOfCapital,
    assumptions: ValuationAssumptions
) -> MultiplesResult:
```

**Formulas:**
```
# Equity multiples
payout_ratio = 1 - rir_equity
pe_ratio_intrinsic = payout_ratio / (cost_of_equity - stable_growth_rate)
pbv_ratio_intrinsic = (roe - stable_growth_rate) / (cost_of_equity - stable_growth_rate)

# Firm value multiples
after_tax_margin = (adjusted_ebit × (1 - tax_rate_marginal)) / revenues
ev_sales_intrinsic = after_tax_margin × (1 - rir_firm) / (wacc - stable_growth_rate)
ev_ebitda_intrinsic = ((1 - tax_rate_marginal) - (d_a/ebitda × (1 - tax_rate_marginal)) - reinvestment_firm/ebitda) / (wacc - stable_growth_rate)

# Market comparison
pe_ratio_market = mv_equity / adjusted_net_income  (or net_income)
```

**Output:** Side-by-side comparison showing whether the stock's market multiples are higher or lower than fundamentals justify.

---

## Module 6: Options Pricing & Final Value

**Purpose:** Price employee stock options using Black-Scholes, adjust equity value for dilution.

**Function signature:**
```python
def compute_options_and_final_value(
    dcf_result: DCFResult,
    option_inputs: OptionInputs
) -> FinalValuation:
```

**Formulas (Black-Scholes):**
```
d1 = (ln(S/K) + (r - y + σ²/2) × t) / (σ × √t)
d2 = d1 - σ × √t

call_value = S × e^(-y×t) × N(d1) - K × e^(-r×t) × N(d2)

value_of_options = call_value × number_of_options
value_per_share = (value_of_equity - value_of_options) / shares_outstanding
```

Where `N(x)` is the standard normal CDF (from `scipy.stats.norm.cdf`).

---

## Orchestrator

**Purpose:** Chain all modules, support incremental recomputation.

**Function signature:**
```python
def run_full_valuation(ticker: str, ...) -> ValuationReport:
```

**Incremental recomputation logic:**
```
When user edits a variable:
  1. Identify which module owns this variable
  2. Re-run that module and all downstream modules
  3. Return updated ValuationReport

Module dependency: M0 → M1 → M2 → M3 → {M4, M5, M6}

Edit in M2 input → re-run M2, M3, M4, M5, M6
Edit in M4 assumption → re-run M4, M6 only
Edit in M5 → re-run M5 only (no downstream)
```
