# Three-Story Closed-Loop Consistency Test + Lenovo Anomaly Fixes — Design Spec

**Date:** 2026-05-04
**Status:** Draft for user review
**Source documents:**
- `docs/Ginzu understanding/module_05_dcf_projection.md` (core philosophy + inputs)
- `docs/Ginzu understanding/module_06_terminal_and_pv.md` (terminal mechanics)
- `docs/Ginzu understanding/module_03_operating_leases.md` + `module_02_rd_capitalization.md` (IC composition)
- User's Damodaran "Narrative and Numbers" brief pasted in brainstorm session
- Backend: `module_3_cashflow.py`, `module_4_dcf.py`, `data_dictionary.py`
- Frontend: `InputSheet.tsx`, `ValuationOutput.tsx`, `lib/baseYear.ts`

---

## 1. Purpose

Two coupled deliverables in one spec because they touch the same files and share data structures:

**A. Three-Story Closed-Loop Consistency Test (primary).** Implement Damodaran's *Narrative and Numbers* framework: every valuation is the composition of three independent analyst stories (Growth, Margin, Capital Efficiency) that mathematically imply a fourth quantity — Implied ROIC. Cross-check that Implied ROIC against historical ROIC and WACC to surface narrative inconsistencies the moment the analyst finishes entering their story.

**B. Lenovo-specific anomaly fixes (secondary).** Seven issues surfaced while auditing the Lenovo upload — tax rate override, reinvestment defaults, base-year fallback, Key Drivers completeness, scope tooltips. Folded into this spec because the UI work for (A) naturally subsumes several of them (particularly Issue 5b).

## 2. Core philosophy — what the folder actually says

Directly cited from `module_05_dcf_projection.md §2`:

> *"The analyst's judgment is concentrated in the high-growth story — how aggressive the growth is, how fat the margins become, how efficiently capital is deployed. The convergence toward maturity is mechanical; the terminal state defaults to sensible values (growth at the risk-free rate, ROIC equal to WACC meaning no excess returns)."*

> *"Growth — tells a story about market opportunity and market share. Margin — tells a story about competitive position and pricing power. Sales-to-capital — tells a story about capital efficiency."*

Distilled:
- DCF projects a story; analyst authors it; Ginzu extends it mechanically.
- Three stories are independently authored but **arithmetically coupled** — the implied ROIC is the closing link.
- Historical data serves two roles only: anchoring the base year (LTM), and providing diagnostic benchmarks.
- Convergence to maturity is mechanical; terminal defaults to zero-excess-returns.

A silent fallback that substitutes `ROIC × RIR` for a blank analyst growth input (as `module_4_dcf.py:231-233` currently does) **contradicts this philosophy** and will be removed as part of this work.

## 3. The Three Stories — formulas

All formulas match the existing backend where it exists; any deltas are explicit.

### 3.1 Story 1 — Growth

**Analyst inputs (already in schema):**
- `revenue_growth_next_year`
- `revenue_growth_years_2_5` (single flat value; folder `module_05 §3.1`)

**Per-year revenue path:**
```
Revenue[t] = Revenue[t-1] × (1 + g_revenue[t])

g_revenue[1]    = revenue_growth_next_year
g_revenue[2..5] = revenue_growth_years_2_5 (or year-1 if blank — folder default)
g_revenue[6..10] = linear convergence from g_revenue[5] → g_terminal
g_terminal       = min(riskfree_after_yr10 override, risk_free_rate)
```

### 3.2 Story 2 — Margin

**Analyst inputs (already in schema):**
- `operating_margin_next_year` (Year 1)
- `target_operating_margin`
- `margin_convergence_year` K (default 5)

**Per-year margin path (folder `module_05 §3.2`):**
```
Margin[1]         = operating_margin_next_year
Margin[t] for 1<t≤K = target − (target − Margin[1]) × (K − t) / K
Margin[t] for t>K  = target_operating_margin
```

**Derived EBIT and its growth:**
```
EBIT[t]                 = Revenue[t] × Margin[t]
Expected_Growth_EBIT[t] = EBIT[t] / EBIT[t-1] − 1
```

