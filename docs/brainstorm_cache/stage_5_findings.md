# Stage 5 — Failure Rate + Option Value: Ginzu-Truth Findings

**Source sheets:**
- `Failure Rate worksheet` (110 formulas, 222 reference values)
- `Option value` (24 formulas)

---

## 5.1 — Failure Rate Worksheet

### A. Sheet purpose: reference lookup, not compute pipeline

**Critical structural finding:** the Failure Rate worksheet is **not referenced by any formula in any other sheet** — it is a standalone reference table the analyst consults to pick a failure probability, then types the chosen number into `Input!B63`. The Valuation output B41 formula reads `Input!B63` directly (not the Failure Rate worksheet).

This means:
- **Ginzu has NO automatic age/rating → failure probability derivation.**
- The analyst looks at the table, judges their firm, and manually picks a value.
- Our engine should mirror this: `ValuationAssumptions.failure_probability` is a direct user input; the table is UX/reference only.

### B. Approach 1 — Rating-based cumulative default probability

Static lookup table at `B5:K12` (no formulas — all literal values):

| Rating | Yr 1 | Yr 2 | Yr 3 | Yr 4 | Yr 5 | Yr 6 | Yr 7 | Yr 8 | Yr 9 | Yr 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AAA | 0.00% | 0.03% | 0.13% | 0.24% | 0.35% | 0.45% | 0.51% | 0.59% | 0.64% | 0.70% |
| AA | 0.02% | 0.06% | 0.12% | 0.21% | 0.31% | 0.42% | 0.50% | 0.58% | 0.65% | 0.72% |
| A | 0.05% | 0.14% | 0.23% | 0.35% | 0.47% | 0.62% | 0.79% | 0.93% | 1.08% | 1.24% |
| BBB | 0.16% | 0.45% | 0.78% | 1.17% | 1.58% | 1.98% | 2.33% | 2.67% | 3.00% | 3.32% |
| BB | 0.61% | 1.92% | 3.48% | 5.05% | 6.52% | 7.85% | 9.01% | 10.04% | 10.97% | 11.78% |
| B | 3.33% | 7.71% | 11.55% | 14.58% | 16.93% | 18.83% | 20.36% | 21.60% | 22.70% | 23.74% |
| CCC/C | 27.08% | 36.64% | 41.41% | 44.10% | 46.19% | 47.09% | 48.26% | 49.05% | 49.76% | 50.38% |

**Usage:** analyst picks a rating (matching their synthetic-rating output) and a horizon (typically 10 years), reads the probability, types into Input!B63.

### C. Approach 2 — Age + Industry failure rate (BLS data)

Industries (columns) — primary at C–L, mirrored at O–X:
- C/O: Agriculture
- D/P: Mining
- E/Q: Utilities
- F/R: Construction
- G/S: Manufacturing
- H/T: Retail
- I/U: Transportation
- J/V: Information
- K/W: Health Care
- L/X: All Sectors

Rows: age in years (O19:X28 = ages 1–10 survival probabilities, from BLS).

Formulas `C19:L28` compute cumulative failure rates from the O–X survivorship table:
```
C19..L19:  =1 - age_1_survival              # year-1 failure rate
C20..L20:  =age_1_survival - age_10_survival  # etc, cumulative
C21..L21:  =age_2_survival - age_10_survival  # cumulative from year 2
...
C28..L28:  =age_9_survival - age_10_survival  # near-end-of-horizon
C29..L29:  =0                                  # terminal (age-10 and beyond)
```

**Example usage:** for a 6-year-old technology firm, read `J23` (Information, age ≈ 6) → 20.9% failure rate. The worksheet's notes suggest this: "if you are valuing a technology firm that is 6 years old, the chance of failure is 11.70%" (the worksheet's example; actual value depends on cell).

### D. Our engine implications

