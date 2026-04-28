# Atom-Level Codebase Audit

> **⚠️ SUPERSEDED (2026-04-28)** — this audit was performed against `docs/valuation_framework_textbook.md`, which has since been found to contain divergences from the authoritative Ginzu workbook. See `docs/ginzu_spec_v2.md` for the reconciled spec, `docs/textbook_corrections.md` for the per-item textbook divergences, and `docs/project_plan_v2.md` for the revised implementation plan. This file is kept as a historical record.

**Scope:** every data dictionary field, every formula, every CIQ mnemonic, every Damodaran parser field, every engine line, every frontend data reference — all compared against `docs/valuation_framework_textbook.md`.

**Legend:**
- ✅ matches textbook and works correctly
- ⚠️ present but partial / uses wrong input / incomplete
- ❌ missing entirely
- 🔴 present but produces wrong number
- 🔵 present in code; not used downstream (dead)

---

## Part 1 — Data Dictionary Field-by-Field Audit

Every field in `backend/engine/data_dictionary.py` cross-referenced against: (a) textbook usage, (b) what populates it, (c) what reads it downstream.

### A. MacroInputs

| Field | Populated by | Read by | Textbook role | Status |
|---|---|---|---|---|
| `risk_free_rate` | `routes.py` (user-provided) | M2 (`cost_of_equity`), M4 (terminal g default) | Stage 3i, 6 | ✅ |
| `equity_risk_premium` | Damodaran country parser | M2 (`cost_of_equity`) | Stage 3b | ✅ |
| `country_risk_premium` | Damodaran country parser | M2 (additive to ERP) | Stage 3b variant | ✅ |
| `tax_rate_marginal` | `routes.py` / macro default | M2 (`cost_of_debt_aftertax`, `beta_l`), M4, M5 | Stage 3j, 5 | ✅ |
| `tax_rate_effective` | **Never set by M0** | **Never read** | Stage 5d (tax convergence) | 🔵 dead field |
| `default_spread` | Damodaran country parser | M2 fallback for Kd | Stage 3c | ⚠️ fallback-only |

**Gap:** `tax_rate_effective` exists on MacroInputs but `CompanyValuationInput.effective_tax_rate_ciq` is where the CIQ value actually lives. Two separate fields for the same concept — confusing.

### B. RawFinancials (per year)

| Field | Populated by | Read by engine | Textbook role | Status |
|---|---|---|---|---|
| `fiscal_year` | M0 via CIQ | display | label | ✅ |
| `revenues` | CIQ `IQ_TOTAL_REV` | M4 (revenue projection base), M3, M5 (margin) | Stage 1 | ✅ |
| `ebit` | CIQ `IQ_EBIT` | M1 (`capitalize_operating_leases` input), M3 (via adjusted) | Stage 1 | ✅ |
| `ebitda` | CIQ `IQ_EBITDA` | M5 (EV/EBITDA) | Stage 5 (multiples) | ✅ |
| `net_income` | CIQ `IQ_NI` | M1 adjustment, M5 | Stage 2a | ✅ |
| `interest_expense` | CIQ `IQ_INTEREST_EXP` | **No engine module reads this** for synthetic rating | Stage 3c | 🔵 (fetched, never used in engine) |
| `capex` | CIQ `IQ_CAPEX` | M3 (accounting reinvestment) | Stage 5g (but Ginzu uses S/C method, not capex) | ⚠️ used in wrong method |
| `d_a` | CIQ `IQ_DA_CF` | M3 (accounting reinvestment) | Stage 5g (but Ginzu uses S/C method) | ⚠️ |
| `noncash_wc` | Not populated by CIQ | Not read | Stage 5g | 🔵 dead |
| `change_in_noncash_wc` | Not populated by CIQ | M3 (accounting reinvestment) | Stage 5g | 🔵 nil-populated |
| `net_debt_issued` | Not populated by CIQ | M3 (FCFE calculation) | FCFE (non-Ginzu) | 🔵 nil-populated |
| `cash_and_marketable_securities` | CIQ `IQ_CASH_EQUIV` | M4 (equity bridge) | Stage 9 | ✅ |
| `bv_equity` | CIQ `IQ_TOTAL_EQUITY` | M1 (adjustment) | Stage 2a | ✅ |
| `bv_debt` | CIQ `IQ_TOTAL_DEBT` | M1 (MV_debt base) | Stage 3d | ⚠️ used as-is, no bond pricing |
| `mv_equity` | CIQ `IQ_MARKETCAP` | M2 (weights), M5 (market PE) | Stage 3e | ✅ |
| `mv_debt` | Populated = bv_debt initially | Stage 3d should override | Stage 3d | ❌ no bond repricing logic |
| `shares_outstanding` | CIQ `IQ_TOTAL_OUTSTANDING_FILING_DATE` | M4 (per share), M6 | Stage 9, 10 | ✅ |
| `stock_price` | CIQ `IQ_CLOSEPRICE` | Display + frontend comparison | Stage 10 | ✅ |
| `cross_holdings` | CIQ `IQ_LT_INVEST` | **Not read in equity bridge** | Stage 9 | 🔴 fetched, never applied |
| `minority_interests` | CIQ `IQ_MINORITY_INTEREST` | **Not read in equity bridge** | Stage 9 | 🔴 fetched, never applied |
| `r_and_d_expense` | CIQ `IQ_RD_EXP` (+ fallback) | Passed to `adjustment_inputs` | Stage 2a | ✅ |
| `earnings_before_tax` | CIQ `IQ_EBT_EXCL` | **Not read by engine** | Stage 5e (tax base check) | 🔵 dead |
| `total_tax_expense` | CIQ `IQ_INC_TAX` | **Not read by engine** (only frontend display) | Stage 5d effective tax | 🔵 dead |

**Major finding:** 8 fields are populated but never consumed by the engine. Most critically: `cross_holdings`, `minority_interests`, `interest_expense` (for synthetic rating), `total_tax_expense` (for effective tax).

### C. AdjustmentInputs

| Field | Populated by | Read by | Textbook role | Status |
|---|---|---|---|---|
| `amortization_period_n` | Default 5 or user | M1 | Stage 2a | ✅ |
| `r_and_d_expense_current` | CIQ FY-0 R&D | M1 | Stage 2a | ✅ |
| `r_and_d_expense_past` | CIQ FY-1..FY-N R&D | M1 | Stage 2a | ✅ |
| `operating_lease_expense_current` | CIQ `IQ_OPERATING_LEASE_PAYMENTS` | M1 | Stage 2b | ✅ |
| `operating_lease_commitments` | CIQ lease footnote mnemonics | M1 | Stage 2b | ✅ |
| `has_r_and_d` | derived from R&D values | M1 gate | — | ✅ |
| `has_operating_leases` | derived from commitments | M1 gate | — | ✅ |

**Status: ✅ All fields fully utilized.**

