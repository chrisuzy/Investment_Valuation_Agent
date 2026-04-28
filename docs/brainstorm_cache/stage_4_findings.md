# Stage 4 — DCF Core: Ginzu-Truth Findings

**Source sheet:** `Valuation output` — 398 formulas. The heart of the valuation.

**Critical structural finding:** the NVIDIA Ginzu has **THREE parallel FCFF streams** in parallel columns:
- **Rows 1–10: "Rest" segment** (everything not AI or Auto) — this is the canonical single-segment DCF
- **Rows 12–19: AI segment overlay** — NVIDIA-specific market-size × market-share model
- **Rows 21–28: Auto segment overlay** — ditto

The AI+Auto overlay is **NVIDIA-specific**, not canonical Damodaran framework. A generic Ginzu valuation has only one stream (rows 1–10). Our engine should focus on the canonical flow; multi-segment market-sizing is an optional extension.

**Column convention:** B = base year; C–L = years 1–10; M = terminal year (year 11) flows; N = terminal value.

---

## 4.1 — Revenue Path (Row 2, Row 3)

### Revenue growth rate path (Row 2)

Ginzu-form, variable terms:

| Year | Cell | Formula | Meaning |
|---|---|---|---|
| 1 | C2 | `='Input sheet'!B25` | `g_revenue_year_1 = revenue_growth_next_year` |
| 2 | D2 | `='Input sheet'!B27` | `g_revenue_year_2 = revenue_growth_years_2_5` (defaults to year 1 growth) |
| 3–5 | E2, F2, G2 | `=D2`, `=E2`, `=F2` | flat at year-2 growth |
| 6–10 | H2–L2 | `=G2 - ((G2-$M$2)/5) × k` for k=1..5 | **linear convergence from year-5 growth to terminal growth** over years 6–10 |
| Terminal | M2 | `=IF('Input sheet'!B78="Yes", 'Input sheet'!B79, IF('Input sheet'!B75="Yes", 'Input sheet'!B76, 'Input sheet'!B33))` | terminal growth dispatch: **override_perpetuity → override_riskfree → riskfree** |

Terminal growth dispatch in variable form:
```
g_terminal =
  IF override_growth_perpetuity:
    growth_perpetuity_rate
  ELIF override_riskfree:
    riskfree_after_yr10
  ELSE:
    riskfree_rate
```

### Revenue level path (Row 3)

| Year | Cell | Formula | Meaning |
|---|---|---|---|
| Base | B3 | `='Input sheet'!B10 - B14 - B23` | **Rest revenue = total revenue − AI segment revenue − Auto segment revenue**. In canonical single-segment mode, this reduces to `='Input sheet'!B10`. |
| 1–10 | C3–L3 | `=prev × (1 + g_t)` | compounding |
| Terminal | M3 | `=L3 × (1 + M2)` | terminal revenue |

---

## 4.2 — Operating Margin Path (Row 4)

| Year | Cell | Formula | Meaning |
|---|---|---|---|
| Base | B4 | `=B5/B3` | implied from base-year adjusted EBIT / Rest revenue |
| 1 | C4 | `='Input sheet'!B26` | `margin_year_1 = operating_margin_next_year` |
| 2–10 | D4–L4 | `=IF(t > K, target, target - ((target - margin_1) / K) × (K - t))` where K = `'Input sheet'!$B$29` and margin_1 = `$C$4` | linear convergence from year 1 to target over K years |
| Terminal | M4 | `=L4` | terminal margin = year-10 margin (which should equal target if K ≤ 10) |

Variable form (canonical):
```
operating_margin_year_t =
  IF year_t > margin_convergence_year_K:
    target_operating_margin
  ELSE:
    target_operating_margin
    - (target_operating_margin - operating_margin_next_year) × (K - year_t) / K
```

**Ginzu copy bug in NVIDIA workbook:** the **D4** formula references `$C$15` (AI segment margin) instead of `$C$4` (Rest year-1 margin). In the NVIDIA sample both happen to equal 0.65 so the output is correct by coincidence, but the formula is incorrect. **Our implementation should use `$C$4` = operating_margin_next_year universally.** E4..L4 are all correct (use `$C$4`).

---

