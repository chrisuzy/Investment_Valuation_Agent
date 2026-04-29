# Ginzu vs Backend — LENOVO (Lenovo Group Limited (SEHK:992))

**Source:** `TEST_DATA/TEST_LENOVO.xlsx`  ·  **Ginzu package:** `ginzu_inputs_LENOVO.md`

Ginzu values filled in: **44 / 46**

## M2

| Metric | Sheet · Cell | Ours | Ginzu | Δ (abs) | Δ (%) | Flag |
|--------|--------------|------|-------|---------|-------|------|
| Unlevered beta (β_u) | Cost of capital worksheet · `B23` | 1.3246 | 1.1183 | 0.2063 | +18.4% | ❌ |
| Levered beta for equity (β_L) | Cost of capital worksheet · `C57` | 1.3627 | 1.1542 | 0.2084 | +18.1% | ❌ |
| Equity Risk Premium used | Cost of capital worksheet · `B27` | 4.86% | 4.86% | 0.00% | +0.0% | ✓ |
| Pre-tax Cost of Debt | Cost of capital worksheet · `B37` | 5.67% | 5.67% | 0.00% | +0.0% | ✓ |
| Market Value of Equity | Cost of capital worksheet · `B60` | 146,747.12 | 146,747.12 | 0.00 | +0.0% | ✓ |
| Market Value of Debt | Cost of capital worksheet · `C60` | 5,052.47 | 5,648.34 | -595.8710 | -10.5% | ❌ |
| Weight of Equity | Cost of capital worksheet · `B61` | 96.67% | 96.29% | 0.38% | +0.4% | ✓ |
| Weight of Debt | Cost of capital worksheet · `C61` | 3.33% | 3.71% | -0.38% | -10.2% | ❌ |
| Cost of Equity | Cost of capital worksheet · `B62` | 10.88% | 9.86% | 1.01% | +10.3% | ❌ |
| After-tax Cost of Debt | Cost of capital worksheet · `C62` | 4.73% | 4.73% | 0.00% | +0.0% | ✓ |
| WACC (blended, year 1) | Cost of capital worksheet · `E62` | 10.67% | 9.67% | 1.00% | +10.3% | ❌ |
| Cost of capital — final (Approach 1) | Cost of capital worksheet · `B13` | 10.67% | 9.67% | 1.00% | +10.3% | ❌ |

## M1

| Metric | Sheet · Cell | Ours | Ginzu | Δ (abs) | Δ (%) | Flag |
|--------|--------------|------|-------|---------|-------|------|
| Current-year R&D expense (input echo) | R& D converter · `B24` | 5,876.59 | 11,665.00 | -5,788.41 | -49.6% | ❌ |
| Value of Research Asset (sum unamortized) | R& D converter · `D35` | 6,445.59 | 15,724.39 | -9,278.80 | -59.0% | ❌ |
| Amortization of research asset (this year) | R& D converter · `D37` | 1,817.20 | 1,817.20 | 0.00 | +0.0% | ✓ |
| Adjustment to Operating Income (EBIT) | R& D converter · `D39` | — | 9,847.80 | — | — | — |
| Depreciation on operating-lease asset | Operating lease converter · `F31` | 0.00 | 156.7024 | -156.7024 | -100.0% | ❌ |
| Adjustment to Operating Expenses (EBIT) | Operating lease converter · `F32` | 121.0710 | 138.2976 | -17.2266 | -12.5% | ❌ |
| Adjustment to Total Debt (PV of leases) | Operating lease converter · `F33` | 0.00 | 1,253.62 | -1,253.62 | -100.0% | ❌ |

## M4

| Metric | Sheet · Cell | Ours | Ginzu | Δ (abs) | Δ (%) | Flag |
|--------|--------------|------|-------|---------|-------|------|
| Revenue, Year 1 | Summary Sheet · `B3` | 94,163.87 | 82,892.36 | 11,271.51 | +13.6% | ❌ |
| Revenue, Year 10 | Summary Sheet · `B12` | 189,220.99 | 166,571.05 | 22,649.95 | +13.6% | ❌ |
| Operating margin, Year 1 | Summary Sheet · `D3` | — | 5.00% | — | — | — |
| Operating margin, Year 10 | Summary Sheet · `D12` | — | 8.00% | — | — | — |
| Pre-tax EBIT, Year 1 | Summary Sheet · `E3` | 4,708.19 | 4,144.62 | 563.5756 | +13.6% | ❌ |
| Pre-tax EBIT, Year 10 | Summary Sheet · `E12` | 15,137.68 | 13,325.68 | 1,812.00 | +13.6% | ❌ |
| FCFF, Year 1 | Summary Sheet · `F16` | 3,601.93 | 1,780.65 | 1,821.28 | +102.3% | ❌ |
| FCFF, Year 10 | Summary Sheet · `F25` | 11,746.42 | 10,372.43 | 1,373.99 | +13.2% | ❌ |
| Cost of capital (terminal) | Valuation output · `C30` | 10.67% | 9.67% | 1.00% | +10.3% | ❌ |
| Cumulated discount factor (yr 10) | Valuation output · `C31` | 38.49% | 91.18% | -52.69% | -57.8% | ❌ |
| Value as Going Concern (PV cash flows+terminal) | Valuation output · `B40` | 125,707.97 | 108,291.18 | 17,416.80 | +16.1% | ❌ |

## M7

| Metric | Sheet · Cell | Ours | Ginzu | Δ (abs) | Δ (%) | Flag |
|--------|--------------|------|-------|---------|-------|------|
| Probability of failure | Valuation output · `B41` | — | 0.00% | — | — | — |
| Proceeds if firm fails | Valuation output · `B42` | — | 54,145.59 | — | — | — |
| Value of operating assets | Valuation output · `B43` | 125,707.97 | 108,291.18 | 17,416.80 | +16.1% | ❌ |
| Subtract: Debt | Valuation output · `B44` | — | 5,732.96 | — | — | — |
| Subtract: Minority interests | Valuation output · `B45` | — | 1,138.28 | — | — | — |
| Add: Cash | Valuation output · `B46` | — | 4,728.12 | — | — | — |
| Add: Non-operating assets | Valuation output · `B47` | — | 1,825.47 | — | — | — |
| Value of equity | Valuation output · `B48` | 126,765.92 | 107,973.53 | 18,792.39 | +17.4% | ❌ |
| Subtract: Value of options | Valuation output · `B49` | — | 0.00 | — | — | — |
| Value of equity in common stock | Valuation output · `B50` | 126,765.92 | 107,973.53 | 18,792.39 | +17.4% | ❌ |
| Number of shares | Valuation output · `B51` | — | 12,404.66 | — | — | — |

## M9

| Metric | Sheet · Cell | Ours | Ginzu | Δ (abs) | Δ (%) | Flag |
|--------|--------------|------|-------|---------|-------|------|
| Estimated value per share | Valuation output · `B52` | 10.2192 | 8.7043 | 1.5149 | +17.4% | ❌ |
| Market price | Valuation output · `B53` | — | 11.8300 | — | — | — |
| Price as % of value | Valuation output · `B54` | — | 135.91% | — | — | — |

## M8

| Metric | Sheet · Cell | Ours | Ginzu | Δ (abs) | Δ (%) | Flag |
|--------|--------------|------|-------|---------|-------|------|
| Value per option (BSM) | Option value · `B28` | 0.00 | — | — | — | — |
| Value of all options outstanding | Option value · `B29` | 0.00 | — | — | — | — |

## Summary

- ✓ matches (<1%): **6**
- ⚠ small (<5%):   **0**
- ❌ large (≥5%):   **25**