### D. AdjustedFinancials

| Field | Populated by | Read by | Textbook role | Status |
|---|---|---|---|---|
| `unamortized_r_and_d` | M1 | M3 (via value_of_research_asset) | Stage 2a | ✅ |
| `amortization_r_and_d` | M1 | M3 (`adjusted_d_a`) | Stage 2a, 5g | ✅ |
| `value_of_research_asset` | M1 | M3 (IC calc) | Stage 2a | ✅ |
| `pv_of_operating_leases` | M1 | M2 (adjusted MV debt) | Stage 2b | ✅ |
| `depreciation_on_lease_asset` | M1 | **Never read by M3 or M4** | Stage 2b → Stage 5g (add to D&A) | 🔵 dead |
| `lease_adjustment_to_ebit` | M1 | — (already folded into adjusted_ebit) | Stage 2b | ✅ |
| `lease_years_total` | M1 | — (display only) | Stage 2b | ✅ |
| `lease_n_additional_years` | M1 | — (display only) | Stage 2b | ✅ |
| `adjusted_ebit` | M1 | M2, M3, M4 | Stage 2 | ✅ |
| `adjusted_net_income` | M1 | M3, M5 | Stage 2a | ✅ |
| `adjusted_bv_equity` | M1 | M3 (IC calc) | Stage 2a | ✅ |
| `adjusted_mv_debt` | M1 (= bv_debt + PV_leases) | M2 (weights), M4 (equity bridge) | Stage 3d | ⚠️ book not market |

**Gap:** `depreciation_on_lease_asset` should be added to `adjusted_d_a` in M3 (currently only R&D amortization is added). Not doing so understates D&A slightly for lease-heavy firms.

### E. IndustryData

| Field | Populated by | Read by | Textbook role | Status |
|---|---|---|---|---|
| `industry_name` | M0 via IndustryMapper | Display | — | ✅ |
| `region` | M0 | Display | — | ✅ |
| `beta_u` | Damodaran `betas.xls` | M2 | Stage 3a | ✅ |
| `beta_u_corrected_for_cash` | Damodaran `betas.xls` | M2 (preferred over raw beta_u) | Stage 3a | ✅ |
| `industry_d_e_ratio` | Damodaran | Display, reference | — | ⚠️ not used in WACC |
| `industry_effective_tax_rate` | Damodaran | Display | — | ✅ |
| `cost_of_equity` | Damodaran | Display, reference | — | ✅ |
| `cost_of_debt_pretax` | Damodaran | M2 fallback for Kd | Stage 3c fallback | ✅ |
| `wacc` | Damodaran | Display, M2 Alt approach 2 (not implemented) | — | ⚠️ |
| `pretax_operating_margin` | Damodaran | Display | — | ✅ |
| `after_tax_operating_margin` | Damodaran | Display | — | ✅ |
| `sales_to_capital` | Damodaran | Display, **should feed Stage 5g but doesn't** | Stage 5g | 🔵 loaded, not used in engine |
| `revenue_growth` | Damodaran | Display | — | ✅ |
| `std_dev_stock` | Damodaran | **Should feed M6 options but doesn't** | Options | 🔵 loaded, M6 reads OptionInputs instead |
| `roic` | Damodaran | Display | — | ✅ |
| `ev_ebitda`, `ev_sales`, `pe_ratio`, `pbv_ratio` | Damodaran | Display | — | ✅ |

**Key gap:** industry `sales_to_capital` is loaded but the DCF engine doesn't use it. When user leaves `assumptions.sales_to_capital_high` blank, it should default to this industry value.

### F. CostOfCapital (M2 output)

| Field | Computed by | Read by | Status |
|---|---|---|---|
| `d_e_ratio` | M2 | — (display only) | ✅ |
| `beta_l` | M2 | — | ✅ |
| `cost_of_equity` | M2 | M5 | ✅ |
| `cost_of_debt_pretax` | M2 | M3 (to derive tax), M5 | ⚠️ M3 reverse-engineers tax from cost_of_debt — brittle |
| `cost_of_debt_aftertax` | M2 | M3, M4 (implicit) | ✅ |
| `weight_equity`, `weight_debt` | M2 | Display | ✅ |
| `wacc` | M2 | M3, M4, M5 | ✅ |

**Minor issue:** M3 derives `tax_rate = 1 − cost_of_debt_aftertax / cost_of_debt_pretax` — fragile when `cost_of_debt_pretax = 0`. Should pass `macro.tax_rate_marginal` directly.

### G. CashFlowMetrics (M3 output)