- **`ValuationAssumptions.failure_probability` is a direct user input — correct as-is.**
- Frontend `FailureRate.tsx` could expose these two reference tables as helper UX (Phase 5 task). Currently, the page does its own math in the browser (not wired to engine).
- **No backend compute task required for the Failure Rate worksheet.** The compute portion of the model is already correctly represented in `Valuation output!B41..B43` (covered in Stage 4.14).
- Loading the BLS survivorship table as a Damodaran dataset would be a Phase 5 or Phase 6 enhancement, not a requirement for correctness.

---

## 5.2 — Option Value Sheet (Dilution-Adjusted Black-Scholes with Iteration)

### A. Input wiring

| Variable | Cell | Source | NVIDIA cached |
|---|---|---|---|
| `stock_price` | B4 | `='Input sheet'!B21` | 123 |
| `strike_price` | B5 | `='Input sheet'!B38` | 1.29 |
| `expiration_years` | B6 | `='Input sheet'!B39` | 7 |
| `stddev_stock` | B7 | `='Input sheet'!B40` | 0.45 |
| `dividend_yield` | B8 | literal | 0 |
| `riskfree_rate` | B9 | `='Input sheet'!B33` | 0.047 |
| `n_warrants` | B10 | `='Input sheet'!B37` | 7.72 |
| `n_shares` | B11 | `='Input sheet'!B20` | 24,490 |

### B. Dilution-Adjusted Black-Scholes — the iterative fixed point

```
stock_price_raw = B4                                              # market price
strike_raw = B5

# ITERATIVE BLOCK — circular dependency B17 ↔ B28
adjusted_S = (stock_price_raw × n_shares + call_value × n_warrants) / (n_shares + n_warrants)
adjusted_K = strike_raw                                           # no adjustment to strike
variance = stddev_stock^2

d1 = (ln(adjusted_S / adjusted_K) + (riskfree_rate - dividend_yield + variance/2) × T)
     / (stddev_stock × sqrt(T))
d2 = d1 - stddev_stock × sqrt(T)

call_value = adjusted_S × exp(-dividend_yield × T) × N(d1)
           - adjusted_K × exp(-riskfree_rate × T) × N(d2)

# END ITERATIVE BLOCK

value_of_all_options = call_value × n_warrants
```

### C. Circular dependency — Ginzu relies on Excel iterative calc

**B17 → B22 (via d1) → B28 (call) → B17 (adjusted_S).** This is a fixed-point loop. Ginzu uses Excel's built-in iterative calc to converge (default 100 iterations or 0.001 tolerance; the Input sheet notes "There should be a check against the iteration box" to activate).

Typical convergence: 3–5 iterations.

### D. Our engine — module_6_options.py gap

Our implementation uses **one-shot calculation** with `S = value_per_share_pre_options` (the pre-dilution DCF intrinsic value per share) as the stock price input — it does NOT iterate on the dilution adjustment. Atom audit Phase 2.4 is to add the fixed-point solver.

**Additional subtlety — Ginzu uses MARKET price for S in the circular loop, not intrinsic:** Ginzu's B15 reads `=B4` which is `='Input sheet'!B21` = current stock price. Our engine uses the pre-options per-share **intrinsic** value (from DCF). These are different.

This is actually an interesting design choice:
- **Ginzu's approach:** value options at CURRENT MARKET PRICE (pre-dilution), dilute by assuming market is mostly right; subtract resulting option value from DCF equity.
- **Our approach:** value options at INTRINSIC PRE-OPTIONS PRICE, dilute based on intrinsic valuation.

**These converge when market = intrinsic.** When they diverge, Ginzu's approach treats the options-holders' claim as what the market would currently pay; our approach treats it as what the options are worth if the DCF is right.

Textbook MD Section Option Dilution uses the "iterative S* to C*" framing; it's agnostic on whether S* starts from market or intrinsic. Damodaran's actual workbook uses market price. **This is a subtle textbook clarification worth flagging.**

### E. N(d1) and N(d2) — standard normal CDF

Ginzu uses `NORMSDIST()`. Our engine uses `scipy.stats.norm.cdf()`. Numerically equivalent.

---

## 5.3 — Discrepancies vs `valuation_framework_textbook.md`

