# Damodaran-grade Sensitivity Panel — Design

**Date:** 2026-05-03
**Status:** Approved (user went autonomous after design review)
**Replaces:** the v1 `SensitivityPanel` component (4 sliders + 2 line charts + 4 impact cards)

## Problem

The current What-if panel on `/valuation-output` is mechanical, not instructional:

- Four independent sliders (growth Y1, growth Y2-5, target margin, convergence year) — all other Damodaran drivers are hidden.
- No ranking — user can't see which assumption moves VPS most.
- No industry anchoring — a 15% growth rate looks the same whether it's reasonable or absurd for the firm's industry.
- No narrative framing — Damodaran teaches "story → numbers," but the panel offers only numbers.
- No visible terminal-value dominance — a DCF's 60-80% typically comes from year-11+, and nothing on screen signals this.

User feedback (verbatim): "the current adjustable sliders and hypotheses, along with their combinations and relationship to the curve's valuation, are currently very monotonous. This lacks financial instinct and fails to capture what Aswath Damodaran intended."

## Goal

Replace the v1 panel with a single cohesive section that makes the three most important Damodaran lenses simultaneously visible:

1. **Which drivers matter most** for this specific company — tornado chart ranked by |ΔVPS|.
2. **How those drivers compare to industry norms** — sliders annotated with Q1/Median/Q3 markers and a live percentile indicator.
3. **What plausible stories look like** — six archetype presets that set all 8 drivers coherently.

Scope of v1 intentionally excludes: equity-bridge waterfall, saved scenario comparison (Bull/Base/Bear), Monte Carlo distributions, 2D heat maps. These may follow in subsequent PRs.

## Design

### Layout (one panel, three stacked sections)

```
┌─────────────────────────────────────────────────────────────┐
│  VALUE DRIVER IMPACT RANKING                                 │
│  ┌────────────────┬────────────────────────────────────────┐ │
│  │ Target margin  │ ◄────── −$14.2   $73   +$18.6 ──────► │ │
│  │ Yrs 2-5 growth │   ◄──── −$9.5    $73   +$13.2 ───►    │ │
│  │ WACC           │    ◄─── −$8.1    $73   +$5.9 ──►      │ │
│  │ Terminal growth│     ◄── −$5.0    $73   +$6.2 ──►      │ │
│  │ Sales/capital  │       ◄ −$3.3    $73   +$3.7 ►        │ │
│  │ Growth Y1      │       ◄ −$3.0    $73   +$3.2 ►        │ │
│  │ Convergence yr │         −$1.3    $73   +$1.6          │ │
│  │ Failure prob   │         −$0.8    $73                  │ │
│  └────────────────┴────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  DRIVERS (ranked by impact)                │ LIVE IMPACT    │
│  #1 Target margin ▼ ──────●───── 22.0% p62 │ VPS  $73.44    │
│  #2 Yrs 2-5 growth ──●───────── 8.0%  p41  │ Mkt  $123.00   │
│  #3 WACC shift    ────●──────── +0bp  p47  │ P/V  1.68×     │
│  #4 Terminal g    ──────●────── 4.25% p55  │ OpA  $10,280   │
│  #5 Sales/capital ────●──────── 2.5   p38  │                │
│  #6 Growth Y1     ─────●─────── 8.0%  p40  │                │
│  #7 Convergence y ──────●────── 5     n/a  │                │
│  #8 Failure prob  ●──────────── 0%    n/a  │                │
├─────────────────────────────────────────────────────────────┤
│  STORY ARCHETYPES                                            │
│  [🚀 Disruptor*] [📈 Growth] [🏢 Mature] [⚡ Utility]        │
│  [🔄 Cyclical] [💔 Distressed]                               │
│  (* = closest to current dials)                              │
└─────────────────────────────────────────────────────────────┘
```

### Drivers (the canonical 8)