⚠️ **Terminology discipline:** `Expected_Growth_EBIT[t]` as computed here is a *top-down derived* quantity from the three stories. It is distinct from the historical-derived `expected_growth_ebit = ROIC × RIR` currently in `CashFlowMetrics`. Both will exist; we will rename the historical one for clarity (see §7).

### 3.3 Story 3 — Capital Efficiency

**Analyst inputs (already in schema):**
- `sales_to_capital_high` (years 1–5)
- `sales_to_capital_stable` (years 6–10)

**Per-year reinvestment (folder `module_05 §3.6`):**
```
Reinvestment[t] = (Revenue[t+lag] − Revenue[t+lag−1]) / S/C[t]
```
Lag defaults to 1 (folder default).

**Invested-capital roll-forward:**
```
Invested_Capital[0] = Adjusted_Invested_Capital (base year, from Module 3)
Invested_Capital[t] = Invested_Capital[t-1] + Reinvestment[t]
```

### 3.4 Closed-loop output — Implied ROIC

```
NOPAT[t]        = EBIT[t] × (1 − tax_rate[t])
Implied_ROIC[t] = NOPAT[t] / Invested_Capital[t-1]
```

This is the quantity the analyst does NOT input; it is algebraically forced by the three stories. The consistency checks in §4 below cross-examine `Implied_ROIC[t]` against historical ROIC and WACC.

## 4. Consistency checks

Each check produces a `ValidationSignal`. Severities:
- `INFO` — informational, green/emerald badge
- `SOFT_WARNING` — amber badge, consider revising
- `HARD_WARNING` — orange badge, strong suggestion to revisit story
- `RED_FLAG` — red badge, story has serious internal inconsistency

### Check A — Year-1 growth vs. historical fundamental growth

```
historical_fundamental_g = historical_ROIC × historical_RIR
delta = Expected_Growth_EBIT[1] − historical_fundamental_g

|delta| < 2pp                  → INFO        "story aligned with history"
2pp ≤ |delta| < 10pp           → SOFT_WARN   "departs from history — explain"
|delta| ≥ 10pp                 → HARD_WARN   "large narrative jump — what structural change justifies this?"
```

### Check B — Implied ROIC vs. historical ROIC (trajectory)

For each year t in 1..10:
```
If Implied_ROIC[t] > 2 × historical_ROIC        → HARD_WARN
If Implied_ROIC[t] > 3 × historical_ROIC        → RED_FLAG   "capital-efficiency miracle required"
If Implied_ROIC[t] < 0.5 × historical_ROIC      → SOFT_WARN  "deteriorating capital efficiency — intentional?"
```

### Check C — Implied ROIC vs. WACC (value creation)

For each year t during the high-growth period (1..5):
```
spread[t] = Implied_ROIC[t] − WACC[t]

spread[t] < 0                                       → HARD_WARN  "growth destroys value in year t"
spread[t] > 20pp sustained for 5+ consecutive years → HARD_WARN  "sustained super-normal returns — what is the moat?"
```

### Check D — Terminal invariants

```
|terminal_growth − risk_free_rate| > 0.5pp                     → RED_FLAG
|Implied_ROIC_terminal − WACC_terminal| > 2pp (unless override) → RED_FLAG
```

This enforces Damodaran's "no excess returns in perpetuity" rule (folder `module_06`).

### Check E — Reinvestment feasibility

For each year:
```
reinvestment_rate[t] = Reinvestment[t] / NOPAT[t]

reinvestment_rate[t] > 1.0  → HARD_WARN  "firm must raise external capital — is that in the story?"
reinvestment_rate[t] < 0    → SOFT_WARN  "firm is shrinking capital base while growing revenue — unusual"
```

