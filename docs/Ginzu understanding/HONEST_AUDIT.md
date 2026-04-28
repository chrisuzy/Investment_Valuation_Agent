# Honest Audit — Code vs Ginzu Understanding Docs

**Stop-the-world self-check.** This document is written from actual code reads, not from memory. Every claim is what the file literally does, not what I wish it did.

**Purpose:** give the user a specific per-module list of gaps between my module_XX.md promises and the actual backend/frontend implementation, so priorities can be set with full information.

---

## Module 01 — LTM

**Doc promises:** `LTM = FY0 − Prior_YTD + Current_YTD`; balance sheet from FQ-0; K-parameter alignment using `+4` offset for prior year.

**Backend (`ltm_calculator.py`, 94 LOC):**
- Formula: ✅ correct (FQ-0..FQ-(K-1) for current, FQ-4..FQ-(K+3) for prior). Verified end-to-end against 4 test companies.
- Called by orchestrator: ✅ yes (feeds all downstream modules).
- Insufficient-data guard: ✅ present.
- Balance-sheet FQ-0 snapshot with FY-0 fallback: ✅ present.

**Frontend (`TrailingTwelveMonth.tsx`, `InputSheet.tsx`):**
- Input Sheet reads `data.ltm_financials` (authoritative): ✅
- TTM page reads `data.ltm_financials`: ✅
- Insufficient-data warning banner: ✅

**Verdict: matches doc.**

---

## Module 02 — R&D Capitalization

**Doc promises:** Straight-line amortization with unamortized fraction = (N-t)/N; current R&D + Σ(unamortized) = value of research asset; EBIT adjustment = current R&D − amortization; industry-specific N defaults.

**Backend (`module_1_adjustments.py::capitalize_r_and_d`):**
- Formula: ✅ exact match.
- `r_and_d_expense_current` sourced from LTM: ✅ (rectification applied this session).
- Industry-specific N default: ✅ (lookup table in routes.py covers 10 industries).

**Frontend (`RDConverter.tsx`, `InputSheet.tsx` §3):**
- Derivation schedule shown: ✅ (on dedicated RDConverter page).
- Industry-specific hint next to N: ❌ UI still shows "3, 5, or 10" generic hint; doesn't tell user "for your industry (Software), 5 is Damodaran's default".
- R&D-to-revenue ratio context for historical years: ❌ not shown.
- Outputs shown on Input Sheet §3: ❌ only inputs displayed.

**Verdict: calculation correct; UI reference data from my Rule F audit NOT implemented.**

---

## Module 03 — Operating Leases

**Doc promises:** Yr1-5 discounted individually; beyond-yr5 treated as annuity whose length = round(beyond / avg yr1-5); annual depreciation = PV / total years; EBIT adjustment = lease expense − depreciation; D&A add-back.

**Backend (`module_1_adjustments.py::capitalize_operating_leases` + `module_3_cashflow.py`):**
- Formula: ✅ exact.
- Edge case `n_additional = 0` (single payment in yr6): ✅ fixed this session.
- `depreciation_on_lease_asset` added to `adjusted_d_a` in M3: ✅ fixed this session.

**Frontend (`LeaseConverter.tsx`):**
- Full derivation shown: ✅.
- Has-leases toggle with hint about post-2019 double-count risk: ❌ just a Yes/No, no guidance.

**Verdict: calculation correct; UI minimal.**

---

## Module 04 — Cost of Capital (THIS IS WHERE THE GAP IS HUGE)

**Doc promises:** 4 approaches + 5 β variants + 4 ERP variants + 3 Kd variants + preferred stock + convertible debt + bond-priced MV of debt.

**Backend (`module_2_risk.py`, 69 LOC):**

