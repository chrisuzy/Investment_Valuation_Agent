# Stage 1 — Inputs + LTM: Ginzu-Truth Findings

**Source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, sheets `Input sheet` (35 formulas, 111 data values) and `Trailing 12 month` (11 formulas, 55 values).
**Extracted:** 2026-04-28 via `backend/tools/extract_ginzu_formulas.py`.
**Note:** variables prefixed by `Input!` map to Input sheet cells; `LTM!` maps to Trailing 12 month sheet.

---

## 1.1 Input sheet — Variable catalog

### A. Company identification (rows 3–9)

| Variable | Cell | NVIDIA sample | Source of this input |
|---|---|---|---|
| `valuation_date` | Input!B3 | 2025-01-01 | user |
| `company_name` | Input!B4 | "Nvidia" | user |
| `country_of_incorporation` | Input!B7 | (blank in NVIDIA copy) | user |
| `industry_us` | Input!B8 | (blank in NVIDIA copy) | user / picks from Industry Averages(US)!col A |
| `industry_global` | Input!B9 | (blank) | user / picks from Industry Average Beta (Global)!col A |

### B. Base year financial data (rows 10–23) — column B = "this year", column C = "last year"

| Variable | This year (B) | Last year (C) | Months-since-10K (D) | NVIDIA sample (B / C) |
|---|---|---|---|---|
| `revenues` | B10 | C10 | D10 | 113,269 / 60,922, 0.75 |
| `operating_income_ebit` | B11 | C11 | D11 | 71,033 / 32,972, 0.75 |
| `interest_expense` | B12 | C12 | — | 249 / 257 |
| `book_value_of_equity` | B13 | C13 | — | 65,899 / 42,978 |
| `book_value_of_debt` | B14 | C14 | — | 10,225 / 11,056 |
| `has_rd_to_capitalize` | B15 (Yes/No) | — | — | blank in sample |
| `has_operating_leases` | B16 (Yes/No) | — | — | blank in sample |
| `cash_and_marketable_securities` | B17 | C17 | — | 38,487 / 25,984 |
| `cross_holdings` | B18 | C18 | — | 2,237 / 1,546 |
| `minority_interests` | B19 | C19 | — | 0 / 0 |
| `shares_outstanding` | B20 | — | — | 24,490 |
| `current_stock_price` | B21 | — | — | 123 |
| `effective_tax_rate` | B22 | — | — | 0.135 |
| `marginal_tax_rate` | B23 | — | — | 0.25 |

**Ginzu convention:** column B holds the most-recent-period value and column C holds the prior-year value. Column D (fraction: months-since-10K / 12) is used ONLY for implied-growth-rate reference formulas in column I (I25, I28). The base-year data fed to the DCF is always column B.

### C. Value drivers — Growth story (rows 25–31)

| Variable | Cell | NVIDIA sample | Reference benchmarks available |
|---|---|---|---|
| `revenue_growth_next_year` | B25 | 0.15 | I25 (implied-from-historical), J25 (US industry avg), K25 (Global industry avg), L/M/N25 (input-stat Q1/median/Q3) |
| `revenue_growth_years_2_5` | B27 (formula `=B25` as default) | 0.15 (via =B25) | I27, J27, K27, L/M/N27 |
| `operating_margin_next_year` | B26 | 0.65 | I26, J26, K26, L/M/N26 |
| `target_pretax_operating_margin` | B28 | 0.60 | I28 (implied), J28/K28 (industry), L/M/N28 (quartiles) |
| `year_of_convergence_for_margin` | B29 | 5 | J29/K29 (industry avg convergence); plus I29 |
| `sales_to_capital_ratio_years_1_5` | B30 | 2.5 | J30 (US industry S/C), K30 (Global) |
| `sales_to_capital_ratio_years_6_10` | B31 | 2.5 | J31, K31, L/M/N31 |

**Critical: `revenue_growth_years_2_5` defaults to `revenue_growth_next_year` via the formula `B27 = B25`.** This is a compute default, not just a hint. It's the *only* compute formula on an input-value cell — every other value in column B is a literal.

### D. Market numbers (rows 32–34)

| Variable | Cell | NVIDIA | Source |
|---|---|---|---|
| `riskfree_rate` | B33 | 0.047 | user / market data |
| `initial_cost_of_capital` | B34 (formula) | 0.1179 | `='Cost of capital worksheet'!B13` — pulled from cost-of-capital sheet |

**B34 is the ONLY cross-sheet formula on the Input sheet that feeds the compute graph.** Cost of capital is computed elsewhere and piped in.

