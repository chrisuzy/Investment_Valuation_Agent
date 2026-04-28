# Stage 3 — Cost of Capital: Ginzu-Truth Findings

**Source sheet:** `Cost of capital worksheet` (217 formulas + 105 values), with cross-references to `Synthetic rating` (9 formulas) and `Country equity risk premiums` (202 formulas, mostly reference-table unlocks).

**Structure:** the sheet is divided into **three approaches**. B11 is an approach selector dropdown; B13 dispatches to the appropriate computed cell:

```
B13 = IF(B11="I will input", B12,
     IF(B11="Detailed", E62,
     IF(B11="Industry Average", B67, B72)))
```

where E62 is the Approach-1 detailed WACC, B67 is Approach-2 industry-average-adjusted WACC, and B72 is Approach-3 regional-decile WACC.

---

## 3.1 — Approach 1 Detailed: Inputs

### A. Selector cells (all user-editable text dropdowns)

| Selector | Cell | Options |
|---|---|---|
| `cost_of_capital_approach` | B11 | "I will input" / "Detailed" / "Industry Average" / "Decile" |
| `beta_estimation_approach` | B21 | "Single Business(US)" / "Multibusiness(US)" / "Single Business(Global)" / "Multibusiness(Global)" / "Direct Input" |
| `erp_estimation_approach` | B25 | "Will Input" / "Country of Incorporation" / "Operating countries" / "Operating regions" |
| `cost_of_debt_approach` | B33 | "Direct Input" / "Synthetic Rating" / "Actual Rating" |
| `actual_rating_code` | B35 | e.g. "A+", "BBB" (when B33 = "Actual Rating") |
| `synthetic_rating_company_type` | B36 | 1 = large firm, 2 = small firm (when B33 = "Synthetic Rating") |
| `has_convertible_debt` | — | implicit via B40..B43 values being > 0 |
| `has_preferred_stock` | — | implicit via B48..B50 values being > 0 |

### B. Equity block (rows 18–27)

| Variable | Cell | Formula (variable form) | NVIDIA cached |
|---|---|---|---|
| `shares_outstanding` | B18 | `='Input sheet'!B20` | 24,490 |
| `current_stock_price` | B19 | `='Input sheet'!B21` | 123 |
| `direct_levered_beta_input` | B22 | literal | 1.2 (used only if B21 = "Direct Input"; but Ginzu actually dispatches on unlevered beta branches, not levered — B22 is dormant display-only in practice) |
| `unlevered_beta` | B23 | IF-dispatch (see Table 3.1.C) | 1.46 |
| `riskfree_rate` | B24 | `='Input sheet'!B33` | 0.047 |
| `direct_erp_input` | B26 | literal | 0.06 |
| `equity_risk_premium` | B27 | IF-dispatch (see Table 3.1.D) | 0.0486 |

### C. Unlevered beta dispatch (B23)

Ginzu-form:
```
unlevered_beta =
  IF(beta_approach == "Single Business(US)",
    VLOOKUP(industry_us, 'Industry Averages(US)'!A:G, col=7),
  IF(beta_approach == "Multibusiness(US)",
    K48,
  IF(beta_approach == "Single Business(Global)",
    VLOOKUP(industry_global, 'Industry Average Beta (Global)'!A:G, col=7),
    K64)))
```

Where:
- **Column 7** of Industry Averages(US) is the unlevered beta column.
- **K48** is the multi-business US blended beta (see §3.1.E below).
- **K64** is the multi-business Global blended beta (mirror of K48 for Global).
- **Direct Input (B22)** is NOT wired into B23 — Ginzu actually has five options in the dropdown but B23 only handles four branches. The "Direct Input" case falls through to `K64` by default. **Potential Ginzu bug or intentional: if user picks "Direct Input" but does not use the Multibusiness(Global) fallback, B23 returns K64 which could be wrong.** Our implementation should NOT replicate this; instead we should add a proper Direct Input branch.

Column mapping for Industry Averages sheets:
- Col 7: Unlevered beta
- Col 13: Cost of capital (industry avg)
- Col 15: EV/Sales ratio (used in multi-business EV weighting)