## 4.3 — Operating Income (Row 5)

Base year (B5) — the adjusted-EBIT assembly formula in variable form:
```
rest_ebit_base_year =
  reported_ebit
  + (has_leases ? lease_adjustment_to_ebit : 0)
  + (has_rd ? rd_adjustment_to_ebit : 0)
  - ai_segment_revenue × ai_segment_margin
  - auto_segment_revenue × auto_segment_margin
```

Where `ai_segment_revenue × ai_segment_margin` and `auto_segment_revenue × auto_segment_margin` subtract the segment-level EBIT, leaving "Rest" EBIT. In canonical single-segment mode, those subtractions are zero.

Years 1–10 (C5..L5) and terminal (M5): `= margin_t × revenue_t` — no compounding of EBIT; **EBIT is always derived from Revenue × Margin**, never compounded independently.

**Our code gap (confirmed):** `module_4_dcf.py` at line 95 uses `ebit_t = ebit_prev × (1 + g)`. **This is wrong.** Ginzu always uses `ebit_t = revenue_t × margin_t`. This is on the atom audit as Task 1.3.

---

## 4.4 — Tax Rate Path (Row 6)

| Year | Cell | Formula | Meaning |
|---|---|---|---|
| Base | B6 | `='Input sheet'!B22` | `tax_rate_base = effective_tax_rate` |
| 1–5 | C6..G6 | `=prev` | flat at effective rate |
| 6–10 | H6..L6 | `=prev + ($M$6 - $G$6)/5` | **linear step-up from year-5 effective to terminal marginal** over 5 years |
| Terminal | M6 | `=IF('Input sheet'!B70="Yes", 'Input sheet'!B22, 'Input sheet'!B23)` | terminal tax: **if override_tax_convergence flag="Yes", keep effective; else use marginal** |

Variable form:
```
tax_rate_year_t =
  IF t ≤ 5:           effective_tax_rate
  IF 5 < t ≤ 10:      tax_rate_year_{t-1} + (tax_terminal - effective) / 5
  Terminal:           IF override_tax_convergence: effective  ELSE: marginal
```

**Our code gap:** M4 uses flat `macro.tax_rate_marginal` for all years. Must implement the convergence path and read `effective_tax_rate_ciq` or `macro.tax_rate_effective`. Atom audit Task 1.6 + 1.7.

---

## 4.5 — NOL Carryforward (Row 10)

| Year | Cell | Formula | Meaning |
|---|---|---|---|
| Base | B10 | `=IF('Input sheet'!B72="Yes", 'Input sheet'!B73, 0)` | `nol_initial = override_nol ? nol_amount : 0` |
| 1–10 | C10..L10 | `=IF(EBIT_t < 0, NOL_{t-1} - EBIT_t, IF(NOL_{t-1} > EBIT_t, NOL_{t-1} - EBIT_t, 0))` | dynamic carryforward |
| Terminal | M10 | `=IF(M5<0, L10-M5, IF(L10>M5, L10-M5, 0))` | terminal-year NOL |

Variable form:
```
nol_end_year_t =
  IF ebit_year_t < 0:
    nol_end_{t-1} - ebit_year_t             # grows (subtracting negative EBIT)
  ELIF nol_end_{t-1} > ebit_year_t:
    nol_end_{t-1} - ebit_year_t             # NOL partially consumed
  ELSE:
    0                                        # NOL fully consumed
```

**Matches textbook Stage 5e exactly.** Our engine has zero NOL handling — atom audit Task 1.8.

---

## 4.6 — After-Tax Operating Income / NOPAT (Row 7) — NOL-Aware

Ginzu-form (C7..L7): `=IF(EBIT_t > 0, IF(EBIT_t < NOL_{t-1}, EBIT_t, EBIT_t - (EBIT_t - NOL_{t-1}) × tax_t), EBIT_t)`

Variable form:
```
nopat_year_t =
  IF ebit_year_t > 0:
    IF ebit_year_t < nol_end_{t-1}:       # NOL absorbs all income
      ebit_year_t                          # (zero tax paid)
    ELSE:                                   # partial absorption
      ebit_year_t - (ebit_year_t - nol_end_{t-1}) × tax_rate_year_t
  ELSE:                                     # operating loss, no tax
    ebit_year_t
```