### E. Options (rows 36–40)

| Variable | Cell | NVIDIA |
|---|---|---|
| `has_options_outstanding` | B36 (Yes/No) | blank in sample |
| `options_outstanding` | B37 | 7.72 |
| `options_avg_strike` | B38 | 1.29 |
| `options_avg_maturity` | B39 | 7 |
| `stock_price_std_dev` | B40 | 0.45 |

### F. Multi-segment overlay (rows 42–52, NVIDIA-specific; not generic)

Columns B=Current, C=Year 10. Two segments used in NVIDIA copy:

| Variable | AI chip (row 44–46) | Auto chip (row 50–52) |
|---|---|---|
| `segment_total_market` | B44=80,000 / C44=300,000 | B50=20,000 / C50=200,000 |
| `segment_market_share` | B45=0.8 / C45=0.6 | B51=0.06 / C51=0.15 |
| `segment_operating_margin` | B46=0.65 / C46=0.60 | B52=0.65 / C52=0.60 |

**This is a custom NVIDIA overlay, not part of the canonical Ginzu template.** The generic Ginzu Input sheet does not have rows 42–52 in a standard instance. Skip for framework spec.

### G. Default assumption overrides (rows 54–83)

Every override has the same shape: a narrative row, a Yes/No answer cell, and (sometimes) a numeric-override-value cell. User leaves the Yes/No blank to accept the default; types "Yes" to activate the override value.

| Narrative text (row) | Override flag cell | Override value cell | NVIDIA sample (flag / value) | Default if not overridden |
|---|---|---|---|---|
| WACC converges to riskfree+4.5% by yr 10 | B56 (Yes/No) | B57 (decimal) | blank / 0.085 | WACC stays at initial value |
| ROIC stable = cost of capital (no moat) | B59 | B60 | blank / 0.20 | terminal ROIC = terminal WACC |
| No failure probability | B62 | B63 | blank / 0.12 | p_failure = 0 |
| Failure tie-to: B or V | — | B64 (text "B" or "V") | (sample has value somewhere, commentary only shown in my dump) | "V" (fair value) |
| Distress proceeds pct | — | B65 | 0.5 | — |
| Reinvestment lag = 1 year | B67 | B68 (0–3) | blank / 3 | lag = 1 |
| Tax converges to marginal by yr 11 | B70 | — | blank | converge to marginal |
| No NOL carried into year 1 | B72 | B73 (formula `=474.8+256.6`) | blank / 731.4 | NOL_0 = 0 |
| Riskfree unchanged after yr 10 | B75 | B76 | blank / 0.02 | riskfree stays at B33 |
| Terminal g = riskfree | B78 | B79 | blank / -0.05 | g_terminal = riskfree |
| No trapped foreign cash | B81 | B82 (amount), B83 (foreign tax rate) | blank / 140,000 / 0.15 | usable_cash = cash |

**Discovery:** The NVIDIA copy shows numerical values in the override-value cells even though the Yes/No trigger cells are blank. Two possibilities:
1. Downstream formulas use `IF(OverrideCell="Yes", OverrideValue, Default)` — in which case these values are dormant in the NVIDIA copy.
2. Downstream formulas use `IF(OverrideValue>0, OverrideValue, Default)` — the numeric value itself triggers.
**To confirm in Stage 4 by inspecting Valuation output formulas.** This distinction matters for our implementation: which schema fields should engine read.

### H. Industry-benchmark reference columns (I, J, K, L, M, N on rows 25–31)

Per row, the I–N columns are read-only benchmarks the analyst compares their input to. Their formulas are:

| Col | Semantic | Formula pattern |
|---|---|---|
| I | Implied from your data | Derived from B10/C10, B13/B14/B17, Valuation output back-reference |
| J | US industry average | `VLOOKUP(Input!B8, 'Industry Averages(US)'!A2:S95, <col>)` |
| K | Global industry average | `VLOOKUP(Input!B9, 'Industry Average Beta (Global)'!A2:N95, <col>)` |
| L | 1st quartile (Damodaran input stat distribution) | `VLOOKUP(Input!B9, 'Input Stat Distributioons'!A3:R96, <col>, FALSE)` |
| M | Median | same, +1 column |
| N | 3rd quartile | same, +1 column |

**None of these feed the compute graph** — they are purely display. So loading `Input Stat Distributioons` sheet is a Phase 6 (sensitivity layer) nice-to-have, not a requirement for correctness.

---

## 1.2 Trailing 12 month — Variable catalog