| Field | Computed by | Read by | Status |
|---|---|---|---|
| `adjusted_capex` | M3 | — (display only) | ✅ |
| `adjusted_d_a` | M3 | — | ✅ |
| `reinvestment_firm` | M3 | — (display; M4 doesn't use it) | 🔵 |
| `reinvestment_equity` | M3 | — (display) | 🔵 |
| `fcff` | M3 | — (display) | ⚠️ M4 recomputes |
| `fcfe` | M3 | — (FCFE path not implemented) | 🔵 |
| `adjusted_invested_capital` | M3 (if prior year available) | — | ⚠️ M4 should use |
| `roic` | M3 | — (display) | 🔵 |
| `roe` | M3 | M5 (PBV intrinsic) | ✅ |
| `rir_firm` | M3 | M4 (used as reinvestment rate) | ⚠️ M4 uses this as fraction instead of Sales-to-Capital |
| `rir_equity` | M3 | M5 (payout ratio) | ✅ |
| `expected_growth_ebit` | M3 (=ROIC×RIR) | M4 (as `growth_rate`) | 🔴 M4 uses this instead of user's revenue_growth_next_year |
| `expected_growth_ni` | M3 | — | 🔵 |

**Critical:** M3 outputs `expected_growth_ebit` (a fundamental growth rate from historical data) and M4 uses it as the projection growth rate, **overriding the user's `assumptions.revenue_growth_next_year`**. This is wrong per the textbook Stage 5a: the user's story should drive projection, not historical ROIC × RIR.

### H. ValuationAssumptions (user story)

| Field | Used in Engine? | Module | Textbook stage |
|---|---|---|---|
| `projection_years` | ✅ | M4 | Stage 5 |
| `high_growth_years` | ✅ | M4 | Stage 5 |
| `stable_growth_rate` | ✅ | M4 | Stage 6 |
| `revenue_growth_next_year` | ⚠️ M4 falls back to growth_rate | M4 | Stage 5a |
| `operating_margin_next_year` | 🔴 Field defined, **never read** | — | Stage 5b |
| `revenue_growth_years_2_5` | 🔴 **Never read** | — | Stage 5a |
| `target_operating_margin` | 🔴 **Never read** | — | Stage 5b |
| `margin_convergence_year` | 🔴 **Never read** | — | Stage 5b |
| `sales_to_capital_high` | 🔴 **Never read** | — | Stage 5g |
| `sales_to_capital_stable` | 🔴 **Never read** | — | Stage 5g |
| `cost_of_capital_stable_override` | ✅ | M4 | Stage 6 |
| `roic_stable_override` | ✅ | M4 | Stage 6 |
| `failure_probability` | ⚠️ Applied but at wrong place | M4 | Stage 8 |
| `distress_proceeds_pct` | ⚠️ Applied but no tie_to variant | M4 | Stage 8 |
| `failure_tie_to` | 🔴 **Never read** | — | Stage 8 |
| `override_reinvestment_lag` | 🔴 **Never read** | — | Stage 5g |
| `reinvestment_lag_years` | 🔴 **Never read** | — | Stage 5g |
| `override_tax_convergence` | 🔴 **Never read** | — | Stage 5d |
| `override_nol` | 🔴 **Never read** | — | Stage 5e |
| `nol_amount` | 🔴 **Never read** | — | Stage 5e |
| `override_riskfree` | 🔴 **Never read** | — | Stage 6 |
| `riskfree_after_yr10` | 🔴 **Never read** | — | Stage 6 |
| `override_growth_perpetuity` | 🔴 **Never read** | — | Stage 6 |
| `growth_perpetuity_rate` | ⚠️ Partially via `stable_growth_rate` | M4 | Stage 6 |
| `override_trapped_cash` | 🔴 **Never read** | — | Stage 9 |
| `trapped_cash_amount` | 🔴 **Never read** | — | Stage 9 |
| `trapped_cash_tax_rate` | 🔴 **Never read** | — | Stage 9 |

**Count: 17 of 27 ValuationAssumptions fields are dead (never read by any module).** This is the single biggest implementation gap.

### I. OptionInputs, FinalValuation, DCFResult, MultiplesResult

- **OptionInputs**: all 6 fields used in M6. ✅
- **FinalValuation**: 3 fields, all computed correctly. ✅
- **DCFResult**: 11 fields; all populated and displayed. ✅
- **MultiplesResult**: 5 fields; all computed. ✅ (but no UI page)

---

## Part 2 — Stage 1 (LTM) Atom-Level

### Textbook formulas

```
LTM_Flow = Last_10K + Current_YTD - Prior_YTD
BS_Value = Most_Recent_10Q_Value
```

### Current implementation (`ltm_calculator.py`)

| Line | Purpose | Textbook-correct? |
|---|---|---|
| 17-21 | FLOW_FIELDS set | ✅ |
| 24-27 | BALANCE_SHEET_FIELDS set | ✅ |
| 54 | `quarters_since = max(0, min(4, months_since_fy_end // 3))` | ✅ |
| 65-80 | Current partial sum (FQ-0..FQ-(n-1)) | ✅ |
| 83-94 | Prior partial sum (FQ-n..FQ-(2n-1)) | ✅ |
| 96 | `result[field] = fy0_val - prior_sum + current_sum` | ✅ |
| 102 | BS uses `quarterly_data[0]` (FQ-0) | ✅ |

**Stage 1 atom-level: ✅ no defects.** 

Potential improvement: the prior partial should be FQ-4 to FQ-(4+n-1) (same calendar quarter one year earlier), which matches Damodaran's exact method. The current implementation uses FQ-n to FQ-(2n-1). For n=1 these are the same; for n=2,3 they're different. Verify by testing with `n=2` (6-month-old 10-K).

**Potential bug:** For n=2, current code sums FQ-0, FQ-1 as current and FQ-2, FQ-3 as prior. Textbook (Damodaran) says prior should be FQ-4, FQ-5. This could be a hidden issue worth verifying with a test.

---

## Part 3 — Stage 2a (R&D) Atom-Level

### Textbook formulas

```
Unamortized_Fraction_t = (N - t) / N       for t = 1..N
Unamortized_Value_t = R&D_past_t × Unamortized_Fraction_t
Amortization_This_Year_t = R&D_past_t / N
Value_of_Research_Asset = R&D_current + Σ Unamortized_Value_t
Total_Amortization = Σ Amortization_This_Year_t
Adjusted_EBIT = EBIT + R&D_current - Total_Amortization
Adjusted_BV_Equity = BV_Equity + Value_of_Research_Asset
Adjusted_Net_Income = Net_Income + R&D_current - Total_Amortization
```

### Current implementation (`module_1_adjustments.py::capitalize_r_and_d()` lines 13-46)

| Line | Code | Matches textbook? |
|---|---|---|
| 37-43 | `t = t_idx + 1; unamortized += rd × (n-t)/n; amortization += rd/n` | ✅ exact |
| 45 | `value_of_research_asset = r_and_d_current + unamortized` | ✅ |

### In `compute_adjustments()` lines 122-140

| Line | Code | Matches textbook? |
|---|---|---|
| 132 | `adjusted_ebit = ebit + r_and_d_current - amortization` | ✅ |
| 136 | `adjusted_net_income = net_income + r_and_d_current - amortization` | ✅ |
| 140 | `adjusted_bv_equity = bv_equity + value_of_research_asset` | ✅ |

**Stage 2a atom-level: ✅ no defects.**

---

## Part 4 — Stage 2b (Leases) Atom-Level

### Textbook formulas

```
Years_Beyond_Five = ROUND(Beyond / AVERAGE(Yr1..Yr5), 0)   (min 1 if beyond > 0)
Annual_Annuity = Beyond / Years_Beyond_Five
PV_Yrs_1_5 = Σ Commitment_t / (1+Kd)^t   for t=1..5
PV_Beyond = (Annuity × [1-(1+Kd)^-Years_Beyond]/Kd) / (1+Kd)^5
Debt_Value = PV_Yrs_1_5 + PV_Beyond
Total_Lease_Years = 5 + Years_Beyond_Five
Depreciation = Debt_Value / Total_Lease_Years
EBIT_Adjustment = Lease_Expense - Depreciation
Debt_Adjustment = Debt_Value
```

### Current implementation (`module_1_adjustments.py::capitalize_operating_leases()` lines 49-91)

| Line | Code | Matches textbook? |
|---|---|---|
| 72-74 | Years 1-5 discounted individually | ✅ |
| 80 | `avg_yr1_5 = sum(...) / n_yr` | ✅ |
| 82 | `n_additional = max(1, round(beyond / avg_yr1_5))` | ✅ (min-1 clause) |
| 85 | `annual_annuity = beyond / n_additional` | ✅ |
| 86-88 | Discount annuity payments at years 6+j | ⚠️ implementation uses yr-by-yr discount instead of annuity formula × yr-5 discount; mathematically equivalent for integer years |
| 90 | `total_years = n_yr + n_additional` | ✅ |

### In `compute_adjustments()` lines 142-170

| Line | Code | Matches textbook? |
|---|---|---|
| 158 | `adjusted_mv_debt = adjusted_mv_debt + pv_of_operating_leases` | ✅ |
| 164 | `depreciation_on_lease_asset = pv / total_years` | ✅ |
| 168 | `lease_adjustment_to_ebit = lease_expense - depreciation` | ✅ |
| 170 | `adjusted_ebit += lease_adjustment_to_ebit` | ✅ |

**Stage 2b atom-level: ✅ no defects.**

---

## Part 5 — Stage 3 (Cost of Capital) Atom-Level

### Sub-step 3a — Unlevered Beta

**Textbook:** 5 variants (Single US, Multi US, Single Global, Multi Global, Direct)

**Current:** `module_2_risk.py:37`
```python
beta_u = industry.beta_u_corrected_for_cash or industry.beta_u
```

| Variant | Supported? |
|---|---|
| Single Business (US) | ✅ via `region='US'` at fetch time |
| Multi Business (US, EV-weighted) | ❌ |
| Single Business (Global) | ✅ via `region='Global'` |
| Multi Business (Global) | ❌ |
| Direct Input | ❌ |

### Sub-step 3b — Equity Risk Premium

**Textbook:** 3 variants (Country of Incorporation, Operating Countries weighted, Operating Regions weighted) + Direct input

**Current:** `module_2_risk.py:41`
```python
erp = macro.equity_risk_premium + macro.country_risk_premium
```

| Variant | Supported? |
|---|---|
| Country of Incorporation | ✅ |
| Operating Countries weighted | ❌ |
| Operating Regions weighted | ❌ |
| Direct input | ❌ |

### Sub-step 3c — Pre-Tax Cost of Debt

**Textbook:** 3 variants (Actual Rating, Synthetic Rating, Direct input)

**Current:** `module_2_risk.py:45`
```python
cost_of_debt_pretax = industry.cost_of_debt_pretax or (macro.risk_free_rate + (macro.default_spread or 0.0))
```

| Variant | Supported? |
|---|---|
| Industry fallback (not in textbook) | ✅ |
| RF + country default spread fallback | ✅ |
| Actual Rating → spread lookup | ❌ — needs `ratings.xls` Damodaran table + rating in input |
| Synthetic Rating → coverage → spread | ❌ — needs `synthrating.xls` + pipeline |
| Direct input | ❌ |

### Sub-step 3d — Market Value of Debt

**Textbook:** `MV_D = Interest × annuity + BV_D / (1+Kd)^n`

**Current:** `module_1_adjustments.py:158` sets `adjusted_mv_debt = raw.mv_debt + pv_of_operating_leases`. Then `raw.mv_debt` is populated as `bv_debt` in most paths. **No bond-repricing logic.**

| Item | Supported? |
|---|---|
| Book debt as MV (current shortcut) | ✅ |
| Bond-priced MV with maturity | ❌ |

### Sub-step 3e — Market Value of Equity

**Textbook:** `shares × price`

**Current:** implicitly computed where needed; stored in `raw.mv_equity` via CIQ.

**Status: ✅**

### Sub-step 3f — Preferred Stock

**Textbook:** add preferred component to WACC.

**Current:** No preferred field in schema. WACC formula is equity + debt only.

**Status: ❌**

### Sub-step 3g — Weights

**Textbook:** each MV / total MV.

**Current:** `module_2_risk.py:53-55`
```python
total_capital = mv_equity + adjusted_mv_debt
weight_equity = mv_equity / total_capital
weight_debt = adjusted_mv_debt / total_capital
```

**Status: ✅** (missing preferred, but otherwise correct)

### Sub-step 3h — Levered Beta

**Textbook:** `β_L = β_U × (1 + (1 - t) × D/E)`

**Current:** `module_2_risk.py:38`
```python
beta_l = beta_u * (1 + (1 - macro.tax_rate_marginal) * d_e_ratio)
```

**Status: ✅**

### Sub-step 3i — Cost of Equity

**Textbook:** `Ke = Rf + β_L × ERP`

**Current:** `module_2_risk.py:42`
```python
cost_of_equity = macro.risk_free_rate + beta_l * erp
```

**Status: ✅**

### Sub-step 3j — After-tax Kd

**Textbook:** `Kd × (1 - t_marginal)`

**Current:** `module_2_risk.py:50`
```python
cost_of_debt_aftertax = cost_of_debt_pretax * (1 - macro.tax_rate_marginal)
```

**Status: ✅**

### Sub-step 3k — WACC

**Textbook:** `w_E × Ke + w_D × Kd_aftertax + w_P × Kp`

**Current:** `module_2_risk.py:58`
```python
wacc = cost_of_equity * weight_equity + cost_of_debt_aftertax * weight_debt
```

**Status: ✅** (preferred term missing)

### Alternate approaches (Industry Average, Regional Decile)

Neither implemented. **❌**

---

## Part 6 — Stage 4 Schema

See Part 1 Section H. **Schema is complete; 17 fields are dead (not read downstream).**

---

## Part 7 — Stage 5 (DCF Projection) ATOM-LEVEL LINE-BY-LINE

This is the biggest defect area. Walking through `module_4_dcf.py` line by line against textbook Stage 5.

### Line 48 — `n = assumptions.projection_years`
**Intent:** total projection years (should be 10)
**Textbook:** explicit 10-year period
**Issue:** Also references `assumptions.high_growth_years` separately later (line 81-86). Creates ambiguity — if `projection_years=10` and `high_growth_years=5`, the transition is years 6-10. Matches textbook.
**Status:** ✅

### Line 49-54 — Stable growth resolution
```python
stable_growth = assumptions.stable_growth_rate
if stable_growth is None:
    stable_growth = macro.risk_free_rate
stable_growth = min(stable_growth, macro.risk_free_rate)
```
**Textbook:** terminal growth resolves as (override_perpetuity → override_riskfree → risk_free). Current: only checks `stable_growth_rate`, ignores the 3 override flags.
**Gap:** `override_growth_perpetuity`, `override_riskfree`, `riskfree_after_yr10` are never read here.
**Status:** ⚠️

### Line 56 — `tax_rate = macro.tax_rate_marginal`
**Textbook Stage 5d:** Years 1-5 effective, years 6-10 convergence, terminal marginal.
**Current:** Single flat rate for all years.
**Gap:** `Effective_Tax_Rate` not read (should use `effective_tax_rate_ciq` field from CompanyValuationInput); no convergence; `override_tax_convergence` ignored.
**Status:** 🔴 wrong. Overstates tax for firms with low effective rate.

### Line 57 — `growth_rate = cf_metrics.expected_growth_ebit or stable_growth`
**Textbook Stage 5a:** Revenue growth from `assumptions.revenue_growth_next_year` (user story). 
**Current:** Uses M3's ROIC × RIR (backward-looking fundamental), **ignoring the user's story**.
**Gap:** 🔴 This is the core Stage 5 defect. Changes the projected revenue path entirely.

### Line 58 — `rir_firm = cf_metrics.rir_firm if ... else 0.5`
**Textbook Stage 5g:** Reinvestment = ΔRevenue / Sales-to-Capital, with lag.
**Current:** Uses RIR as fraction of NOPAT.
**Gap:** 🔴 Wrong mechanic. Produces different reinvestment numbers.

### Line 60-61 — WACC variables
```python
wacc = cost_of_capital.wacc
wacc_stable = assumptions.cost_of_capital_stable_override or wacc
```
**Textbook Stage 5i:** Path from initial WACC to terminal WACC over years 6-10.
**Current:** Single `wacc` used for all projection years; `wacc_stable` only used in Stage 6 (terminal).
**Gap:** No WACC path. Treats WACC as constant years 1-10.

### Line 63-77 — Pre-loop setup
**Sets:** ebit_current, revenue_projections (empty), ebit_prev, rev_prev, rev_growth.
**Status:** OK structurally.

### Line 73-74 — `rev_current = raw.revenues`, `rev_growth = assumptions.revenue_growth_next_year or growth_rate`
**Textbook:** rev_growth should be the user's input, not falling back to computed growth.
**Current:** Falls back to M3's growth_rate if `revenue_growth_next_year` is None (always None in practice because M0 doesn't set it).
**Gap:** User assumption never actually used.

