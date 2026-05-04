# Stories to Numbers Redesign — Three-Story Joint Examination

**Date:** 2026-05-04
**Status:** Draft for user review
**Supersedes:** `2026-05-04-three-story-consistency-and-lenovo-anomalies-design.md` (earlier version over-built this feature into a system-wide consistency engine with 5 severity checks, Module 7, ValidationSignal dataclass, Key-Drivers-on-ValuationOutput expansion — all out of scope per user correction).
**Ground truth document:** `docs/Ginzu understanding/three_story_joint_examination.md`

---

## 1. What this spec is

A narrow, **composition-based** redesign of a single page — **Stories to Numbers** — so it becomes the consolidated surface where the analyst authors the three stories and sees them immediately cross-examined against history, industry, and the required arithmetic. Plus one backend-side mechanical fix: the tax-rate override for years 1–5 (Issue 1 from the Lenovo anomaly audit).

**Composition principle.** The existing adjustable infrastructure on ValuationOutput is preserved and reused, not duplicated or rebuilt. `SensitivityPanel.tsx` already implements:
- Tornado chart ranking 8 canonical drivers by VPS sensitivity
- 8 driver cells with ▲/▼ fine-tune controls, Q1/median/Q3 industry chips, live percentile
- 6 archetype preset cards (Disruptor / Growth / Mature / Utility / Cyclical / Distressed)
- "↺ Reset to original inputs" button
- Live impact cards (VPS, market price, P/V, operating assets) with correct listing-vs-reporting currency handling

That component is mounted verbatim on Stories to Numbers with the same `onPatch` / `onPatchMany` props already plumbed through `App.tsx` for ValuationOutput. No functional duplication, no sync logic — editing on either page produces the same PATCH to the session, both pages re-render with the new state on next navigation.

**What this is not:**
- Not a system redesign. No new pipeline module.
- No severity scoring, warnings, red flags, or color-coded alerts. The display shows numbers; the analyst judges.
- No changes to the DCF math. The existing `compute_dcf` projection is untouched.
- No expansion of inputs. Every hypothesis field already exists in `ValuationAssumptions`; this spec only reorganizes their presentation.
- **Not removing anything from ValuationOutput.** Its SensitivityPanel mount continues to work exactly as today. The three-story validation is an *additional* layer on Stories to Numbers.

The remaining Lenovo anomalies (2b base-year reinvestment, 3 vintage badges, 5a σ_stock tooltip) are **out of scope for this spec** and will be addressed in a separate short spec later. They touch different pages (ValuationOutput, OptionValue) and don't depend on this work.

## 2. The new Stories to Numbers page — layout

Composition: existing components preserved + three new components layered on top.