## 5. Architecture — data flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ CIQ Template (Lenovo.xlsx) — historical data only                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ read_ciq_template (tools/) — parse formulas, extract historical       │
│   - annual[0..4] revenue, EBIT, tax, CapEx, D&A, balance sheet        │
│   - quarterly[0..3] for LTM rotation                                  │
│   - effective_tax_rate_ciq, stock_price, shares, etc.                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ routes.py::fetch_from_file                                           │
│   - build RawFinancials[] (5 yrs), LTM, MacroInputs                  │
│   - NEW: tax_history: compute [yr_0..yr_4] effective + 3/5yr avg     │
│   - construct CompanyValuationInput with empty ValuationAssumptions  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ orchestrator.run_full_valuation                                      │
│                                                                       │
│   Module 1 — adjustments (R&D, leases)                                │
│   Module 2 — cost of capital (WACC)                                   │
│   Module 3 — cashflow: historical NOPAT, IC, ROIC, RIR,               │
│              historical_fundamental_g = ROIC × RIR                    │
│   Module 4 — DCF projection with NEW outputs:                         │
│              • margin_projections[] (expose the ramp)                 │
│              • tax_rate_projections[] (per-year applied rate)         │
│              • wacc_projections[] (per-year WACC path)                │
│              • implied_roic_projections[] (closed-loop)               │
│              • implied_roic_terminal                                  │
│   Module 5 — multiples                                                │
│   Module 6 — options                                                  │
│   Module 7 — NEW: consistency checks                                  │
│              run_consistency_checks(dcf, cf, wacc) → signals[]        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ValuationResponse (augmented)                                         │
│   - inputs, dcf, cashflow, multiples, final (existing)                │
│   - tax_history (NEW)                                                 │
│   - consistency_signals: list[ValidationSignal] (NEW)                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frontend                                                              │
│   InputSheet.tsx                                                      │
│     - NEW "Historical diagnostics" block (calc rows):                 │
│         NOPAT, IC, ROIC, Reinvestment, RIR, historical_fundamental_g  │
│     - NEW inline diagnostic badge next to each of 3 story input cells │
│     - NEW "Story Consistency Panel" section showing triggered signals │
│     - NEW "Closed-Loop Summary" strip at top showing Implied ROIC vs  │
│           historical ROIC vs WACC at year 5 and terminal              │
│     - NEW Tax-override sub-panel (Issue 1):                           │
│         5 historical yr rates + 3/5yr avg + preset buttons            │
│   ValuationOutput.tsx                                                 │
│     - Key Drivers section mirrors every InputSheet hypothesis input   │
│       as manually-adjustable (Issue 5b)                               │
│     - Derived paths (margins 2..K, per-year tax, per-year WACC) as    │
│       read-only diagnostic rows                                       │
│     - Base-year reinvestment filled with historical (Issue 2b)        │
│     - Vintage badge on every base-year cell (Issue 3)                 │
│   OptionValue.tsx                                                     │
│     - σ_stock tooltip clarifying scope (Issue 5a)                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 6. File-by-file change list

### Backend

| File | Change | Scope |
|---|---|---|
| `backend/engine/data_dictionary.py` | Add `ValidationSignal`, `ConsistencyResult` classes. Add `tax_history` model. Extend `DCFResult` with `margin_projections`, `tax_rate_projections`, `wacc_projections`, `implied_roic_projections`, `implied_roic_terminal`. Rename `CashFlowMetrics.expected_growth_ebit` → `historical_fundamental_growth` to disambiguate (breaking; update all consumers). Add `effective_tax_rate_override_years_1_5: float \| None` to `ValuationAssumptions`. | ~60 lines added, 1 field rename |
| `backend/engine/module_4_dcf.py` | **Remove** the cascade fallback at lines 231-233 (`g_year_1 = ... or cf_metrics.expected_growth_ebit or g_terminal`). Replace with blank-stays-blank: if analyst hasn't entered growth, surface a `ValidationSignal.INFO("Growth not set — using 0% placeholder; please enter your story")` and use 0 for the calculation. Same pattern for margin and S/C defaults. Expose `margin_projections`, `tax_rate_projections`, `wacc_projections`, `implied_roic_projections` in DCFResult. Wire `effective_tax_rate_override_years_1_5` into `_tax_path`. | ~80 lines changed |
| `backend/engine/module_7_consistency.py` | **NEW.** `run_consistency_checks(dcf: DCFResult, cf: CashFlowMetrics, cost: CostOfCapital, assumptions: ValuationAssumptions) -> ConsistencyResult`. Implements Checks A–E from §4. | ~150 lines new |
| `backend/engine/orchestrator.py` | Call `run_consistency_checks` after Module 4. Attach result to the `ValuationResponse`. | ~10 lines |
| `backend/api/routes.py` | In `fetch_from_file` and `upload_direct`: compute `tax_history` from `annual[0..4]` tax_exp/EBT. Include in response payload. | ~30 lines |
| `backend/tests/test_three_story_consistency.py` | **NEW.** 5 fixtures (one per check A–E) triggering each severity level; one "all clean" fixture producing zero HARD/RED signals; terminal invariant test. | ~200 lines new |

