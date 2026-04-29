# Ginzu vs Backend — One-to-One Comparison Experiment

**Date:** 2026-04-29
**Goal:** Verify our Python valuation engine against Damodaran's Ginzu workbook by running identical test-company inputs through both and comparing every intermediate variable plus the final output, module by module.

**Ground truth:** `knowledge_base/Ginzu_NVIDIA.xlsx` — when recalculated by Excel on Windows, this workbook IS our reference implementation.

**Test companies:** MSFT, BABA, TSLA, LENOVO (files in `TEST_DATA/TEST_*.xlsx`).

---

## Why this is tricky

Linux can't recalc `Ginzu_NVIDIA.xlsx`:
- Windows Excel unavailable
- LibreOffice headless fails to load the file (iterative calc + data-validation extensions)
- Python Excel-engine libraries (pycel/formulas) don't handle Ginzu's iterative calculations reliably

Chosen resolution: **User runs Ginzu on Windows**. Claude prepares input packages + output-cell checklists; user pastes inputs into an Excel-side copy of Ginzu, lets Excel recalc, pastes outputs back. Claude does the comparison side.

---

## Three-phase workflow

### Phase 1 — Claude prepares input packages (offline)

For each of MSFT/BABA/TSLA/LENOVO, produce a file:

```
docs/experiments/ginzu_inputs_<TICKER>.md
```

Each file contains:

**A. Input sheet cells** — a table with columns `cell | label | value` covering rows 3–83 of Ginzu's Input sheet. Values are pulled from the company's `TEST_DATA/TEST_<TICKER>.xlsx` (after running our CIQ parser on it) plus macro/industry data from the Damodaran store. Explicit cell coordinates so no ambiguity where each value goes.

**B. R&D converter inputs** (if `has_r_and_d`): amortization period N (from industry lookup), plus last 5 years of R&D expense (cells B11–B15 or similar in R&D converter sheet).

**C. Operating lease converter inputs** (if `has_operating_leases`): current lease expense + future commitments per year (cells in Lease converter).

**D. Ginzu output cells to record** — a separate table listing ~40 cells I need the user to read back after Ginzu recalcs. Covers:
- Cost of capital worksheet: β_u, β_L, ERP used, Kd pre-tax, W_e/W_d, WACC (B23, B27, B37, C57, B61, B67)
- R&D converter: current R&D amortization, value of research asset (output rows 24–30)
- Lease converter: PV of leases, lease depreciation, adjusted EBIT delta
- Valuation output: PV cash flows, PV terminal, V_operating, V_equity, VPS, price/value ratio (B37–B54)
- Summary Sheet: year-by-year FCFF, cumulative discount factors

### Phase 2 — User runs Ginzu (Windows)