| Doc promise | Code reality | Status |
|---|---|---|
| Approach "Direct input" (analyst types WACC) | not implemented | 🔴 MISSING |
| Approach "Detailed" | supported as the only option | ✅ (partial — see below) |
| Approach "Industry Average" | not implemented | 🔴 MISSING |
| Approach "Decile" | not implemented | 🔴 MISSING |
| β "Single Business(US)" | supported | ✅ |
| β "Single Business(Global)" | supported via region param | ✅ |
| β "Multi Business(US)" | not implemented | 🔴 MISSING |
| β "Multi Business(Global)" | not implemented | 🔴 MISSING |
| β "Direct Input" (levered) | not implemented | 🔴 MISSING |
| β "Direct Input" (unlevered) | not implemented | 🔴 MISSING |
| ERP "Country of Incorporation" | supported | ✅ |
| ERP "Operating Countries" (revenue-weighted) | not implemented | 🔴 MISSING |
| ERP "Operating Regions" (revenue-weighted) | not implemented | 🔴 MISSING |
| ERP "Will Input" (direct) | not implemented | 🔴 MISSING |
| Kd "Industry Fallback" | supported as the only path | ✅ |
| Kd "Direct Input" | not implemented | 🔴 MISSING |
| Kd "Synthetic Rating" | not implemented | 🔴 MISSING (tables not loaded) |
| Kd "Actual Rating" | not implemented | 🔴 MISSING (tables not loaded) |
| MV of debt via bond pricing | not implemented (uses book) | 🔴 MISSING |
| Preferred stock WACC term | not implemented | 🔴 MISSING |
| Convertible debt decomposition | not implemented | 🔴 MISSING |
| Levered β formula | supported | ✅ |
| CAPM | supported | ✅ |
| After-tax Kd | supported | ✅ |
| 2-term WACC (E+D) | supported | ✅ (missing P term) |

**Frontend:**
- Methodology-choice selectors: ❌ do not exist as interactive controls anywhere.
- Cost of Capital page: shows computed results only; no path selection.

**Verdict: ~15% of documented functionality present. The rest of the doc is aspirational.**

---

## Module 05 — DCF Projection

**Doc promises:** Revenue path (yr1 / yr2-5 / yr6-10 convergence), margin path, tax path, NOL, S/C reinvestment with lag 0-3, WACC path.

**Backend (`module_4_dcf.py`, 416 LOC after rewrite):**
- Revenue path: ✅.
- Margin path with K-year convergence: ✅.
- Tax path with effective → marginal convergence + override: ✅.
- NOL dynamic carryforward: ✅.
- S/C reinvestment with lag 0/1/2/3: ✅.
- WACC path: ✅.

**Frontend:**
- Summary Sheet year-by-year table: ✅.
- Reinvestment lag selector (0/1/2/3 dropdown): ❌ (field is editable number, not a dropdown).
- All override Yes/No toggles: ✅ present in §11.

