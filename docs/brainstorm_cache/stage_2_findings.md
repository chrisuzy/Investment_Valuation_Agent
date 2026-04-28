# Stage 2 — Adjustments (R&D + Operating Leases): Ginzu-Truth Findings

**Source sheets:** `R& D converter` (67 formulas), `Operating lease converter` (25 formulas).
**Purpose:** capitalize R&D as an intangible asset; convert operating leases to debt + depreciation.
**Downstream consumers:** `Input sheet` base-year values (EBIT, BV_Equity, BV_Debt); `Cost of capital worksheet` (uses lease debt in MV_D); `Valuation output` (uses adjusted EBIT for projection).

---

## 2.1 R&D Converter — Variable-Linked Formulas

### Inputs

| Variable | Cell | NVIDIA sample |
|---|---|---|
| `amortization_period_n` | F6 | 5 |
| `r_and_d_expense_current` | F7 | 11,665 |
| `r_and_d_expense_past_t=1..10` | B11, B12, B13, B14, B15, B16, B17, B18, B19, B20 | 8675, 7339, 5268, 3924, 2829, 0, 0, 0, 0, 0 |

NVIDIA amortizes over 5 years, so only B11..B15 (t=1..5) carry real data; B16..B20 are zero.

### Year-index self-computation (A11..A20)

| Cell | Formula | Purpose |
|---|---|---|
| A11 | literal `-1` | year index for first past row (1 year ago) |
| A12 | `=IF((0 - A11) < $F$6, IF(A11 > -1, 0, A11 - 1), 0)` | extends index to -2, -3, ... only if |prev_index| < amort_period |

In variable form:
```
year_index_t = IF(abs(year_index_{t-1}) < amortization_period_n,
                  year_index_{t-1} - 1,
                  0)
```

This means the amortization period controls how many past years are pulled in. For N=5, Ginzu pulls years -1 to -5; for N=10, -1 to -10.

### Per-row compute (rows 24–34)

Row 24 is the "Current" row; rows 25–34 are past years indexed by year_index.

| Output cell | Formula | Variable form |
|---|---|---|
| B24 | `=F7` | `current_rd_for_row_24 = r_and_d_expense_current` |
| C24 | `=1` | `unamortized_fraction_current = 1` (full capitalization of current year) |
| D24 | `=B24*C24` | `unamortized_value_current = r_and_d_expense_current × 1` |
| B25..B34 | `=B11..B20` | `past_rd_row = r_and_d_expense_past_t` (pass-through) |
| A25..A34 | `=A11..A20` | `year_index_row = year_index_t` |
| C25..C34 | `=IF(A_row < 0, ($F$6 + A_row) / $F$6, 0)` | `unamortized_fraction_t = max(0, (N + year_index_t) / N)` |
| D25..D34 | `=B_row * C_row` | `unamortized_value_t = past_rd_t × unamortized_fraction_t` |
| E25..E34 | `=IF(A_row < 0, B_row / $F$6, 0)` | `amortization_this_year_from_t = past_rd_t / N  (zero when year_index=0)` |

**Textbook equivalent (unamortized fraction):** `(N - t) / N` for t = 1..N. Since `year_index_t = -t`, `(N + year_index_t) / N = (N - t) / N`. ✅ **Formulas match exactly.**

### Summation cells

| Variable | Cell | Formula | Textbook form |
|---|---|---|---|
| `value_of_research_asset` | D35 | `=SUM(D24:D34)` | `r_and_d_current + Σ unamortized_value_t` |
| `amortization_r_and_d_total` | E35 | `=SUM(E25:E34)` | `Σ past_rd_t / N` (current row excluded) |
| `adjustment_to_operating_income` | D39 | `=F7 - E35` | `r_and_d_current - amortization_total` (net pre-tax EBIT add-back) |
| `tax_effect_of_r_and_d` | D40 | `=D39 * 'Input sheet'!B23` | `adjustment_to_ebit × marginal_tax_rate` (DISPLAY ONLY — not wired back) |

### Downstream references into this sheet

Where does the rest of the Ginzu read these outputs?

- **`value_of_research_asset` (D35)**: used in `Cost of capital worksheet` as part of Invested Capital for the ROIC denominator (to confirm in Stage 3).
- **`amortization_r_and_d_total` (E35)**: referenced in `Valuation output` row 18 as the "reinvestment baseline" component.
- **`adjustment_to_operating_income` (D39)**: added to `Input sheet!B11` (operating income) conceptually, but mechanically the analyst is expected to add this by hand when entering the adjusted EBIT. Our engine does this automatically in `compute_adjustments()`.
- **`tax_effect_of_r_and_d` (D40)**: display only in this Ginzu. Not wired further.

---

