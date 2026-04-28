# Current State Audit vs Textbook Framework

> **⚠️ SUPERSEDED (2026-04-28)** — this audit was performed against `docs/valuation_framework_textbook.md`, which has since been found to contain divergences from the authoritative Ginzu workbook. See `docs/ginzu_spec_v2.md` for the reconciled spec, `docs/textbook_corrections.md` for the per-item textbook divergences, and `docs/project_plan_v2.md` for the revised implementation plan. This file is kept as a historical record.

**Reference:** `docs/valuation_framework_textbook.md` (10 stages).
**Scope:** every backend module, every data source, every frontend page.
**Audit date:** 2026-04-19.

Legend: ✅ complete · ⚠️ partial · ❌ missing · 🔴 implemented **wrong** (will produce incorrect numbers)

---

## Stage-by-Stage Mapping

### Stage 1 — Base Year Normalization (LTM)

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| LTM flow formula: `Last_10K + YTD − Prior_YTD` | ✅ | `backend/engine/ltm_calculator.py:95` | Formula matches textbook exactly |
| Balance sheet point-in-time rule | ✅ | `ltm_calculator.py:100-105` | Uses most recent quarterly value |
| Flow vs. balance-sheet field classification | ✅ | `ltm_calculator.py:17-27` | Sets defined |
| Quarterly data fetch (FQ-0 through FQ-7) | ✅ | `capiq_formula_map.py:171-181` | 8 quarters fetched per flow item |
| Period date fetch | ✅ | `capiq_formula_map.py:242-255` | Per-FY offset + quarterly |

**Stage 1 overall: ✅ DONE.**

---

### Stage 2 — Financial Statement Adjustments

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| R&D: unamortized fraction `(N-t)/N` | ✅ | `module_1_adjustments.py:41` | Correct |
| R&D: Value of Research Asset = current + Σ unamortized | ✅ | `module_1_adjustments.py:45` | Correct |
| R&D: Amortization = Σ R&D_past/N | ✅ | `module_1_adjustments.py:43` | Correct |
| R&D: Adjustments to EBIT, Net Income, BV Equity | ✅ | `module_1_adjustments.py:131-140` | Correct |
| Leases: `n_additional = round(beyond / avg_yr1_5)` | ✅ | `module_1_adjustments.py:82` | Correct (recently fixed) |
| Leases: annuity PV for beyond-yr-5 | ✅ | `module_1_adjustments.py:85-88` | Correct |
| Leases: depreciation = PV / total_years (straight-line) | ✅ | `module_1_adjustments.py:163-164` | Correct |
| Leases: EBIT adj = lease_expense − depreciation | ✅ | `module_1_adjustments.py:166-170` | Correct (recently fixed) |

**Stage 2 overall: ✅ DONE** (R&D and lease capitalization both correct).

---

### Stage 3 — Cost of Capital

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Unlevered beta — Single Business (US) | ✅ | `module_2_risk.py:37` + `damodaran_store.py:lookup_industry` | Works |
| Unlevered beta — Multi-Business (revenue/EV weighted) | ❌ | — | Not implemented |
| Unlevered beta — Global variant | ✅ | Via region param | Regional dataset selection works |
| Unlevered beta — Direct input | ❌ | — | No bypass mechanism |
| ERP — Country of incorporation | ✅ | `module_2_risk.py:41` | Works |
| ERP — Operating countries (revenue-weighted) | ❌ | — | Not implemented |
| ERP — Operating regions | ❌ | — | Not implemented |
| Pre-tax cost of debt — Industry average fallback | ✅ | `module_2_risk.py:45` | Works but passive |
| Pre-tax cost of debt — Actual rating lookup | ❌ | — | Damodaran rating-to-spread table not loaded |
| Pre-tax cost of debt — Synthetic rating | ❌ | — | Frontend-only page; not wired to engine |
| Market Value of Debt — bond pricing | ❌ | — | Uses book + lease PV, no repricing |
| Market Value of Equity | ✅ | implicit via shares × price | OK |
| Preferred stock component | ❌ | — | Not in schema |
| Levered beta formula | ✅ | `module_2_risk.py:38` | Correct |
| Cost of Equity (CAPM) | ✅ | `module_2_risk.py:42` | Correct |
| After-tax cost of debt | ✅ | `module_2_risk.py:50` | Correct |
| WACC blended | ✅ | `module_2_risk.py:58` | Correct |
| Alternate approach 2 (industry-avg WACC adjusted) | ❌ | — | Not implemented |
| Alternate approach 3 (regional decile) | ❌ | — | Not implemented |