### Line 79-93 — Main projection loop
```python
for t in range(1, n + 1):
    if t <= (assumptions.high_growth_years or n):
        g = growth_rate       # ← same for all years 1-5, using M3's computed rate
        rg = rev_growth       # ← falls back to growth_rate since rev_growth is None
    else:
        # Transition
        transition_years = n - (assumptions.high_growth_years or n)
        if transition_years > 0:
            progress = (t - (assumptions.high_growth_years or n)) / transition_years
            g = growth_rate + (stable_growth - growth_rate) * progress
            rg = rev_growth + (stable_growth - rev_growth) * progress
```

**Textbook:**
- Years 1-5: `revenue_growth_next_year` (single story input)
- Years 2-5: could use `revenue_growth_years_2_5` (often = next_year)
- Years 6-10: linear convergence from yr-5 growth to terminal

**Current:**
- Uses `expected_growth_ebit` for both years 1-5 (should be user input)
- Convergence logic exists but from the wrong starting point
- Transition logic formula `growth_rate + (stable - growth) × progress` is correct in structure

**Gap:** Input source is wrong throughout. `revenue_growth_years_2_5` never consulted.

### Line 95-99 — Core per-year calculation
```python
ebit_t = ebit_prev * (1 + g)       # 🔴 EBIT compounded, not Revenue × Margin
rev_t = rev_prev * (1 + rg)         # Revenue compounded separately
nopat_t = ebit_t * (1 - tax_rate)   # Tax flat (no convergence)
reinvestment_t = nopat_t * rir_firm # 🔴 Wrong reinvestment mechanic
fcff_t = nopat_t - reinvestment_t
```

