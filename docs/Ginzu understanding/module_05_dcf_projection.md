# Module 05 — 10-Year DCF Projection

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, sheet `Valuation output` rows 2–10 (the per-year projection block).

---

## 1. What this module is trying to do

Take the LTM-rotated, adjustment-corrected base year and project ten explicit future years of operating cash flow. The projection follows Damodaran's three-period structure:

- **Years 1–5: high-growth period.** User-story inputs (growth rate, margin, sales-to-capital) hold constant at high-growth values.
- **Years 6–10: transition period.** Every lever — growth rate, operating margin, tax rate, sales-to-capital, WACC — linearly converges from the year-5 high-growth value toward its terminal/mature value.
- **Year 11+: terminal state.** Captured as a single Gordon-formula perpetuity (covered in Module 6).

The output is a stream of ten free cash flow to firm (FCFF) numbers plus an implied terminal-year cash flow, ready to be discounted.

---

## 2. The financial intuition

A good DCF doesn't project that a firm will grow at 15% forever — that's impossible in the long run (eventually the firm would exceed the economy). Nor does it assume the firm instantly becomes a mature utility — that ignores the firm's current competitive position.

The three-period structure captures this by acknowledging: firms have a current story (reflected in the high-growth inputs), they mature over time (reflected in the convergence mechanism), and eventually they settle into a stable state (reflected in the terminal perpetuity). The analyst's judgment is concentrated in the high-growth story — how aggressive the growth is, how fat the margins become, how efficiently capital is deployed. The convergence toward maturity is mechanical; the terminal state defaults to sensible values (growth at the risk-free rate, ROIC equal to WACC meaning no excess returns).

Every lever has a specific economic meaning:
- **Growth** — tells a story about market opportunity and market share.
- **Margin** — tells a story about competitive position and pricing power.
- **Sales-to-capital** — tells a story about capital efficiency (how much revenue each dollar of invested capital produces).
- **Tax rate convergence** — reflects that effective tax rates tend to drift toward statutory marginal rates as tax-minimization structures age.
- **WACC convergence** — reflects that high-growth firms eventually de-risk as they mature, their betas drop, their cost of capital falls.

---

## 3. The algorithm — in financial terms

### 3.1 Revenue path

Year 1 growth equals the analyst's first-year judgment. Years 2 through 5 grow at the analyst's two-through-five judgment (which defaults to the year-1 rate if the analyst leaves it blank). Years 6 through 10 linearly converge from the year-5 growth rate toward the terminal growth rate:

```
growth in year t (for t > high-growth years) 
  = growth at end of high-growth period
  − (growth at end of high-growth period − terminal growth) × (t − high-growth years) / transition years
```

Each year's revenue equals the previous year's revenue times one plus that year's growth rate. The base-year revenue is the LTM-rotated revenue from Module 1.

### 3.2 Operating margin path

Year 1's margin is the analyst's first-year judgment. Margins then converge linearly toward the terminal target margin by a specified convergence year (default year 5). Past the convergence year, the margin stays flat at target:

```
margin in year t (for 1 < t ≤ K)
  = target margin
  − (target margin − year-1 margin) × (K − t) / K
margin in year t (for t > K) = target margin
```

Where K is the margin convergence year.

### 3.3 Operating income

Revenue times margin. Explicitly NOT computed by compounding the previous year's EBIT by a growth rate — that would drift uncontrollably. The Ginzu discipline: every year's EBIT is rebuilt from the fundamentals (that year's revenue, that year's margin).

### 3.4 Tax rate path

Years 1–5 hold at the firm's current effective tax rate (reflecting whatever tax optimization the firm currently enjoys). Years 6–10 linearly converge to the marginal rate. The terminal year uses the marginal rate unless the analyst explicitly overrides to stay at effective (for firms with genuinely durable tax advantages).

### 3.5 NOL dynamic carryforward

If the firm has net operating losses carried forward, those shield income from tax until exhausted. Each year:
- If operating income is negative, the NOL balance grows by the loss amount.
- If positive, taxable income equals max(0, operating income − NOL balance); the NOL balance decreases by the amount consumed.

NOPAT is operating income minus computed tax. For a firm with no NOL, this simplifies to operating income × (1 − tax rate).

### 3.6 Reinvestment via sales-to-capital with lag

Damodaran's preferred reinvestment mechanic (different from the CapEx − D&A + ΔNCWC accounting approach): treat revenue growth as requiring capital investment in proportion to a sales-to-capital ratio. Each dollar of new capital produces (1 / S/C) dollars of new revenue.