Which is algebraically: `taxable_income = max(0, ebit - nol_start)`; `tax = taxable × rate`; `nopat = ebit - tax`.

Base year B7: `=IF(B5>0, B5×(1-B6), B5)` — simpler, no NOL (NOL handling kicks in starting year 1).
Terminal year M7: `=M5×(1-M6)` — simpler, no NOL in terminal (assumed fully consumed by year 10).

**Our code gap:** M4 uses `nopat = ebit × (1 - tax)` with no NOL awareness. Must add NOL-gated taxable-income logic. Atom audit Task 1.8.

---

## 4.7 — Reinvestment with Sales-to-Capital and Lag (Row 8)

The single most complex Ginzu formula outside Cost of capital. C8 in variable form:
```
reinvestment_year_1 =
  IF override_reinvestment_lag == "No":                       # default (lag = 1)
    (revenue_year_2 - revenue_year_1) / sales_to_capital_year_1
  ELIF reinvestment_lag_years == 0:                           # anticipated (no lag)
    (revenue_year_1 - revenue_base) / sales_to_capital_year_1
  ELIF reinvestment_lag_years == 2:                           # 1-year delay
    (revenue_year_3 - revenue_year_2) / sales_to_capital_year_1
  ELIF reinvestment_lag_years == 3:                           # 2-year delay
    (revenue_year_4 - revenue_year_3) / sales_to_capital_year_1
  ELSE:                                                        # fallback to default
    (revenue_year_2 - revenue_year_1) / sales_to_capital_year_1
```

### Lag semantics (Damodaran convention)

| `reinvestment_lag_years` | Meaning | Formula for year t reinvestment |
|---|---|---|
| 0 | Anticipated: reinvestment happens AT year t alongside revenue | `(rev_t - rev_{t-1}) / S/C_t` |
| 1 (default, when `B67="No"`) | Standard: year-t capital funds year-(t+1) revenue | `(rev_{t+1} - rev_t) / S/C_t` |
| 2 | Delayed: year-t capital funds year-(t+2) revenue | `(rev_{t+2} - rev_{t+1}) / S/C_t` |
| 3 | Heavily delayed (capex-intensive, e.g. semiconductors) | `(rev_{t+3} - rev_{t+2}) / S/C_t` |

### Edge case: last few years with lag > 0

For lag = 2 or 3, computing reinvestment in years 9 or 10 requires revenue in years 11 or 12. Ginzu projects revenue into those phantom years by extrapolating **at terminal growth rate**:

- K8 (year 9) with lag=3: `M3*M2/K57` ≈ `rev_terminal × g_terminal / S/C_year_9` — interprets `rev_year_12 - rev_year_11 = rev_year_11 × g_terminal × 1 = M3 × M2` (since rev_year_11 grows by g_terminal each year)
- L8 (year 10) with lag=3: `(M3*(1+M2)^2 - M3*(1+M2)) / L57` = `M3 × (1+M2) × M2 / L57` — same pattern, one year further out

### Terminal reinvestment (M8)

`=IF(M2>0, (M2/M59)*M7, 0)` where M59 is ROIC_terminal.

Variable form:
```
reinvestment_terminal =
  IF g_terminal > 0:
    (g_terminal / roic_terminal) × nopat_terminal     # RIR-based
  ELSE:
    0
```

### Sales-to-Capital ratio source (row 57)

Need to decode row 57 separately — it's in the "Implied variables" block below the main DCF. Will address in §4.10. Preview: C57..G57 pull from `'Input sheet'!B30` (years 1–5) and H57..L57 pull from `'Input sheet'!B31` (years 6–10).

**Our code gap:** `module_4_dcf.py` uses `reinvestment = nopat × rir` (fraction of NOPAT based on historical ROIC × RIR). This is the WRONG mechanic. Must switch to ΔRevenue / S/C with lag. Atom audit Task 1.9 (scoped for 60 min — probably needs more).

---

## 4.8 — Free Cash Flow to Firm (Row 9)

Trivial: `FCFF_year_t = NOPAT_year_t - Reinvestment_year_t` for years 1–10 and terminal.