**Textbook Stage 5c:** `Operating_Income_t = Revenue_t × Operating_Margin_t`.
**Current:** EBIT and Revenue grow independently with different growth rates. Implied margin drifts uncontrollably.

**Gap:** 🔴 EBIT mechanic completely wrong. Should compute margin path (Stage 5b) and multiply Revenue × Margin.

### Line 103 — `df = 1 / (1 + wacc) ** t`
**Textbook Stage 7:** Cumulative discount factor built year-by-year (because WACC varies).
**Current:** Closed-form with constant WACC.
**Gap:** ⚠️ OK today (WACC is constant), but will need fix when WACC convergence is added.

### Line 117 — `roic_stable = assumptions.roic_stable_override or wacc_stable`
**Textbook Stage 6:** Terminal ROIC override; default is WACC (no excess returns).
**Current:** ✅ correct.

### Line 118 — `rir_stable = stable_growth / roic_stable if roic_stable > 0 else 0.0`
**Textbook:** `RIR_terminal = g_terminal / ROIC_terminal`.
**Status:** ✅ correct.

### Line 120-122 — Terminal FCFF
```python
ebit_terminal = ebit_prev * (1 + stable_growth)
nopat_terminal = ebit_terminal * (1 - tax_rate)
fcff_terminal = nopat_terminal * (1 - rir_stable)
```
**Textbook:** `FCFF_terminal = EBIT(1-t) × (1 - RIR)`.
**Current:** matches, but `tax_rate` is the wrong number (should be `tax_rate_marginal` even if years 1-5 had effective; current uses marginal already so OK by coincidence).
**Status:** ✅ coincidentally correct given current simple tax handling.

### Line 124-127 — Terminal Value
```python
if wacc_stable > stable_growth:
    terminal_value_firm = fcff_terminal / (wacc_stable - stable_growth)
else:
    terminal_value_firm = 0.0
```
**Textbook:** Gordon formula with sanity guard.
**Status:** ✅

### Line 129 — `pv_terminal = terminal_value_firm / (1 + wacc) ** n`
**Textbook:** Terminal value discounted at year-10 cumulative factor.
**Current:** Using initial WACC with closed-form discount.
**Gap:** Wrong once WACC converges. For constant WACC, OK.
**Status:** ⚠️

### Line 132-133 — PV summation
```python
pv_cash_flows_sum = sum(pv_fcff)
value_of_operating_assets = pv_cash_flows_sum + pv_terminal
```
**Textbook Stage 7:** `Value_as_Going_Concern = Σ PV_FCFF + PV_TV`.
**Status:** ✅

### Line 136-139 — Equity bridge (Stage 9)
```python
cash = raw.cash_and_marketable_securities or 0.0
debt = adjusted.adjusted_mv_debt or 0.0
value_of_equity = value_of_operating_assets + cash - debt
```

**Textbook Stage 9:**
```
V_equity = V_op_assets - debt - minority_interests + cash_usable + cross_holdings
```

**Current missing:**
- `minority_interests` not subtracted (raw.minority_interests is fetched but not used)
- `cross_holdings` not added (raw.cross_holdings is fetched but not used)
- No trapped-cash logic

**Gap:** 🔴 Three items missing from the equity bridge.

### Line 141-147 — Failure adjustment
```python
if assumptions.failure_probability > 0:
    distress_value = value_of_equity * assumptions.distress_proceeds_pct
    value_of_equity = value_of_equity * (1 - p) + distress_value * p
```

**Textbook Stage 8:**
```
V_op_assets = V_going_concern × (1 - p) + V_distress × p
```
Apply BEFORE the equity bridge, not after. Also needs `failure_tie_to` branching.

**Current:**
- Applied to `value_of_equity` (after bridge) — wrong place
- `failure_tie_to` flag ignored; always uses fair-value path
- Book-value variant (`(BV_eq + BV_debt) × pct`) not implemented

**Gap:** 🔴 Wrong place, missing variant.

