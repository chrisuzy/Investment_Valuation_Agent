# Stories to Numbers Redesign + Lenovo Anomaly Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Layer the three-story joint examination (Damodaran *Narrative and Numbers*) onto a consolidated Stories to Numbers page, reusing SensitivityPanel verbatim; add tax-rate override for years 1–5; fix base-year reinvestment, per-field vintage fallback, σ_stock tooltip, and S/C tooltip from the Lenovo anomaly audit.

**Architecture:** Composition-first. Existing SensitivityPanel mounts on StoriesToNumbers alongside new validation rows. Backend adds historical-series computations and two new schema fields; no new pipeline module. DCF math is unchanged.

**Tech Stack:** FastAPI + Pydantic v2 (backend), React + Vite + TS + Tailwind (frontend), pytest, openpyxl. Backend is running on :8000; frontend on :5173.

**Source documents:**
- Spec: `docs/superpowers/specs/2026-05-04-stories-to-numbers-redesign-design.md`
- Understanding: `docs/Ginzu understanding/three_story_joint_examination.md`

---

## Phase 1 — Backend foundations

### Task 1: Schema additions

**Files:**
- Modify: `backend/engine/data_dictionary.py`

- [ ] Add `effective_tax_rate_override_years_1_5: float | None = None` to `ValuationAssumptions`.
- [ ] Add `implied_roic_projections: list[float] = []` and `implied_roic_terminal: float | None = None` to `DCFResult`.
- [ ] Add new fields to `CashFlowMetrics`: `historical_roic_by_year`, `historical_s_c_by_year`, `historical_margin_by_year`, `historical_revenue_growth_by_year` (each `list[float | None] = []`), `historical_roic_avg_3yr`, `historical_roic_avg_5yr`, `historical_s_c_avg_3yr`, `historical_s_c_avg_5yr`, `historical_margin_avg_3yr`, `historical_margin_avg_5yr` (all `float | None = None`).
- [ ] Add new Pydantic model `TaxHistory` with `yearly: list[float | None] = []`, `avg_3yr: float | None = None`, `avg_5yr: float | None = None`.
- [ ] Ensure `CompanyValuationInput` includes an optional `tax_history: TaxHistory | None = None`.

Commit: `feat(schema): add three-story examination fields + tax override`

### Task 2: Historical series in Module 3

**Files:**
- Modify: `backend/engine/module_3_cashflow.py`

- [ ] Extend `compute_cashflow_and_growth` to accept `raw_financials_history: list[RawFinancials]` (most-recent-first, up to 5 entries).
- [ ] For each index `i` in `range(len(history))`, compute:
  - `NOPAT_i = Adjusted_EBIT_i × (1 − effective_tax_rate_i)`; use `macro.tax_rate_effective` when available, else fallback to same field for each historical year (assume constant for simplicity — the user can later override)
  - `IC_i = (prior) bv_equity_{i+1} + R&D_research_asset + bv_debt_{i+1} − cash_{i+1}` — use prior-year IC to match the existing convention
  - `Revenue_i / IC_i` for Sales/IC
  - `EBIT_i / Revenue_i` for margin
  - `Revenue_i / Revenue_{i+1} − 1` for revenue growth
- [ ] Handle missing (`None`) inputs gracefully — any component missing → that year's entry is `None`.
- [ ] Compute `avg_3yr` and `avg_5yr` as `mean(non-None first 3 or all 5)`.
- [ ] Populate all 12 new `CashFlowMetrics` fields.

Commit: `feat(m3): compute historical ROIC/S/C/margin/growth series for three-story validation`

### Task 3: Implied ROIC path in Module 4

**Files:**
- Modify: `backend/engine/module_4_dcf.py`

- [ ] After the existing `ic_path` and `roic_path` computation (line ~349-360), expose:
  - `implied_roic_projections = roic_path[:]` (the per-year implied ROIC)
  - `implied_roic_terminal = nopat_terminal / ic_path[-1]` (guard div-by-zero)
- [ ] Add both to the returned `DCFResult`.

Commit: `feat(m4): expose implied_roic_projections and terminal for three-story validation`

### Task 4: Tax override wiring

**Files:**
- Modify: `backend/engine/module_4_dcf.py`