### D. ERP dispatch (B27)

Ginzu-form:
```
equity_risk_premium =
  IF(erp_approach == "Will Input",
    direct_erp_input,
  IF(erp_approach == "Country of Incorporation",
    VLOOKUP(country_of_incorporation, 'Country equity risk premiums'!A:E, col=4),
  IF(erp_approach == "Operating regions",
    K32,
    K18)))
```

Where:
- **Column 4** of Country ERPs is the total ERP (incl. country risk premium embedded). Not broken out into "base ERP + CRP" in the sheet.
- **K18** = operating-countries weighted ERP (see §3.1.E).
- **K32** = operating-regions weighted ERP.

### E. Multi-Business / Multi-Country / Multi-Region weighting

The rows/columns 20–50 and G–L host three parallel weighting blocks:

**Operating Countries ERP (rows 5–18, cols G/H/I/J/K):** user fills G5..G17 with country names, H5..H17 with revenues in that country; Ginzu looks up ERP per country (col I), computes weights (J_i = H_i / H_total, K_i = I_i × J_i), sums K_i = K18. The VLOOKUP column index is 4 (not specified explicitly in my data, but mirrors B27's dispatch).

**Operating Regions ERP (rows 20–32, same columns):** G21..G31 are auto-populated from `'Country equity risk premiums'!A201..A210` (10 predefined regions: Africa, Asia, Australia & NZ, Caribbean, Central/S. America, E. Europe, Middle East, N. America, ..., Western Europe). User fills H21..H31 with revenues in each region; Ginzu auto-looks up ERP per region from `'Country equity risk premiums'!B201..B210`. K32 = sum of weighted ERPs.

**Multi-Business US beta (rows 34–48, cols G/H/I/J/K/L):** Columns:
- G = business segment name (user-entered, e.g. "Semiconductor")
- H = segment revenue (user)
- I = EV/Sales multiple for that industry (VLOOKUP col 15 in Industry Averages(US))
- J = estimated EV = H × I
- K = unlevered beta for that industry (VLOOKUP col 7)
- L = industry cost of capital (VLOOKUP col 13)

Aggregation:
- H48 = SUM(H36:H47) = total revenue across segments
- J48 = SUM(J36:J47) = total estimated EV
- K48 = SUMPRODUCT of K_i × (J_i / J48) = **EV-weighted unlevered beta** — matches textbook "weighted by enterprise value" rule
- L48 = same pattern for cost of capital

**Multi-Business Global beta (rows 50–64):** mirror of 34–48 using Industry Average Beta (Global) instead of Industry Averages(US). Aggregates at row 64: K64 = EV-weighted Global unlevered beta.

### F. Debt block (rows 29–45)

| Variable | Cell | Formula (variable form) | NVIDIA cached |
|---|---|---|---|
| `book_value_of_debt` | B30 | `='Input sheet'!B14` | 10,225 |
| `interest_expense` | B31 | `='Input sheet'!B12` | 249 |
| `weighted_avg_debt_maturity` | B32 | literal (user input) | 3 (years) |
| `direct_cost_of_debt_pretax` | B34 | literal | 0.04 (used if B33 = "Direct Input") |
| `cost_of_debt_pretax` | B37 | IF-dispatch (see Table 3.1.G) | 0.0612 |
| `tax_rate_for_wacc` | B38 | `='Input sheet'!B23` (marginal) | 0.25 |
| `convertible_debt_book` | B40 | literal | 0 |
| `convertible_interest` | B41 | literal | 0 |
| `convertible_maturity` | B42 | literal | 0 |
| `convertible_market_value` | B43 | literal | 0 |
| `debt_value_of_operating_leases` | B45 | `=IF('Input sheet'!B16="Yes", 'Operating lease converter'!F33, 0)` | 0 |

### G. Cost of Debt dispatch (B37)

Ginzu-form:
```
cost_of_debt_pretax =
  IF(kd_approach == "Direct Input",
    direct_cost_of_debt_pretax,
  IF(kd_approach == "Synthetic Rating",
    'Synthetic rating'!D16,
    riskfree_rate + VLOOKUP(actual_rating_code, 'Synthetic rating'!G42:H56, col=2)))
```

Interpretation:
- **Direct Input:** user value from B34.
- **Synthetic Rating:** pulls from `Synthetic rating!D16`, which is the coverage-driven rating-derived spread added to RF. Stage 3.3 will decode the Synthetic rating sheet.
- **Actual Rating:** takes the user's rating string (B35), looks up the spread in the rating→spread table embedded in `Synthetic rating!G42:H56`, then adds to RF.

**Implied feedback loop:** when `B33 = "Synthetic Rating"`, `B37 ← Synthetic rating!D16 ← (interest_coverage = Adjusted_EBIT / Interest_Expense)`, which means **a change to adjusted EBIT ripples through to Kd and thus WACC**. Ginzu closes this by Excel's iterative calc flag.

### H. Key confirmation — Yes/No override convention

From B45:
```
=IF('Input sheet'!B16="Yes", 'Operating lease converter'!F33, 0)
```

**Resolves the Stage 1 open question.** Ginzu formulas **do** check for literal "Yes" strings in the Input sheet's override flag cells. The numeric override-value cells (e.g. B57 terminal WACC override) are dormant unless the paired Yes cell is set. The NVIDIA copy has numeric values entered in override-value cells with the corresponding Yes/No flag BLANK, meaning those overrides are **NOT active** in the current sample valuation. This must be reflected in our engine's read path: check the boolean flag, not just the presence of a numeric value.

### I. Preferred stock block (rows 47–50)

| Variable | Cell | NVIDIA cached |
|---|---|---|
| `number_of_preferred_shares` | B48 | 0 (not applicable to NVIDIA) |
| `preferred_price_per_share` | B49 | 70 (dormant) |
| `preferred_dividend_per_share` | B50 | 5 (dormant) |

Preferred is present in the schema but NVIDIA has zero shares, so the preferred term falls out of WACC.

---

## 3.2 — Approach 1 Detailed: Assembly

### A. Market Value of Debt — bond pricing (C53, C54)

| Variable | Cell | Formula (variable form) |
|---|---|---|
| `mv_straight_debt` | C53 | `= interest_expense × (1 - (1 + kd_pretax)^(-maturity)) / kd_pretax + bv_straight_debt / (1 + kd_pretax)^maturity` |
| `mv_straight_debt_in_convertible` | C54 | `= convertible_interest × (1 - (1 + kd_pretax)^(-conv_maturity)) / kd_pretax + conv_book / (1 + kd_pretax)^conv_maturity` |
| `value_of_debt_in_op_leases` | C55 | `= B45` (pass-through; already IF-gated on Input!B16="Yes") |
| `value_of_equity_in_convertible` | C56 | `= conv_market_value - mv_straight_debt_in_convertible` |

**Textbook match:** this is the Damodaran bond-pricing formula exactly as in our textbook MD Stage 3d. Ginzu applies it twice — once for straight debt, once for convertible.

**Note:** Ginzu computes `mv_straight_debt` using the **pre-tax** cost of debt as yield-to-maturity. Our engine currently uses book value directly (atom audit flagged as 🔴 — Phase 3 Task 3.4).

### B. Levered Beta (C57)

Ginzu-form:
```
levered_beta =
  IF(beta_approach == "Direct Input",
    direct_levered_beta,
    unlevered_beta × (1 + (1 - tax_rate) × (mv_total_debt / mv_equity)))
```

Where `mv_total_debt = C60 = C53 + C54 + C55` (straight + convertible-straight-part + leases) and `mv_equity = B60 = shares × price`.

**Textbook match:** exact formula. Ginzu's "Direct Input" option for levered beta bypasses un-levering altogether.

**Observation:** this is the one place `direct_levered_beta_input` (B22) is actually used — it overrides the unlevering step. My Stage 3.1 analysis suggested B22 was dormant; it is actually live here. Correcting my earlier note.

### C. Market value block (rows 60–62)

| Variable | Cell | Formula (variable form) |
|---|---|---|
| `mv_equity` | B60 | `= shares_outstanding × stock_price` |
| `mv_debt_total` | C60 | `= mv_straight_debt + mv_straight_debt_in_convertible + debt_value_of_operating_leases` |
| `mv_preferred` | D60 | `= number_of_preferred_shares × preferred_price_per_share` |
| `mv_capital_total` | E60 | `= mv_equity + mv_debt_total + mv_preferred` |

### D. Weights (row 61)

| Variable | Cell | Formula |
|---|---|---|
| `weight_equity` | B61 | `= mv_equity / mv_capital_total` |
| `weight_debt` | C61 | `= mv_debt_total / mv_capital_total` |
| `weight_preferred` | D61 | `= mv_preferred / mv_capital_total` |
| check sum | E61 | `= sum(weights) = 1` |

### E. Component costs (row 62)

| Variable | Cell | Formula (variable form) |
|---|---|---|
| `cost_of_equity_capm` | B62 | `= riskfree_rate + levered_beta × equity_risk_premium` |
| `cost_of_debt_aftertax` | C62 | `= cost_of_debt_pretax × (1 - tax_rate)` |
| `cost_of_preferred` | D62 | `= preferred_dividend_per_share / preferred_price_per_share` |
| **`weighted_average_cost_of_capital` (Approach 1 output)** | **E62** | **`= weight_equity × cost_of_equity + weight_debt × cost_of_debt_aftertax + weight_preferred × cost_of_preferred`** |

**Textbook match:** the CAPM, after-tax Kd, and WACC formulas are all textbook-exact.

---

## 3.3 — Approach 2 (Industry Average Adjusted)

B67 formula (one-line), in variable terms:

```
wacc_industry_adjusted =
  IF(industry_approach == "Single Business(US)",
    industry_wacc_us + (riskfree_rate - 3.88%),
  IF(industry_approach == "Multibusiness(US)",
    multi_biz_us_industry_wacc + (riskfree_rate - 3.88%),
  IF(industry_approach == "Single Business(Global)",
    industry_wacc_global + (riskfree_rate - 3.88%),
    multi_biz_global_industry_wacc + (riskfree_rate - 3.88%))))
```

Where:
- **3.88%** is the hard-coded Damodaran base US dollar risk-free rate at the time of publication (2023 start-of-year). This is a TIME-SENSITIVE CONSTANT — it will drift year-over-year with each Damodaran dataset update.
- `multi_biz_us_industry_wacc = L48` (EV-weighted industry WACC computed in the Approach 1 multi-business weighting block).
- `multi_biz_global_industry_wacc = L64`.

**Textbook note:** textbook MD Section 3 "Alternate approaches" Section 2 mentions this but does not specify the **3.88% constant**. This is a textbook correction.

## 3.4 — Approach 3 (Regional Decile)

B72 formula:

```
wacc_decile =
  VLOOKUP(region,
          region×risk_quartile_table (A75:F79),
          col_index = IF(risk_group == "First Decile", 2,
                      IF(risk_group == "First Quartile", 3,
                      IF(risk_group == "Median", 4,
                      IF(risk_group == "Third Quartile", 5, 6)))))
```

The embedded lookup table (rows 75–79) has five regions (Emerging, Europe, Global, Japan, US) × five risk quartiles (First Decile, First Quartile, Median, Third Quartile, Ninth Decile). Values are US-dollar WACC at start of year:

| Region | 1st Decile | 1st Quartile | Median | 3rd Quartile | 9th Decile |
|---|---:|---:|---:|---:|---:|
| Emerging | 0.0741 | 0.0844 | 0.0961 | 0.1099 | 0.1281 |
| Europe | 0.0678 | 0.0765 | 0.0897 | 0.1011 | 0.1152 |
| Global | 0.0689 | 0.0803 | 0.0906 | 0.1031 | 0.1175 |
| Japan | 0.0686 | 0.0783 | 0.0891 | 0.0977 | 0.1091 |
| US | 0.0578 | 0.0687 | 0.0835 | 0.0931 | 0.1005 |

This is static reference data. Unlike Approach 2, there is **no riskfree-adjustment subtraction here** — it just returns the flat regional-decile rate. That's inconsistent with Approach 2's pattern and is a subtle Ginzu design choice the textbook MD doesn't flag.

**Textbook note:** textbook MD Section 3 Alternate Approach 3 describes this as "regional decile lookup" but doesn't document the specific 5×5 values or note the missing RF adjustment. Textbook correction candidate.

---

## 3.5 — Synthetic Rating Sheet

### A. Inputs (pulled from other sheets)

| Variable | Cell | Formula | NVIDIA cached |
|---|---|---|---|
| `firm_type` | C7 | `='Cost of capital worksheet'!B36` | 2 |
| `adjusted_ebit_for_coverage` | F8 | `=IF('Input sheet'!B16="Yes", 'Input sheet'!B11 + 'Operating lease converter'!F32, 'Input sheet'!B11)` | 71,033 |
| `adjusted_interest_for_coverage` | F9 | `=IF('Input sheet'!B16="Yes", CostOfCap!B31 + lease_PV × kd, CostOfCap!B31)` (full formula adds imputed interest on lease debt) | 249 |
| `riskfree_rate` | F10 | `='Input sheet'!B33` | 0.047 |

**Important subtlety:** F8 uses **reported EBIT plus the lease adjustment** (F32 from lease converter), not the fully-adjusted EBIT that includes R&D capitalization. This means synthetic rating uses **EBIT with leases capitalized but NOT with R&D capitalized** — a **different** EBIT from the one used in Approach 1 WACC. Rationale is that Damodaran views R&D-adjusted EBIT as a modeling adjustment, not a "real" operating income for creditor analysis. **Our engine must preserve this distinction** if we implement synthetic rating.

### B. Derivation

| Variable | Cell | Formula (variable form) | NVIDIA cached |
|---|---|---|---|
| `interest_coverage_ratio` | D12 | `=IF(adj_int==0, 1e6, IF(adj_ebit<0, -1e5, adj_ebit/adj_int))` | 285.27 |
| `estimated_bond_rating` | D13 | 3-way IF on firm_type: VLOOKUP(coverage, {large-firm-table | small-firm-table | third-type-table}, col=3) | "Aaa/AAA" |
| `company_default_spread` | D14 | same 3-way IF, col=4 | 0.0069 |
| `country_default_spread` | D15 | `=VLOOKUP('Input sheet'!B7, 'Country ERP'!A5:C196, col=3)` | 0 |
| **`cost_of_debt_pretax_synthetic`** | **D16** | **`= riskfree_rate + company_default_spread + country_default_spread`** | 0.0539 |

Three lookup tables embedded on the Synthetic rating sheet itself:
- **A22:D36** — large firms (C7 = 1): 15 rows covering coverage thresholds from ">8.5" down to "<0.2"
- **A41:D55** — small/riskier firms (C7 = 2): 15 rows with different (lower) thresholds
- **F22:I36** — third type (C7 = 3): likely financial service firms

Table structure (inferred from column references):
- Col A: coverage threshold (lower bound for lookup)
- Col B: coverage threshold (upper bound; optional)
- Col C: rating string ("Aaa/AAA", "Aa1/AA+", etc.)
- Col D: default spread (decimal)

Also at `G42:H56`: a standalone rating-code→spread lookup used by Cost of capital!B37 when B33 = "Actual Rating" (col 2).

### C. Our engine gap

`backend/engine/module_2_risk.py` does not implement synthetic rating at all. `frontend/src/pages/SyntheticRating.tsx` does the math in the UI only (shown, not fed back into the engine). Feedback loop is broken: changing EBIT does not ripple into Kd → WACC.

**Project plan implications:** already on the plan as Phase 2.1/2.2 (synthetic rating + feedback loop).

---

## 3.6 — Country Equity Risk Premiums Sheet

### A. Structure — country table (rows 4–196)

Single formula pattern repeated 192 times:
```
total_erp_country_t = mature_market_erp + country_risk_premium_country_t
```
Ginzu-form: `D_t = $B$1 + E_t` for t = 5..196.

Where:
- **B1** = `Mature Market ERP` — the global base ERP (4.33% in the NVIDIA sample). User-editable.
- **Col A** = country name (user match key)
- **Col B** = `country_risk_group` (region/grouping, used only for regional aggregation)
- **Col C** = country default spread (used in `Synthetic rating!D15`)
- **Col D** = total country ERP (used in `Cost of capital!B27` with VLOOKUP col 4)
- **Col E** = country risk premium (CRP; additive to B1)

### B. Regional aggregates (rows 201–210)

| Row | Region | Total ERP |
|---|---|---|
| 201 | Africa | 10.49% |
| 202 | Asia | 5.40% |
| 203 | Australia & NZ | 4.33% |
| 204 | Caribbean | 10.34% |
| 205 | Central and South America | 7.91% |
| 206 | Eastern Europe | 6.85% |
| 207 | Middle East | 5.89% |
| 208 | North America | 4.33% |
| 209 | Western Europe | 5.16% |
| 210 | Global | 5.37% |

Formula: `B_r = $B$1 + D_r` where D_r is the regional CRP. User matches against region name in the multi-business operating regions block (G21..G31 on Cost of capital worksheet).

### C. Our engine gap

Our `country_risk_parser.py` parses country ERP + CRP + default spread from `ctryprem.xls`. ✅ coverage.

**Regional aggregates**: not currently parsed in our Damodaran layer. Required for Phase 3.3 (multi-country/region ERP blending).

---

## 3.7 — Comparison vs `backend/engine/module_2_risk.py` (Full Stage 3)

Consolidated gap table:

| Ginzu component | Our code | Gap |
|---|---|---|
| Approach 1: Unlevered β — single US | ✅ | — |
| Approach 1: Unlevered β — multi-business US (EV-weighted) | ❌ | Phase 3.1 |
| Approach 1: Unlevered β — single Global | ✅ (via region param) | — |
| Approach 1: Unlevered β — multi-business Global | ❌ | Phase 3.1 |
| Approach 1: Unlevered β — Direct Input | ❌ | trivial add |
| Approach 1: Direct Input for LEVERED β (bypasses un-levering) | ❌ | trivial add |
| Approach 1: ERP — Country of Incorporation | ✅ | — |
| Approach 1: ERP — Operating Countries (revenue-weighted) | ❌ | Phase 3.3 |
| Approach 1: ERP — Operating Regions (revenue-weighted) | ❌ | Phase 3.3 + parse regional rows |
| Approach 1: ERP — Will Input (direct) | ❌ | trivial add |
| Approach 1: Kd — Direct Input | ⚠️ (falls through to industry fallback) | should be explicit |
| Approach 1: Kd — Actual Rating + rating→spread table | ❌ | need to load `ratings.xls`; Phase 3 task |
| Approach 1: Kd — Synthetic Rating (coverage→rating→spread, firm-type-aware) | ❌ | need to load `synthrating.xls`; Phase 2.1 |
| Approach 1: Synthetic uses lease-adjusted-only EBIT (not R&D-adjusted) | ❌ | bug risk once synthetic is implemented |
| Approach 1: Synthetic adds country default spread to firm spread | ❌ | small detail |
| Approach 1: MV of straight debt via bond pricing | ❌ | Phase 3.4 |
| Approach 1: MV of convertible debt (bond pricing of straight part) | ❌ | new (not in current plan) |
| Approach 1: MV of convertible equity part | ❌ | new (not in current plan) |
| Approach 1: Preferred stock shares/price/dividend → MV + weight + cost | ❌ | Phase 3.5 |
| Approach 1: Levered β formula | ✅ | — |
| Approach 1: CAPM (Ke) | ✅ | — |
| Approach 1: After-tax Kd | ✅ | — |
| Approach 1: WACC 3-term blend (E+D+P) | ⚠️ 2-term only | Phase 3.5 |
| Approach 2: Industry-Average adjusted (−3.88% then +user RF) | ❌ | Phase 3 (not priority; user has Approach 1) |
| Approach 3: Regional Decile lookup (5×5 table) | ❌ | Phase 3 (not priority) |
| Feedback loop: synthetic rating ↔ EBIT ↔ WACC | ❌ (single-pass) | Phase 2.1 |

---

## 3.8 — Discrepancies vs `valuation_framework_textbook.md`

| Textbook claim | Ginzu reality | Delta |
|---|---|---|
| Stage 3a: 5 beta variants | Ginzu has 5 in the dropdown but the dispatch formula (B23) only branches 4 ways; "Direct Input" falls through to Multibusiness(Global) | 🔴 **Ginzu quirk/bug.** Textbook should document the fix: use B22 (direct input) when beta_approach = "Direct Input". Don't replicate the quirk. |
| Stage 3a multi-business β: weight by EV = revenue × EV/Sales | Matches K48 formula exactly | ✅ |
| Stage 3b: 4 ERP variants (incl. Will Input) | Matches | ✅ |
| Stage 3b country-of-incorporation ERP = total ERP (lookup col 4 of country table) | Matches | ✅ |
| Stage 3c synthetic rating uses `Adjusted_EBIT` | Ginzu uses **lease-adjusted EBIT but NOT R&D-adjusted EBIT** | 🔴 **textbook ambiguity** — must clarify which EBIT is used for coverage. Ginzu's choice is to capitalize leases first (since those are debt-like) but not R&D (since that is modeling-sanity, not creditor-analysis). |
| Stage 3c synthetic uses small-firm vs large-firm tables, selector based on market cap threshold ($5B) | Ginzu uses firm-type dropdown (1=large mfg, 2=small/risky, 3=likely financial), NOT a size threshold | 🔴 **textbook incorrect on selection criterion.** The $5B threshold is Damodaran's *rough guidance*, but Ginzu's actual implementation lets the user pick firm type directly. |
| Stage 3c: Cost of debt = RF + firm default spread + country default spread | Matches D16 formula | ✅ |
| Stage 3d MV of debt via bond pricing | Matches C53 | ✅ |
| Stage 3d MV of debt treats convertibles | Textbook MD is silent on convertibles | 🔴 **textbook omission.** Add convertible bond pricing + convertible-equity split (`equity_in_conv = conv_market - straight_in_conv`). |
| Stage 3f: preferred stock weight | Ginzu includes in 3-term WACC | ✅ |
| Stage 3g: weights = MV_i / sum MV | Matches row 61 | ✅ |
| Stage 3h: levered β = β_U × (1 + (1-t) × D/E) | Matches C57 primary branch | ✅ |
| Stage 3h: levered β direct-input bypass | Ginzu supports via C57's IF branch | ✅ (textbook silent; both do it) |
| Stage 3i: CAPM (Ke = RF + β_L × ERP) | Matches B62 | ✅ |
| Stage 3j: after-tax Kd = Kd_pretax × (1-t) | Matches C62 | ✅ |
| Stage 3k: WACC = w_E × Ke + w_D × Kd_after_tax + w_P × Kp | Matches E62 | ✅ |
| Stage 3 alternate approach 2: industry-avg WACC with RF adjustment | Matches B67, but textbook doesn't specify the **3.88% constant** | 🔴 **textbook incomplete.** The 3.88% is the Damodaran-base US RF at publication — it drifts annually and must be refreshed from the dataset, not hard-coded in perpetuity. |
| Stage 3 alternate approach 3: regional decile | Matches B72 but textbook doesn't mention the **absence of RF adjustment** in approach 3 (inconsistent with approach 2) | 🔴 **textbook omission + Ginzu design note.** Flag the inconsistency. |
| Stage 3 feedback loop: synthetic rating ↔ Kd ↔ WACC | Textbook MD Section 13 notes the loop; Ginzu implements it via Excel iterative calc | ✅ acknowledged |

### Stage 3 textbook corrections (to add to `textbook_corrections.md`)

1. **Document Ginzu's `Direct Input` beta dispatch bug** — and prescribe the correct behavior for our implementation.
2. **Clarify which EBIT feeds synthetic rating** — lease-adjusted EBIT only, NOT R&D-adjusted. This is a material implementation detail.
3. **Replace the $5B-threshold rule** in Stage 3c with user-selected firm type (large / small / financial).
4. **Document convertible debt handling** in Stage 3d: bond-price the straight-debt component; subtract straight-debt-MV from market-value-of-convertible to get the equity component.
5. **Document the hard-coded 3.88% constant** in Approach 2 — and note it must be refreshed annually from Damodaran's dataset.
6. **Flag the Approach-3-no-RF-adjustment** design choice as an internal Ginzu inconsistency.
7. **Add regional-aggregate table** (rows 201–210) to the canonical Damodaran dataset list — currently in our plan as "country ERP blender" but the region rows are a separate data subset.

---

## 3.9 — Stage 3 summary

- **Our `module_2_risk.py` is 69 lines** and implements ~15% of what Ginzu's Cost of capital worksheet does. Approach 1 single-business, single-country, book-value-debt, two-term WACC — the baseline only.
- **20+ distinct Stage 3 gaps** catalogued above, already mostly mapped to existing Phase 2 and Phase 3 tasks in the old plan, but with significant elaboration needed (convertible debt, regional aggregates, EBIT-for-coverage nuance, Ginzu direct-input dispatch bug).
- **7 textbook corrections identified** (§3.8), including one possible Ginzu bug (beta dispatch) that we should not replicate.
- **Feedback loop risk:** synthetic rating ↔ Kd ↔ WACC is a known Excel iterative-calc dependency. Our engine must either (a) iterate to fixed point or (b) document the single-pass approximation. Phase 2.1/2.2 tasks.
- **Data gaps identified:** need to load `ratings.xls` (rating→spread) and `synthrating.xls` (coverage→rating) Damodaran files, and parse the regional-aggregate rows of `ctryprem.xls`.

Ready for Stage 4 (DCF core — the 398-formula Valuation output sheet).


---

## 3.7 — Comparison vs `backend/engine/module_2_risk.py` (Stage 3.2 subset)

Gap table for what 3.2 covered:

| Ginzu Approach 1 component | Our code | Gap? |
|---|---|---|
| MV of straight debt via bond pricing (C53) | Uses `raw.mv_debt` ≈ book value; no bond-repricing | 🔴 |
| MV of convertible debt (C54) | Not in schema | 🔴 |
| Debt value of operating leases into MV_D (C55) | Added to `adjusted.adjusted_mv_debt` | ✅ |
| Levered beta formula (C57) | Matches | ✅ |
| Direct-input levered beta bypass | Not supported | ❌ |
| MV equity = shares × price (B60) | Implicit via `raw.mv_equity` from CIQ | ✅ |
| Preferred stock MV (D60) | Not in schema | ❌ |
| Weights (row 61) | Computed for equity + debt only | ⚠️ preferred not included in weights |
| Cost of equity CAPM (B62) | Matches | ✅ |
| After-tax Kd (C62) | Matches | ✅ |
| Cost of preferred (D62) | Not computed | ❌ |
| **WACC formula (E62)** — three-term blend | Two-term blend (equity + debt) | ⚠️ preferred term missing |
| Approach 2 (industry-avg adjusted) | Not implemented | ❌ |
| Approach 3 (regional decile) | Not implemented | ❌ |

**Stage 3.2 gaps feed project_plan_v2.md Phase 3:**
1. Bond-pricing for MV of debt (Phase 3.4 in current plan)
2. Convertible debt schema + bond pricing (new — not currently in any phase)
3. Preferred stock schema + WACC term (Phase 3.5 in current plan)
4. Direct-input levered beta bypass (trivial addition)
5. Approaches 2 and 3 (low priority; user can always pick Approach 1)