**Verdict: calculation matches doc. Minor UI gap (lag isn't a dropdown).**

---

## Module 06 — Terminal + PV

**Doc promises:** Gordon growth; year-by-year cumulative discount factors; terminal WACC dispatch; terminal ROIC default = terminal WACC.

**Backend:**
- All of the above: ✅.

**Frontend:**
- Summary Sheet shows terminal-row values: ✅.

**Verdict: matches doc.**

---

## Module 07 — Failure + Bridge

**Doc promises:** Overlay applied to going-concern before bridge; tie-to "B" vs "V"; full bridge (−debt −minority +cash +cross); trapped-cash adjustment.

**Backend:**
- All of the above: ✅.

**Frontend:**
- Failure Rate page: ⚠️ shows inputs but not the derivation tables (rating/age) from Ginzu's reference.
- Failure tie-to dropdown ("B"/"V"): ✅ present on Input Sheet §11.
- Trapped-cash override toggle + amount + foreign tax: ✅.

**Verdict: calculation matches doc. Ginzu's Failure Rate reference tables not exposed in UI.**

---

## Module 08 — Options Dilution

**Doc promises:** Iterative fixed-point BSM with dilution-adjusted stock price.

**Backend (`module_6_options.py`):**
- Iteration: ✅ added this session.
- Black-Scholes: ✅.

**Frontend (`OptionValue.tsx`):**
- Shows BSM inputs + outputs: ✅.
- Iteration convergence indicator: ❌.

**Verdict: calculation now correct per doc.**

---

## Module 09 — Per-Share

**Doc promises:** Division + verdict bands.

**Both:** ✅ trivial, works.

---

## The actual picture

**Modules 01, 02, 03, 05, 06, 07, 08, 09:** calculation formulas match Ginzu; single supported path works correctly. UI gaps are around reference-data-for-analyst-judgment (Rule F) — hints, industry defaults, derivation-tables — not calculation gaps.

**Module 04:** this is the real problem. ~85% of documented functionality is not implemented. I wrote a 280-line doc describing 4+5+4+3 variants and the code supports only 1+1+1+1 of them. The docs ARE aspirational; the code is NOT the doc.

**Specific lies my docs currently tell:**
- Frontend does NOT have methodology-choice dropdowns (docs say it should; Rule B1).
- Backend does NOT branch on those dropdowns (docs say it should; Rule B2).
- Backend does NOT implement multi-business beta, multi-country ERP, synthetic rating, actual rating, bond-priced MV debt, preferred stock, convertibles.
- Docs mention these as "NOT IMPLEMENTED" in the "assessment" section at the bottom — but the bulk of each doc reads like these variants work, making the overall effect misleading.

**What the user probably sees and calls "completely wrong":**
- Reads module_04_cost_of_capital.md, sees rich variant structure
- Opens the app, sees no dropdowns for any of those variants
- Concludes: implementation and docs are disconnected
- Correct conclusion

---

## What I recommend fixing, in priority order

**Priority 1 (actual correctness, non-negotiable):**
- None. The formulas for supported paths are correct per my audits.

**Priority 2 (honest selectors — closes the doc-vs-code gap):**
1. Add frontend selectors for every methodology-choice family (4 approaches, 5 betas, 4 ERPs, 3 Kds). Each dropdown OPTION exists; backend branches that aren't implemented raise a clear "not yet supported" warning. At minimum the selectors expose the Ginzu structure in the UI.
2. Implement the simple direct-input branches (β direct, ERP direct, Kd direct, WACC direct). Each is 5-10 lines of backend code. Lets users override when the default path doesn't suit.

**Priority 3 (substantive new variants — larger scope):**
3. Multi-business β (requires segment schema + UI).
4. Multi-country ERP (requires country-revenue schema + UI).
5. Synthetic rating (requires loading coverage tables).
6. Actual rating (requires loading rating-spread table).
7. Bond-priced MV debt (requires maturity field).
8. Preferred stock (requires schema additions).
9. Convertible debt (requires schema additions).

**Priority 4 (UI reference-data per Rule F — the industry hints, historical trends, distribution quartiles):**
10. Every judgment cell gets adjacent reference data per Rule Set F. Mostly frontend work.

**Priority 5 (doc corrections):**
11. Every module_XX.md's "assessment" section gets updated to be more upfront about what IS and ISN'T implemented, instead of burying it at the bottom.

---

## My recommendation

Priority 2 is the highest-impact, lowest-risk work. Roughly 1-2 hours of focused AI work:
- Add MethodologyChoices schema with all documented options
- Add backend dispatch: implement direct-input branches; raise clear "not_supported" for non-implemented branches
- Add frontend selector section on Input Sheet (5 dropdowns)
- Verify 4 test companies still work on default paths
- Document which branches are "not yet supported" in-UI

This closes the doc-vs-code honesty gap without requiring me to implement multi-business beta or synthetic rating in one session.

If you want Priority 3 too, each item is 1-2 hours of additional work.

Tell me which of these you want me to do first, and I'll execute without further debate.
