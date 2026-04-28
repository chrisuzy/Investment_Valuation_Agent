# Textbook Corrections — `valuation_framework_textbook.md` vs Ginzu Truth

**Purpose:** a flag-only list of every place `docs/valuation_framework_textbook.md` diverges from the actual Ginzu NVIDIA workbook. Per user instruction, this document **does not auto-edit** the textbook — it catalogs discrepancies for per-item user review.

**Usage:** read each entry, decide whether to (a) edit the textbook MD in place to match Ginzu, (b) keep the textbook claim (if Ginzu is itself wrong/quirky), or (c) keep both and annotate the textbook with the Ginzu variant.

**Format:** each entry shows the stage, the textbook claim (verbatim or paraphrased), the Ginzu reality, the severity, and a recommendation.

**Sources for this document:**
- `docs/brainstorm_cache/stage_{1..6}_findings.md` — per-stage discrepancy sections
- `docs/brainstorm_cache/ginzu_extracted.json` — the ground-truth formula corpus
- `docs/ginzu_spec_v2.md` — the reconciled spec

**Legend:**
- 🔴 Material — affects numerical output or implementation correctness
- 🟡 Clarifying — doesn't change the number but textbook is incomplete/ambiguous
- 🔵 Ginzu quirk — Ginzu is the one diverging (bug or inconsistency); textbook is OK as-is

---

## Stage 1 (Inputs + LTM)

### 1.1 🟡 `operating_margin_next_year` is a separate input, not derived

**Textbook says:** Stage 4 / Section 2.D lists `Target_Pre_Tax_Operating_Margin` but does not explicitly list `operating_margin_next_year` as an input. The reader might assume year-1 margin is derived from base-year adjusted EBIT / revenue.

**Ginzu reality:** Input!B26 is a distinct user input ("Operating Margin for next year"), separate from Input!B28 (target margin). Both are required; year-1 margin is the starting point of the margin convergence path in §6.2.

**Recommendation:** add `operating_margin_next_year` to the Stage 4 inputs table in the textbook MD. Describe margin convergence as "linear from `operating_margin_next_year` (year 1) to `target_pretax_operating_margin` (year K)". The base-year margin computed from historicals is a **reference benchmark**, not an input.

---

## Stage 2 (R&D + Operating Leases)

### 2.1 🟡 Document `n_additional = 0` edge case in lease conversion

**Textbook says:** Stage 2b Step 1 — `Number_of_Additional_Years_Beyond_Five = ROUND(Beyond / AVERAGE(Year1..Year5), 0)`. Silent on what happens when the result rounds to 0 (i.e., when `commitment_beyond_yr5` < half of `AVERAGE(yr1..yr5)`).

**Ginzu reality:** When `n_additional = 0`, Ginzu falls back to treating `commitment_beyond_yr5` as a **single lump payment in year 6**: `pv_beyond = commitment_beyond_yr5 / (1 + kd)^6`. Total lease years = 5 (not 6).

**Recommendation:** add a "Step 1b" to textbook Stage 2b noting the fallback. Formula block:
```
IF n_additional == 0:
    annuity_treatment = single_payment
    pv_beyond = commitment_beyond_yr5 × (1 + kd)^(-6)
    total_lease_years = 5
```

### 2.2 🟡 Missing: `Adjustment_to_Depreciation` as a Stage 2b output

**Textbook says:** Stage 2b Step 5 lists `Adjustment_to_EBIT`, `Adjustment_to_Debt` as outputs, plus `Straight_Line_Depreciation_on_Lease_Asset` as an intermediate.

**Ginzu reality:** Ginzu also emits `Adjustment_to_Depreciation` (cell F34) = `debt_value_of_leases / total_lease_years`. Numerically identical to `depreciation_on_lease_asset`, but semantically it's the D&A increment to apply in Stage 5g / Module 3 reinvestment diagnostics. Our `adjusted_d_a` must include this when leases are capitalized.

**Recommendation:** add `Adjustment_to_Depreciation_from_Leases` to Stage 2b outputs. Note that numerically = `Straight_Line_Depreciation_on_Lease_Asset`, but it serves a different role (adjusts cash-flow depreciation, separate from the EBIT offset).