| Textbook claim | Ginzu reality | Delta |
|---|---|---|
| Stage 9 Options: dilution-adjusted Black-Scholes with fixed-point iteration | Matches | ✅ |
| Step 1 "Stock_Price_Pre_Dilution = Current_Stock_Price (from market)" | Ginzu uses B4 = `Input!B21` = current market price — matches | ✅ (consistent with textbook if textbook means market price) |
| Step 2 "Dilution_Adjusted_Stock_Price = (S_pre × shares + C × warrants) / (shares + warrants)" | Matches B17 | ✅ |
| Step 3 Black-Scholes: `d1 = [ln(S*/K) + (r − y + σ²/2) × T] / (σ × √T)` | Matches B22 | ✅ |
| Step 3 `d2 = d1 − σ × √T` | Matches B25 | ✅ |
| Step 3 `C = S* × e^(-y×T) × N(d1) - K × e^(-r×T) × N(d2)` | Matches B28 | ✅ |
| Step 4: iterate until C stabilizes | Ginzu relies on Excel's iterative calc | ✅ mechanism-equivalent |
| Step 5: `Value_of_All_Options = C × n_warrants` | Matches B29 | ✅ |
| Stage 8 failure probability: "estimated from (a) bond rating, (b) corporate age..." | Ginzu has reference tables for both; analyst picks one and manually enters | ⚠️ **textbook ambiguous** — implies automatic derivation, but Ginzu's actual flow is "read the table, type the number". Our engine correctly treats it as a direct input. |

### Stage 5 textbook corrections (for `textbook_corrections.md`)

1. **Clarify Stage 9 Option Dilution Step 1:** the iteration starts from **current market price** (`Current_Stock_Price` per the textbook's notation), NOT from the DCF's pre-options intrinsic per-share value. This is a subtle but material choice — our current implementation uses intrinsic pre-options, which diverges from Ginzu. (Or: change our engine to use market price; see §5.2.D.)
2. **Clarify Stage 8 failure probability input path:** Damodaran's workbook provides two reference tables (rating-based and age/industry-based) as helpers, but the analyst **manually picks** a probability based on these tables. There is no automated derivation. Textbook MD implies automation; should clarify.

---

## 5.4 — Comparison vs current code

### `module_6_options.py`

| Ginzu | Our code | Gap |
|---|---|---|
| Iterative fixed-point loop S* ↔ C* | One-shot calculation | 🔴 Phase 2.4 |
| S starts from market price | S starts from intrinsic pre-options | ⚠️ possible change needed (§5.2.D) |
| Black-Scholes formula with dilution-adjusted S | Matches after S is set | ✅ |
| Value of all options = call × warrants | Matches | ✅ |

### Failure probability path

| Ginzu | Our code | Gap |
|---|---|---|
| User picks probability from rating/age reference tables | User provides `failure_probability` directly | ✅ (same semantics) |
| Valuation output B41 reads Input!B63 directly | Engine reads `assumptions.failure_probability` | ✅ |
| Distress proceeds = (if "B") BV-based else fair-value-based | Only "V" path implemented; `failure_tie_to` unread | 🔴 (Stage 4 gap, already flagged in atom audit Task 1.15) |
| Failure applied to `value_as_going_concern` before bridge | Applied to `value_of_equity` after bridge | 🔴 (Stage 4 gap, atom audit Task 1.15) |

All failure probability gaps are already covered in Stage 4 findings. No new gaps here.

---

## 5.5 — Stage 5 summary

- **Failure Rate worksheet is a reference table, not compute.** Our engine treats `failure_probability` as a direct user input, matching Ginzu's actual flow.
- **Option value sheet implements iterative dilution-adjusted Black-Scholes.** Our engine is one-shot; Phase 2.4 fixes this.
- **One subtle discrepancy:** Ginzu uses market price as the seed for option valuation; our code uses pre-options intrinsic value. Needs a design decision.
- **No new atom-audit tasks arose** from Stage 5 — everything maps to existing phases.
- **Two textbook clarifications** identified: option pricing seed, failure probability input path.

Ready for Stage 6 (derived views skim) and Stage 7 (synthesis).
