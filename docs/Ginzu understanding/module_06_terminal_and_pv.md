# Module 06 — Terminal Value, Discounting, Present Value Aggregation

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, `Valuation output` rows 30–37 (WACC path, cumulative discount factors, per-year PV, terminal block, value rollup).

---

## 1. What this module is trying to do

Two separate financial operations bundled here because Ginzu treats them together and they're tightly coupled computationally.

First, **terminal value** captures everything that happens after the explicit ten-year window closes. A firm doesn't stop generating cash flow in year 11 — it continues indefinitely. We need a single number representing the value, today, of all future cash flows from year 11 to infinity. Damodaran uses the Gordon growth formula for this: a perpetuity with a growth rate.

Second, **discounting to present value** rolls every year's projected cash flow (years 1 through 10) and the terminal value back to today, using the year-by-year WACC path. The sum of all those present values is the value of operating assets as a going concern — the total firm value before any adjustments for debt, cash, minorities, options.

For a typical company the terminal value is 50–75% of total firm value. This is NOT because Damodaran's method over-weights the terminal — it's because cash flows beyond year 10 really do represent the bulk of a productive business's economic value. Firms tend to be long-lived, and the discounted stream of cash flows from year 11 onward is large.

---

## 2. The financial intuition

### Why Gordon growth

In stable growth, a firm's free cash flow grows at a constant rate (g) into perpetuity. The present value of a perpetuity with constant growth is the first-period cash flow divided by (discount rate minus growth rate):

```
TV_at_end_of_year_10 = FCFF_terminal / (WACC_terminal − g_terminal)
```

This requires `WACC_terminal > g_terminal` or the formula blows up. Damodaran enforces `g_terminal ≤ risk_free_rate` as the binding constraint, reflecting the economic fact that no business can grow faster than the economy in perpetuity (or it would eventually exceed the economy).

### Why the terminal reinvestment follows growth and ROIC

In stable growth, to grow by g percent the firm must reinvest enough new capital to produce that g percent of new revenue. Given the firm's return on invested capital (ROIC) at maturity, the required reinvestment rate is:

```
Reinvestment rate at maturity = g_terminal / ROIC_terminal
```

If ROIC_terminal equals WACC_terminal (the default — no excess returns in stable growth), this simplifies to `g / WACC`. Terminal FCFF is then NOPAT_terminal × (1 − reinvestment rate).

### Why year-by-year cumulative discounting instead of a closed form

If WACC were constant across all ten years, we could use `1 / (1 + WACC)^t` for each year's discount factor. But WACC converges from initial to terminal over years 6–10, so each year's discount factor must be computed as the product of per-year `1 / (1 + WACC_t)` factors:

```
Cumulative discount factor for year t = product of [1 / (1 + WACC_k)] for k = 1 to t
```

This is mechanically more work but mathematically necessary when the discount rate varies. Ginzu does it this way in the `Valuation output` sheet; our backend does it this way in `module_4_dcf.py`.

### Why PV_of_terminal_value uses the year-10 cumulative factor

The terminal value we compute sits conceptually at the end of year 10 (the start of the perpetuity window). To bring it back to today, we discount by exactly ten years' worth of cumulative discount — the product of discount factors through year 10.

---

## 3. The algorithm — in financial terms

### 3.1 Terminal year inputs

```
Revenue_terminal = Revenue_year_10 × (1 + g_terminal)
EBIT_terminal = Revenue_terminal × target_operating_margin
NOPAT_terminal = EBIT_terminal × (1 − terminal_tax_rate)
```

The terminal year is year 11; it represents the first year of the perpetuity. We don't compute this year-by-year past year 10 — we express it as a single snapshot for the Gordon formula.

### 3.2 Terminal reinvestment

```
Reinvestment_rate_terminal = g_terminal / ROIC_terminal
Reinvestment_terminal = NOPAT_terminal × Reinvestment_rate_terminal
```

Where `ROIC_terminal` defaults to `WACC_terminal` (no excess returns at maturity) unless the analyst overrides with a higher value representing a durable competitive advantage.

If terminal growth is zero or negative, reinvestment is zero — no growth requires no new investment.

### 3.3 Terminal FCFF and terminal value

