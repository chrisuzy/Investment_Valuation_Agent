# Stage 6 — Derived Views: Skim Findings

**Source sheets (all display/presentation, not compute):**
- `Summary Sheet` (232 formulas, 165 non-pass-through)
- `Diagnostics` (33 formulas, 11 non-pass-through)
- `Valuation as picture` (212 formulas, 18 non-pass-through)
- `Stories to Numbers` (100 formulas, 27 non-pass-through)
- `Answer keys` (0 formulas — pure reference)

**Stage 6 conclusion:** all five sheets are display layers — they read values from `Valuation output`, `Cost of capital worksheet`, etc., and re-arrange them for human consumption. **No new compute logic.** The heart of the valuation is fully captured in Stages 1–5.

---

## 6.1 — Summary Sheet (232 formulas)

### Structure
Four stacked panels, each a Year × Metric table:

| Panel | Row range | Likely segment |
|---|---|---|
| 1 | 1–13 | Overall / Rest |
| 2 | 14–26 | AI segment (NVIDIA-specific) |
| 3 | 27–38 | Auto segment (NVIDIA-specific) |
| 4 | 39–49 | Combined total |
| Output block | 50+ | Value of operating assets, bridge summary |

### Formula patterns
- `=B2*D2`, `=B3*D3`, ... — revenue × margin = EBIT style computations
- `=B3/B2 - 1` — implied growth rate
- `=E2 - H2` — FCFF reconstruction
- ~165 non-pass-through formulas are all **derivation of display values from Valuation output's stored arrays**.

### Implication for our implementation
**Phase 5.1 in the old plan is exactly this** — a year-by-year DCF display on the frontend. Data already exists in `DCFResult.revenue_projections`, `ebit_projections`, `tax_projections`, `fcff_projections`, `pv_projections`. No new backend work; new frontend page only.

---

## 6.2 — Diagnostics (33 formulas)

The most interesting sheet for us — it's a framework-aware diagnostic display. Matches textbook Section 15.

### Key formulas (non-pass-through)

| Cell | Label | Formula (variable form) | Meaning |
|---|---|---|---|
| D3 | Annual Revenue Growth Rate (latest) | `= current_rev / prior_rev - 1` | check against industry avg |
| E3 | Annual Revenue Growth Rate (5yr CAGR) | `= (current_rev / rev_5yrs_ago)^(1/5) - 1` | 5-year CAGR |
| B21 | PV of after-tax operating income | `= Σ_{t=1..10} NOPAT_t × discount_t` | gross operating value (pre-reinvestment) |
| B22 | Value effect of reinvestment | `= B21 - B23` | how much reinvestment destroyed/created |
| C22 | Value effect as pct of B21 | `= B22 / B21` | reinvestment share of NOPAT-PV |
| B23 | PV of FCFF (10 years) | `= Σ_{t=1..10} FCFF_t × discount_t` | gross 10-year cash value |

### Implication
- **Useful diagnostic formulas** our `Diagnostics.tsx` page can display.
- Adds two metrics we don't currently compute: **PV of NOPAT** (pre-reinvestment) and **value destroyed/created by reinvestment** (PV of NOPAT - PV of FCFF).
- If reinvestment has positive NPV (ROIC > WACC), reinvestment creates value; if ROIC < WACC, it destroys value.
- **New DCFResult field candidate:** `pv_of_nopat_10yr` and `value_effect_of_reinvestment_10yr`.

### Plan implication
Small addition to Phase 1 or Phase 5.6: compute and expose these two diagnostic metrics. Sub-hour of work.

---

## 6.3 — Valuation as picture (212 formulas)

Visual waterfall showing base year → terminal year progression of Revenue, Margin, EBIT, EBIT(1-t).

Non-pass-through formulas are trivial: `=B10/B8` (margin from EBIT/revenue), `=E16+E17+E18` (row sums).

**No new compute.** Entirely a drawing/visualization sheet.

### Implication
`ValuationPicture.tsx` in our frontend is the rough equivalent. Phase 5.1 or Phase 5 expansion.

---

## 6.4 — Stories to Numbers (100 formulas)

Re-presents the key assumption drivers alongside the narrative. `StoriesToNumbers.tsx` in our frontend.

Non-pass-through formulas are straightforward cross-references: `=Diagnostics!C27` (pulls ROIC), `=B17*C17` (margin × revenue), `=E17-F17` (FCFF formation).

**No new compute.**

---

## 6.5 — Answer keys (0 formulas)

Just a Yes/No reference list. Used by data-validation dropdowns in the Input sheet.

No formulas. No compute. No translation needed.

---

## 6.6 — Stage 6 summary

- **All 5 derived-view sheets = display only.** No new compute logic discovered.
- **One useful diagnostic formula set** found in `Diagnostics` (rows 21–23): PV of NOPAT, value effect of reinvestment — worth adding to our `DCFResult` schema as a small Phase-1 addendum.
- **Summary Sheet structure** is the exact spec for our missing `SummarySheet.tsx` frontend page (Phase 5.1 in the old plan). Year × Metric table, 4 panels for multi-segment (or 1 panel for canonical single-segment).

**Total Ginzu compute formulas covered after Stage 6:** 1,675 of 1,675 (100%).
**Formulas on the critical path that we actively decoded:** approximately 700 (rows across Input sheet, LTM, R&D, Lease, Cost of Capital, Synthetic rating, Country ERP, Valuation output, Option value, and Diagnostics). The remaining ~975 are:
- Pure pass-through (cross-sheet echoes)
- Multi-segment overlays (AI, Auto) — skipped per user instruction
- Display-layer formulas on Summary/Picture/Stories sheets
- Reference data in Industry Averages, Input Stat Distributions, Country ERP data rows

**Ready for Stage 7 — synthesis of the three final deliverables.**