## 2.2 Operating Lease Converter — Variable-Linked Formulas

### Inputs

| Variable | Cell | NVIDIA sample |
|---|---|---|
| `operating_lease_expense_current` | E4 | 295 |
| `operating_lease_commitment_yr1..5` | B7, B8, B9, B10, B11 | 287, 235, 194, 151, 98 |
| `operating_lease_commitment_beyond_yr5` | B12 | 605 |
| `cost_of_debt_pretax` | C15 (formula `='Cost of capital worksheet'!B37`) | 0.0612 |

### Derived: number of additional years beyond year 5

| Variable | Cell | Formula | Variable form |
|---|---|---|---|
| `lease_n_additional_years` | D18 | `=IF(B12>0, ROUND(B12/AVERAGE(B7:B11), 0), 0)` | `n_additional = round(commitment_beyond_yr5 / avg(commitment_yr1..5))` |

NVIDIA: 605 / avg(287, 235, 194, 151, 98) = 605 / 193 = 3.13 → rounds to **3**.

### Per-year discounting (rows 22–27)

| Variable (per year t=1..5) | Cell | Formula | Variable form |
|---|---|---|---|
| `year_index_t` | A22..A26 | `=A7..A11` | 1, 2, 3, 4, 5 |
| `commitment_t` | B22..B26 | `=B7..B11` | pass-through |
| `pv_commitment_t` | C22..C26 | `=B_t / (1+$C$15)^A_t` | `commitment_t / (1 + kd)^t` |

### Beyond-year-5 annuity

| Variable | Cell | Formula | Variable form |
|---|---|---|---|
| `annuity_amount_beyond_yr5` | B27 | `=IF(B12>0, IF(D18>0, B12/D18, B12), 0)` | `beyond_yr5 / n_additional` (if n_additional > 0), **else** `= beyond_yr5 itself` (single lump) |
| `pv_annuity_beyond_yr5` | C27 | `=IF(D18>0, (B27*(1-(1+C15)^(-D18))/C15)/(1+$C$15)^5, B27/(1+C15)^6)` | **Primary path (n_additional > 0):** `(annuity × [1 - (1+kd)^-n_additional] / kd) × (1+kd)^-5`. **Fallback (n_additional = 0):** treat B12 as single payment in year 6: `beyond_yr5 × (1+kd)^-6` |

### Aggregation

| Variable | Cell | Formula |
|---|---|---|
| `debt_value_of_operating_leases` | C28 | `=SUM(C22:C27)` |

NVIDIA: 270.45 + 208.68 + 162.33 + 119.07 + 72.82 + 399.66 = **1,232.998**.

### Restated Financials Block

| Variable | Cell | Formula | Variable form |
|---|---|---|---|
| `depreciation_on_lease_asset` | F31 | `=C28/(5+D18)` | `pv_leases / (5 + n_additional)` — straight-line over total-lease-life |
| `adjustment_to_operating_earnings` | F32 | `=E4-F31` | `lease_expense - depreciation_on_lease_asset` (ADDED to EBIT) |
| `adjustment_to_total_debt` | F33 | `=C28` | `pv_leases` (ADDED to debt) |
| `adjustment_to_depreciation` | F34 | `=C28/(5+D18)` | `pv_leases / (5 + n_additional)` — **identical** to F31 |

**Critical finding:** F31 and F34 are literally the same number. Ginzu separates them to document two logical uses — one is depreciation of the lease asset (deducted from operating income, offsetting the add-back), and the other is the D&A increment to add to reported D&A when computing adjusted cash flow. **Our current engine stores only `depreciation_on_lease_asset` (F31-equivalent) in `AdjustedFinancials` and the atom audit flagged that it is never added to `adjusted_d_a` in `module_3_cashflow.py`.** This matches Task 1.18 in the atom audit.

### Downstream references