| # | Label | Input path | Sweep endpoints |
|---|---|---|---|
| 1 | Revenue growth Y1 | `valuation_assumptions.revenue_growth_next_year` | industry Q1 ↔ Q3 |
| 2 | Revenue growth Y2-5 | `valuation_assumptions.revenue_growth_years_2_5` | industry Q1 ↔ Q3 |
| 3 | Terminal growth | `valuation_assumptions.growth_perpetuity_rate` *(requires `override_growth_perpetuity=True`)* | canonical: 0% ↔ RF |
| 4 | Target operating margin | `valuation_assumptions.target_operating_margin` | industry Q1 ↔ Q3 |
| 5 | Margin convergence year | `valuation_assumptions.margin_convergence_year` | canonical: 2 ↔ 8 |
| 6 | Sales-to-capital | `valuation_assumptions.sales_to_capital_high` | industry Q1 ↔ Q3 |
| 7 | WACC level shift | `valuation_assumptions.wacc_level_shift_bps` **(new)** | canonical: −150 ↔ +150 bps |
| 8 | Failure probability | `valuation_assumptions.failure_probability` | canonical: 0% ↔ 30% |

All ranges are applied as-is; the bar length reflects the actual VPS delta at each endpoint, so the chart shows magnitude *and* asymmetry.

### Archetype preset values

| Archetype | Y1 growth | Y2-5 growth | Target margin | Conv year | S/C | WACC shift | Fail prob |
|---|---|---|---|---|---|---|---|
| 🚀 Disruptor | industry p90 | industry p85 | industry p75 | 7 | industry median | +100 bps | 5% |
| 📈 Growth | industry p70 | industry p65 | industry p60 | 5 | industry median | 0 | 2% |
| 🏢 Mature | industry median | industry median | industry median | 3 | industry median | 0 | 0% |
| ⚡ Utility | 3% (canonical) | 3% | industry p25 | 2 | industry p75 | −50 bps | 0% |
| 🔄 Cyclical | industry median | industry median | industry p40 | 5 | industry median | +50 bps | 3% |
| 💔 Distressed | −5% (canonical) | industry p10 | industry p10 | 8 | industry median | +150 bps | 20% |

