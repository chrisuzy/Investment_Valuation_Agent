# Module 09 — Per-Share Value + Market Verdict

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, `Valuation output` rows 51–54 (per-share arithmetic + market-price comparison).

---

## 1. What this module is trying to do

Take the final equity value (from Module 7's bridge adjusted for Module 8's option dilution) and convert it to a per-share number by dividing by the firm's outstanding share count. Compare that intrinsic per-share value against the current market price to produce a verdict: undervalued, fairly valued, or overvalued.

This is arithmetically trivial. The interpretive question — what do we do with the output — is the more interesting part.

---

## 2. The financial intuition

### Per-share math is just division

```
Value per share = Value of equity in common stock / Shares outstanding
```

Shares outstanding is the **basic** (not diluted) share count. The dilution adjustment happened in Module 8 via the options subtraction; dividing by diluted share count here would double-count dilution.

### Market verdict bands

Damodaran's rule-of-thumb interpretation:

- **Market-to-intrinsic > 1.20** → stock appears significantly overvalued
- **1.00 to 1.20** → modestly overvalued
- **0.80 to 1.00** → modestly undervalued
- **< 0.80** → significantly undervalued

The 20% buffer zone acknowledges that intrinsic valuation is an OPINION, not a measurement. A 20% gap may reflect the analyst's story being wrong, not the market. Before declaring "the market is irrational," the analyst should re-examine their assumptions.

### What the per-share number is NOT

It is NOT a price target. It is NOT a prediction of where the stock will trade. It is the analyst's estimate of fundamental value given the specific narrative inputs (growth, margin, capital efficiency, risk) encoded in the valuation. Different analysts will legitimately arrive at different per-share values for the same firm because they tell different stories. The only claim the DCF makes is: IF your story is right, THEN the firm is worth this much per share today.

---

## 3. The algorithm — in financial terms

```
Value_per_share_pre_options = Value_of_equity_pre_options / Shares_outstanding

After Module 8's iterative dilution calculation:
Value_per_share_final = (Value_of_equity_pre_options − Value_of_all_options) / Shares_outstanding

Market_to_intrinsic_ratio = Current_stock_price / Value_per_share_final
```

Where Shares_outstanding is the most recent 10-Q basic share count (from Module 1's FQ-0 balance-sheet snapshot).

---

## 4. Inputs and where they come from

- **Value of equity pre-options** — Module 7 output
- **Value of all options** — Module 8 output
- **Shares outstanding** — Module 1 LTM/FQ-0 balance-sheet snapshot
- **Current stock price** — Module 0 market data (current, not rotated)

No user judgment. Pure arithmetic and display.

---

## 5. Outputs and what consumes them

- **Intrinsic value per share** — the headline DCF number, displayed prominently on Valuation Output, Summary Sheet, and Relative Valuation pages.
- **Price-to-value ratio** — displayed with a color-coded verdict band on the summary views.

These are the numbers the analyst ultimately cares about — everything else in the pipeline exists to support them.

---

## 6. Current implementation assessment

### Formula correctness

Pure division. Backend computes it correctly. Tests pass. No gaps.

### Frontend display

The Summary Sheet's "Value Rollup" block shows:
- Value of equity in common stock
- Value per share (pre-options)
- Value per share (final)
- Market price
- Price / Value ratio

With verdict-band color coding implied by sign (positive = market premium = possibly overvalued, negative = market discount = possibly undervalued). The Relative Valuation page extends this with multiples-level comparisons.

For MSFT with all rectifications applied: intrinsic $360, market $425, ratio +18% → modestly overvalued per the Damodaran bands (between 1.00 and 1.20).

### No outstanding issues

This is the one module where correctness is easy and everything is working.

---

## 7. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. No rectifications needed. |