- **`cost_of_debt_pretax` (C15)**: pulled from `Cost of capital worksheet!B37`. There is a bootstrapping implication: compute cost of debt first (which itself depends on EBIT, and adjusted EBIT depends on lease adjustment, which needs cost of debt). Ginzu closes the loop via Excel's iterative-calc flag. Our engine uses an initial Kd from Damodaran industry fallback → compute leases → WACC — **single-pass, no iteration loop**. This is an acceptable simplification for Phase 1 but is formally a known Stage 3 feedback loop (textbook Section 13, Loop 2).
- **`debt_value_of_operating_leases` (C28)**: added to MV of debt in `Cost of capital worksheet` (we'll see in Stage 3 that C52 or row 52 references it).
- **`adjustment_to_operating_earnings` (F32)**: added to the adjusted EBIT fed into `Valuation output!B4` (Year 0 margin base).
- **`adjustment_to_depreciation` (F34)**: for auditors — Ginzu doesn't wire this into a cell; it's informational.

---

## 2.3 Comparison to `backend/engine/module_1_adjustments.py`

### R&D Capitalization — line-by-line against Ginzu

| Ginzu | Our code | Match? |
|---|---|---|
| `unamortized_fraction_t = (N + year_idx_t) / N` = `(N - t) / N` | `(n - t) / n` where `t = t_idx + 1` | ✅ |
| `unamortized_value_t = past_rd_t × unamortized_fraction_t` | `unamortized += rd_expense * (n - t) / n` | ✅ |
| `amortization_t = past_rd_t / N` | `amortization += rd_expense / n` | ✅ |
| `value_of_research_asset = current + Σ unamortized_value` | `value_of_research_asset = r_and_d_expense_current + unamortized` | ✅ |
| `adjustment_to_ebit = r_and_d_current - amortization_total` | `adjusted_ebit = adjusted_ebit + current - amortization` | ✅ |
| `tax_effect = adjustment × marginal_tax` (display only) | not computed | ✅ OK (display only) |
| Iteration loop bounded by `amortization_period_n` | `if t > n: break` | ✅ |

**R&D: perfect match. No discrepancies vs Ginzu.**

### Operating Leases — line-by-line

| Ginzu | Our code | Match? |
|---|---|---|
| `n_additional = IF(B12>0, ROUND(B12/AVERAGE(yr1_5), 0), 0)` | `n_additional = max(1, round(beyond / avg_yr1_5))` when `beyond > 0` | 🔴 **Minor divergence.** Ginzu allows `n_additional = 0` (then falls back to single-payment-in-yr6 logic). Our code forces minimum of 1. |
| `annuity_amount = IF(n_additional>0, beyond/n_additional, beyond)` | `annual_annuity = beyond / n_additional` | ⚠️ Our code never hits the n=0 branch because of the max(1, ...) floor above, so effectively equivalent but for a different reason. |
| `pv_commitment_t = commitment_t / (1+kd)^t` (t=1..5) | `pv += op_lease[i] / (1 + kd) ** (i + 1)` | ✅ |
| Primary path: `pv_annuity = (annuity × (1-(1+kd)^-n_add) / kd) / (1+kd)^5` | Year-by-year: `annual_annuity / (1+kd)^year` for year = 6..6+n_additional-1 | ✅ mathematically equivalent (annuity formula = sum of year-by-year discounts) |
| Fallback: `pv_single = beyond / (1+kd)^6` | — not reachable because of max(1, ...) | 🔴 **Our code cannot reproduce Ginzu's single-payment fallback.** Edge case: firms with beyond-yr5 < avg(yr1–5). |
| `debt_value = Σ pv_commitments` | `pv` accumulates | ✅ |
| `depreciation = pv / (5 + n_additional)` | `depreciation_on_lease_asset = pv / total_years` | ✅ |
| `adjustment_to_ebit = lease_expense - depreciation` | `lease_adjustment_to_ebit = lease_expense - depreciation` | ✅ |
| `adjustment_to_debt = pv_leases` | `adjusted_mv_debt = adjusted_mv_debt + pv` | ✅ |
| `adjustment_to_depreciation = pv / (5 + n_additional)` | **not added to adjusted_d_a in M3** | 🔴 confirmed gap (Task 1.18) |

### Edge case: `n_additional = 0` (beyond-yr5 < avg of yr1–5)

**Ginzu behavior:** rounds to 0 → falls back to treating `beyond_yr5` as a single payment in year 6: `pv_single = beyond_yr5 / (1+kd)^6`, combined with the yr1–5 stream. The lease-years-total becomes `5 + 0 = 5` for the depreciation denominator.

**Our behavior:** `max(1, round(...))` forces `n_additional = 1`, which produces an annuity of `beyond_yr5` over 1 year in year 6. In that case `pv_annuity = beyond_yr5 × (1+kd)^-6` — **mathematically identical to Ginzu's fallback**. However, `total_years = 6` in our code vs `total_years = 5` in Ginzu's fallback → our depreciation is `pv/6` vs Ginzu's `pv/5`. **Small but real divergence** (~20% difference in straight-line depreciation for this edge case), affecting lease-heavy firms with small beyond-yr5 lumps.

This is a bug worth a dedicated fix. Severity: low (edge case), but real.

---

## 2.4 Discrepancies vs `valuation_framework_textbook.md`

Walking the textbook's Stage 2 section:

| Textbook claim | Ginzu reality | Delta |
|---|---|---|
| Stage 2a R&D: `Unamortized_Fraction_at_t = (Amortization_Period - t) / Amortization_Period` for t = 1..N | Matches Ginzu's `(N + year_idx)/N` (where year_idx = -t) | ✅ |
| `Value_of_Research_Asset = R&D_current + Σ Unamortized_Value` | Matches D35 `=SUM(D24:D34)` (D24 = current × 1) | ✅ |
| `Total_Amortization = Σ R&D_past_t / N` for t = 1..N | Matches E35 `=SUM(E25:E34)` | ✅ |
| `Adjusted_EBIT = EBIT + R&D_current - Total_Amortization` | Matches D39 = F7 - E35, added to Input!B11 downstream | ✅ |
| `Adjusted_BV_Equity = BV_Equity + Value_of_Research_Asset` | Not in R&D converter sheet itself — applied by analyst to Input!B13 | ✅ (semantically equivalent; our engine does this automatically) |
| Stage 2b Lease: `n_additional = ROUND(Beyond / AVG(Y1..Y5), 0)` with **no** min-1 clause | Matches Ginzu's `IF(B12>0, ROUND(...), 0)`; textbook notes the 0 edge case implicitly | ✅ |
| Step 2: `PV_Yrs_1_5 = Σ commitment_t / (1+kd)^t` | Matches C22..C26 | ✅ |
| Step 3 primary: `PV_Annuity_at_Yr_5 = annuity × [1-(1+kd)^-n_add]/kd`; **`PV_Beyond = PV_Annuity_at_Yr_5 / (1+kd)^5`** | Matches C27 primary branch exactly | ✅ |
| Step 3 edge (n_add = 0): textbook is **silent** about what to do; does not describe the single-payment fallback | Ginzu has an explicit fallback: `beyond / (1+kd)^6` | 🔴 **textbook omission.** The textbook says `n_additional = round(...)` without noting the edge case. Ginzu's fallback behavior (treating B12 as a single yr-6 payment) should be documented. |
| Step 5: `Total_Lease_Years = 5 + n_additional` | Matches | ✅ for primary path; unclear what textbook says for `n_additional = 0` case (should total_years be 5 or 6?) |
| Step 5: `Depreciation = Debt_Value / Total_Lease_Years` | Matches F31 = C28/(5+D18) | ✅ |
| Step 5: `Adjustment_to_EBIT = Lease_Expense - Depreciation` | Matches F32 | ✅ |
| Step 5: `Adjustment_to_Debt = Debt_Value` | Matches F33 | ✅ |
| Step 5: **Missing** — textbook does not mention `Adjustment_to_Depreciation = Debt_Value / Total_Lease_Years` (i.e., the D&A increment) | Ginzu has F34 (same value as F31); the D&A increment is implicitly needed for correct adjusted cash flow | 🔴 **textbook omission.** A lease-heavy firm's adjusted D&A should increase by this amount, but the textbook doesn't say so. Our atom audit already flagged this as Task 1.18. |

### Stage 2 textbook corrections needed

1. **Add edge-case documentation:** when `n_additional = 0` (beyond-yr5 < avg of yr1–5), treat `operating_lease_commitment_beyond_yr5` as a single payment in year 6. `pv_beyond = commitment_beyond_yr5 / (1+kd)^6`. `Total_Lease_Years = 5`.
2. **Add `Adjustment_to_Depreciation` to Stage 2b outputs:** `Depreciation_Increment_for_D&A = Debt_Value_of_Leases / Total_Lease_Years`. This is numerically identical to `Straight_Line_Depreciation_on_Lease_Asset` (the EBIT-offsetting one), but it serves a different purpose — it must be added to reported D&A when computing adjusted cash flow (Stage 5g).

---

## 2.5 Stage 2 code gaps (for project_plan_v2.md)

1. **Fix `n_additional = 0` edge case** in `capitalize_operating_leases()`: remove the `max(1, ...)` floor; add explicit branch for the single-payment-in-yr6 path. Low priority (edge case affects firms with decreasing beyond-yr5 commitments).
2. **Add lease depreciation to `adjusted_d_a` in `module_3_cashflow.py`** (already on the atom audit as Task 1.18). This is the only substantive gap.

Everything else in R&D + lease capitalization matches Ginzu.

---

## 2.6 Stage 2 summary

- **R&D Converter**: 67 formulas decoded. Our implementation matches Ginzu perfectly.
- **Operating Lease Converter**: 25 formulas decoded. Our implementation matches Ginzu for the primary path (n_additional ≥ 1); **one edge case divergence** for `n_additional = 0`. Also **lease depreciation not fed into M3 adjusted D&A**.
- **Two textbook corrections identified:** (1) document the n=0 edge case for leases, (2) document `Adjustment_to_Depreciation` as a Stage 2b output feeding Stage 5g.
- **Two code tasks identified:** (1) fix lease edge case, (2) fix M3 lease-depreciation add-back.

Ready for Stage 3 (Cost of Capital).