```
reinvestment in year t = (revenue in year t + lag − revenue in year t + lag − 1) / S/C in year t
```

The lag parameter accounts for industries where capital takes years to produce revenue: software (0 lag), general industry (1 year), semiconductors (2–3 years), oil/real estate (3+ years). Defaults to 1 unless the analyst overrides.

The sales-to-capital ratio itself has two values: years 1–5 use a high-growth value; years 6–10 use a stable value. These reflect that capital efficiency typically changes as a firm matures.

### 3.7 Free cash flow to firm

```
FCFF in year t = NOPAT − reinvestment
```

This is the cash available to all capital providers after operating taxes and after funding the reinvestment needed to sustain projected growth. Discounting this stream at the WACC gives the value of the operating business.

### 3.8 WACC path

Flat at the initial WACC (from Module 4) for years 1–5. Linearly converges to the terminal WACC over years 6–10. The terminal WACC defaults to the risk-free rate plus the mature-market equity risk premium (roughly the rate a zero-beta, zero-net-debt firm would face at maturity), unless overridden by the analyst.

---

## 4. Inputs and where they come from

**From prior modules (FACT):**
- LTM base-year revenue, EBIT, effective tax rate (Module 1)
- Adjusted EBIT base (Modules 2 and 3)
- Initial WACC (Module 4)

**From user story (JUDGMENT):**
- Revenue growth year 1
- Revenue growth years 2–5
- Operating margin year 1
- Target pre-tax operating margin
- Margin convergence year (K)
- Sales-to-capital ratios (high-growth and stable)

**From user overrides (METHODOLOGY CHOICE):**
- Reinvestment lag (0, 1, 2, or 3 years)
- Tax convergence on/off
- NOL carried forward amount
- Risk-free rate after year 10
- Terminal growth rate

---

## 5. Outputs and what consumes them

Ten years of projections per metric (revenue, EBIT, tax rate, NOPAT, reinvestment, FCFF, WACC), plus terminal-year values, plus derived paths (invested capital, ROIC). Consumed by:

- **Terminal value module** — uses terminal-year NOPAT, terminal WACC, terminal growth rate, terminal ROIC.
- **Discounting module** — uses FCFF path and WACC path to compute cumulative discount factors and present values.
- **Implied variables** (invested capital, ROIC per year) — flow into the diagnostic rows in Ginzu's Valuation output for sanity-checking.

---

## 6. Current implementation assessment

### What works

The backend's `module_4_dcf.py` was rewritten in the 2026-04-28 autonomous session to faithfully implement every mechanic described above:
- Revenue path with year-1 / years-2-5 / years-6-10 structure
- Margin path with K-year linear convergence
- Operating income as revenue × margin (not compounded EBIT)
- Tax rate path with override support
- Dynamic NOL carryforward
- Sales-to-capital reinvestment with lag 0–3
- WACC path with terminal convergence
- Per-year NOPAT, FCFF outputs

All formulas match the Ginzu specification. The 18 formula-specific unit tests added in `test_ginzu_nvidia_ground_truth.py` all pass.

### Data-flow consistency

With Modules 1, 2, and 4 rectifications applied:
- Base-year EBIT and revenue come from the LTM-rotated values
- Marginal tax rate comes from the correct country-aliased lookup (now 25.89% for US, not 0%)
- Adjusted MV debt now falls back to BV debt when market value isn't available

The DCF projection now runs with correct upstream inputs across all four test companies.

### Frontend display

The Summary Sheet page (`SummarySheet.tsx`) shows the year-by-year projection table — revenue, growth, margin, EBIT, tax rate, NOPAT, reinvestment, FCFF, WACC, cumulative DF, PV — across all 10 years plus terminal. Color-coded by period (base = blue, high-growth = green, transition = green, terminal = purple). Hover tooltips on every cell describe the formula.

The Input Sheet Value Drivers section (§7) exposes the JUDGMENT cells with co-located reference data (historical CAGRs, industry medians, statistical quartile ranges).

### Known limitations (not calculation bugs)

- No frontend selector for reinvestment lag (user must edit the override value directly).
- The methodology choice "override tax convergence" is exposed as a Yes/No toggle; all override toggles work correctly.

---

## 7. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Reflects post-rectification state (LTM base year, correct t_marginal, bv_debt fallback). Source: `Ginzu_NVIDIA.xlsx`, `Valuation output` rows 2–10. |