### Line 149-150 — Per-share value
```python
shares = raw.shares_outstanding or 1.0
value_per_share = value_of_equity / shares
```
**Textbook Stage 10.**
**Status:** ✅

### Line 152-165 — DCFResult output
All fields populated. ✅

---

## Part 8 — Stages 6, 7, 8, 9, 10 Atom-Level

**Stage 6 (Terminal Value):** ✅ except for 3 ignored override flags (`override_growth_perpetuity`, `override_riskfree`, `riskfree_after_yr10`).

**Stage 7 (Discounting):** ✅ for constant WACC; needs refactor once Stage 5i WACC convergence is added.

**Stage 8 (Failure Probability):** ⚠️ wrong pipeline position + missing `failure_tie_to` book variant.

**Stage 9 (Equity Bridge):** 🔴 missing minority interests, cross-holdings, trapped cash.

**Stage 10 (Per-Share):** ✅.

**Options dilution:** `module_6_options.py:80` uses pre-dilution stock price directly; no iteration loop. 🔴

---

## Part 9 — CIQ Pipeline Atom-Level

### Inventory of CIQ mnemonics in `capiq_formula_map.py`

Every field → mnemonic → is it consumed by engine?

**INCOME_STATEMENT_FIELDS** (all fetched for 10 years annual + 8 quarters):
| Variable | Mnemonic | Consumed by |
|---|---|---|
| revenues | IQ_TOTAL_REV | M3, M4, M5, display |
| ebit | IQ_EBIT | M1 (for leases), M3 via adjusted | ✅ |
| ebitda | IQ_EBITDA | M5 (EV/EBITDA only) | ⚠️ |
| net_income | IQ_NI | M1, M5 | ✅ |
| interest_expense | IQ_INTEREST_EXP | 🔵 never used in engine (synthetic rating not implemented) |
| d_a | IQ_DA_CF | M3 | ⚠️ |
| r_and_d_expense | IQ_RD_EXP | M1 (primary) | ✅ |
| r_and_d_expense_fn | IQ_RD_EXP_FN | M1 (fallback) | ✅ |
| capex | IQ_CAPEX | M3 (accounting method, not Ginzu) | ⚠️ |
| operating_lease_expense | IQ_OPERATING_LEASE_PAYMENTS | M1 via adjustment_inputs | ✅ |
| earnings_before_tax | IQ_EBT_EXCL | 🔵 never used |
| total_tax_expense | IQ_INC_TAX | 🔵 never used |

**BALANCE_SHEET_FIELDS** (10 years annual + FQ-0 point-in-time):
| Variable | Mnemonic | Consumed by |
|---|---|---|
| cash_and_marketable_securities | IQ_CASH_EQUIV | M4 (bridge) | ✅ |
| bv_equity | IQ_TOTAL_EQUITY | M1 | ✅ |
| bv_debt | IQ_TOTAL_DEBT | M1, M2 | ✅ |
| shares_outstanding | IQ_TOTAL_OUTSTANDING_FILING_DATE | M4, M6 | ✅ |
| cross_holdings | IQ_LT_INVEST | 🔴 fetched, never applied in bridge |
| minority_interests | IQ_MINORITY_INTEREST | 🔴 fetched, never applied in bridge |

**MARKET_FIELDS** (current only):
| Variable | Mnemonic | Consumed |
|---|---|---|
| stock_price | IQ_CLOSEPRICE | display | ✅ |
| mv_equity | IQ_MARKETCAP | M2, M5 | ✅ |
| reporting_currency | IQ_FILING_CURRENCY | Display | ✅ |
| primary_exchange | IQ_EXCHANGE | Currency mapping | ✅ |
| effective_tax_rate_ciq | IQ_EFFECT_TAX_RATE | 🔴 fetched, never used in DCF tax path |

**OPTION_FIELDS** (current only): options_outstanding, options_avg_strike, options_avg_maturity — all used in M6. ✅

**LEASE_COMMITMENT_FIELDS**: yr1..yr5 + beyond — all used in M1. ✅

**PERIOD_DATE_FIELDS**: annual + quarterly — used for LTM + display. ✅

### CIQ mnemonics that SHOULD be fetched but aren't

| Variable | Mnemonic | Textbook need |
|---|---|---|
| Geographic segment names | IQ_GEO_SEG_NAME_1..10 | Multi-country ERP (Stage 3b) |
| Geographic segment revenues | IQ_GEO_SEG_REV_1..10 | Same |
| Business segment names | IQ_BUS_SEG_NAME_1..10 | Multi-business beta (Stage 3a) |
| Business segment revenues | IQ_BUS_SEG_REV_1..10 | Same |
| S&P credit rating | IQ_SP_RATING | Rating approach (Stage 3c) |
| Moody's credit rating | IQ_MOODY_RATING | Alt to S&P |
| Stock return std dev | IQ_DAILY_STDDEV or computed from prices | Options (M6) |
| Weighted debt maturity | IQ_AVG_MATURITY or manual | MV Debt (Stage 3d) |
| Preferred stock shares | IQ_PREFERRED_STOCK_OS | Preferred component (Stage 3f) |
| Preferred dividend rate | IQ_PREFERRED_DIVS | Same |
| Non-op assets (beyond IQ_LT_INVEST) | various | Equity bridge |

---

## Part 10 — Damodaran Data Pipeline Atom-Level

### Parsers and fields they extract (`backend/data_sources/damodaran_parsers/`)

| Parser | File | Fields extracted | Used? |
|---|---|---|---|
| `beta_parser.py` | betas.xls (8 regions) | beta_u, beta_u_corrected_for_cash, d_e_ratio, effective_tax_rate, std_dev_stock | beta_u ✅, beta_u_corrected ✅, std_dev_stock 🔵, d_e_ratio 🔵 |
| `wacc_parser.py` | wacc.xls | cost_of_equity, cost_of_debt_pretax, wacc | cost_of_debt_pretax ✅; others displayed only |
| `margin_parser.py` | margin.xls | pretax_operating_margin, aftertax_operating_margin | Display only |
| `taxrate_parser.py` | taxrate.xls | effective_tax_rate_avg | Display |
| `country_risk_parser.py` | ctryprem.xls | equity_risk_premium, country_risk_premium, default_spread | ERP ✅, CRP ✅, default_spread ✅ |
| `country_tax_parser.py` | countrytaxrates.xls | corporate_tax_rate | ✅ |
| `capex_parser.py` | capex.xls | sales_to_capital, capex_to_depreciation | 🔵 loaded, not used in DCF |
| `fundgr_parser.py` | fundgrEB.xls | revenue_growth, ROC, reinvestment_rate | Display |
| `eva_parser.py` | EVA.xls | ROIC, std_dev_stock, cost_of_capital | Display |
| `vebitda_parser.py` | vebitda.xls | ev_ebitda | Display |
| `pedata_parser.py` | pe.xls | pe_ratio, trailing_pe, forward_pe, PEG | Display |
| `pbvdata_parser.py` | pbv.xls | pbv_ratio, ROE | Display |
| `psdata_parser.py` | ps.xls | ev_sales, price_to_sales | Display |