```
┌──────────────────────────────────────────────────────────────────────┐
│ 0. Narrative mapping table (EXISTING, kept at top)                    │
│    Qualitative question → Value driver → Input field → Current value │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ A. Closed-loop summary strip (NEW, sticky below narrative)            │
│   Story requires ROIC = X%  |  Historical = Y% (5y avg Z%)            │
│                              |  Industry median = A% (Q1–Q3 B–C%)      │
│                              |  WACC = W%         Gap: +Δpp           │
│   Story requires S/C = M×    |  Historical = N× (5y avg O×)           │
│                              |  Industry median = P× (Q1–Q3 Q–R×)      │
│                              |  Gap: +Δ×                               │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ B. Growth Story — validation rows (NEW)                               │
│   Historical annual   yr-4  yr-3  yr-2  yr-1  yr-0   revenue growth   │
│   Averages            3-yr avg  5-yr avg                              │
│   Industry            median    Q1  Q3                                │
│   Reverse check       Required ROIC = X%  Historical = Y%  Gap: +Zpp  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ C. Margin Story — validation rows (NEW)                               │
│   Historical annual   (5 yrs)  pre-tax operating margin               │
│   Averages            3-yr avg  5-yr avg                              │
│   Industry            median    Q1  Q3                                │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ D. Capital-Efficiency Story — validation rows (NEW)                   │
│   Historical annual   (5 yrs)  Sales / Invested Capital               │
│   Averages            3-yr avg  5-yr avg                              │
│   Industry            median    Q1  Q3                                │
│   Reverse check       Required S/C = X×  Historical = Y×  Gap: +Z×    │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ E. Tax-rate override, Years 1–5 (NEW — Issue 1)                       │
│   Historical annual   yr-4 … yr-0   |tax_exp|/|EBT|                   │
│   Averages            3-yr avg  5-yr avg                              │
│   Override            (editable)  Preset: [Base yr] [3yr] [5yr] [Custom] │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ F. SensitivityPanel (mounted EXISTING component, unchanged)           │
│    • Impact tornado — ranks 8 drivers by VPS sensitivity              │
│    • 8 drivers as editable cells with ▲/▼ fine-tune controls,          │
│      Q1/median/Q3 industry chips, live percentile                     │
│    • Live impact cards: VPS, market price, P/V, op assets             │
│      (correct listing-vs-reporting currency handling)                 │
│    • Archetype presets (6 cards)                                      │
│    • ↺ Reset to original inputs                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ G. Other methodology-choice drivers (NEW, exposes remaining schema)   │
│    Not in SensitivityPanel's 8 canonical drivers:                      │
│    - failure_tie_to (B/V)          - reinvestment_lag_years + override │
│    - nol_amount + override         - riskfree_after_yr10 + override    │
│    - growth_perpetuity_rate + override                                 │
│    - trapped_cash_amount + tax_rate + override                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Order rationale.** Narrative mapping at top for orientation; closed-loop strip sticky for headline; three story validation blocks in analyst's natural order (growth → margin → capital efficiency); tax override immediately below because it affects the same year-1–5 projection window as the stories; **SensitivityPanel lower on the page because it's the analyst's fine-tune loop (adjust, see impact, iterate)** — goes below the "here's what your story requires" validation so the analyst sees the diagnosis first and then uses the panel to react; other methodology drivers at bottom as the least-touched set.

**Key point about SensitivityPanel.** Section F is *the existing component* mounted on this page. The 8 canonical drivers it exposes (revenue_growth_next_year, operating_margin_next_year, target_operating_margin, sales_to_capital_high, sales_to_capital_stable, margin_convergence_year, stable_growth_rate, cost_of_capital_stable_override) are the analyst's primary story inputs. Sections B, C, D contain **only the validation rows** (historical, industry, reverse-check) that wrap those inputs — not duplicate input cells. The input cells live in SensitivityPanel's Section F; the validation wraps them there or renders as adjacent sections above.

**Implementation choice for Sections B/C/D validation rows.** Two options:
- Option i: three separate story-validation blocks above SensitivityPanel (clean, but distance between "here's your input" and "here's its validation" is visually large).
- Option ii: inject the validation rows directly into SensitivityPanel's driver cell for each of the three story drivers (historical row + industry row + reverse-check row collapsed below each of the three relevant drivers). Requires modifying SensitivityPanel to accept optional per-driver children.

**Recommendation: Option i** for this first iteration — less invasive, keeps SensitivityPanel single-responsibility. If visual separation turns out to be confusing in user testing, switch to Option ii in a follow-up.

## 3. Mirror strategy (both pages editable)

Because we're **mounting the same `SensitivityPanel` component** on both Stories to Numbers and Valuation Output, there is no duplication and no sync problem. Both pages share:

- The same `ValuationAssumptions` dot-paths bound via `onPatch`
- The same session store updated through `PATCH /api/valuation/{session_id}`
- The same archetype preset bag, the same Reset-to-original snapshot (the snapshot watches `sessionId` only, per CLAUDE.md, so it doesn't get overwritten by cross-page navigation)

**Plumbing change.** `App.tsx` currently routes `onPatch` and `onPatchMany` into `ValuationOutput`. We'll add the same two props to the `StoriesToNumbers` route. One-line change per route definition; the callbacks themselves are reused.

**No per-page state.** The three-story validation rows (Sections B/C/D) and the tax-override panel (Section E) read from the shared session state; no local component state. Every PATCH anywhere in the app triggers a full re-render on both pages.

The Input Sheet §7 inputs continue to work as they do today — same dot-paths, independent read-only-or-editable decisions per cell.

## 4. Reverse-calculation math (from `three_story_joint_examination.md §3`)

All formulas display-only — no side effects on the DCF.

```
# Closed-loop identity (DuPont):
Required_ROIC = story_margin_target × story_S_C_high