For each ticker, user:
1. Opens `Ginzu_NVIDIA.xlsx`, Save-As `<TICKER>_ginzu.xlsx`.
2. Types/pastes each value from `ginzu_inputs_<TICKER>.md` Section A/B/C into the listed cells.
3. Lets Excel recalculate (ensures iteration is enabled per Ginzu's README note).
4. Fills in the output-cell column of the same `.md` file (or pastes values in chat).

### Phase 3 — Claude runs the comparison (online)

Python script that, per company:
1. Builds `CompanyValuationInput` from the same CIQ data + industry/macro.
2. POSTs to `/api/valuation`.
3. Reads user-provided Ginzu values from the filled-in `.md`.
4. Writes `docs/experiments/ginzu_comparison_<TICKER>.md` with per-module comparison tables:
   - M1 Adjustments (R&D + Leases)
   - M2 Cost of Capital (all intermediate beta/ERP/Kd/weights)
   - M3 Cash Flow & Growth
   - M4 DCF (year-by-year projections, PV sums)
   - M5 Multiples
   - M6 Options & Final VPS

Each row: `variable | ours | ginzu | Δ absolute | Δ % | flag`
where `flag` ∈ {✓ match (<1%), ⚠ small (<5%), ❌ significant (≥5%)}.

5. Writes a consolidated cross-company summary at `docs/experiments/ginzu_comparison_summary.md`.

---

## Scope discipline

- **Observation only.** No backend code changes during the experiment.
- After the experiment, gaps trigger a SEPARATE brainstorming + fix cycle.
- Do NOT "fix" discrepancies live — this corrupts the measurement.

---

## Mapping guide (partial — full cell-level mapping in per-company files)

Source for Ginzu Input sheet mapping (verified by reading `Ginzu_NVIDIA.xlsx`):

| Ginzu cell | Ginzu label | Source field in `CompanyValuationInput` |
|---|---|---|
| B4  | Company name | `company_name` |
| B7  | Country of incorporation | `country` |
| B8  | Industry (US) | `industry_data.industry_name` |
| B9  | Industry (Global) | `industry_data_global.industry_name` |
| B10 | Revenues (this year) | `ltm_financials.revenues` |
| C10 | Revenues (last year) | `raw_financials[1].revenues` |
| D10 | Years since last 10K | `quarters_since_10k / 4` |
| B11 | EBIT (this year) | `ltm_financials.ebit` |
| C11 | EBIT (last year) | `raw_financials[1].ebit` |
| B12 | Interest expense | `ltm_financials.interest_expense` |
| B13 | Book value of equity | `ltm_financials.bv_equity` |
| B14 | Book value of debt | `ltm_financials.bv_debt` |
| B15 | Has R&D? | `adjustment_inputs.has_r_and_d` ("Yes"/"No") |
| B16 | Has operating leases? | `adjustment_inputs.has_operating_leases` |
| B17 | Cash + marketable securities | `ltm_financials.cash_and_marketable_securities` |
| B18 | Cross holdings + non-op assets | `ltm_financials.cross_holdings` |
| B19 | Minority interests | `ltm_financials.minority_interests` |
| B20 | Shares outstanding | `ltm_financials.shares_outstanding` |
| B21 | Current stock price | `ltm_financials.stock_price` |
| B22 | Effective tax rate | `effective_tax_rate_ciq` |
| B23 | Marginal tax rate | `macro_inputs.tax_rate_marginal` |
| B25 | Revenue growth next year | `valuation_assumptions.revenue_growth_next_year` |
| B26 | Operating margin next year | `valuation_assumptions.operating_margin_next_year` |
| B27 | CAGR years 2-5 | `valuation_assumptions.revenue_growth_years_2_5` |
| B28 | Target pre-tax operating margin | `valuation_assumptions.target_operating_margin` |
| B29 | Year of margin convergence | `valuation_assumptions.margin_convergence_year` |
| B30 | Sales/capital years 1-5 | `valuation_assumptions.sales_to_capital_high` |
| B31 | Sales/capital years 6-10 | `valuation_assumptions.sales_to_capital_stable` |
| B33 | Risk-free rate | `macro_inputs.risk_free_rate` |

Assumption overrides (rows 56–83) + option inputs (rows 36–40) mapped in each per-company file.

---

## Risks and mitigations

1. **User miskeys a value** → comparison wrong.
   - *Mitigation:* I produce inputs as a copy-pasteable single column in Ginzu's cell order, not a random-access table. User can bulk-paste into the Input sheet column B.
2. **Ginzu's NVDA workbook has NVDA-specific AI/Auto business segments baked into the "Stories to Numbers" layer.** Our engine doesn't do multi-story DCF.
   - *Mitigation:* For MSFT/BABA/TSLA/LENOVO, user should SKIP the AI/Auto business drivers (rows 42–52) or zero them out. I'll flag which rows are NVDA-specific.
3. **Ginzu's R&D converter expects historical R&D.** Our test data has LTM R&D but not always 5y of history.
   - *Mitigation:* Script reads R&D from multiple FYs in `raw_financials`. If fewer than 5, pad with zeros or note "insufficient data" in the input package.
4. **Operating leases — Ginzu requires future commitments by year.** CIQ templates don't fetch this.
   - *Mitigation:* Mark lease section "N/A" unless user has the data; most test companies don't have meaningful leases anyway.

---

## Success criteria

1. Four per-company input packages delivered with complete cell mappings.
2. After user returns with Ginzu outputs, four comparison reports produced.
3. Consolidated summary identifies the top 3 largest discrepancies across all companies × all modules.
4. For each significant (≥5%) discrepancy, the summary states a hypothesis for the root cause — which is the output this experiment is designed to produce.