---

## Stage 3 (Cost of Capital)

### 3.1 🔵 Ginzu `B23` unlevered beta dispatch omits "Direct Input" branch

**Textbook says:** Stage 3a lists 4 variants (single/multi × US/Global) plus optional "direct input".

**Ginzu reality:** the Ginzu B23 IF-formula only has 4 branches — "Direct Input" falls through to Multibusiness(Global). The levered-beta Direct Input path (C57) DOES work. The unlevered Direct Input path is effectively unreachable in Ginzu.

**Recommendation:** **do not replicate this Ginzu bug.** Our engine should have an explicit Direct-Input branch for unlevered beta. Flag in textbook only as a note: "Ginzu has a dispatch bug here; implement the 5th branch explicitly."

### 3.2 🟡 Which EBIT feeds synthetic rating?

**Textbook says:** Stage 3c — synthetic rating uses `Adjusted_Operating_Income` to compute interest coverage.

**Ginzu reality:** Ginzu's Synthetic rating!F8 uses **lease-adjusted EBIT only** — NOT R&D-adjusted. Formula:
```
ebit_for_coverage = reported_ebit + (has_leases ? lease_adjustment_to_ebit : 0)
```
R&D capitalization is deliberately excluded because R&D adjustments are modeling sanity checks, not creditor-relevant operating income.

**Recommendation:** clarify in textbook Stage 3c that the "Adjusted_EBIT" feeding synthetic rating is lease-adjusted only, not R&D-adjusted.

### 3.3 🟡 Synthetic rating small vs large firm selection is firm-type, not size-threshold

**Textbook says:** Stage 3c mentions using small-firm vs large-firm tables, with selection "based on market cap threshold ($5B)" or similar size rule.

**Ginzu reality:** Ginzu's C7 firm_type is a user-editable input with three options (1 = large manufacturing, 2 = small/riskier, 3 = likely financial service). No automatic size-based selection.

**Recommendation:** textbook should say "user selects firm type from {large manufacturing, small/risky, financial service}" rather than describing an automatic size threshold.

### 3.4 🟡 Convertible debt handling

**Textbook says:** Stage 3d MV of debt is computed via bond-pricing for straight debt. Silent on convertibles.

**Ginzu reality:** Ginzu has explicit convertible-debt handling (rows 40–43 + 54, 56). The convertible is decomposed into:
- **Straight debt part:** priced as a bond using Kd_pretax
- **Equity part:** `conv_market_value - straight_debt_part`

