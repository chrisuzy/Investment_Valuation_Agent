# Project Plan v2 — Ginzu-Authoritative Implementation Roadmap

**Supersedes:** `docs/project_plan_next_steps.md` (now deleted).
**Anchor spec:** `docs/ginzu_spec_v2.md`.
**Ground truth:** `knowledge_base/Ginzu_NVIDIA.xlsx` via `docs/brainstorm_cache/ginzu_extracted.json`.
**Issued:** 2026-04-28 after full Stage 0–6 reconciliation walk.

---

## Executive Summary

This plan sequences ~12 weeks of engineering work to bring the AD_CC_pilot valuation engine from ~30% Ginzu fidelity to ~95% Ginzu fidelity, with a functioning Linux-based deployment path.

**Top-3 near-term priorities (in order):**
1. **Phase 1 — DCF engine rewrite** (~7 hrs) — fixes the 17 dead `ValuationAssumptions` fields and the wrong EBIT/reinvestment mechanics. This is the single highest-impact change.
2. **Phase A — Data acquisition via template upload** (~1 hr glue work, mostly already in place) — unblock Linux-only usage immediately.
3. **Phase 2 — Self-consistency feedback loops** (~4.5 hrs) — synthetic rating & option dilution iteration.

**Total effort estimate:** ~55 hours of focused work across 8 phases, roughly 7–10 working days.

---

## Phase A — Data Acquisition (Locked Architecture)

**Ship immediately.** No new infrastructure. The existing pipeline already supports this; we formally lock it as the canonical mode.

### Workflow (user-facing)
1. User enters a ticker in the Linux web UI.
2. Backend generates `<TICKER>_ciq_template.xlsx` via `backend/tools/generate_ciq_template.py` and returns it for download.
3. User opens the template on any Windows / Mac-with-Parallels machine that has Excel + CIQ plugin.
4. CIQ formulas auto-resolve; user saves the workbook.
5. User drags the resolved `.xlsx` into the web UI.
6. Backend parses via `backend/tools/read_ciq_template.py` and feeds the valuation engine.

### Design properties
- **Zero credential handling on Linux.** CIQ credentials stay on user's Windows box, bound to the Excel plugin.
- **No S&P API contract required.**
- **Existing plumbing.** `generate_ciq_template.py` and `read_ciq_template.py` are already written.

### Phase A tasks
- **A.1** Verify `generate_ciq_template.py` produces a template that reads all 37 CIQ fields specified in `capiq_formula_map.py`. *(Already verified as of last session; spot-check before ship.)*
- **A.2** Verify `read_ciq_template.py` parses the resolved template into `CompanyValuationInput` correctly on Linux. *(Sanity-test with NVIDIA sample.)*
- **A.3** Document the workflow in a README section for users.
- **A.4** Add a frontend upload state with "Waiting for resolved template" messaging.

**Effort: ~1 hour.** Almost all plumbing exists.

---

## Phase 1 — Core DCF Correctness (Stage 5, 8, 9 fixes)

**Deliverable:** `backend/engine/module_4_dcf.py` rewritten to consume all 17 previously-dead `ValuationAssumptions` fields and produce Ginzu-equivalent numbers.

**Why first:** every other phase depends on having a correct DCF baseline. Ginzu-fidelity testing requires it.

### 1.1 Read & thread `operating_margin_next_year`
File: `backend/engine/module_4_dcf.py`.
- Add `margin_y1 = assumptions.operating_margin_next_year or (raw.ebit / raw.revenues if raw.revenues > 0 else 0)` near line 65.
- 5 minutes.

### 1.2 Build margin path helper
Add `_margin_path(margin_y1, margin_target, convergence_year_K, total_years=10) -> list[float]`:
```python
def _margin_path(margin_y1, margin_target, K, years=10):
    path = []
    for t in range(1, years + 1):
        if t == 1:
            path.append(margin_y1)
        elif t <= K:
            # linear: target - (target - y1) × (K - t) / K
            path.append(margin_target - (margin_target - margin_y1) * (K - t) / K)
        else:
            path.append(margin_target)
    return path
```
30 minutes.

### 1.3 Replace `ebit_t = ebit_prev × (1+g)` with `ebit_t = revenue_t × margin_t`
File: `module_4_dcf.py` line ~95. 10 minutes (after 1.2).