### Frontend

| File | Change | Scope |
|---|---|---|
| `frontend/src/types.ts` (or wherever `ValuationResponse` is typed) | Add `ValidationSignal`, `ConsistencyResult`, `tax_history` types. Extend `DCFResult` with new projection arrays. | ~30 lines |
| `frontend/src/pages/InputSheet.tsx` | Add: (a) "Historical diagnostics" calc-row block showing NOPAT/IC/ROIC/Reinv/RIR/historical_fundamental_g; (b) inline diagnostic badges next to each of 3 story input cells (growth, margin, S/C) showing the historical reference; (c) "Story Consistency Panel" section rendering `consistency_signals`; (d) "Closed-Loop Summary" strip at top; (e) Tax-override sub-panel with 5yr/3yr averages and preset buttons. | ~400 lines added |
| `frontend/src/pages/ValuationOutput.tsx` | Expand Key Drivers to mirror every InputSheet hypothesis input as editable (Issue 5b). Add derived-path rows (margin 2..K, per-year tax, per-year WACC, Implied_ROIC[t]) as read-only diagnostic rows. Fill `reinvestment[0]` with historical value (Issue 2b). Add vintage badge to every base-year column cell (Issue 3). | ~300 lines changed |
| `frontend/src/pages/OptionValue.tsx` | Add tooltip on `stock_price_std_dev` display: "Used only in Black-Scholes option valuation (Module 8)." (Issue 5a) | ~5 lines |
| `frontend/src/components/ConsistencySignal.tsx` | **NEW.** Single row renderer: severity badge + message + expandable numeric breakdown + "Go to input" link that scrolls to the correct cell. | ~80 lines new |
| `frontend/src/components/ClosedLoopSummary.tsx` | **NEW.** Strip showing Implied_ROIC[5], Implied_ROIC[terminal], historical ROIC, WACC, pass/fail checks. | ~80 lines new |
| `frontend/src/lib/baseYear.ts` | Extend to return per-field vintage source ("LTM" / "10-K" / "10-K-1"). Used by ValuationOutput base-year vintage badges. | ~40 lines |

## 7. Backend task list (ordered, ≤1 hour each)

Dependencies noted with **→**. All require passing unit tests before next task begins.

1. **B1 — Schema additions.** Add `ValidationSignal`, `ConsistencyResult`, `TaxHistory` to `data_dictionary.py`. Add `effective_tax_rate_override_years_1_5` field to `ValuationAssumptions`. Add new projection fields to `DCFResult`. Rename `CashFlowMetrics.expected_growth_ebit` → `historical_fundamental_growth`.

2. **B2 — Update `module_3_cashflow.py` for rename.** Propagate field rename. Add a new field `historical_fundamental_growth` computation (same formula, clearer name). Also compute `historical_roic_5yr_avg` and `historical_rir_5yr_avg` if history available.  → depends on B1

3. **B3 — Extend `module_4_dcf.py` to emit new projection arrays.** Already computes the paths internally; just expose them in `DCFResult`. Also compute `implied_roic_projections[]` by roll-forward. → depends on B1

4. **B4 — Remove cascade fallback in `module_4_dcf.py`.** Delete lines 231-233's ROIC×RIR fallback. Blank growth → 0 with a flag. Same pattern for margin (blank → use adjusted EBIT/revenue) and S/C (blank → industry median, reference-sourced, flagged). → depends on B3

5. **B5 — Wire `effective_tax_rate_override_years_1_5` into `_tax_path`.** If override set, use it for years 1..high_growth_years; else existing folder-literal behavior. → depends on B1