**Key finding:** the LTM sheet in NVIDIA's copy still contains Netflix data from a prior analysis (rows reference "Content Costs", "Technology & Content"). It is **NOT wired into the Input sheet** — no Input sheet cell references LTM. It is a standalone calculator; the analyst computes LTM separately and pastes the result into Input!B10..B23.

### Formulas present

Only one formula pattern, applied 11 times across flow rows:
```
LTM_value_E_column = Last_10K_B_column - Prior_Year_YTD_C_column + Current_Year_YTD_D_column
```
Ginzu-form per row:
```
LTM!E2  revenues:             = B2 - C2 + D2
LTM!E3  "Technology & Content": = B3 - C3 + D3
LTM!E4  operating_income_ebit:   = B4 - C4 + D4
LTM!E5  interest_expense:        = B5 - C5 + D5
LTM!E36 G&A (Netflix line item): = B36 - C36 + D36
LTM!E37 Marketing Costs:         = B37 - C37 + D37
LTM!E38 Content Costs:           = B38 - C38 + D38
LTM!E40 Content Costs (Cash Flows): = B40 - C40 + D40
LTM!B14..D14  effective_tax_rate: = tax_expense / pretax_income (literal for each column)
```

### Balance sheet rows (rows 6, 7, 9, 10, 11, 12, 13)

**No formulas.** Balance sheet values are shown for column B (last 10K) and column D (current quarter), but column E is left empty — which is consistent with the textbook rule that balance-sheet items are point-in-time, not flows.

### Lease commitment scratchpad (rows 17–25)

Rows 17–21 hold projected lease commitments for years 1–5; row 22 holds beyond-year-5. These are manually entered values that the analyst then **manually copies** into the Operating lease converter sheet (per commentary cell C18: "Copy into operating lease worksheet").

### Implications for our architecture

1. **Our LTM layer is more automated than Ginzu's.** Our `ltm_calculator.py` computes LTM from CIQ-fetched quarterly data and produces the base-year values the DCF reads. Ginzu asks the analyst to do this by hand.
2. **Ginzu's LTM formula is simple and matches our implementation:**  `LTM_Flow = Last_10K + Current_YTD - Prior_YTD`. We already validated this.
3. **The LTM sheet does not define the interface** — the Input sheet defines the interface (rows 10–23 are what feed the DCF). Our backend should produce values that populate those 14 base-year fields; how we derive them (LTM calculator + CIQ quarterly data) is an implementation choice.

---

## 1.3 Variable → CIQ fetch coverage map

Check every base-year field Ginzu wants (Input sheet rows 10–23) against `backend/data_sources/capiq_formula_map.py`.

| Ginzu input | Our CIQ mnemonic | Our variable | Coverage |
|---|---|---|---|
| revenues (this year + last year) | `IQ_TOTAL_REV` @ FY-0, FY-1 | `revenues` | ✅ |
| operating_income_ebit | `IQ_EBIT` @ FY-0, FY-1 | `ebit` | ✅ |
| interest_expense | `IQ_INTEREST_EXP` @ FY-0, FY-1 | `interest_expense` | ✅ |
| book_value_of_equity | `IQ_TOTAL_EQUITY` @ FY-0, FY-1 | `bv_equity` | ✅ |
| book_value_of_debt | `IQ_TOTAL_DEBT` @ FY-0, FY-1 | `bv_debt` | ✅ |
| cash_and_marketable_securities | `IQ_CASH_EQUIV` @ FY-0, FY-1 | `cash_and_marketable_securities` | ✅ |
| cross_holdings | `IQ_LT_INVEST` @ FY-0, FY-1 | `cross_holdings` | ✅ fetched but (per atom audit) not applied in equity bridge |
| minority_interests | `IQ_MINORITY_INTEREST` @ FY-0, FY-1 | `minority_interests` | ✅ fetched but not applied |
| shares_outstanding | `IQ_TOTAL_OUTSTANDING_FILING_DATE` @ FY-0, FQ-0 | `shares_outstanding` | ✅ |
| current_stock_price | `IQ_CLOSEPRICE` | `stock_price` | ✅ |
| effective_tax_rate | `IQ_EFFECT_TAX_RATE` /100 | `effective_tax_rate_ciq` | ✅ but (per atom audit) dead — DCF engine does not read it |
| marginal_tax_rate | not fetched from CIQ; from `countrytaxrates.xls` | macro.tax_rate_marginal | ✅ |
| riskfree_rate | not from CIQ; user-supplied or country-based | macro.risk_free_rate | ✅ |
| options_outstanding | `IQ_OPTIONS_END_OS` | `options_outstanding` | ✅ |
| options_avg_strike | `IQ_OPTIONS_STRIKE_PRICE_OS` | `options_avg_strike` | ✅ |
| options_avg_maturity | `IQ_OPTIONS_AVG_LIFE` | `options_avg_maturity` | ✅ |
| stock_price_std_dev | **NOT FETCHED** — uses Damodaran industry default instead | — | ❌ gap |