### 1.4 Fix growth source
Current: `growth_rate = cf_metrics.expected_growth_ebit or stable_growth`.
New: `growth_rate = assumptions.revenue_growth_next_year or cf_metrics.expected_growth_ebit or stable_growth`.
Primary source must be user story. 5 minutes.

### 1.5 Honor `revenue_growth_years_2_5`
For years 2–5, use `assumptions.revenue_growth_years_2_5 or revenue_growth_next_year`. Note: `revenue_growth_years_2_5` defaults to `revenue_growth_next_year` if blank (matches Ginzu B27=B25). 15 minutes.

### 1.6 Build tax rate path helper
```python
def _tax_path(t_effective, t_marginal, override_convergence, years=10):
    terminal = t_effective if override_convergence else t_marginal
    path = []
    step = (terminal - t_effective) / 5
    for t in range(1, years + 1):
        if t <= 5:
            path.append(t_effective)
        else:
            path.append(path[-1] + step)
    path.append(terminal)  # terminal year
    return path
```
20 minutes.

### 1.7 Thread effective tax rate through M4
Source from `CompanyValuationInput.effective_tax_rate_ciq` or `macro.tax_rate_effective`. Currently dead field. 15 minutes (includes orchestrator update).

### 1.8 Dynamic NOL carryforward
```python
def _apply_nol(ebit_path, tax_path, nol_initial):
    nol_balance = [nol_initial]
    taxes = []
    for t, (ebit, rate) in enumerate(zip(ebit_path, tax_path)):
        nol_start = nol_balance[-1]
        if ebit < 0:
            nol_end = nol_start - ebit  # grows
            taxable = 0
        else:
            taxable = max(0, ebit - nol_start)
            nol_end = max(0, nol_start - ebit)
        taxes.append(taxable * rate)
        nol_balance.append(nol_end)
    return taxes, nol_balance
```
40 minutes.

### 1.9 Sales-to-Capital reinvestment with lag
```python
def _reinvestment_path(revenue_path, revenue_terminal, g_terminal, sc_high, sc_stable, lag):
    """
    revenue_path: length 11, indices 0..10 (year 0 = base, years 1..10 projected)
    For lag ≥ 2 near end-of-horizon, extrapolate revenue using terminal growth.
    """
    # Extend revenue up to year 10 + max_lag
    extended = list(revenue_path)
    for _ in range(3):  # buffer for lag = 3
        extended.append(extended[-1] * (1 + g_terminal))

    reinvestment = []
    for t in range(1, 11):
        sc = sc_high if t <= 5 else sc_stable
        rev_a = extended[t + lag]
        rev_b = extended[t + lag - 1]
        reinvestment.append((rev_a - rev_b) / sc if sc > 0 else 0)
    return reinvestment
```
60 minutes.

### 1.10 WACC path helper
```python
def _wacc_path(wacc_initial, wacc_terminal, high_growth_years=5, total_years=10):
    path = []
    step = (wacc_terminal - wacc_initial) / (total_years - high_growth_years)  # negative typically
    for t in range(1, total_years + 1):
        if t <= high_growth_years:
            path.append(wacc_initial)
        else:
            path.append(wacc_initial + step * (t - high_growth_years))
    return path
```
20 minutes.

### 1.11 Cumulative discount factors
Replace `1/(1+wacc)^t` with year-by-year product:
```python
df = []
cumulative = 1.0
for wacc_t in wacc_path:
    cumulative = cumulative / (1 + wacc_t)
    df.append(cumulative)
```
15 minutes.

### 1.12 Invested capital + ROIC path tracking
Per `ginzu_spec_v2.md` §12.
```python
def _ic_roic_path(ic_base, reinvestment_path, nopat_path):
    ic = [ic_base]
    roic = []
    for rein, nopat in zip(reinvestment_path, nopat_path):
        roic.append(nopat / ic[-1] if ic[-1] > 0 else 0)
        ic.append(ic[-1] + rein)
    return ic, roic
```
Also: `ic_base = bv_equity + bv_debt - cash + (has_leases ? pv_leases : 0) + (has_rd ? value_of_research_asset : 0)`. Expose `ic_path[]` and `roic_path[]` on `DCFResult` for diagnostics. 30 minutes.