6. **B6 — Create `module_7_consistency.py` with Check A.** Implement year-1 growth vs historical fundamental growth. Return signal with severity. → depends on B2, B3

7. **B7 — Extend `module_7_consistency.py` with Check B.** Implied ROIC trajectory vs historical ROIC. → depends on B6

8. **B8 — Extend `module_7_consistency.py` with Check C.** Implied ROIC vs WACC spread. → depends on B7

9. **B9 — Extend `module_7_consistency.py` with Check D.** Terminal invariants. → depends on B8

10. **B10 — Extend `module_7_consistency.py` with Check E.** Reinvestment feasibility. → depends on B9

11. **B11 — Wire Module 7 into orchestrator.** Call after Module 4; attach signals to response. → depends on B10

12. **B12 — Compute `tax_history` in `routes.py`.** For each of `annual[0..4]`, compute `|tax_exp| / |EBT|`. Compute 3yr and 5yr averages. Attach to response. → depends on B1

13. **B13 — Write `test_three_story_consistency.py`.** 5 severity fixtures + all-clean + terminal invariant tests. All pass. → depends on B11

### Frontend task list

14. **F1 — TypeScript types.** Mirror backend schema additions. → depends on B1

15. **F2 — `ConsistencySignal.tsx` component.** Row renderer with badge + message + expandable numeric + scroll link. → depends on F1

16. **F3 — `ClosedLoopSummary.tsx` component.** Top strip showing Implied ROIC, historical ROIC, WACC at Y5 and terminal. → depends on F1

17. **F4 — InputSheet "Historical diagnostics" block.** New calc-row section showing NOPAT, IC, ROIC, Reinv, RIR, historical_fundamental_g. Color-coded as `calc` type (emerald). → depends on F1

18. **F5 — InputSheet inline diagnostic badges.** Next to each of the 3 story input cells (`revenue_growth_next_year`, `operating_margin_next_year`, `sales_to_capital_high`), show an emerald reference badge with the historical benchmark. → depends on F4

19. **F6 — InputSheet Tax-override sub-panel.** Shows 5 historical yr effective rates + 3yr + 5yr averages as reference rows; editable override cell; preset buttons ("Base year", "3yr avg", "5yr avg", "Custom"). → depends on F1 + B12

20. **F7 — InputSheet Story Consistency Panel.** Render `consistency_signals` as rows, with `ConsistencySignal` component. → depends on F2

21. **F8 — InputSheet Closed-Loop Summary strip.** At top of Input Sheet. → depends on F3

22. **F9 — ValuationOutput Key Drivers expansion.** Mirror every editable input from InputSheet; add derived paths as read-only rows. → depends on F1

23. **F10 — ValuationOutput vintage badges.** Per-field cascade in `baseYear.ts`; every base-year cell shows its vintage. → depends on F1

24. **F11 — ValuationOutput base-year reinvestment fill.** `reinvestment[0] = historical Reinvestment_firm` from M3. Label as historical. → depends on F10

25. **F12 — OptionValue tooltip.** σ_stock scope clarification. → independent

## 8. Test plan

### Unit tests (backend)

| Fixture | Triggers | Expected severity |
|---|---|---|
| `clean_story.json` | Analyst inputs match historical ~closely | All signals `INFO` |
| `check_a_soft.json` | `Expected_Growth_EBIT[1]` = historical + 5pp | `SOFT_WARN` on Check A |
| `check_a_hard.json` | `Expected_Growth_EBIT[1]` = historical + 15pp | `HARD_WARN` on Check A |
| `check_b_miracle.json` | `Implied_ROIC[5]` = 3.5× historical | `RED_FLAG` on Check B |
| `check_b_decline.json` | `Implied_ROIC[5]` = 0.3× historical | `SOFT_WARN` on Check B |
| `check_c_value_destroy.json` | `Implied_ROIC[3]` < WACC | `HARD_WARN` on Check C |
| `check_c_super_normal.json` | spread > 20pp for 6 years | `HARD_WARN` on Check C |
| `check_d_terminal_broken.json` | `Implied_ROIC_terminal` = WACC + 5pp | `RED_FLAG` on Check D |
| `check_e_reinv_infeasible.json` | `Reinvestment[2] / NOPAT[2]` = 1.5 | `HARD_WARN` on Check E |
| `check_e_shrinking.json` | `Reinvestment[2]` < 0 | `SOFT_WARN` on Check E |