**Stage 3 overall: ⚠️ PARTIAL.** Core single-business calculation works; five major variants missing.

---

### Stage 4 — Story Calibration (ValuationAssumptions schema)

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| `revenue_growth_next_year` | ✅ | `data_dictionary.py:158` | Field exists |
| `revenue_growth_years_2_5` | ✅ | `data_dictionary.py:160` | Field exists |
| `target_operating_margin` | ✅ | `data_dictionary.py:161` | Field exists |
| `margin_convergence_year` | ✅ | `data_dictionary.py:162` | Field exists |
| `sales_to_capital_high/stable` | ✅ | `data_dictionary.py:163-164` | Fields exist |
| `reinvestment_lag_years` | ✅ | `data_dictionary.py:171` | Field exists |
| `override_tax_convergence` | ✅ | `data_dictionary.py:172` | Field exists |
| `override_nol` + `nol_amount` | ✅ | `data_dictionary.py:173-174` | Fields exist |
| `override_riskfree` + `riskfree_after_yr10` | ✅ | `data_dictionary.py:175-176` | Fields exist |
| `override_growth_perpetuity` + `growth_perpetuity_rate` | ✅ | `data_dictionary.py:177-178` | Fields exist |
| `override_trapped_cash` + amount + foreign tax | ✅ | `data_dictionary.py:179-181` | Fields exist |
| `failure_probability` + `distress_proceeds_pct` + `failure_tie_to` | ✅ | `data_dictionary.py:167-169` | Fields exist |
| `roic_stable_override`, `cost_of_capital_stable_override` | ✅ | `data_dictionary.py:165-166` | Fields exist |

**Stage 4 overall: ✅ SCHEMA COMPLETE.** All fields exist. The question is whether they are *used* — see Stage 5 below.

---