### 1.13 Honor `override_riskfree` + `riskfree_after_yr10` in terminal WACC
```python
if assumptions.override_cost_of_capital_stable:
    wacc_terminal = assumptions.cost_of_capital_stable_override
elif assumptions.override_riskfree:
    wacc_terminal = assumptions.riskfree_after_yr10 + mature_market_erp
else:
    wacc_terminal = macro.risk_free_rate + mature_market_erp
```
Need to surface `mature_market_erp` from the Damodaran country ERP dataset (Country ERP!B1). 15 minutes (plus Phase 4.2 dataset parse).

### 1.14 Honor `override_growth_perpetuity`
```python
if assumptions.override_growth_perpetuity:
    g_terminal = assumptions.growth_perpetuity_rate
elif assumptions.override_riskfree:
    g_terminal = assumptions.riskfree_after_yr10
else:
    g_terminal = macro.risk_free_rate
```
5 minutes.

### 1.15 Move failure adjustment to operating assets (before bridge)
Before:
```python
value_of_equity = bridge_components
if failure_probability > 0:
    value_of_equity = value_of_equity * (1 - p) + distress * p
```
After:
```python
# Compute value_as_going_concern first (sum of PVs + PV_terminal)
distress_value = (
    (raw.bv_equity + raw.bv_debt) * distress_pct if failure_tie_to == "B"
    else value_as_going_concern * distress_pct
)
value_of_operating_assets = value_as_going_concern * (1 - p) + distress_value * p
# THEN run equity bridge from value_of_operating_assets
```
20 minutes.

### 1.16 Equity bridge completion
```python
debt_total = raw.bv_debt + (adjusted.pv_of_operating_leases if has_leases else 0)
value_of_equity = (
    value_of_operating_assets
    - debt_total
    - (raw.minority_interests or 0)
    + cash_usable
    + (raw.cross_holdings or 0)
)
```
10 minutes.

### 1.17 Trapped cash adjustment
```python
if assumptions.override_trapped_cash:
    cash_usable = raw.cash - assumptions.trapped_cash_amount * (
        macro.tax_rate_marginal - assumptions.trapped_cash_tax_rate
    )
else:
    cash_usable = raw.cash
```
15 minutes.

### 1.18 M3 lease depreciation add-back
Fix `backend/engine/module_3_cashflow.py` to include `adjusted.depreciation_on_lease_asset` in `adjusted_d_a`. 5 minutes.

### 1.19 M3 pass `macro.tax_rate_marginal` directly
Remove the reverse-engineer-tax-from-Kd hack. Pass `macro.tax_rate_marginal` directly. 10 minutes (plus signature update).

### 1.20 Ginzu NVIDIA ground-truth test
New file: `backend/tests/engine/test_ginzu_nvidia_ground_truth.py`.
- Load `knowledge_base/Ginzu_NVIDIA.xlsx`, extract Input sheet values (cells B10..B23 base year, all story assumptions, all override flags and values).
- Feed to our engine.
- Compare `value_per_share` against Ginzu's Valuation output B52 (77.51 in the sample).
- Tolerance: **within 2%** (tighter target is 1% but allow 2% for floating-point + ordering differences).
- Also verify year-by-year revenue, EBIT, NOPAT, FCFF match within 1%.

120 minutes.

### 1.21 Fix lease `n_additional = 0` edge case
Remove the `max(1, ...)` floor in `capitalize_operating_leases()`. Add explicit single-payment fallback per `ginzu_spec_v2.md` §4. 15 minutes.

**Phase 1 total effort: ~7 hours.**

**Exit criteria:** all 65 existing tests still pass + new NVIDIA ground-truth test passes within 2% tolerance.

---

## Phase 2 — Self-Consistency Feedback Loops

**Deliverable:** synthetic rating ↔ Kd ↔ WACC iteration, option dilution iteration.

### 2.1 Rating & coverage lookup tables
New file: `backend/data_sources/damodaran_credit.py`.
- Parse `Synthetic rating!A22:D36` (large-firm coverage table, 15 rows)
- Parse `Synthetic rating!A41:D55` (small/risky-firm table, 15 rows)
- Parse `Synthetic rating!F22:I36` (third-type / financial firm table, 15 rows)
- Parse `Synthetic rating!G42:H56` (rating-code → spread lookup for actual rating)

Input data is embedded in the Ginzu workbook OR downloadable from Damodaran's `synthrating.xls` + `ratings.xls` (add to `download_damodaran.py`). 90 minutes.