Terminal Value at row 9 column N:
- N9: `=M9 / (M30 - M2)` — Gordon formula: `TV = FCFF_terminal / (WACC_terminal - g_terminal)`.

Where M30 is the terminal WACC (to be decoded in §4.9).

**Our code:** matches.

---

## 4.9 — WACC Path (Row 30 — to decode next sub-task)

From M9's formula, M30 = terminal WACC. Rows 30 for years 1–10 hold the year-by-year WACC path. This is Stage 4.3 territory — will decode next along with discount factors + PV.

---

## 4.10 — Implied Variables Block (Rows 56–59 — will decode in Stage 4.4)

- Row 57: Sales-to-capital ratio path — feeds reinvestment in row 8.
- Row 58: Invested capital path — implied from reinvestment accumulation.
- Row 59: ROIC path — NOPAT / IC_{t-1}.

Row 59 M-column is referenced in M8 (terminal reinvestment). Will decode in the next sub-task.

---

Stage 4.1 complete (rows 1–10 canonical DCF).

---

## 4.11 — Cost of Capital Path (Row 30)

Ginzu-form per year:

| Year | Cell | Formula | Variable form |
|---|---|---|---|
| 1 | C30 | `='Input sheet'!B34` | `wacc_year_1 = initial_wacc` (from Cost of capital worksheet) |
| 2–5 | D30..G30 | `=prev` | flat at initial WACC |
| 6–10 | H30..L30 | `=prev - ($G$30 - $M$30)/5` | **linear convergence from year-5 WACC to terminal WACC over 5 years** |
| Terminal | M30 | `=IF('Input sheet'!B56="Yes", 'Input sheet'!B57, IF('Input sheet'!B75="Yes", 'Input sheet'!B76 + 'Country equity risk premiums'!B1, 'Input sheet'!B33 + 'Country equity risk premiums'!B1))` | (see below) |

Terminal WACC dispatch (M30) in variable form:
```
wacc_terminal =
  IF override_cost_of_capital_stable:                       # B56="Yes"
    cost_of_capital_stable_override                          # B57 (user input)
  ELIF override_riskfree:                                    # B75="Yes"
    riskfree_after_yr10 + mature_market_erp                  # B76 + CountryERP!B1
  ELSE:
    riskfree_rate + mature_market_erp                        # B33 + CountryERP!B1
```

**Critical non-obvious finding:** Ginzu's default terminal WACC is **`RF + mature_market_ERP`** (e.g. 4.7% + 4.33% = 9.03%), **not** the initial WACC, and **not** the industry WACC. This assumes a stable company with β=1 and zero debt leverage — i.e. a pure mature-market risk posture. The textbook MD Section 6 implies terminal WACC defaults to industry stable WACC or the initial WACC; Ginzu does neither.

**Textbook discrepancy:** flag for `textbook_corrections.md`.

**Our engine:** currently treats `wacc_stable = assumptions.cost_of_capital_stable_override or wacc` — defaults to INITIAL WACC, not RF + mature-market ERP. This is a structural difference vs Ginzu. Atom audit Task 1.13.

---

## 4.12 — Cumulative Discount Factors (Row 31)

Ginzu-form:
- C31: `=1/(1+C30)` → `df_1 = 1/(1 + wacc_1)`
- D31..L31: `=prev × (1/(1+wacc_t))` → **year-by-year multiplicative product**

Variable form (canonical):
```
cumulative_discount_factor_year_t = Π_{k=1..t} 1 / (1 + wacc_year_k)
```

**Critical:** Ginzu builds the cumulative product **year-by-year** because WACC varies. A single-WACC closed-form `1/(1+wacc)^t` is wrong once WACC converges in years 6–10. Our engine currently uses the closed form; must switch to year-by-year product. Atom audit Task 1.11.

---

## 4.13 — Present Value of FCFF (Row 32 only — skip 33, 34 segment overlays)

Row 32 (Rest segment, canonical):
- C32..L32: `=FCFF_t × df_t` (cell-wise product)

Value of Rest (row 37):
- B37: `=SUM(C32:L32) + N9*L31` — **sum of 10 PVs + terminal value discounted at year-10 factor**