### Edge cases

- Zero growth story (Lenovo-like with blank inputs → 0): consistency checks must not crash; should produce signal that analyst hasn't set story.
- Negative historical EBIT (e.g., loss-making firm): historical_ROIC undefined → Check A skipped with `INFO("No historical fundamental growth — firm has negative EBIT")`.
- `Invested_Capital[t-1]` = 0: Implied_ROIC undefined → division guarded; signal `INFO`.
- Missing historical quarterly data (Lenovo-thin-feed case): vintage fallback reported; no crash.
- `S/C = 0` or `None` default: reinvestment = 0 per current code; Check E warns about zero reinvestment if growth > 0.
- Analyst sets `failure_probability = 1.0`: DCF value = distress value; consistency panel still runs but most signals irrelevant.

### Integration tests

- Run Lenovo file through full pipeline; verify all new fields populated in response.
- Run NVIDIA ground truth through; verify Implied ROIC matches known Ginzu answer within 1pp.
- Patch growth via `/sensitivity` endpoint; verify signals update.

## 9. Open questions — resolve before coding

**OQ-1. Which "historical ROIC" for Check A and B?**
Options:
- (a) Most recent year's ROIC (what `module_3_cashflow.py` currently computes)
- (b) 3-year average of historical ROIC
- (c) 5-year average
Current code returns single-year. Folder doesn't specify. **Recommendation: compute both single-year and 3yr-avg; use 3yr-avg for Checks A/B (smooths one-off years); display both.**

**OQ-2. Which historical RIR for Check A?**
Same choice as OQ-1. **Recommendation: same as OQ-1 — 3yr average.**

**OQ-3. `Expected_Growth_EBIT[1]` — how computed?**
Given Revenue[1] and Margin[1] both input by analyst, `EBIT[1] = Revenue[1] × Margin[1]`. But `EBIT[0]` for the ratio — is that the adjusted base-year EBIT (post R&D + lease adjustments) or the raw EBIT? **Recommendation: adjusted EBIT, matching the folder's convention that projections start from M1-adjusted base.**

**OQ-4. `reinvestment_rate[t]` denominator in Check E.**
NOPAT can be zero or negative in early loss-making years. Division guards required. **Recommendation: skip Check E for years where NOPAT ≤ 0; emit `INFO("Reinvestment rate undefined — NOPAT non-positive")`.**

**OQ-5. Terminal invariant tolerance for Check D.**
Spec says "within tolerance" but doesn't quantify. **Recommendation: 0.5pp for terminal growth vs risk-free; 2pp for Implied_ROIC_terminal vs WACC_terminal. These reflect rounding/computation noise, not substantive deviations.**

**OQ-6. Should the consistency panel run on every PATCH, or only on initial upload?**
Every PATCH recomputes the full valuation (per CLAUDE.md). If signals attach to the response, they update automatically. **Recommendation: run on every PATCH; no gating.**

**OQ-7. Severity of "analyst hasn't entered any inputs" case.**
With the cascade removed, a fresh upload will have all three story inputs blank → flat projection. **Recommendation: emit a single `HARD_WARN("Story not entered — please set Growth, Margin, and Sales/Capital in the Input Sheet")` that shadows all other signals until the story is set.**

**OQ-8. Base-year reinvestment (Issue 2b): which historical figure?**
Folder doesn't specify. Current Module 3 computes `reinvestment_firm = adjusted_CapEx − adjusted_D&A + ΔNCWC`. **Recommendation: use this value, label as historical, show vintage badge "annual[0]".**

**OQ-9. Scope: do we remove `expected_growth_ebit` from CashFlowMetrics entirely, or keep it (renamed) as diagnostic?**
The code currently uses it as a cascade fallback (to be removed) and as a metric. **Recommendation: rename to `historical_fundamental_growth` and keep as a diagnostic field; surface in UI as reference only; never use as a silent default.**