### Damodaran datasets NOT parsed

| File | Purpose | Needed for |
|---|---|---|
| `ratings.xls` | Rating → default spread | Stage 3c actual rating approach |
| `synthrating.xls` | Interest coverage → synthetic rating (small + large) | Stage 3c synthetic approach |
| `cumdefrates.xls` | Default probabilities by rating × horizon | Stage 8 |
| `statsmicro.xls` / `statsmacro.xls` | Industry input distributions | Phase 6 Monte Carlo |
| BLS survival rate by age | Young firm failure rates | Stage 8 |
| "Mature Market ERP" extraction from ctryprem | Terminal WACC when RF override=Yes | Stage 6 |

---

## Part 11 — Frontend Atom-Level

### Data references by page (what data fields each page reads)

#### InputSheet.tsx (811 LOC)
Reads: `data.inputs.raw_financials[...]`, `data.inputs.adjustment_inputs`, `data.inputs.industry_data`, `data.inputs.industry_data_global`, `data.inputs.macro_inputs`, `data.inputs.company_metrics`, `data.inputs.period_dates_annual`, `data.inputs.effective_tax_rate_ciq`, `data.adjusted`.
**Writes back (via patch):** none — view-only
**Gaps:** displays `effective_tax_rate_ciq` but DCF doesn't use it.

#### TrailingTwelveMonth.tsx (282 LOC)
Reads: `data.inputs.raw_financials[0]`, `data.inputs.quarterly_financials`, `data.inputs.quarters_since_10k`, `data.inputs.period_date_10k`, `data.inputs.period_date_10q`.
**Status:** ✅ direct match with LTM calculator.

#### RDConverter.tsx (145 LOC)
Reads: `data.adjusted.unamortized_r_and_d`, `value_of_research_asset`, `amortization_r_and_d`; plus raw R&D history.
**Status:** ✅

#### LeaseConverter.tsx (166 LOC)
Reads: `data.inputs.adjustment_inputs.operating_lease_commitments`, `data.inputs.industry_data.cost_of_debt_pretax`, `data.adjusted.pv_of_operating_leases`, `depreciation_on_lease_asset`, `lease_adjustment_to_ebit`, `lease_years_total`, `lease_n_additional_years`.
**Status:** ✅ full read of adjusted output.

#### SyntheticRating.tsx (83 LOC)
Reads: `data.inputs.raw_financials[0].ebit`, `interest_expense`, `data.adjusted.adjusted_ebit`.
Performs lookup in RATING_TABLE locally. Result never fed back to engine.
**Status:** ⚠️ visual only.

#### CostOfCapital.tsx (160 LOC)
Reads: `data.cost_of_capital.*`, industry data.
**Status:** ✅ displays M2 output.

#### StoriesToNumbers.tsx (135 LOC)
Reads: `data.inputs.valuation_assumptions.*`, `data.inputs.industry_data.*`, `data.inputs.raw_financials[0]`, `data.cost_of_capital.wacc`.
**Status:** ⚠️ static label mapping, no editing.

#### FailureRate.tsx (90 LOC)
Reads: `data.inputs.valuation_assumptions.failure_probability`, `distress_proceeds_pct`, `data.dcf.value_of_operating_assets`.
Performs expected value calc locally; displays rating→default-rate table as static reference.
**Status:** ⚠️ visual only.

#### ValuationOutput.tsx (278 LOC)
Reads: everything from `data.dcf`, `data.final`, plus cost_of_capital, adjusted, raw.
**Status:** ✅ comprehensive display.

#### ValuationPicture.tsx (119 LOC)
Static bridge layout.
**Status:** ⚠️ thin.

#### OptionValue.tsx (213 LOC)
Reads: `data.inputs.option_inputs.*`, `data.final.*`, `data.dcf.value_per_share_pre_options`.
**Status:** ✅

#### Diagnostics.tsx (218 LOC)
Not read yet but likely shows sanity checks. Need audit.

#### AnswerKeys.tsx (97 LOC)
Static summary of key inputs + outputs.
**Status:** ⚠️ thin.

### Missing pages (would read what?)

| Proposed page | Would read |
|---|---|
| Relative Valuation | `data.multiples.*` (already computed, unsurfaced) |
| Summary Sheet | All `data.dcf.*_projections[]` arrays year by year |
| Country Risk Blender | New fetch: `data.inputs.revenue_by_country[]` |
| Industry Averages browser | Damodaran store browse endpoint (none exists) |
| Simulations | Damodaran Input Stat Distributions + new Monte Carlo endpoint |

---

## Part 12 — Atom-Level Implementation Plan

Each task below is a single-function-level edit. Sized for one sitting.

### Phase 1 — Core DCF Correctness

**Task 1.1** — Read `assumptions.operating_margin_next_year` in M4 (currently exists in schema but never touched). Expose as `margin_year_1`.
**File:** `backend/engine/module_4_dcf.py` (add variable near line 65)
**Effort:** 5 min

**Task 1.2** — Build margin path in M4. New function `_margin_path(margin_y1, margin_target, K, years=10) -> list[float]` returning margin for years 1..10.
**File:** `backend/engine/module_4_dcf.py`
**Effort:** 30 min

**Task 1.3** — Replace `ebit_t = ebit_prev × (1 + g)` with `ebit_t = rev_t × margin_t`.
**File:** `module_4_dcf.py:95-96`
**Effort:** 10 min (after 1.2)

**Task 1.4** — Replace `growth_rate = cf_metrics.expected_growth_ebit or stable_growth` with `growth_rate = assumptions.revenue_growth_next_year or cf_metrics.expected_growth_ebit or stable_growth`. Primary source must be user story.
**File:** `module_4_dcf.py:57`
**Effort:** 5 min

**Task 1.5** — Use `assumptions.revenue_growth_years_2_5` for years 2-5 if provided.
**File:** `module_4_dcf.py` in main loop
**Effort:** 15 min

**Task 1.6** — Build tax rate path. New function `_tax_path(t_effective, t_marginal, override_convergence) -> list[float]` returning tax for years 1..10 + terminal.
**File:** `module_4_dcf.py`
**Effort:** 20 min

**Task 1.7** — Thread effective tax through M4. Source from `CompanyValuationInput.effective_tax_rate_ciq` or `macro.tax_rate_effective`.
**File:** `module_4_dcf.py`, `orchestrator.py`
**Effort:** 15 min

**Task 1.8** — NOL carryforward. New function `_apply_nol(ebit_path, tax_path, nol_initial) -> (taxable_income_path, taxes_path, nol_balance_path)`.
**File:** `module_4_dcf.py`
**Effort:** 40 min