Variable form:
```
value_of_rest_going_concern =
  Σ_{t=1..10} FCFF_t × cumulative_discount_factor_t
  + terminal_value × cumulative_discount_factor_year_10
```

where `terminal_value = FCFF_terminal / (wacc_terminal - g_terminal)` (N9, per §4.8).

Row 40 "Value as Going Concern" sums Rest + AI + Auto (non-canonical). Canonical form: `value_as_going_concern = value_of_rest_going_concern`.

---

## 4.14 — Failure Probability Overlay (Rows 40–43)

| Variable | Cell | Formula | Variable form |
|---|---|---|---|
| `value_as_going_concern` | B40 | `=SUM(B37:B39)` | (in canonical mode: `= value_of_rest_going_concern`) |
| `probability_of_failure` | B41 | `=IF('Input sheet'!B62="Yes", 'Input sheet'!B63, 0)` | `override_failure_probability ? failure_probability : 0` |
| `distress_proceeds` | B42 | `=IF('Input sheet'!B64="B", (BV_eq + BV_debt) × proceeds_pct, value_going_concern × proceeds_pct)` | see below |
| `value_of_operating_assets` | B43 | `=B40*(1-B41) + B42*B41` | probability-weighted expected value |

Distress proceeds dispatch:
```
distress_proceeds =
  IF failure_tie_to == "B":
    (bv_equity + bv_debt) × distress_proceeds_pct            # book value
  ELSE (failure_tie_to == "V" or default):
    value_as_going_concern × distress_proceeds_pct           # fair value
```

Value of operating assets:
```
value_of_operating_assets =
  value_as_going_concern × (1 - probability_of_failure)
  + distress_proceeds × probability_of_failure
```

**Matches textbook Stage 8 exactly.** Key insight: **failure adjustment happens BEFORE the equity bridge, not after.** Our engine currently applies it AFTER the bridge (atom audit Task 1.15). Ginzu applies to `value_as_going_concern` to produce `value_of_operating_assets`, then the bridge proceeds from there.

Also: Ginzu supports both `failure_tie_to = "B"` (book) and `"V"` (fair value). Our engine only handles "V". Atom audit Task 1.15.

---

## 4.15 — Equity Value Bridge (Rows 44–52)

| Variable | Cell | Formula | Variable form |
|---|---|---|---|
| `minus_debt` | B44 | `=IF(Input!B16="Yes", Input!B14 + lease!C28, Input!B14)` | `debt_total = bv_debt + (if has_leases: lease_PV else 0)` |
| `minus_minority_interests` | B45 | `='Input sheet'!B19` | `minority_interests = Input!B19` |
| `plus_cash` | B46 | `=IF(Input!B81="YES", Input!B17 - Input!B82 × (Input!B23 - Input!B83), Input!B17)` | **trapped cash adjustment** (see below) |
| `plus_non_operating` | B47 | `='Input sheet'!B18` | `cross_holdings = Input!B18` |
| `value_of_equity` | B48 | `=B43 - B44 - B45 + B46 + B47` | `= V_op_assets - debt - minority + cash_usable + cross_holdings` |
| `minus_options` | B49 | `=IF(Input!B36="No", 0, 'Option value'!B29)` | `value_of_all_options = if has_options: Option!B29 else 0` |
| `value_of_equity_in_common` | B50 | `=B48 - B49` | `= value_of_equity - value_of_all_options` |
| `shares_outstanding` | B51 | `='Input sheet'!B20` | pass-through |
| **`value_per_share`** | **B52** | **`=B50 / B51`** | **INTRINSIC VALUE PER SHARE** |
| `market_price` | B53 | `='Input sheet'!B21` | current market price |
| `price_as_pct_of_value` | B54 | `=B53 / B52` | market / intrinsic ratio |

### Trapped cash dispatch (B46)

**Important:** the check is `IF(Input!B81="YES",...)` — **ALL CAPS "YES"**, not "Yes"! This is inconsistent with the other override flags (which use "Yes"). Ginzu quirk — probably a typo Damodaran never fixed. Our engine must accept case-insensitively.