# Required S/C given growth and margin targets, anchored to a target ROIC:
Required_S_C  = ROIC_anchor / story_margin_target

# Gap statements (factual, not judgmental):
ROIC_gap      = Required_ROIC − historical_ROIC_5yr_avg
S_C_gap       = Required_S_C  − historical_S_C_5yr_avg
```

`ROIC_anchor` defaults to the historical 5-yr average ROIC. If `roic_stable_override` is set, use that. If neither, fall back to WACC.

## 5. Historical-series calculations (backend additions)

Computed once per valuation in `module_3_cashflow.py`, attached to `CashFlowMetrics`. All read from `raw_financials[0..4]` (annual history, most-recent-first).

```
# Per-year (last 5 fiscal years, index 0 = most recent):
historical_roic_by_year[i]       = NOPAT_i      / Adjusted_IC_{i+1}      (prior year IC)
historical_s_c_by_year[i]        = Revenue_i    / Adjusted_IC_i
historical_margin_by_year[i]     = EBIT_i       / Revenue_i              (pre-tax)
historical_revenue_growth[i]     = Revenue_i    / Revenue_{i+1} − 1

# Averages (only include years with non-None values):
avg_3yr = mean of [i=0,1,2]
avg_5yr = mean of [i=0..4]
```

Convention matches the existing `module_3_cashflow.py::compute_cashflow_and_growth` (prior-year invested capital as denominator, effective tax rate for NOPAT).

## 6. Implied ROIC projections (backend additions)

Computed in `module_4_dcf.py` during the existing projection loop. No new math — the Invested Capital roll-forward already happens; just expose it.

```
# Added to DCFResult:
implied_roic_projections[t]  = nopat_projections[t] / ic_path[t]    (for t in 1..10)
implied_roic_terminal        = nopat_terminal / ic_path[10]
```

Used by Section A summary strip.

## 7. Tax-override panel (Section E, Issue 1 remediation)

Backend:
```
# In routes.py::fetch_from_file + upload paths:
for i in range(5):
    tax_exp_i = _fval_or_none(annual[i], "total_tax_expense")
    ebt_i     = _fval_or_none(annual[i], "earnings_before_tax")
    if ebt_i and tax_exp_i and ebt_i != 0:
        historical_tax_by_year[i] = abs(tax_exp_i) / abs(ebt_i)

tax_history.avg_3yr = mean of first 3 non-None
tax_history.avg_5yr = mean of 5

# In data_dictionary.py::ValuationAssumptions:
effective_tax_rate_override_years_1_5: float | None = None

# In module_4_dcf.py::_tax_path:
if assumptions.effective_tax_rate_override_years_1_5 is not None:
    t_effective = assumptions.effective_tax_rate_override_years_1_5