### 2.2 Synthetic rating computation in M2
```python
def synthetic_rating(ebit, interest, firm_type, riskfree, country_default_spread):
    if interest == 0:
        coverage = 1e6
    elif ebit < 0:
        coverage = -1e5
    else:
        coverage = ebit / interest
    table = coverage_tables[firm_type]  # 1 | 2 | 3
    rating, spread = lookup_rating_and_spread(coverage, table)
    return riskfree + spread + country_default_spread
```
30 minutes.

### 2.3 Rating-approach dispatch in `compute_cost_of_capital()`
Add `rating_approach: str = "industry_fallback"` parameter with branches for "actual" / "synthetic" / "industry_fallback" / "direct". 45 minutes.

### 2.4 Option dilution iteration
Rewrite `backend/engine/module_6_options.py`:
```python
def compute_options_value_iterative(S_seed, K, T, r, sigma, y, n_shares, n_warrants, tol=0.01, max_iter=20):
    call_value = 0.0
    for _ in range(max_iter):
        adjusted_S = (S_seed * n_shares + call_value * n_warrants) / (n_shares + n_warrants)
        d1 = (log(adjusted_S / K) + (r - y + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        new_call = adjusted_S * exp(-y * T) * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
        if abs(new_call - call_value) < tol:
            return new_call
        call_value = new_call
    return call_value
```

**Design decision needed:** `S_seed` = current market price (Ginzu style) or intrinsic pre-options (current behavior)? Recommendation: **match Ginzu (market price)** for spec fidelity; make it configurable via parameter for advanced users. 45 minutes.

### 2.5 Iteration convergence tests
`backend/tests/engine/test_options_convergence.py`. 60 minutes.

**Phase 2 total: ~4.5 hours.**

---

## Phase 3 — Stage 3 Cost of Capital Variants

### 3.1 Multi-business unlevered beta (US + Global)
- `BusinessSegment` schema: `{name, revenue, industry_code_us, industry_code_global}`.
- `CompanyValuationInput.business_segments: list[BusinessSegment]`.
- `compute_multi_business_beta(segments, region)`: EV-weighted per `ginzu_spec_v2.md` §5.1.
60 minutes.

### 3.2 Direct-input for unlevered & levered beta
Add explicit Direct-Input branches. Do NOT replicate Ginzu's B23 fallthrough bug. 15 minutes.

### 3.3 Multi-country / multi-region ERP blending
- Extend schema with `revenue_by_country: dict[str, float]` and `revenue_by_region: dict[str, float]`.
- `compute_multi_country_erp()`, `compute_multi_region_erp()` — revenue-weighted.
- Parse Country ERP rows 201–210 (10 regional aggregates) in our `country_risk_parser.py`.
90 minutes.

### 3.4 Bond-priced MV of debt
- Add `weighted_avg_debt_maturity` field to schema.
- Compute `mv_debt = interest × annuity_factor + bv_debt / (1+kd)^maturity`.
- Add lease-PV separately.
45 minutes.

### 3.5 Preferred stock schema + WACC term
- Extend schema with `preferred_shares`, `preferred_dividend_per_share`, `preferred_price_per_share`.
- Add preferred weight and cost to WACC.
60 minutes.

### 3.6 Convertible debt
- Extend schema with `convertible_book`, `convertible_interest`, `convertible_maturity`, `convertible_market_value`.
- Bond-price the straight debt component of convertibles.
- Equity component = `market_value - straight_debt_component` (for reference only; not included in debt weight).
45 minutes.

### 3.7 Approaches 2 & 3 (industry average & regional decile)
- Load Damodaran's base RF constant (refresh annually from dataset metadata, not hard-code 3.88%).
- Approach 2: industry_wacc + (user_rf - damodaran_base_rf).
- Approach 3: 5×5 table lookup. Note: Ginzu lacks RF adjustment in Approach 3; our implementation applies it for consistency with Approach 2 (document deviation).
60 minutes.

**Phase 3 total: ~7 hours.**

---

## Phase 4 — Missing Data Intake

### 4.1 CIQ template additions
Add to `capiq_formula_map.py`:
- `IQ_GEOGRAPHIC_SEGMENTS_NAME` / `IQ_GEOGRAPHIC_SEGMENTS_REV`
- `IQ_BUSINESS_SEGMENTS_NAME` / `IQ_BUSINESS_SEGMENTS_REV`
- `IQ_SP_RATING`
- `IQ_PREFERRED_STOCK`, `IQ_PREFERRED_SHARES`, `IQ_PREFERRED_DIVIDEND_RATE`
- `IQ_AVG_MATURITY_LT_DEBT` (or manual input fallback)
- `IQ_STOCK_PRICE_STANDARD_DEVIATION`