**Lease footnote data** (rows 17–25 of LTM sheet, rows where user manually enters):
| Ginzu input | Our CIQ mnemonic | Coverage |
|---|---|---|
| lease_commitment_yr1..5 | `IQ_OL_COMM_CY`, `..CY1..CY4` | ✅ |
| lease_commitment_beyond_yr5 | `IQ_OL_COMM_NEXT_FIVE` | ✅ |
| operating_lease_expense_current | `IQ_OPERATING_LEASE_PAYMENTS` | ✅ |

**R&D history** (for capitalization; up to 10 years of past R&D):
| Ginzu input | Our CIQ mnemonic | Coverage |
|---|---|---|
| r_and_d_expense (10 years) | `IQ_RD_EXP` @ FY-0..FY-9 | ✅ with fallback to `IQ_RD_EXP_FN` |

**Story inputs (user judgment, not CIQ):**
- revenue_growth_next_year, revenue_growth_years_2_5, operating_margin_next_year, target_pretax_operating_margin, year_of_convergence_for_margin, sales_to_capital_ratio_years_1_5, sales_to_capital_ratio_years_6_10, all override flags + values.

These all come from the user via the frontend `InputSheet.tsx` UI. No CIQ fetch needed.

### Summary — CIQ gaps vs Ginzu Input requirements

1. ❌ `stock_price_std_dev` — Ginzu expects it (B40); we use Damodaran industry default. Not strictly wrong; Damodaran's own sheet sometimes also falls back to industry. Low priority.
2. ✅ All base-year balance sheet + income items covered.
3. ✅ Options, leases, R&D history covered.
4. ✅ Effective tax rate fetched, but dead in the engine (flagged in atom audit; Stage 4 will confirm usage).

**Primary Stage 1 finding:** CIQ fetch layer is sufficient for the Input sheet. The "dead CIQ fields" problem (cross_holdings, minority_interests, effective_tax_rate_ciq) is a consumer-side issue in the engine, not a producer-side issue in the fetcher.

---

## 1.4 Discrepancies vs `valuation_framework_textbook.md`

Walking the textbook's Stage 1 (LTM) and Stage 2/ Prerequisites sections against Ginzu.

| Textbook claim | Ginzu reality | Delta |
|---|---|---|
| "Number_of_Additional_Years_Beyond_Five = ROUND(Beyond / AVERAGE(Year1–5), 0)" with min-1 clause | Same formula; min-1 clause is in our code only (defensive) — Ginzu doesn't have it because real commitments always have non-zero yr1–5 averages | ✅ equivalent |
| Stage 1 inputs = `Last_10K_Value + Current_YTD - Prior_YTD` | Exact match, LTM!E2..E5 | ✅ equivalent |
| "Textbook Stage 2 Section D: Employee stock options" lists 4 inputs: options count, strike, maturity, stock return stddev | Ginzu Input sheet B37..B40 matches exactly | ✅ equivalent |
| "Stage 4 Story — `revenue_growth_years_2_5` default = next-year growth" | Confirmed by Ginzu's B27=B25 formula | ✅ equivalent |
| Textbook does not explicitly state "cross_holdings and minority_interests are inputs to the equity bridge" but implies it via Stage 9 formula | Ginzu Input!B18 (cross holdings) and B19 (minority interests) confirm these are direct user inputs fed to the bridge | ✅ equivalent |
| Textbook Section 2.D (Stage 2 prerequisites) does NOT list `operating_margin_next_year` as a separate input — it only lists `Target_Pre_Tax_Operating_Margin` | Ginzu has BOTH: B26 (Year-1 margin) and B28 (target) as separate inputs | 🔴 **textbook omission** — margin_next_year is a distinct input, not a derived value. Stage 5b (margin path) needs margin_Y1 as one endpoint and margin_target as the other. |
| Textbook Section F (Macro): "Marginal_Tax_Rate = 21% federal + ~4% state ≈ 25% for US" | Ginzu B23 = 0.25 | ✅ equivalent |
| Textbook Section H: "Failure probability by rating and corporate age" — mentions tables | Ginzu uses a dedicated Failure Rate worksheet (Stage 5 will unpack) — not the rating-age tables | 🔵 textbook mentions an approach Ginzu doesn't implement literally; both are valid |
| Textbook: "`override_growth_perpetuity`, `growth_perpetuity_rate`" | Ginzu B78/B79 pair exists | ✅ equivalent |
| Textbook: "override_trapped_cash, trapped_cash_amount, trapped_cash_tax_rate" | Ginzu B81/B82/B83 triple exists | ✅ equivalent |
| Textbook: "distress_proceeds_pct is a single number in [0, 1]" | Ginzu B65 = 0.5 | ✅ equivalent |
| Textbook: "Failure_Tie_To is 'B' or 'V'" | Ginzu B64 takes those literals | ✅ equivalent |