### Stage 5 — Ten-Year Explicit Projection (`module_4_dcf.py`) 🔴

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Revenue path years 1-5 flat, years 6-10 converge | ⚠️ | `module_4_dcf.py:79-93` | Logic exists but driven by `expected_growth_ebit` (from M3's ROIC × RIR), not user's `revenue_growth_next_year` |
| `revenue_growth_years_2_5` used | 🔴 | — | Field defined but **never read** in `module_4` |
| Operating margin path (linear convergence to target) | ❌ | — | EBIT is compounded by growth rate; **no revenue × margin mechanic** |
| `target_operating_margin` used | 🔴 | — | Field defined but **never read** |
| `margin_convergence_year` used | 🔴 | — | Field defined but **never read** |
| Operating Income = Revenue × Margin | ❌ | — | Not computed this way |
| Tax rate years 1-5 effective, years 6-10 converge to marginal | ❌ | `module_4_dcf.py:56` | Uses flat `macro.tax_rate_marginal` every year |
| `override_tax_convergence` honored | 🔴 | — | Field defined but **never read** |
| Dynamic NOL carryforward | ❌ | — | Not implemented anywhere |
| `nol_amount` used | 🔴 | — | Field defined but **never read** |
| After-tax Operating Income | ✅ | `module_4_dcf.py:97` | `ebit_t × (1 − tax_rate)` correct |
| Sales-to-Capital reinvestment method | ❌ | `module_4_dcf.py:98` | Uses `nopat_t × rir_firm` (fraction of NOPAT); textbook requires `ΔRev / S_C` |
| `sales_to_capital_high/stable` used | 🔴 | — | Fields defined but **never read** |
| Reinvestment lag (0-3 years) | ❌ | — | Not implemented |
| `reinvestment_lag_years` used | 🔴 | — | Field defined but **never read** |
| FCFF = NOPAT − Reinvestment | ✅ | `module_4_dcf.py:99` | Correct |
| WACC path years 1-5 flat, years 6-10 converge | ❌ | `module_4_dcf.py:103` | Uses constant WACC for all years |
| Invested Capital path year-by-year | ❌ | — | Not tracked |
| ROIC tracked year-by-year | ❌ | — | Not tracked |

**Stage 5 overall: 🔴 STRUCTURAL PROBLEM.**
The DCF engine is PRD-accurate but Ginzu-inaccurate. Multiple user-specified assumption fields (target margin, margin convergence, sales-to-capital, reinvestment lag, NOL, tax convergence, WACC convergence) exist in the schema but **are never consumed by the DCF engine**. Numbers produced are structurally different from what Damodaran would produce for the same inputs.

---

### Stage 6 — Terminal Value

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Terminal reinvestment rate = g / ROIC_terminal | ✅ | `module_4_dcf.py:118` | Correct |
| `roic_stable_override` honored | ✅ | `module_4_dcf.py:117` | Correct |
| `cost_of_capital_stable_override` honored | ✅ | `module_4_dcf.py:61` | Correct |
| Terminal g ≤ risk-free constraint | ✅ | `module_4_dcf.py:54` | Correct |
| `override_growth_perpetuity` honored | ⚠️ | — | User sets `stable_growth_rate` directly; override flag not checked |
| `override_riskfree` (post-year-10) honored | ❌ | — | Field exists, never read |
| Gordon formula TV = FCFF / (WACC_terminal − g) | ✅ | `module_4_dcf.py:125` | Correct |
| Terminal tax = marginal (not effective) | ✅ | Implicit via `macro.tax_rate_marginal` | Works because whole projection uses marginal; would need fix if Stage 5 tax path fixed |

**Stage 6 overall: ✅ MOSTLY DONE.** Two override flags not honored.

---

### Stage 7 — Discounting

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Cumulative discount factors (year-by-year product) | ⚠️ | `module_4_dcf.py:103` | Uses `1/(1+wacc)^t` closed form with constant WACC — correct if WACC is indeed constant, wrong once Stage 5 WACC convergence is added |
| PV of each year's FCFF | ✅ | `module_4_dcf.py:110` | Correct |
| PV of terminal value | ✅ | `module_4_dcf.py:129` | Correct |
| Sum of PVs | ✅ | `module_4_dcf.py:132-133` | Correct |

**Stage 7 overall: ✅ OK TODAY.** Will need update when WACC convergence is added.

---

### Stage 8 — Failure Probability Overlay

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Probability-weighted expected value | ⚠️ | `module_4_dcf.py:142-147` | Applied to `value_of_equity`, not `value_of_operating_assets` (Ginzu applies before the equity bridge) |
| Distress tied to fair value ("V") | ✅ | `module_4_dcf.py:143` | `value_of_equity × pct` |
| Distress tied to book value ("B") | ❌ | — | `failure_tie_to` flag never read |
| Distress against operating assets, not equity | ❌ | — | Wrong line in the pipeline |

**Stage 8 overall: ⚠️ PARTIAL.** Mechanically runs, but order-of-operations differs from Ginzu and book-value variant missing.

---

### Stage 9 — Equity Value Bridge

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Start from Value of Operating Assets | ⚠️ | `module_4_dcf.py:139` | Starts from `value_of_operating_assets` but subtracts debt/adds cash directly on the same line — compressed, not stage-separated |
| − Adjusted Book Debt (incl lease PV) | ✅ | `module_4_dcf.py:137-139` | Uses `adjusted.adjusted_mv_debt` which includes lease PV |
| − Minority Interests | ❌ | — | Not subtracted |
| + Cash (with trapped-cash adjustment) | ⚠️ | `module_4_dcf.py:136-139` | Adds cash but **no trapped-cash adjustment** |
| + Cross-holdings and non-operating assets | ❌ | — | Not added |
| − Value of All Options | ✅ | `module_6_options.py:91` | Subtracted in M6 |
| `override_trapped_cash` honored | 🔴 | — | Fields exist, **never read** |

**Stage 9 overall: ❌ MAJOR GAPS.** Minority interests, cross-holdings, trapped-cash adjustment all missing.

---

### Stage 10 — Per-Share and Verdict

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Equity / shares | ✅ | `module_4_dcf.py:150` and `module_6_options.py:94` | Correct |
| Compare to market price | ⚠️ | Frontend only (`ValuationOutput.tsx`) | Ratio not returned from engine |

**Stage 10 overall: ✅ DONE.**

---

### Option Dilution Sub-Loop (Stage 9 insertion)

| Textbook item | Status | Where | Notes |
|---|---|---|---|
| Dilution-adjusted stock price S* | ❌ | `module_6_options.py:80` | Uses `S = value_per_share_pre` directly — no adjustment for dilution |
| Iteration S* ↔ C* to fixed point | ❌ | — | Not implemented |
| Black-Scholes formula | ✅ | `module_6_options.py:40-44` | Correct |
| Value of options × count | ✅ | `module_6_options.py:88` | Correct |

**Option dilution overall: ❌ MISSING.**

---

## Data Fetching Audit (CIQ)

### What IS fetched (generate_ciq_template.py + read_ciq_template.py)
| Variable | Mnemonic | Years | Status |
|---|---|---|---|
| Revenues | IQ_TOTAL_REV | 10 FY + 8 FQ | ✅ |
| Operating Income (EBIT) | IQ_EBIT | 10 FY + 8 FQ | ✅ |
| EBITDA | IQ_EBITDA | 10 FY + 8 FQ | ✅ |
| Net Income | IQ_NI | 10 FY + 8 FQ | ✅ |
| Interest Expense | IQ_INTEREST_EXP | 10 FY + 8 FQ | ✅ (ABS applied) |
| D&A | IQ_DA_CF | 10 FY + 8 FQ | ✅ (ABS applied) |
| R&D (primary + footnote fallback) | IQ_RD_EXP / IQ_RD_EXP_FN | 10 FY + 8 FQ | ✅ |
| CapEx | IQ_CAPEX | 10 FY + 8 FQ | ✅ (ABS applied) |
| Operating Lease Payments | IQ_OPERATING_LEASE_PAYMENTS | 10 FY + 8 FQ | ✅ (ABS applied) |
| Earnings Before Tax | IQ_EBT_EXCL | 10 FY + 8 FQ | ✅ |
| Income Tax | IQ_INC_TAX | 10 FY + 8 FQ | ✅ |
| Cash & Equivalents | IQ_CASH_EQUIV | 10 FY + FQ-0 | ✅ |
| Total Equity | IQ_TOTAL_EQUITY | 10 FY + FQ-0 | ✅ |
| Total Debt | IQ_TOTAL_DEBT | 10 FY + FQ-0 | ✅ |
| Shares Outstanding | IQ_TOTAL_OUTSTANDING_FILING_DATE | 10 FY + FQ-0 | ✅ |
| Cross Holdings | IQ_LT_INVEST | 10 FY + FQ-0 | ✅ |
| Minority Interests | IQ_MINORITY_INTEREST | 10 FY + FQ-0 | ✅ |
| Stock Price | IQ_CLOSEPRICE | current | ✅ |
| Market Cap | IQ_MARKETCAP | current | ✅ |
| Reporting Currency | IQ_FILING_CURRENCY | current | ✅ |
| Exchange | IQ_EXCHANGE | current | ✅ |
| Effective Tax Rate | IQ_EFFECT_TAX_RATE | current (÷100) | ✅ |
| Options Outstanding | IQ_OPTIONS_END_OS | current | ✅ |
| Options Avg Strike | IQ_OPTIONS_STRIKE_PRICE_OS | current | ✅ |
| Options Avg Life | IQ_OPTIONS_AVG_LIFE | current | ✅ |
| Operating Lease Commitments Yr1-5 + Beyond | IQ_OL_COMM_CY, IQ_OL_COMM_CY1..4, IQ_OL_COMM_NEXT_FIVE | current | ✅ |
| Period Dates (10-K, 10-Q) | IQ_PERIODDATE | FY-0, FQ-0 | ✅ |

### What is MISSING from CIQ fetch
| Variable | Why needed | Textbook stage |
|---|---|---|
| Geographic revenue breakdown (by country) | Multi-country ERP calculation | 3b |
| Business segment revenue (SIC/industry breakdown) | Multi-business unlevered beta | 3a |
| Preferred stock shares / dividend / price | WACC preferred-stock component | 3f |
| Weighted average debt maturity | MV of debt (bond pricing) | 3d |
| Actual credit rating (S&P / Moody's) | Cost of debt lookup | 3c |
| Stock return standard deviation | Options pricing (currently comes from Damodaran industry) | Options |
| NOL carryforward balance | Dynamic NOL in DCF | 5e |
| Trapped foreign cash | Equity bridge | 9 |

**Data fetching status: ✅ 90% complete** for the 6 modules we have, but missing the 8 items above — these are what prevent full Ginzu replication.

---

## Damodaran External Data Integration

### What IS loaded (244 files, 8 regions, 11 parsers)
| Dataset | Purpose | Status |
|---|---|---|
| Unlevered Betas (by industry, 8 regions) | β_U lookup | ✅ |
| WACC (by industry) | Industry avg WACC for comparison/fallback | ✅ |
| Margins (pretax, aftertax) | Industry comparison | ✅ |
| Tax rates (by industry) | Industry reference | ✅ |
| CapEx / Sales-to-Capital | Industry S/C ratio | ✅ |
| Fundamental growth EB | Industry growth | ✅ |
| EVA / ROIC | Industry return on capital | ✅ |
| EV/EBITDA, EV/Sales, P/E, P/BV | Multiples comparison | ✅ |
| Country Equity Risk Premium | ERP lookup | ✅ |
| Country Tax Rates | Country tax lookup | ✅ |
| Country Default Spread | Embedded in country ERP parser | ✅ |

### What is MISSING from Damodaran integration
| Dataset | Why needed | Textbook stage |
|---|---|---|
| Rating-to-Default-Spread table | Cost of debt via actual rating | 3c |
| Interest-Coverage-to-Rating table (small-firm + large-firm) | Synthetic rating approach | 3c |
| Default probability by rating + time horizon | Failure rate derivation | 8 |
| Survival rate by corporate age (BLS data) | Failure rate for young firms | 8 |
| Input Statistical Distributions (industry quartiles) | Monte Carlo / sensitivity | Beyond textbook (advanced) |
| Mature Market ERP value (from ctryprem.xls metadata) | Terminal WACC when RF override = Yes | 6 |

**Damodaran integration status: ✅ 80% complete** for core data, missing the 6 specialist tables above.

---

## Frontend Audit

| Page | Backend integration | Textbook coverage | Status |
|---|---|---|---|
| InputSheet (811 LOC) | Full | Stages 1, 4 (schema display) | ✅ Solid |
| TrailingTwelveMonth (282 LOC) | M0/LTM | Stage 1 | ✅ Solid |
| RDConverter (145 LOC) | M1 | Stage 2a | ✅ Solid |
| LeaseConverter (166 LOC) | M1 | Stage 2b | ✅ Solid |
| SyntheticRating (83 LOC) | None — frontend lookup | Stage 3c | ⚠️ Display only; not wired to engine |
| CostOfCapital (160 LOC) | M2 | Stage 3 | ✅ Solid for single-business |
| StoriesToNumbers (135 LOC) | None — static labels | Stage 4 narrative | ⚠️ Thin |
| ValuationPicture (119 LOC) | M4 read-only | Stage 10 visual | ⚠️ Thin |
| Diagnostics (218 LOC) | Various read-only | Section 15 (diagnostics) | ⚠️ Needs audit for completeness |
| OptionValue (213 LOC) | M6 | Stage 9 options | ✅ Solid (but no iteration) |
| FailureRate (90 LOC) | None — frontend math | Stage 8 | ⚠️ Display only; not wired to engine |
| ValuationOutput (278 LOC) | M4 full | Stages 5-10 | ✅ Solid |
| AnswerKeys (97 LOC) | All modules read-only | Section 15 | ⚠️ Thin summary |
| — Relative Valuation — | M5 computes but no UI | Stage 5 output (multiples) | ❌ MISSING |
| — Summary Sheet (year-by-year DCF table) — | Data available in M4 | Essential for auditing | ❌ MISSING |
| — Country Risk Blender — | M0 fetches but no UI | Stage 3b | ❌ MISSING |
| — Industry Averages Browser — | Damodaran store loaded but no UI | Stage 3 reference | ❌ MISSING |
| — Simulations / Sensitivity — | — | Beyond textbook (advanced) | ❌ MISSING |

---

## Summary Score

| Layer | Complete | Partial | Missing | Wrong |
|---|---:|---:|---:|---:|
| Stage 1 (LTM) | 5 | 0 | 0 | 0 |
| Stage 2 (Adjustments) | 8 | 0 | 0 | 0 |
| Stage 3 (Cost of Capital) | 7 | 0 | 10 | 0 |
| Stage 4 (Assumptions schema) | 13 | 0 | 0 | 0 |
| Stage 5 (10-year Projection) | 2 | 1 | 10 | 7 |
| Stage 6 (Terminal Value) | 5 | 0 | 2 | 0 |
| Stage 7 (Discounting) | 3 | 1 | 0 | 0 |
| Stage 8 (Failure Probability) | 1 | 1 | 2 | 0 |
| Stage 9 (Equity Bridge) | 2 | 2 | 3 | 0 |
| Stage 10 (Per-share) | 2 | 0 | 0 | 0 |
| Options dilution | 2 | 0 | 2 | 0 |
| Data fetching (CIQ) | 24 | 0 | 8 | 0 |
| External data (Damodaran) | 11 | 0 | 6 | 0 |
| Frontend pages | 7 | 6 | 5 | 0 |

**Top priorities (ordered by impact on correctness):**
1. **Stage 5 engine rewrite** (7 fields defined but unused; multiple mechanics wrong)
2. **Stage 9 equity bridge completion** (minority interests, cross-holdings, trapped cash)
3. **Stage 3 synthetic rating feedback loop**
4. **Stage 3 MV of debt via bond pricing**
5. **Option dilution iteration**
6. **Stage 3 multi-country ERP blending**
7. **Stage 3 multi-business unlevered beta**
8. **Missing CIQ fetches** (segments, rating, preferred stock, etc.)
9. **Missing Damodaran datasets** (rating-to-spread, default probabilities)
10. **Missing UI surfaces** (Relative Valuation, Summary Sheet, Country Risk Blender, Simulations)