**Task 1.9** — Sales-to-Capital reinvestment with lag. New function `_reinvestment_path(revenue_path, sc_high, sc_stable, lag) -> list[float]`. Note: for lag > 0, we need revenues past year 10 (project lag additional years of revenue).
**File:** `module_4_dcf.py`
**Effort:** 60 min

**Task 1.10** — WACC path. New function `_wacc_path(wacc_initial, wacc_terminal, high_growth_years=5, total_years=10) -> list[float]`.
**File:** `module_4_dcf.py`
**Effort:** 20 min

**Task 1.11** — Cumulative discount factors. Replace `1/(1+wacc)^t` with year-by-year product.
**File:** `module_4_dcf.py`
**Effort:** 15 min

**Task 1.12** — Invested Capital tracking. Build `ic_path[]` by accumulating reinvestments. Build `roic_path[]` for diagnostics. Add to DCFResult.
**File:** `module_4_dcf.py`, `data_dictionary.py` (DCFResult extension)
**Effort:** 30 min

**Task 1.13** — Honor `override_riskfree` + `riskfree_after_yr10` in terminal WACC.
**File:** `module_4_dcf.py`
**Effort:** 15 min

**Task 1.14** — Honor `override_growth_perpetuity` flag explicitly.
**File:** `module_4_dcf.py`
**Effort:** 5 min

**Task 1.15** — Move failure adjustment to operating assets (before bridge). Add `failure_tie_to` branching.
**File:** `module_4_dcf.py`
**Effort:** 20 min

**Task 1.16** — Equity bridge completion. Subtract minority_interests, add cross_holdings.
**File:** `module_4_dcf.py`
**Effort:** 10 min

**Task 1.17** — Trapped cash adjustment.
**File:** `module_4_dcf.py`
**Effort:** 15 min

**Task 1.18** — Depreciation on lease asset → add to `adjusted_d_a` in M3.
**File:** `module_3_cashflow.py`
**Effort:** 5 min

**Task 1.19** — Update M3 to pass `macro.tax_rate_marginal` directly (don't reverse-engineer from cost_of_debt).
**File:** `module_3_cashflow.py:40-46`
**Effort:** 10 min (plus update signature — pass macro into M3)

**Task 1.20** — Comprehensive tests for new DCF mechanics.
**File:** `tests/engine/test_module_4_dcf.py`
**Effort:** 2 hours

**Total Phase 1:** ~7 hours solid work.

### Phase 2 — Feedback Loops

**Task 2.1** — Create `backend/data_sources/damodaran_credit.py` with rating → spread table + small/large firm coverage tables.
**Effort:** 1.5 hours

**Task 2.2** — Add `synthetic_rating()` and `rating_to_spread()` functions in M2.
**File:** `module_2_risk.py`
**Effort:** 30 min

**Task 2.3** — Add `rating_approach` parameter to `compute_cost_of_capital()`. Branch between actual/synthetic/industry/direct.
**File:** `module_2_risk.py`
**Effort:** 45 min

**Task 2.4** — Option dilution iteration. Rewrite M6 `compute_options_and_final_value()` with fixed-point solver.
**File:** `module_6_options.py`
**Effort:** 45 min

**Task 2.5** — Tests: synthetic rating; option dilution convergence.
**Effort:** 1 hour

**Total Phase 2:** ~4.5 hours.

### Phase 3 — Stage 3 Variants

**Task 3.1** — `BusinessSegment` schema; `CompanyValuationInput.business_segments`.
**File:** `data_dictionary.py`
**Effort:** 15 min

**Task 3.2** — `compute_multi_business_beta()`.
**File:** `module_2_risk.py`
**Effort:** 1 hour

**Task 3.3** — `compute_multi_country_erp()`.
**File:** `module_2_risk.py`
**Effort:** 45 min

**Task 3.4** — Bond pricing for `market_value_of_debt`. Add `weighted_avg_debt_maturity` field.
**File:** `data_dictionary.py`, `module_2_risk.py`
**Effort:** 45 min

**Task 3.5** — Preferred stock schema + WACC term.
**File:** `data_dictionary.py`, `module_2_risk.py`
**Effort:** 1 hour

**Total Phase 3:** ~4 hours.

### Phase 4 — Missing Data Intake

**Task 4.1** — Add segment mnemonics to `capiq_formula_map.py`.
**Effort:** 45 min

**Task 4.2** — Add preferred, rating, std-dev mnemonics to `capiq_formula_map.py`.
**Effort:** 30 min

**Task 4.3** — Extend `read_ciq_template.py` to parse segment rows.
**Effort:** 1 hour

**Task 4.4** — Download `ratings.xls`, `synthrating.xls`, `cumdefrates.xls` via `download_damodaran.py`.
**Effort:** 30 min (add URLs)

**Task 4.5** — New parsers for the three credit files.
**Effort:** 1.5 hours

**Total Phase 4:** ~4.5 hours.

### Phase 5 — UI Surfaces

**Task 5.1** — SummarySheet.tsx (year-by-year DCF table).
**Effort:** 2 hours

**Task 5.2** — RelativeValuation.tsx (multiples comparison).
**Effort:** 1.5 hours

**Task 5.3** — CountryRiskBlender.tsx.
**Effort:** 2 hours

**Task 5.4** — IndustryBrowser.tsx.
**Effort:** 1.5 hours

**Task 5.5** — Wire SyntheticRating + FailureRate to engine output.
**Effort:** 1 hour

**Task 5.6** — Diagnostics.tsx expansion (Section 15 sanity checks).
**Effort:** 2 hours

**Total Phase 5:** ~10 hours.

### Phase 6 — Statistical Layer

**Task 6.1** — Parse `statsmicro.xls` into quartile lookup.
**Effort:** 1.5 hours

**Task 6.2** — Display industry distribution on InputSheet.
**Effort:** 1 hour

**Task 6.3** — Tornado sensitivity engine + UI.
**Effort:** 3 hours

**Task 6.4** — Monte Carlo simulation + histogram UI.
**Effort:** 4 hours

**Total Phase 6:** ~9.5 hours.

### Phase 7 — Excel Export

**Task 7.1** — Audit `export_workbook.py` for formula vs. static cells.
**Effort:** 1.5 hours

**Task 7.2** — Refactor to produce live formulas with stable cell positions.
**Effort:** 6 hours (largest single task)

**Task 7.3** — Add missing sheets (Summary, Diagnostics) as formula-based.
**Effort:** 3 hours

**Total Phase 7:** ~10.5 hours.

---

## Grand Total

| Phase | Hours |
|---|---:|
| 1 — Core DCF correctness | 7 |
| 2 — Feedback loops | 4.5 |
| 3 — Stage 3 variants | 4 |
| 4 — Missing data intake | 4.5 |
| 5 — UI surfaces | 10 |
| 6 — Statistical layer | 9.5 |
| 7 — Excel export | 10.5 |
| **Total** | **~50 hours** |

Approximately 6-8 focused working days.