Variable form:
```
cash_usable =
  IF override_trapped_cash (case-insensitive "YES"/"Yes"):
    cash - trapped_cash_amount × (marginal_tax_rate - foreign_tax_rate)
  ELSE:
    cash
```

### Base case equity bridge (variable form)

```
value_of_equity_in_common =
  value_of_operating_assets
  - debt_total
  - minority_interests
  + cash_usable
  + cross_holdings
  - value_of_all_options
```

**Textbook match** for formula structure. Our engine gaps (atom audit Tasks 1.15, 1.16, 1.17):
- Does NOT subtract minority interests (although `raw.minority_interests` is fetched)
- Does NOT add cross_holdings (although `raw.cross_holdings` is fetched)
- Does NOT apply trapped-cash adjustment (although schema has `override_trapped_cash`, `trapped_cash_amount`, `trapped_cash_tax_rate` fields)

---

## 4.16 — Implied Variables Block (Rows 56–59)

### Sales-to-Capital ratio path (Row 57)

- C57: `='Input sheet'!B30` → `s_to_c_year_1 = sales_to_capital_ratio_years_1_5`
- D57..F57: `='Input sheet'!B30` or `=prev` → years 2–4 also at years-1-5 value
- G57: `='Input sheet'!B31` → **step change to `sales_to_capital_ratio_years_6_10` starting year 5 (NOT year 6)**
- H57..L57: `=prev` → years 6–10 at years-6-10 value

Wait — G57 = Input!B31 means year-5 uses the years-6-10 S/C ratio. That's an off-by-one vs textbook (textbook says years 1–5 use high-growth S/C, years 6–10 use stable S/C). Both happen to be 2.5 in the NVIDIA sample so no observable difference, but **this is a Ginzu bug or convention difference**.

Actually, looking more carefully: in the NVIDIA copy `sales_to_capital_ratio_years_1_5 = 2.5` and `sales_to_capital_ratio_years_6_10 = 2.5` (both the same), so the output masks the discrepancy. **Flag as possible Ginzu issue.**

### Invested capital path (Row 58)

Base IC (B58) in variable form:
```
invested_capital_base_year =
  bv_equity
  + bv_debt
  - cash
  + (has_leases ? lease_PV : 0)
  + (has_rd ? value_of_research_asset : 0)
```

Years 1–10 (C58..L58):
- `IC_t = IC_{t-1} + reinvestment_Rest_t + reinvestment_AI_t + reinvestment_Auto_t`

In canonical single-segment mode:
- `IC_year_t = invested_capital_year_{t-1} + reinvestment_year_t`

### ROIC path (Row 59)

- B59 (base year): `= ((rev × margin + AI_segment_rev × AI_margin + Auto_segment_rev × Auto_margin) × (1 - tax)) / IC_base`
  - In canonical: `= adjusted_EBIT × (1 - effective_tax) / IC_base`
- C59..L59: `=NOPAT_year_t / IC_{t-1}` — **note denominator is PRIOR year's IC**
  - In canonical: `ROIC_year_t = nopat_year_t / invested_capital_year_{t-1}`
- M59 (terminal ROIC): `=IF(Input!B59="Yes", Input!B60, #REF!)` — **BROKEN**

### Ginzu bug: M59 terminal ROIC default is `#REF!`

The default branch (when `override_roic_stable = "No"`) returns a `#REF!` error. The NVIDIA copy has `override = "Yes"` so the error never evaluates. **Per textbook convention, the default terminal ROIC should equal terminal WACC** (meaning no excess returns in stable growth). Our engine must:
```
roic_terminal =
  IF override_roic_stable:
    roic_stable_override
  ELSE:
    wacc_terminal    # default = no excess returns
```

**This is a confirmed Ginzu bug.** Flag for `textbook_corrections.md` and implement the correct default in our engine. Atom audit already has this logic in place (Task 1.12 — invested capital tracking includes terminal ROIC defaulting to WACC).

---

## 4.17 — Comparison vs `backend/engine/module_4_dcf.py`

Full gap table, consolidated from Stages 4.1–4.4:

| Ginzu behavior (canonical) | Our code | Gap | Atom audit task |
|---|---|---|---|
| Revenue path: year 1 = `revenue_growth_next_year`, years 2–5 = `revenue_growth_years_2_5` (default = yr1), years 6–10 linear converge to terminal | Uses `cf_metrics.expected_growth_ebit` (historical ROIC × RIR) as primary source, ignoring user inputs | 🔴 wrong source | 1.4, 1.5 |
| Terminal growth dispatch: `override_perpetuity → override_riskfree → riskfree` | Only reads `stable_growth_rate`, ignores override flags | 🔴 incomplete | 1.14, 1.13 |
| Margin path: year-1 margin from `operating_margin_next_year`, linear convergence to `target_operating_margin` by year `margin_convergence_year` | All 3 fields unused; engine compounds EBIT by growth rate | 🔴 completely wrong | 1.1, 1.2, 1.3 |
| Operating Income = Revenue × Margin | `ebit_t = ebit_prev × (1+g)` | 🔴 wrong | 1.3 |
| Tax path: flat at effective for yrs 1–5, linear convergence to marginal yrs 6–10, terminal marginal unless override | Flat marginal for all years | 🔴 wrong | 1.6, 1.7 |
| NOL dynamic carryforward | Not implemented | 🔴 missing | 1.8 |
| Reinvestment = ΔRevenue / S/C with 0–3 year lag | `nopat × rir_firm` (fraction-of-NOPAT method) | 🔴 wrong mechanic | 1.9 |
| FCFF = NOPAT − Reinvestment | matches | ✅ | — |
| Terminal FCFF = NOPAT_T × (1 − RIR_T) where RIR_T = g_T / ROIC_T | matches | ✅ | — |
| Terminal WACC default = RF + mature-market ERP | Defaults to initial WACC | 🔴 wrong default | 1.13 |
| Terminal ROIC default = terminal WACC (Ginzu has #REF! bug, but correct default is WACC) | matches (our engine correctly defaults to wacc_stable) | ✅ | — |
| WACC path: flat yrs 1–5, linear convergence to terminal yrs 6–10 | Single flat WACC for all years | 🔴 missing convergence | 1.10 |
| Cumulative discount factor = year-by-year product | Uses `1/(1+wacc)^t` closed form | 🔴 wrong once WACC varies | 1.11 |
| Terminal value = FCFF_T / (WACC_T − g_T) discounted at year-10 cumulative factor | matches (ok for constant WACC) | ⚠️ needs fix when WACC path added | 1.11 |
| Failure adjustment applied to `value_as_going_concern` → produces `value_of_operating_assets`, BEFORE bridge | Applied to `value_of_equity`, AFTER bridge | 🔴 wrong position | 1.15 |
| `failure_tie_to = "B"` variant: uses (BV_eq + BV_debt) × pct | `failure_tie_to` field entirely unread | 🔴 missing | 1.15 |
| Equity bridge: − debt − minority + cash_usable + cross_holdings − options | − debt + cash − options; missing minority, missing cross, no trapped cash | 🔴 incomplete | 1.16 |
| Trapped cash adjustment: if `override_trapped_cash`, `cash_usable = cash − trapped × (t_marg − t_foreign)` | All 3 fields unread | 🔴 missing | 1.17 |
| Case-insensitive "YES"/"Yes" for override flags | N/A (we use bool schema fields) | ✅ equivalent | — |
| Invested capital path tracked year-by-year | Not tracked | 🔴 missing | 1.12 |
| ROIC path tracked year-by-year | Not tracked | 🔴 missing | 1.12 |
| Segment overlays (AI/Auto) | Not supported | OK (canonical does not need this) | — |

**Confirmed: every gap in the atom audit's Task 1.1 through 1.17 is real against Ginzu.** No atom audit tasks are bogus; a few need elaboration (Task 1.9 reinvestment lag needs 4 branches for lag = 0, 1, 2, 3).

---

## 4.18 — Discrepancies vs `valuation_framework_textbook.md`

| Textbook claim | Ginzu reality | Delta |
|---|---|---|
| Stage 5a revenue growth convergence: "linear from year-5 to terminal over years 6–10" | Ginzu linear convergence matches: `g_t = g_5 − (g_5 − g_T) × (t−5)/5` | ✅ |
| Stage 5b margin convergence: "linear from year 1 margin to target over K years" | Ginzu: `target − (target − margin_1) × (K − t) / K`. Equivalent to textbook formula | ✅ |
| Stage 5c: Operating Income = Revenue × Margin | Matches | ✅ |
| Stage 5d tax convergence: yrs 1–5 effective, yrs 6–10 linear step-up, terminal marginal unless override | Matches Ginzu row 6 | ✅ |
| Stage 5e NOL: `taxable = max(0, EBIT − NOL_start)`, updates per-year | Matches Ginzu row 10 | ✅ |
| Stage 5g reinvestment: `ΔRevenue / S/C` with lag k years | Matches Ginzu row 8 with 0/1/2/3 branches | ✅ |
| Stage 5i WACC convergence: "linear from initial to terminal over years 6–10" | Matches Ginzu row 30 | ✅ |
| Stage 5i terminal WACC: textbook says "default = industry stable WACC"; if `override_riskfree`, "new RF + US mature ERP" | Ginzu default is **`RF + mature-market ERP`** regardless of override — textbook is silent on what happens in the NON-override case | 🔴 **textbook incomplete.** Should explicitly say: default terminal WACC = `riskfree_rate + mature_market_erp` (where mature market ERP = 'Country equity risk premiums'!B1, typically ~4.3%). |
| Stage 5j IC path: `IC_base + Σ reinvestment`; ROIC = NOPAT / prior IC | Matches rows 58, 59 | ✅ |
| Stage 5j IC_base: BV_eq + BV_debt − cash | Ginzu adds lease_PV and R&D_asset_value when applicable | 🔴 **textbook omission.** Should include the R&D asset and lease PV in invested capital (consistent with the adjustments in Stage 2). |
| Stage 6 terminal value: Gordon formula on FCFF_T | Matches N9 | ✅ |
| Stage 7 cumulative discount factors: year-by-year product | Matches row 31 | ✅ |
| Stage 8 failure: apply to going-concern BEFORE bridge, tied to "B" or "V" | Matches rows 40–43 | ✅ |
| Stage 9 equity bridge: − debt − minority + cash + cross − options | Matches rows 44–50 | ✅ |
| Stage 9 trapped cash: subtract `trapped × (t_marg − t_foreign)` | Matches Ginzu B46; note case "YES" vs "Yes" | ✅ (with casing note) |

### Stage 4 textbook corrections (for `textbook_corrections.md`)

1. **Document default terminal WACC as `RF + mature_market_erp`** (not industry WACC or initial WACC).
2. **Document that invested_capital_base includes R&D asset and lease PV** (when those adjustments are applied).
3. **Flag Ginzu bug in M4 D4** — references `$C$15` (AI segment margin) instead of `$C$4` (Rest year-1 margin). Our implementation should use `$C$4` / `operating_margin_next_year` universally.
4. **Flag Ginzu bug in M59** — terminal ROIC default formula has `#REF!` error. Correct default should be terminal WACC.
5. **Flag Ginzu case inconsistency** — trapped cash flag is "YES" (uppercase) while other override flags are "Yes". Our engine accepts both.
6. **Flag Ginzu row 57 off-by-one** — G57 (year 5) uses `sales_to_capital_ratio_years_6_10` instead of years_1_5. Masked by NVIDIA's identical values. Our engine should use years_1_5 for years 1–5 and years_6_10 for years 6–10 per textbook.

---

## 4.19 — Stage 4 summary

- **Canonical Ginzu DCF has 10 rows of compute** (rows 2–10) × 11 columns (C–M) = ~110 core compute cells.
- **Our engine implements ~30% correctly** (FCFF formula, terminal Gordon, basic discount, equity bridge skeleton).
- **17 distinct gaps confirmed**, all matching atom audit Tasks 1.1–1.17.
- **6 textbook corrections identified**, including 3 Ginzu quirks/bugs we should document but NOT replicate.
- **Invested capital composition** (must include R&D asset + lease PV) is the single biggest hidden defect — affects ROIC calculation, which drives terminal reinvestment rate. Addressed implicitly when Task 1.12 is done.
- **Canonical path only:** AI/Auto segment overlays are NVIDIA-specific; skipping.

Ready for Stage 5 (Failure Rate worksheet + Option value).