Both are added to `mv_debt_total`, with the equity part treated as additional equity claim (not debt claim). (Though in Ginzu's implementation, both parts sum into mv_debt_total C60 via rows 53–55; the equity split is displayed at C56 but not mechanically separated.)

**Recommendation:** add Stage 3d.2 "Convertible Debt Decomposition" to textbook, showing the bond-price decomposition and the equity-part residual.

### 3.5 🟡 Approach 2 uses a hard-coded Damodaran-base RF constant

**Textbook says:** Stage 3 Alternate Approach 2 — "Industry_Average_WACC + (Current_Risk_Free - Industry_Base_Risk_Free)".

**Ginzu reality:** Ginzu B67 hard-codes **3.88%** as the Industry_Base_Risk_Free — this is Damodaran's US treasury rate at publication (2023 edition). Drifts annually and must be refreshed from the Damodaran dataset metadata.

**Recommendation:** add a note that "Industry_Base_Risk_Free" is a time-sensitive constant from the Damodaran dataset, typically distributed as metadata. Don't hard-code.

### 3.6 🔵 Approach 3 lacks RF adjustment

**Textbook says:** Stage 3 Alternate Approach 3 — "regional decile lookup".

**Ginzu reality:** unlike Approach 2, Approach 3 returns the flat regional-decile rate with **no** riskfree adjustment. Internally inconsistent with Approach 2.

**Recommendation:** flag as Ginzu internal inconsistency. Our implementation should apply the same RF adjustment pattern as Approach 2 to Approach 3, and document the deviation from Ginzu.

### 3.7 🟡 Mature Market ERP is a separate Damodaran dataset value

**Textbook says:** terminal-WACC dispatch references "US_Mature_Market_ERP" without specifying where it comes from.

**Ginzu reality:** Country ERP!B1 is a user-editable cell that represents the mature market ERP (currently ~4.33%). All country ERPs are computed as `$B$1 + country_crp_in_column_E`. This is the Damodaran base ERP, refreshed annually.

**Recommendation:** state that `mature_market_erp` is the Damodaran base ERP (sourced from ctryprem.xls row 1 of data region, or equivalent metadata).

### 3.8 🟡 Regional aggregate rows as separate dataset subset

**Textbook says:** Stage 3b lists "Country of Incorporation", "Operating Countries", "Operating Regions" as variants.

**Ginzu reality:** Ginzu's Country ERP sheet has country rows 5–196 AND 10 regional aggregate rows 201–210 (Africa, Asia, Australia & NZ, Caribbean, Central/S America, E Europe, Middle East, N America, W Europe, Global). Our current `country_risk_parser.py` parses only the country rows.

**Recommendation:** add a Stage 3b.4 section describing the 10 regional aggregates. Also add a task to parse these rows in our Damodaran layer.

---

## Stage 4 (DCF Projection) — largest concentration of corrections

### 4.1 🔴 Default terminal WACC is `RF + mature_market_erp`, not industry WACC

**Textbook says:** Stage 5i — terminal WACC "converges to terminal" over years 6–10. Implies default terminal WACC is either industry stable WACC or initial WACC.

**Ginzu reality:** Ginzu M30 default is:
```
wacc_terminal =
  IF override_cost_of_capital_stable: user_override
  ELIF override_riskfree:             new_rf + mature_market_erp
  ELSE:                               current_rf + mature_market_erp
```
This implies a company at maturity has beta = 1 and zero net debt (thus no tax shield effect) — a pure mature-market risk posture.

**Recommendation:** add to Stage 5i:
> "By default, terminal WACC = `riskfree_rate + mature_market_erp`, representing a mature company with market-average equity risk and negligible debt structure. Override with `cost_of_capital_stable_override` for firms with specific maturity risk profile."

This is the **most material textbook correction** — it directly affects every valuation.

### 4.2 🟡 Invested capital base should include R&D asset and lease PV

**Textbook says:** Stage 5j — `Invested_Capital_Base = Adjusted_Book_Value_of_Equity + Adjusted_Book_Value_of_Debt - Cash`.

**Ginzu reality:** Ginzu B58 adds R&D asset and lease PV **on top of** the bv_equity+bv_debt−cash base. The "Adjusted" in the textbook is ambiguous.

**Recommendation:** make explicit:
```
invested_capital_base =
  bv_equity
  + bv_debt
  - cash
  + (has_leases ? debt_value_of_operating_leases : 0)
  + (has_rd    ? value_of_research_asset         : 0)
```

### 4.3 🔵 Ginzu D4 margin formula bug

**Textbook says:** Stage 5b margin convergence from `operating_margin_next_year`.

**Ginzu reality:** D4 formula references `$C$15` (AI segment margin) instead of `$C$4` (canonical year-1 margin). Masked in NVIDIA sample since both = 0.65.

**Recommendation:** **do not replicate.** Textbook needs no change. Flag for our engine: use `operating_margin_next_year` universally (C$4-equivalent).

### 4.4 🔵 Ginzu M59 terminal ROIC #REF! bug

**Textbook says:** Stage 5j — terminal ROIC defaults to cost of capital (no excess returns) if not overridden.

**Ginzu reality:** M59 formula has `#REF!` in the default branch (broken). Masked by NVIDIA setting override = "Yes". The correct default, per textbook, is `wacc_terminal`.

**Recommendation:** **do not replicate.** Textbook is correct. Flag for our engine: default `roic_terminal = wacc_terminal`.

### 4.5 🔵 "YES" vs "Yes" case inconsistency in trapped cash flag

**Textbook says:** override flags consistently "Yes"/"No".

**Ginzu reality:** B81 (trapped cash override) checks for uppercase "YES" while all other flags use "Yes". A Ginzu typo Damodaran never fixed.

**Recommendation:** **do not replicate** — normalize case-insensitively.

### 4.6 🔵 Ginzu G57 S/C path off-by-one

**Textbook says:** Stage 4 — `sales_to_capital_ratio_years_1_5` for years 1–5, `sales_to_capital_ratio_years_6_10` for years 6–10.

**Ginzu reality:** G57 (year 5) uses `sales_to_capital_ratio_years_6_10`. Masked in NVIDIA since both = 2.5.

**Recommendation:** **do not replicate.** Textbook is correct. Ginzu's boundary is off by one.

---

## Stage 5 (Failure + Options)

### 5.1 🟡 Option dilution starting point: market vs. intrinsic

**Textbook says:** Stage 9 Option Dilution Step 1 — "Stock_Price_Pre_Dilution = Current_Stock_Price (from market)".

**Ginzu reality:** Ginzu seeds the iteration with **market price** (Input!B21). Matches textbook if "from market" is taken literally.

**Our current code:** seeds with **intrinsic per-share value** (computed DCF output pre-options). Diverges from Ginzu.

**Design decision:**
- Ginzu: options-holders' claim = what market would currently pay → subtract from DCF equity
- Our code: options-holders' claim = what options are worth if DCF is right → subtract from DCF equity

Both produce the same answer when market = intrinsic; different when they diverge.

**Recommendation:** clarify in textbook which seed to use. Per Damodaran's actual workbook → use market price. Update our engine or keep it as a documented deviation.

### 5.2 🟡 Failure probability input path

**Textbook says:** Stage 8 — failure probability "estimated from bond rating, corporate age, interest coverage".

**Ginzu reality:** two reference lookup tables are provided (rating-based cumulative default probability by time horizon, and age+industry failure probability from BLS data). But **the analyst manually picks a value** and types it into Input!B63. No automated derivation.

**Recommendation:** clarify in textbook Stage 8: "The Failure Rate worksheet provides two reference lookup tables to help the analyst choose a probability; the chosen value is entered as a direct user input." Our engine correctly treats it as a direct input.

---

## Stage 6 (Derived views)

No new textbook corrections — the derived views are display layers and don't introduce new formulas beyond what Stages 1–5 cover.

Note: the Diagnostics sheet does suggest two useful metrics not currently in textbook or our DCFResult:
- `pv_of_nopat_10yr` (pre-reinvestment value)
- `value_effect_of_reinvestment_10yr` (= pv_of_nopat_10yr - pv_of_fcff_10yr)

These are helpful diagnostics (showing whether reinvestment creates or destroys value) but not strictly framework corrections. Consider adding to Stage 13 of ginzu_spec_v2.md (already included).

---

## Summary Counts

| Category | Count |
|---|---:|
| 🔴 Material corrections | **1** (default terminal WACC formula) |
| 🟡 Clarifications/additions | **10** (op margin input, lease edge case, lease depreciation output, EBIT for coverage, firm type selection, convertibles, Approach 2 RF constant, mature market ERP source, regional aggregates, IC base composition, option seed, failure probability path — note some overlap) |
| 🔵 Ginzu quirks to NOT replicate | **6** (beta Direct Input, Approach 3 no RF, D4 margin bug, M59 ROIC #REF!, YES casing, G57 S/C off-by-one) |

**One item — 4.1 default terminal WACC — is the highest-impact correction** because it affects every valuation's terminal value, which is typically 50–75% of total firm value.

---

## Next steps for this document

The user's tiebreaker policy is **"flag, do not decide"**. Each entry above is a decision request. Options for each:

1. **Accept Ginzu:** edit `valuation_framework_textbook.md` to match Ginzu. Discard this entry from this document.
2. **Reject Ginzu:** keep textbook as-is; note in `ginzu_spec_v2.md` §15 "Ginzu Quirks to NOT Replicate" (already done for 🔵 items).
3. **Merge both:** keep textbook prose but add "Ginzu variant:" sidebar.

Once decisions are made, this document can be archived.

---

*End of `textbook_corrections.md`.*