# ... rest of path unchanged
```

Years 6–10 convergence to marginal is unchanged. Base-year display (read from `macro.tax_rate_effective`) is unchanged — per OQ-11 recommendation, keep base year as historical fact.

## 8. File-by-file change list

### Backend

| File | Change | Approx lines |
|---|---|---|
| `backend/engine/data_dictionary.py` | Add `effective_tax_rate_override_years_1_5` to `ValuationAssumptions`. Add `TaxHistory` class. Extend `CashFlowMetrics` with 4 historical-series lists + 2 average fields for each (ROIC, S/C, margin, growth = 12 new fields). Extend `DCFResult` with `implied_roic_projections` + `implied_roic_terminal`. | +40 |
| `backend/engine/module_3_cashflow.py` | Add historical-series computation loop over `raw_financials[0..4]`. Populate new `CashFlowMetrics` fields. | +50 |
| `backend/engine/module_4_dcf.py` | Wire override into `_tax_path`. Expose `implied_roic_projections` + `implied_roic_terminal` in returned `DCFResult`. | +15 |
| `backend/api/routes.py` | Compute `tax_history` block in `fetch_from_file` and upload-direct paths. Attach to response. | +25 |
| `backend/tests/test_three_story_examination.py` | **NEW.** Unit tests for historical-series math, reverse calculations, tax override wiring. | +150 |

### Frontend

| File | Change | Approx lines |
|---|---|---|
| `frontend/src/types/valuation.ts` (or wherever types live) | Mirror schema additions. | +30 |
| `frontend/src/pages/StoriesToNumbers.tsx` | **Full rewrite** per §2 layout. Sections A–F. | ~400 |
| `frontend/src/lib/reverseChecks.ts` | **NEW.** Pure functions: `requiredROIC()`, `requiredSC()`, `gapStatement()`. | +40 |
| `frontend/src/components/StoryBlock.tsx` | **NEW.** One reusable block for each story (input row + historical row + industry row + reverse-check row). | +120 |
| `frontend/src/components/ClosedLoopStrip.tsx` | **NEW.** Section A renderer. | +80 |
| `frontend/src/components/TaxOverridePanel.tsx` | **NEW.** Section E with preset buttons. | +100 |

**Total:** ~130 backend + ~770 frontend = ~900 lines, one new backend module of work (historical series + tax override), one new frontend page rewrite + 4 new components.

(Compare to the superseded spec's ~1400 lines with Module 7, ValidationSignal, 5 severity checks, Key Drivers expansion on ValuationOutput.)

## 9. Backend task list (ordered, ≤1 hour each)

1. **B1 — Schema additions.** Add `effective_tax_rate_override_years_1_5`, `TaxHistory`, new `CashFlowMetrics` fields, new `DCFResult` fields.
2. **B2 — Historical-series computation in M3.** Loop over `raw_financials[0..4]`; populate 12 new fields. → B1
3. **B3 — Expose `implied_roic_projections` in M4.** Already computed internally; just add to returned `DCFResult`. → B1
4. **B4 — Wire tax override in M4.** `_tax_path` reads new field. → B1
5. **B5 — Tax history in routes.py.** Compute `tax_history` block on upload paths. → B1
6. **B6 — Unit tests.** Historical series math + tax override + implied_roic math. → B2, B3, B4, B5

## 10. Frontend task list (ordered, ≤1 hour each)

7. **F1 — TypeScript types.** Mirror backend schema. → B1
8. **F2 — `reverseChecks.ts` helpers.** Pure math functions with tests. → F1
9. **F3 — `StoryBlock.tsx` component.** Reusable for all three stories. → F1
10. **F4 — `ClosedLoopStrip.tsx` component.** Section A. → F2
11. **F5 — `TaxOverridePanel.tsx` component.** Section E. → F1
12. **F6 — Rewrite `StoriesToNumbers.tsx`.** Compose Sections A–F from components. → F3, F4, F5
13. **F7 — Visual check.** Navigate between StoriesToNumbers / InputSheet / SensitivityPanel; confirm edits mirror correctly on each navigation.

## 11. Test plan

### Backend unit

- Historical ROIC series with 5, 4, 3, 2, 1 years of data (tests the None handling)
- Historical S/C series with zero/negative IC years
- Historical margin series with negative EBIT years
- `avg_3yr` and `avg_5yr` computations with some missing values
- Tax override: override set → year 1–5 path uses override; override None → folder-literal behavior
- `implied_roic_projections[]` length = 10, terminal present

### Backend integration

- Lenovo upload → `historical_roic_by_year` populated with actual Lenovo values, `tax_history.yearly` has 5 entries including 1.27% for year 0
- NVIDIA upload → historical series matches known values from `Ginzu_NVIDIA.xlsx`

### Frontend

- Fresh Lenovo session → Stories to Numbers page loads with three story blocks visible, historical rows populated, industry rows populated, reverse-check row showing blank (because story inputs are blank)
- Set growth = 15%, margin = 8%, S/C = 2.5 → reverse-check row shows "Required ROIC = 20% | Historical = 24.7% | Gap: −4.7pp"
- Set tax override → DCF projections respond; Valuation Output page shows years 1–5 at the overridden rate
- Edit a growth input on Stories to Numbers → navigate to InputSheet → same value is present in the InputSheet §7 cell (mirror works)

## 12. Open questions — narrow set

**OQ-1. `ROIC_anchor` in the `Required_S_C` formula.**
Candidates: historical 5-yr avg ROIC, `roic_stable_override` if set, WACC. **Recommendation:** use historical 5-yr avg ROIC as the primary anchor; if `roic_stable_override` set, show both side-by-side ("Required S/C to match historical ROIC = X; required S/C to match your override ROIC = Y").

**OQ-2. What if historical data is too thin (< 3 years)?**
**Recommendation:** populate whatever years are available; `avg_3yr` becomes `avg_available`; show a source note in the page header: "Historical averages based on N years of available data."

**OQ-3. Industry data absent.**
**Recommendation:** show "—" in industry column with tooltip "Industry data not available for this firm's classification." Reverse checks still compute against historical.

**OQ-4. Should the `Required ROIC` gap be shown against historical only, or against industry + WACC as well?**
**Recommendation:** show all three gaps ("vs historical: +Xpp", "vs industry median: +Ypp", "vs WACC: +Zpp"). Three gaps give the 3P triangulation (Possible / Plausible / Probable per the Understanding doc).

**OQ-5. Terminal implied ROIC — display it?**
**Recommendation:** yes, as the second row of the closed-loop strip. Shows whether the analyst's story satisfies the "no excess returns in perpetuity" invariant (terminal implied ROIC ≈ terminal WACC unless override is set).

**OQ-6. Section F ordering.**
**Recommendation:** group by workflow — terminal-state overrides first (stable_growth, COC_stable_override, ROIC_stable_override), then narrative adjustments (failure_probability, distress_proceeds_pct), then technical overrides (reinvestment_lag, NOL, riskfree_after, trapped_cash). User can rearrange if preferred.

## 13. Success criteria

1. Lenovo upload → Stories to Numbers page renders with all historical rows populated (5 years of ROIC, S/C, margin, growth).
2. Tax-override panel shows 5 historical yearly rates including the 1.27% FY-0 value plus 3-yr and 5-yr averages.
3. Setting growth = 25%, margin = 30%, S/C = 3 on Stories to Numbers renders a closed-loop strip showing Required ROIC = 90% with factual gap statement against historical ROIC.
4. Editing any driver on Stories to Numbers mirrors to InputSheet §7 and SensitivityPanel on next navigation.
5. All new backend unit tests pass. No regressions in existing tests.
6. The underlying DCF valuation math is unchanged — same `value_per_share` for any given session as before this change, within floating-point tolerance.

## 14. Non-goals (explicit)

- Not building a consistency-check engine. No severity classifications. No Module 7.
- Not expanding ValuationOutput's Key Drivers. That page stays as a projection display + equity bridge.
- Not changing the archetype panel. It continues to work on Stories to Numbers and SensitivityPanel.
- Not fixing Issues 2b, 3, or 5a in this spec. They will be addressed separately.
- Not changing SensitivityPanel. It continues to work as a tornado + ranked-driver tool where it already lives.

---

## Appendix — What the user already confirmed in the brainstorm

| Decision | Source |
|---|---|
| The three stories are arithmetically coupled; cross-examination is the discipline that surfaces the implied ROIC | Brainstorm turn-by-turn |
| Display-only, no severity or warnings; analyst judges | Brainstorm |
| Consolidate all hypothesis inputs onto Stories to Numbers; both pages remain editable mirrors | Brainstorm (explicit answer) |
| Reverse-check line style: raw numbers + factual gap statement | Brainstorm (explicit answer) |
| Historical depth: last 5 years + 3-yr and 5-yr averages | Brainstorm (explicit answer) |
| Tax override for year 1–5 with 5 historical values + 3/5yr avg + preset buttons | Brainstorm (Issue 1 decision) |
| Years 2..K margins stay as derived interpolation (folder-literal) | Brainstorm (explicit answer) |
| Growth years 2–5 is one analyst-input flat value (already in schema as `revenue_growth_years_2_5`) | Brainstorm + folder §3.1 |
| Damodaran's 3P framework (Possible/Plausible/Probable) informs the triangulation across historical, industry, and WACC anchors | Understanding doc §6 |