**Stage 1 textbook corrections needed (to add to `textbook_corrections.md`):**

1. **Missing input variable:** `operating_margin_next_year` (Input!B26) should be listed in Stage 4 alongside `target_pretax_operating_margin`. The textbook currently implies year-1 margin is derived from the base-year data; Ginzu treats it as a separate user input with a separate reference benchmark column.

---

## 1.5 Discrepancies vs current code (`data_dictionary.py` + `routes.py` + `capiq_formula_map.py`)

| Area | Current code | Ginzu | Gap |
|---|---|---|---|
| Base-year fields in `CompanyValuationInput` | All 14 Input-sheet base-year fields are present in `raw_financials[0]` + `macro_inputs` | Exactly match | ✅ |
| `operating_margin_next_year` as schema field | Present on `ValuationAssumptions` (but dead per atom audit) | Present on Input!B26 | ✅ field exists; engine read path broken (Stage 4 territory) |
| Override flag pattern | Boolean schema fields (e.g. `override_riskfree: bool`) + value fields (e.g. `riskfree_after_yr10: float`) | Yes/No text cells + value cells | ✅ equivalent — we use booleans, Ginzu uses text; semantically same |
| `revenue_growth_years_2_5` default logic | Not implemented as default — just a field | Implemented via `=B25` formula | ⚠️ when user leaves blank, engine should default to `revenue_growth_next_year` |
| `B34 = Cost of capital worksheet!B13` wiring | Engine computes WACC in M2 separately; Input sheet echoes the computed value for display | Ginzu wires it to the cost-of-capital sheet | ✅ our architecture matches; we separate compute from display |
| Industry-benchmark reference columns I/J/K/L/M/N | Not shown in frontend | Shown alongside user inputs for comparison | ❌ UI feature gap (Phase 5); not a correctness issue |
| `stock_price_std_dev` | We use Damodaran industry default | Ginzu expects user input at B40 | ⚠️ minor fetcher/UX gap |

**Stage 1 code gaps (to feed `project_plan_v2.md`):**

1. **Default for `revenue_growth_years_2_5`:** when the user leaves it blank in the UI, M4 should default to `revenue_growth_next_year` (currently no such fallback; field is entirely dead per atom audit).
2. **Display industry benchmarks on InputSheet.tsx:** implement the I/J/K/L/M/N benchmark columns from the Input Stat Distributioons and Industry Averages tables — nice-to-have, Phase 5 or later.
3. **Add `stock_price_std_dev` as optional user override:** currently implicit via Damodaran industry default — low priority.

---

## 1.6 Stage 1 summary

- **Ginzu Input sheet = 44 user-editable cells + 1 compute formula (B27 = B25 default) + 1 cross-sheet pipe (B34 ← Cost of capital).**
- **CIQ fetch layer fully covers** the base-year financial data Ginzu wants (14/14), and covers options (4/4), lease commitments (6/6), R&D history (10 years). Only `stock_price_std_dev` is not fetched but is substitutable via industry default.
- **LTM sheet is a scratchpad, not a compute node.** Our backend's `ltm_calculator.py` improves on Ginzu by automating what Ginzu asks the analyst to do by hand. The LTM formula itself matches exactly.
- **One textbook omission identified:** `operating_margin_next_year` should be listed explicitly as a Stage 4 input alongside `target_pretax_operating_margin`.
- **One code default missing:** M4 should default `revenue_growth_years_2_5` to `revenue_growth_next_year` when not user-provided.
- **Override-value-cell convention** (Yes/No vs. value-triggered) is ambiguous from the Input sheet alone; Stage 4 must resolve by inspecting Valuation output formulas.

Ready for Stage 2 (R&D + Operating lease converter).