45 minutes.

### 4.2 Damodaran dataset additions
Add to `download_damodaran.py`:
- `ratings.xls` — rating → default spread table.
- `synthrating.xls` — coverage → synthetic rating tables (small + large firm).
- `cumdefrates.xls` — default probabilities by rating × time horizon (Stage 8 reference).
- Mature market ERP metadata (extract from `ctryprem.xls`).

Create parsers under `backend/data_sources/damodaran_parsers/`. 2 hours.

### 4.3 Parse regional aggregates
Extend `country_risk_parser.py` to emit the 10 regional ERP aggregates (Africa, Asia, …) in addition to per-country data. 30 minutes.

### 4.4 Enhance `read_ciq_template.py` for new fields
Preserve backward compat; handle variable-length segment arrays. 60 minutes.

**Phase 4 total: ~4.5 hours.**

---

## Phase 5 — UI Surfaces

### 5.1 SummarySheet.tsx (year-by-year DCF table)
Mirror Ginzu `Summary Sheet`. Single scrollable table: Year × {Revenue, Growth, Margin, Op Income, NOL, Tax Rate, NOPAT, Reinvestment, FCFF, WACC, Discount Factor, PV}. Base year + 10 explicit years + terminal row. Data already exists in `DCFResult` after Phase 1 (via `ic_path`, `roic_path`, plus existing projections). 2 hours.

### 5.2 RelativeValuation.tsx
Surface M5 multiples output (intrinsic vs market PE / PBV / EV-EBITDA / EV-Sales). Color-coded over/under. 1.5 hours.

### 5.3 CountryRiskBlender.tsx
Editable country × revenue table; auto-computes weighted ERP from Damodaran country data. Feeds `revenue_by_country` / `revenue_by_region` for Phase 3.3. 2 hours.

### 5.4 IndustryAveragesBrowser.tsx
Searchable table over Damodaran industries (US + Global). Reference view. 1.5 hours.

### 5.5 SyntheticRating.tsx wiring
Currently frontend-only math. Wire to M2 synthetic-rating output so displayed rating/Kd reflects engine state. 45 minutes.

### 5.6 FailureRate.tsx wiring
Show effective failure probability applied + effect on `value_of_operating_assets`. Add reference tables (BLS age+industry, rating cumulative default) as lookup helpers. 90 minutes.

### 5.7 Diagnostics expansion
Full textbook Section 15 sanity checks + the two new Ginzu-Diagnostics-sheet metrics (`pv_of_nopat_10yr`, `value_effect_of_reinvestment`). 2 hours.

### 5.8 Benchmark columns on InputSheet.tsx
Industry-avg (US + Global) + 1st/median/3rd quartile columns alongside each story input. Ginzu shows columns I/J/K/L/M/N. Data from `Input Stat Distributioons` sheet — requires Phase 6 parser. 1 hour (after Phase 6).

**Phase 5 total: ~12 hours.**

---

## Phase 6 — Statistical Layer

### 6.1 Parse `statsmicro.xls` / `statsmacro.xls`
Industry quartile data (revenue growth, operating margin, S/C, cost of capital) — 1924 cells per file. 90 minutes.

### 6.2 Display on InputSheet.tsx
Phase 5.8 above. Already counted.

### 6.3 Tornado sensitivity engine
For top-N drivers (growth, margin, S/C, WACC, g_terminal): compute `value_per_share` at ±1σ, ±2σ from user input. Horizontal bar chart. 3 hours.

### 6.4 Monte Carlo simulation
Sample from input distributions; 1,000 iterations; histogram + percentile bands. 4 hours.

**Phase 6 total: ~8.5 hours.**

---

## Phase 7 — Excel Export with Live Formulas

Per CLAUDE.md Rule 8: every computed cell must be a live Excel formula.

### 7.1 Audit `backend/api/export_workbook.py` for formula vs static cells
(Current 1,282 LOC.) 1.5 hours.

### 7.2 Refactor to fully formula-based
All compute cells become formulas; cross-sheet refs like `='Input Sheet'!B25`. Stable cell positions map maintained. 6 hours.