- [ ] In the `_tax_path` invocation block (line ~286-288), before calling `_tax_path`, check `if assumptions.effective_tax_rate_override_years_1_5 is not None` → override `t_effective = assumptions.effective_tax_rate_override_years_1_5`.
- [ ] Years 6–10 still converge to `t_marginal` (behavior unchanged).
- [ ] Base-year `macro.tax_rate_effective` display is unchanged.

Commit: `feat(m4): honor effective_tax_rate_override_years_1_5`

### Task 5: Remove silent cascade fallback

**Files:**
- Modify: `backend/engine/module_4_dcf.py`

- [ ] Replace lines 231-233 (`g_year_1 = assumptions.revenue_growth_next_year; if g_year_1 is None: g_year_1 = cf_metrics.expected_growth_ebit or g_terminal`) with: `g_year_1 = assumptions.revenue_growth_next_year if assumptions.revenue_growth_next_year is not None else 0.0`.
- [ ] Same change for `g_years_2_5`: if `None`, default to `g_year_1` (folder §3.1), NOT to historical fundamental growth.
- [ ] Same change for margin: if `margin_y1 is None`, default to `adjusted.adjusted_ebit / raw.revenues` if available, else `0.0`. (No cascade to `expected_growth_ebit`.)
- [ ] Same change for S/C: default `sc_high = 2.5` remains (Damodaran default), but log it's a placeholder.
- [ ] `cf_metrics.expected_growth_ebit` is now purely diagnostic — never substituted into the projection.

Commit: `fix(m4): remove silent ROIC×RIR cascade — blank story inputs stay blank`

### Task 6: Tax history in routes

**Files:**
- Modify: `backend/api/routes.py`

- [ ] In `fetch_from_file` (line ~505) and upload-direct paths: after the existing effective tax computation (line ~605), loop over `annual[0..4]` to compute yearly `|tax_exp_i| / |ebt_i|` (guard zero/None).
- [ ] Compute `avg_3yr` and `avg_5yr` on non-None values.
- [ ] Attach `tax_history = TaxHistory(yearly=..., avg_3yr=..., avg_5yr=...)` to the `CompanyValuationInput`.

Commit: `feat(routes): compute and attach tax_history (5yr annual + 3/5yr averages)`

### Task 7: Backend unit tests

**Files:**
- Create: `backend/tests/test_stories_to_numbers.py`

- [ ] Test `compute_cashflow_and_growth` with 5-year history → `historical_roic_by_year` length 5, `avg_5yr` = mean of all 5.
- [ ] Test with 3-year history → `avg_5yr` still works (mean of available 3).
- [ ] Test with missing fields in year 2 → that year's entry is `None`, averages skip it.
- [ ] Test `_tax_path` with `override = 0.12` → years 1–5 all 0.12, years 6–10 converge to marginal.
- [ ] Test `_tax_path` with `override = None` → folder-literal behavior unchanged.
- [ ] Test `implied_roic_projections` length 10 after `compute_dcf` call.
- [ ] Test Lenovo file end-to-end: `tax_history.yearly[0] ≈ 0.0127`, `historical_roic_by_year[0] ≈ 0.247`.

Run: `pytest backend/tests/test_stories_to_numbers.py -v`. Expect all pass.

Commit: `test: add three-story examination backend unit tests`

---

## Phase 2 — Frontend type + pure helpers

### Task 8: TypeScript types

**Files:**
- Modify: `frontend/src/types/valuation.ts`

- [ ] Add types matching backend: `TaxHistory`, extended `CashFlowMetrics` with new fields, extended `DCFResult`, extended `ValuationAssumptions`.
- [ ] Add `CompanyValuationInput.tax_history?: TaxHistory`.

Commit: `feat(types): mirror backend three-story examination schema`

### Task 9: Reverse-check math helpers

**Files:**
- Create: `frontend/src/lib/reverseChecks.ts`

- [ ] `requiredROIC(margin: number | null, sc: number | null): number | null` — returns `margin * sc` or `null` if either missing.
- [ ] `requiredSC(roicAnchor: number | null, margin: number | null): number | null` — returns `roicAnchor / margin` or `null`.
- [ ] `gapStatement(actual: number | null, reference: number | null, unit: 'pp' | '×'): string` — returns e.g. `"+6pp"` or `"+0.5×"` or `"—"`.
- [ ] Unit tests (in a `.test.ts` sibling file if vitest set up, else skip for now).

Commit: `feat(lib): add reverseChecks helpers for three-story validation`

### Task 10: Vintage helper