Terminal growth defaults to the risk-free rate for all archetypes (Damodaran's hard ceiling).

"Industry p25/median/p75" resolves to the corresponding quartile from `industry_data` fields (revenue_growth, pretax_operating_margin, sales_to_capital). When industry data is unavailable for a particular driver, fall back to the canonical value used in the sweep range above.

### Components (unit boundaries)

```
frontend/src/components/sensitivity/
├── SensitivityPanel.tsx        # outer component, owns tornado+sliders+presets, fetches /sensitivity
├── TornadoChart.tsx            # renders ranked horizontal bars given {driver, deltaLo, deltaHi} list
├── DriverSlider.tsx            # single slider with Q1/Median/Q3 markers + percentile chip
├── ArchetypePresets.tsx        # 6 buttons, detects closest match to current inputs
└── archetype_definitions.ts    # canonical mapping; each archetype returns a patch object given industry_data
```

### Data flow

1. User lands on `/valuation-output`. `SensitivityPanel` mounts with current `data`.
2. Panel POSTs `{session_id}` to `POST /api/valuation/{sid}/sensitivity` → receives `[{driver, delta_lo, delta_hi, range_lo, range_hi, baseline_vps}]` for all 8 drivers.
3. Panel renders tornado + sliders (using industry Q1/Median/Q3 from `data.industry_data` + standardized per-driver ranges) + presets.
4. User moves a slider → local draft state updates instantly → after 300 ms, frontend dispatches `PATCH /api/valuation/{sid}` with the new driver value.
5. `App.tsx` re-renders with fresh data → `SensitivityPanel` re-renders → re-fetches tornado (the ranking changes as the operating point moves).
6. User clicks an archetype preset → frontend dispatches a *multi-field* patch via a single PATCH call (all 8 drivers at once).

### Backend changes

1. **New `MethodologyChoices.wacc_level_shift_bps: int`** (default 0). Applied in `compute_cost_of_capital` as `wacc += shift_bps / 10000` after the detailed computation. Provides a single knob to flex the total WACC for the tornado.

2. **New endpoint: `POST /api/valuation/{sid}/sensitivity`**
   - Body: none (reads session state).
   - Response:
     ```json
     {
       "baseline_vps": 73.44,
       "currency": "USD",
       "bars": [
         {"driver": "target_operating_margin", "label": "Target margin",
          "range_lo": 0.12, "range_hi": 0.32,
          "vps_lo": 59.20, "vps_hi": 92.04,
          "delta_lo": -14.24, "delta_hi": 18.60,
          "range_source": "industry_q1_q3"},
         …8 entries total
       ]
     }
     ```
   - Implementation: for each driver, clone the inputs, set the driver to `range_lo` then `range_hi`, run `run_full_valuation` twice, capture `value_per_share`. Restore original session untouched.
   - Range source: per-driver lookup — industry Q1/Q3 where `industry_data` has it, canonical values otherwise. Encoded in a new `backend/engine/sensitivity_ranges.py` module.

3. **Optional: `GET /api/valuation/archetypes?industry=<name>&region=<region>`**
   - Returns the 6 archetype payloads with industry-aware values filled in.
   - *Alternative:* compute archetype values client-side from `data.industry_data`, avoiding the round-trip. **Chosen: client-side**, to keep backend state stateless. Archetype math lives in `frontend/src/components/sensitivity/archetype_definitions.ts`.

### Percentile indicator

For each slider, the "p62" chip is the percentile of the current value within the industry distribution.

- For drivers with only Q1/Median/Q3 available (Damodaran's standard fields), compute percentile by piecewise-linear interpolation: map value → percentile using (p25→25, p50→50, p75→75) as anchor points, linear extrapolation beyond.
- For drivers without industry data, show "n/a".

Implementation lives in a small `percentile()` helper in `archetype_definitions.ts`.

### Edge cases

- **Industry data missing or zero:** fall back to canonical ranges; slider shows "no industry data" instead of percentile.
- **Failure probability tornado bar:** only shows downside (higher failure → lower VPS), so `delta_hi ≈ 0`. Render with only the left (red) half filled.
- **Terminal growth when `override_growth_perpetuity=False`:** panel sets the flag when the user moves the slider, so the value takes effect.
- **Sensitivity endpoint latency:** 8 drivers × 2 runs = 16 valuations. Each runs fast (~20 ms). Total ~320 ms. Acceptable; show a "recomputing…" subtitle while waiting.
- **Slider debounce while tornado is recomputing:** if a second slider commit fires while the first is still in flight, cancel the in-flight request and issue a new one. Use an `AbortController`.

### Testing

- **Backend unit:** new `sensitivity_endpoint_test.py` — posts a minimal demo, calls `/sensitivity`, asserts 8 bars returned with `baseline_vps == data.final.value_per_share`, and that `vps_lo ≠ vps_hi` for every driver.
- **Backend unit:** `wacc_level_shift` affects computed WACC by exactly the shift amount; double-check integration with `cost_of_capital_stable_override` (which wins for terminal phase).
- **Frontend typecheck + build:** existing pipeline.
- **Manual smoke (documented in handoff):** open `/valuation-output` with NVDA demo, verify tornado populates, sliders move VPS, archetype buttons load coherent values.

## Out of scope (v1)

- Equity-bridge waterfall chart (user scoped this out).
- Saved scenario comparison (Bull/Base/Bear).
- Monte Carlo distributions / probabilistic VPS.
- 2D heat map for pair-wise driver interaction.
- Clicking a tornado bar → animated explanation / sweep curve.

## Rollback

`rollback-pre-viz-redesign-2026-05-03` (tag at `3d583d0`) predates this entire sensitivity / palette redesign line of work. To unwind: `git reset --hard rollback-pre-viz-redesign-2026-05-03`.