### 7.3 Replicate Ginzu sheet structure
All canonical sheets (Input, LTM, R&D, Leases, Cost of Capital, Synthetic Rating, Country ERP, Valuation Output, Option Value, Summary, Diagnostics) with live formulas. 3 hours.

**Phase 7 total: ~10.5 hours.**

---

## Phase 8 — Windows Fetch-Agent Daemon (Optional Enhancement)

**Goal:** upgrade Phase A (template upload) to one-click fetch. Optional; Phase A remains a supported fallback.

### 8.1 Windows-side FastAPI daemon
New file: `tools/windows_fetch_agent/main.py` (or separate repo). Single endpoint: `POST /fetch {ticker} → resolved .xlsx`. Wraps existing `backend/data_sources/capiq_excel_automation.py` (which already drives Excel COM). Adds bearer-token auth. 3 hours.

### 8.2 Network tunnel
User picks one: Tailscale / WireGuard / local LAN / ngrok. Configuration doc only, no code. 30 minutes.

### 8.3 Linux backend integration
Add `CIQ_FETCH_MODE` env var: `"template_upload"` (default) | `"windows_agent"`. When "windows_agent", POST to the Windows daemon URL. 1.5 hours.

### 8.4 Frontend toggle
Let users choose "upload resolved template" vs "fetch from Windows agent" if agent URL is configured. 30 minutes.

**Phase 8 total: ~5.5 hours.**

---

## Grand Summary

| Phase | Theme | Effort (hours) |
|---|---|---:|
| A | Data acquisition (template upload) | 1 |
| 1 | Core DCF correctness | 7 |
| 2 | Self-consistency loops | 4.5 |
| 3 | Stage 3 variants | 7 |
| 4 | Missing data intake | 4.5 |
| 5 | UI surfaces | 12 |
| 6 | Statistical layer | 8.5 |
| 7 | Excel export | 10.5 |
| 8 | Windows fetch-agent (optional) | 5.5 |
| **Total** | | **~60.5** |

**Approximate calendar time:** 8–12 working days at a sustainable pace.

**Minimum viable Ginzu-fidelity release:** Phase A + Phase 1 + Phase 2. ~13 hours. Produces Ginzu-equivalent valuations for any publicly-traded firm with a resolved CIQ template, including synthetic rating and option dilution.

---

## Key Dependencies

```
A (data acquisition) ──► Phase 1 (needs CIQ template to test NVIDIA)
   │
Phase 1 ──► Phase 2 (WACC iterate requires correct base)
   │         │
   │         └──► Phase 5.5 (synthetic rating UI wiring)
   │
   ├──► Phase 3 (variants need Phase 1 baseline + Phase 4.2 data)
   │
   ├──► Phase 5.1 (SummarySheet needs Phase 1 complete DCFResult fields)
   │
   ├──► Phase 5.7 (Diagnostics needs Phase 1 new metrics)
   │
   └──► Phase 6 (sensitivity needs working DCF)

Phase 4.2 (credit datasets) ──► Phase 2.1 (rating tables needed)
Phase 4.3 (regional aggregates) ──► Phase 3.3 (multi-region ERP)

Phase 7 (Excel export) depends on Phases 1, 2, 3 for formula logic.
Phase 8 (Windows agent) independent — can ship any time.
```

---

## Change Log

- **2026-04-19** (previous plan): `docs/project_plan_next_steps.md` issued, 7-phase plan based on textbook MD.
- **2026-04-28** (this plan): reissued after full Ginzu workbook reconciliation walk. Key changes:
  - Phase 0 (Data Acquisition) added as explicit Phase A, locking Option A as canonical.
  - Phase 1 expanded from 19 tasks to 21 (added lease `n_additional=0` edge case; Ginzu NVIDIA ground-truth test broken into 1.20 dedicated line item).
  - Phase 3 expanded to include Direct-Input beta (3.2) and convertible debt (3.6) per Ginzu inspection.
  - Phase 4 adds mature-market-ERP metadata extraction (needed for Phase 1.13 default terminal WACC).
  - Phase 5 adds Benchmark columns (5.8) mirroring Ginzu's Industry Stat Distributions reference columns.
  - Phase 8 (Windows fetch-agent) added as optional enhancement over Phase A.
  - Total effort: 60.5 hrs vs prior 50 hrs (+10.5 hrs absorbing the new-found gaps).

---

*End of `project_plan_v2.md`. Implementation begins with Phase A (verify template upload works) followed immediately by Phase 1 (DCF rewrite).*