**Files:**
- Create: `frontend/src/lib/baseYearVintage.ts`

- [ ] Export `VintageSource = 'LTM' | '10-K' | '10-K-1'`.
- [ ] Export `getField<K extends keyof RawFinancials>(data: ValuationResponse, key: K): { value: RawFinancials[K] | undefined; vintage: VintageSource | null }` — tries LTM → annual[0] → annual[1] per field; returns first non-null.
- [ ] Export `vintageBadge(source: VintageSource | null): string` — returns colored badge string.

Commit: `feat(lib): add baseYearVintage per-field cascade with source tracking`

---

## Phase 3 — Frontend components

### Task 11: VintageBadge component

**Files:**
- Create: `frontend/src/components/VintageBadge.tsx`

- [ ] Renders a small chip: `LTM` (emerald), `10-K` (sky), `10-K-1` (amber), hidden if null.
- [ ] Props: `source: VintageSource | null`, optional `className`.

Commit: `feat(components): add VintageBadge for base-year column provenance`

### Task 12: ClosedLoopStrip component

**Files:**
- Create: `frontend/src/components/ClosedLoopStrip.tsx`

- [ ] Props: `data: ValuationResponse`.
- [ ] Reads `data.cashflow.historical_roic_avg_5yr`, `historical_s_c_avg_5yr`, `data.inputs.industry_data`, `data.cost_of_capital.wacc`, `data.inputs.valuation_assumptions.target_operating_margin`, `sales_to_capital_high`.
- [ ] Computes `requiredROIC` and `requiredSC` via the helpers.
- [ ] Renders a two-row sticky strip with factual gap statements.
- [ ] Renders "—" for any missing value, with tooltip if applicable.

Commit: `feat(components): add ClosedLoopStrip three-story headline`

### Task 13: StoryValidationBlock component

**Files:**
- Create: `frontend/src/components/StoryValidationBlock.tsx`

- [ ] Props: `title: string`, `historical: (number | null)[]`, `avg3: number | null`, `avg5: number | null`, `industryMedian: number | null`, `industryQ1: number | null`, `industryQ3: number | null`, `formatAs: 'pct' | 'dec'`, `reverseCheck?: { label: string; required: number | null; actual: number | null; unit: 'pp' | '×' }`.
- [ ] Renders one card with four rows: historical annual (5 cells), averages (2 cells), industry (median + Q1–Q3 range), reverse-check factual gap line.

Commit: `feat(components): add StoryValidationBlock for growth/margin/capital-efficiency rows`

### Task 14: TaxOverridePanel component

**Files:**
- Create: `frontend/src/components/TaxOverridePanel.tsx`

- [ ] Props: `data: ValuationResponse`, `onPatch: (path: string, value: PatchValue) => void`.
- [ ] Reads `data.inputs.tax_history.yearly[0..4]`, `avg_3yr`, `avg_5yr`, `data.inputs.macro_inputs.tax_rate_marginal`.
- [ ] Renders a row with 5 historical yearly cells + 3yr + 5yr average cells + an editable override cell.
- [ ] Preset buttons below: "Use base year", "Use 3-yr avg", "Use 5-yr avg", "Clear" — each patches `valuation_assumptions.effective_tax_rate_override_years_1_5`.

Commit: `feat(components): add TaxOverridePanel with historical anchors and preset buttons`

---

## Phase 4 — Stories to Numbers page rewrite

### Task 15: Wire onPatch through App to StoriesToNumbers

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] Find the `<Route>` for StoriesToNumbers. Pass `onPatch` and `onPatchMany` props the same way ValuationOutput already receives them.

Commit: `feat(app): pass onPatch/onPatchMany to StoriesToNumbers route`

### Task 16: StoriesToNumbers rewrite

**Files:**
- Modify: `frontend/src/pages/StoriesToNumbers.tsx`