```
FCFF_terminal = NOPAT_terminal − Reinvestment_terminal
Terminal_value = FCFF_terminal / (WACC_terminal − g_terminal)
```

Guarded: if WACC_terminal ≤ g_terminal, terminal value is set to zero (the formula is undefined; this case should not arise with proper inputs but the guard prevents divide-by-near-zero explosions).

### 3.4 Terminal WACC and terminal growth dispatch

Terminal WACC uses an override hierarchy: analyst's explicit override wins, else risk-free-after-year-10 plus mature-market ERP, else current risk-free plus mature-market ERP.

Terminal growth uses a similar hierarchy: analyst's explicit perpetuity-growth override wins, else risk-free-after-year-10, else current risk-free. And terminal growth is capped at risk-free unless the analyst explicitly allows exceeding it.

### 3.5 Cumulative discount factors

```
DF_1 = 1 / (1 + WACC_1)
DF_t = DF_{t-1} × 1 / (1 + WACC_t)   for t = 2..10
```

### 3.6 Present values

```
PV_FCFF_t = FCFF_t × DF_t                    for t = 1..10
PV_terminal = Terminal_value × DF_10
```

### 3.7 Going-concern aggregate

```
Value_as_going_concern = sum of PV_FCFF_1 through PV_FCFF_10 + PV_terminal
```

This is the value of the operating business assuming continuous operation into perpetuity — not yet adjusted for failure probability or bridged to equity value.

---

## 4. Inputs and where they come from

**From Module 5 (DCF projection):**
- NOPAT path (for terminal-year extrapolation)
- Revenue path (for terminal revenue compounding)
- FCFF path (for PV sum)
- WACC path (for discount factors)

**From Module 4 (Cost of Capital):**
- Initial WACC (start of the WACC convergence)

**From user inputs (JUDGMENT / METHODOLOGY CHOICE):**
- Terminal growth rate (defaults to risk-free)
- Terminal WACC override (defaults to risk-free + mature-market ERP)
- Terminal ROIC override (defaults to terminal WACC)
- Target operating margin (used for terminal EBIT)

**From Module 1 (via macro):**
- Risk-free rate
- Equity risk premium (mature-market ERP approximation)

---

## 5. Outputs and what consumes them

- **Terminal value** — displayed in summary blocks, consumed by discounting math.
- **PV of terminal value** — added to the going-concern total.
- **Cumulative discount factors per year** — consumed by PV calculation, also useful for sensitivity analysis.
- **PV of each year's FCFF** — enters the going-concern sum and is displayed per-year on the Summary Sheet.
- **Value as going concern** — the primary output; feeds the failure overlay in Module 7.

---

## 6. Current implementation assessment

### Formula correctness

All terminal and PV formulas in `module_4_dcf.py` match Ginzu exactly:
- Terminal revenue = year-10 revenue × (1 + g_terminal) ✓
- Terminal NOPAT = terminal EBIT × (1 − terminal tax) ✓
- Terminal reinvestment = (g / ROIC) × NOPAT when growth positive, else 0 ✓
- Terminal value = FCFF_terminal / (WACC_terminal − g_terminal) with guard ✓
- Cumulative discount factors built year-by-year ✓
- PV sum aggregation ✓

MSFT verification:
- LTM revenue $305.5B → year-10 revenue $852B → terminal revenue growing at 4.25% RF
- Terminal value $3.76T
- PV terminal $1.50T
- Sum PV FCFF years 1–10: $1.25T
- Value of operating assets: $2.75T

### Data flow

Takes its inputs from Module 5's projections. No separate schema; all intermediate values live inside `DCFResult`.

### Frontend display

The Summary Sheet (`SummarySheet.tsx`) shows per-year WACC, cumulative DF, FCFF, PV, plus a terminal-value row. The aggregate rollup at the bottom shows Σ PV FCFF + PV terminal = value of operating assets, then the equity bridge and per-share calculations.

### Remaining

No calculation bugs. Terminal year is sometimes confusing in the UI because it's labeled as "Year 11 / Terminal" — clarity could be improved but not a correctness issue.

---

## 7. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Source: `Valuation output` terminal block + rows 30–37. |