**OQ-10. Visual integration of Issue 5b (Key Drivers completeness).**
User preference: "every hypothesis input from InputSheet appears in ValuationOutput's Key Drivers as adjustable, nothing missing." ValuationOutput's current Key Drivers is a fragment. **Recommendation: complete mirror of all ~15 InputSheet hypothesis inputs in Key Drivers; derived paths as read-only diagnostic rows. This is a large UI change (~300 lines in ValuationOutput.tsx). Confirm scope.**

**OQ-11. Tax override scope — base year display?**
User's brainstorm brief mentioned both "years two through five" and "base year through year five" for the override. The folder's tax path applies effective to years 1–5 (not base year); base year display reads `macro.tax_rate_effective` directly. Question: when the analyst sets the override, does it also replace the base-year display value, or only years 1–5? **Recommendation: override replaces years 1–5 only; base year always shows the raw historical `|tax_exp|/|EBT|` for transparency, with a note adjacent showing the override value that will be applied in year 1+. Keeps the base year as a historical fact, not an edited story value.**

## 10. Explicit non-goals for this spec

- Not changing the CIQ reader (`tools/read_ciq_template.py`) — it's working.
- Not changing WACC computation (Module 2) — not part of the consistency issues.
- Not changing options valuation math (Module 6) — only adding a scope tooltip (Issue 5a).
- Not adding new hypothesis inputs — per user direction, the input set is complete; we only expose existing ones better and cross-check them.
- Not changing the archetype panel — it stays as-is; the three-story test replaces it as the primary "story sanity" tool but doesn't remove it.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Removing the cascade fallback breaks existing saved sessions with blank inputs | Serve blank as 0 with `HARD_WARN`; analyst sees flat projection and knows to set story. No silent regressions. |
| Rename `expected_growth_ebit` → `historical_fundamental_growth` breaks frontend reads | Search-replace all consumers in one commit; TS types flag misses at compile time. |
| Consistency signals noisy — every analyst input change fires warnings | Tune thresholds in §4 on NVIDIA / MSFT / AAPL ground-truth valuations first; calibrate so INFO covers the "canonical Damodaran" story. |
| Key Drivers expansion (F9) is large and risks layout breakage | Build behind a feature flag; roll out incrementally by section. |
| Tax override panel adds cognitive load on Input Sheet | Collapsed by default; expand when analyst clicks "Override year-1 to year-5 tax rate?" |

## 12. Success criteria

1. Fresh Lenovo upload with no analyst inputs produces: flat revenue projection, `HARD_WARN` that story is unset, `tax_history` block visible with 1.27% year-0 + 5yr average reference.
2. With analyst entering 15% growth, target margin 6%, S/C 2.5: Implied ROIC at year 5 computes and displays in the Closed-Loop Summary strip. Check A fires if delta from historical fundamental growth > 10pp.
3. NVIDIA ground truth valuation passes all 5 checks as `INFO`.
4. All Issue 1, 2b, 3, 5a, 5b symptoms resolved.
5. All new tests pass (`pytest -q` green).
6. No regression on existing tests.

---

## Appendix A — Decisions already captured in brainstorm session

| # | Issue | Decision |
|---|---|---|
| 1 | 1.27% tax override | Add `effective_tax_rate_override_years_1_5` with historical panel + preset buttons |
| 2 | Reinv. zeros yrs 1–4 | Remove cascade fallback; blank growth → 0 + warning |
| 2b | Base-yr reinv. empty | Fill with historical `adj_CapEx − adj_D&A + ΔNCWC`; label as historical |
| 3 | Base-yr fields missing | Per-field cascade LTM → annual[0] → annual[1] with vintage badge |
| 4 | S/C misunderstood | Folder-literal tooltip + historical diagnostic block |
| 5a | σ_stock scope | Tooltip only |
| 5b | Key Drivers incomplete | ValuationOutput mirrors every InputSheet input as adjustable |
| NEW | Three-story consistency | Module 7 + Input Sheet Story Consistency Panel + Closed-Loop Summary |