- [ ] Accept `onPatch` and `onPatchMany` props.
- [ ] Keep the existing narrative mapping table at the top (unchanged).
- [ ] Add `ClosedLoopStrip` below narrative.
- [ ] Add three `StoryValidationBlock` instances: Growth, Margin, Capital Efficiency. Each reads from `data.cashflow.historical_*_by_year` and `data.inputs.industry_data`.
- [ ] Add `TaxOverridePanel` below the three blocks.
- [ ] Mount `<SensitivityPanel data={data} onPatch={onPatch} onPatchMany={onPatchMany} />` at the bottom.
- [ ] (Other methodology drivers Section G — defer to a follow-up spec; SensitivityPanel's 8 already cover the primary knobs.)

Commit: `feat(page): rewrite StoriesToNumbers with three-story examination + SensitivityPanel`

---

## Phase 5 — Side fixes (Lenovo anomalies 2b, 3, 4, 5a)

### Task 17: Base-year reinvestment fill (Issue 2b)

**Files:**
- Modify: `frontend/src/pages/ValuationOutput.tsx`

- [ ] At line ~126-131 where `reinvestment` array is built: set `reinvestment[0] = data.cashflow?.reinvestment_firm`.
- [ ] Add a tooltip to the base-year reinvestment cell: "Historical: Adjusted CapEx − Adjusted D&A + ΔNCWC from annual[0]."

Commit: `fix(valuation-output): fill base-year reinvestment with historical (Issue 2b)`

### Task 18: Vintage badges on base-year column (Issue 3)

**Files:**
- Modify: `frontend/src/pages/ValuationOutput.tsx`

- [ ] Replace the `fin0` access at line 45 with `const fin0WithVintage = getFieldSet(data, [...fields])` using `lib/baseYearVintage.ts`.
- [ ] For each base-year cell in the projection table, render a small `<VintageBadge source={...} />` inline with the value.

Commit: `feat(valuation-output): add vintage badges to base-year column (Issue 3)`

### Task 19: σ_stock tooltip (Issue 5a)

**Files:**
- Modify: `frontend/src/pages/OptionValue.tsx`

- [ ] Locate cells displaying `stock_price_std_dev` (or similar). Add tooltip: "Used only in Black-Scholes option valuation (Module 6/8). Does not feed the main DCF."

Commit: `docs(option-value): clarify σ_stock scope (Issue 5a)`

### Task 20: S/C folder-literal tooltip (Issue 4)

**Files:**
- Modify: `frontend/src/pages/InputSheet.tsx`

- [ ] On the `sales_to_capital_high` and `sales_to_capital_stable` editable cells, add tooltip: "Reinvestment = ΔRevenue / S/C. Two values reflect capital efficiency changes as the firm matures (folder: module_05 §3.6)."

Commit: `docs(input-sheet): explain Sales-to-Capital formula and two-value design (Issue 4)`

---

## Phase 6 — Integration verification

### Task 21: Lenovo end-to-end smoke test

- [ ] Backend running on :8000; frontend on :5173.
- [ ] Re-upload `TEST_DATA/CIQ_Fetch_Template_Lenovo.xlsx` via the UI.
- [ ] Navigate to Stories to Numbers. Verify:
  - Narrative table visible
  - ClosedLoopStrip shows historical ROIC (~24.7%), historical S/C (computed), WACC (from data)
  - Three Story Validation Blocks show 5 historical annual values for ROIC / S/C / margin / growth
  - TaxOverridePanel shows 1.27% at year 0 + 3yr/5yr averages + editable override
  - SensitivityPanel tornado + 8 sliders + archetypes + Reset all functional
- [ ] Navigate to Valuation Output. Verify:
  - Base-year reinvestment cell populated with historical value (not blank)
  - Vintage badges visible on base-year column
  - SensitivityPanel still works
- [ ] Navigate to Option Value. σ_stock tooltip visible.
- [ ] Navigate to Input Sheet. S/C cells have folder-literal tooltip.
- [ ] Test mirror: change `revenue_growth_next_year` on StoriesToNumbers SensitivityPanel → navigate to InputSheet → value is reflected there.

Commit: (no code change — if verification fails, fix inline and recommit affected task)

---

## Open decisions rolled into execution

- **OQ-1 ROIC anchor:** Use historical 5-yr avg ROIC; if `roic_stable_override` set, show a second `required_s_c_alt` next to it.
- **OQ-2 Thin history:** Populate available years; averages on whatever non-None values exist.
- **OQ-3 Industry absent:** Cells show "—" with tooltip.
- **OQ-4 Gap shown vs:** Three gaps in closed-loop strip (vs historical, vs industry, vs WACC).
- **OQ-5 Terminal implied ROIC:** Displayed in second row of closed-loop strip.
- **OQ-11 Tax override scope:** Only years 1–5; base year unchanged.

## Rollback strategy

Each task commits independently. If any task breaks existing functionality, `git revert <sha>` rolls back just that task without touching the others.
