# Ginzu Input Package — LENOVO (Lenovo Group Limited)

**Generated:** 2026-04-29
**Source:** `TEST_DATA/TEST_LENOVO.xlsx` (CIQ-resolved)
**Ginzu workbook:** `knowledge_base/Ginzu_NVIDIA.xlsx`

## Instructions

1. Open `Ginzu_NVIDIA.xlsx`, immediately **Save As** `LENOVO_ginzu.xlsx`.
2. In Excel, verify iterative calculation is ON: `File → Options → Formulas → Enable iterative calculation`.
3. Go to the **Input sheet** and paste each value below into the listed cell.
4. If 'Capitalize R&D? (B15)' is **Yes**, also fill Section B into the **R& D converter** sheet.
5. If 'Have operating leases? (B16)' is **Yes**, also fill Section C into the **Operating lease converter** sheet.
6. **IMPORTANT — NVIDIA-specific story rows (B44–B52):** leave them at their current NVIDIA values OR zero them out. They drive Ginzu's AI/Auto business-unit valuation which does not apply to this company. If left at NVIDIA values, the final VPS will include spurious AI/Auto PV; if zeroed, the final VPS will be lower than Ginzu's main DCF would compute for a non-NVIDIA firm.
7. Let Excel recalculate (F9, or wait for auto-calc to settle if iteration is slow).
8. Fill in Section D with Ginzu's computed values — these are the ground-truth numbers the comparison script will read.

---

## A. Input sheet cells

| Cell | Label | Value to paste | Notes |
|------|-------|----------------|-------|
| `B3` | Date of valuation | `Mar 31, 2025` |  |
| `B4` | Company name | `Lenovo Group Limited` |  |
| `B7` | Country of incorporation | `Hong Kong` |  |
| `B8` | Industry (US) | `Computers/Peripherals` |  |
| `B9` | Industry (Global) | `Computers/Peripherals` |  |
| `B10` | Revenues (LTM) | `69,076.97` |  |
| `C10` | Revenues (prior FY) | `56,863.78` |  |
| `D10` | Years since last 10K | `0.000000` |  |
| `B11` | EBIT / Operating income (LTM) | `2,006.90` |  |
| `C11` | EBIT / Operating income (prior FY) | `1,990.82` |  |
| `B12` | Interest expense (LTM) | `293.5950` |  |
| `C12` | Interest expense (prior FY) | `275.2030` |  |
| `B13` | Book value of equity | `6,659.92` |  |
| `C13` | Book value of equity (prior) | `6,081.19` |  |
| `B14` | Book value of debt | `5,732.96` |  |
| `C14` | Book value of debt (prior) | `3,961.69` |  |
| `B15` | Capitalize R&D? | `Yes` |  |
| `B16` | Have operating leases? | `No` |  |
| `B17` | Cash + marketable securities | `4,728.12` |  |
| `C17` | Cash + marketable (prior) | `3,559.83` |  |
| `B18` | Cross holdings & non-op assets | `1,825.47` |  |
| `C18` | Cross holdings (prior) | `1,768.44` |  |
| `B19` | Minority interests | `1,138.28` |  |
| `C19` | Minority interests (prior) | `1,045.95` |  |
| `B20` | Shares outstanding | `12,404.66` |  |
| `B21` | Current stock price | `11.8300` |  |
| `B22` | Effective tax rate | `0.200000` |  |
| `B23` | Marginal tax rate | `0.165000` |  |
| `B25` | Revenue growth rate — next year | `0.100000` |  |
| `B26` | Operating margin — next year | `0.029053` |  |
| `B27` | CAGR revenue growth, years 2-5 | `0.080000` |  |
| `B28` | Target pre-tax operating margin | `0.224849` |  |
| `B29` | Year of margin convergence | `5` |  |
| `B30` | Sales/Capital ratio (years 1-5) | `3.6198` |  |
| `B31` | Sales/Capital ratio (years 6-10) | `3.6198` |  |
| `B33` | Risk-free rate | `0.042500` |  |
| `B56` | Override stable cost of capital? (Yes/No) | `Yes` |  |
| `B57` | Stable cost of capital (after yr 10) | `0.085000` |  |
| `B59` | Override stable ROIC? (Yes/No) | `Yes` |  |
| `B60` | Stable ROIC (after yr 10) | `0.120000` |  |
| `B62` | Override zero failure? (Yes/No) | `No` |  |
| `B64` | Tie proceeds to? (B/V) | `V` |  |
| `B65` | Distress proceeds as % of book/fair | `0.500000` |  |
| `B67` | Override reinvestment-lag=1? (Yes/No) | `Yes` |  |
| `B68` | Lag years (0-3) | `1` |  |
| `B36` | Have employee options outstanding? | `No` |  |

## B. R&D converter inputs

Go to the **R& D converter** sheet in Ginzu.

| Cell | Label | Value |
|------|-------|-------|
| `B6` | Amortization period N (years) | `5` |
| `B7` | Current year R&D expense (LTM) | `2,288.20` |

Past-years R&D — 10 years available from CIQ. Paste into cells B11, B12, B13… (most-recent year first):

| Cell | Year offset | R&D expense |
|------|-------------|-------------|
| `B11` | -1 | `2,027.53` |
| `B12` | -2 | `2,195.33` |
| `B13` | -3 | `2,073.46` |
| `B14` | -4 | `1,453.91` |
| `B15` | -5 | `1,335.74` |
| `B16` | -6 | `1,266.34` |
| `B17` | -7 | `1,273.73` |
| `B18` | -8 | `1,361.69` |
| `B19` | -9 | `1,491.37` |
| `B20` | -10 | `1,220.92` |

## C. Operating lease converter inputs

_This company has no material operating-lease commitments (post-ASC 842 the balance-sheet lease liability is already in `bv_debt`). Leave Ginzu's B16 = 'No' and skip the lease converter sheet._

## D. Ginzu output cells — record after recalc

Read each cell below from Ginzu **after** Excel has finished recalculating. Paste the value in the 'Ginzu value' column. Decimals please (e.g., `0.1179` not `11.79%`).

| Module | Sheet | Cell | Metric | Ginzu value |
|--------|-------|------|--------|-------------|
| M2 | Cost of capital worksheet | `B23` | Unlevered beta (β_u) | _fill in_ |
| M2 | Cost of capital worksheet | `C57` | Levered beta for equity (β_L) | _fill in_ |
| M2 | Cost of capital worksheet | `B27` | Equity Risk Premium used | _fill in_ |
| M2 | Cost of capital worksheet | `B37` | Pre-tax Cost of Debt | _fill in_ |
| M2 | Cost of capital worksheet | `B60` | Market Value of Equity | _fill in_ |
| M2 | Cost of capital worksheet | `C60` | Market Value of Debt | _fill in_ |
| M2 | Cost of capital worksheet | `B61` | Weight of Equity | _fill in_ |
| M2 | Cost of capital worksheet | `C61` | Weight of Debt | _fill in_ |
| M2 | Cost of capital worksheet | `B62` | Cost of Equity | _fill in_ |
| M2 | Cost of capital worksheet | `C62` | After-tax Cost of Debt | _fill in_ |
| M2 | Cost of capital worksheet | `E62` | WACC (blended, year 1) | _fill in_ |
| M2 | Cost of capital worksheet | `B13` | Cost of capital — final (Approach 1) | _fill in_ |
|     |     |     |     |     |
| M1 | R& D converter | `B24` | Current-year R&D expense (input echo) | _fill in_ |
| M1 | R& D converter | `D35` | Value of Research Asset (sum unamortized) | _fill in_ |
| M1 | R& D converter | `D37` | Amortization of research asset (this year) | _fill in_ |
| M1 | R& D converter | `D39` | Adjustment to Operating Income (EBIT) | _fill in_ |
| M1 | Operating lease converter | `F31` | Depreciation on operating-lease asset | _fill in_ |
| M1 | Operating lease converter | `F32` | Adjustment to Operating Expenses (EBIT) | _fill in_ |
| M1 | Operating lease converter | `F33` | Adjustment to Total Debt (PV of leases) | _fill in_ |
|     |     |     |     |     |
| M4 | Summary Sheet | `B3` | Revenue, Year 1 | _fill in_ |
| M4 | Summary Sheet | `B12` | Revenue, Year 10 | _fill in_ |
| M4 | Summary Sheet | `D3` | Operating margin, Year 1 | _fill in_ |
| M4 | Summary Sheet | `D12` | Operating margin, Year 10 | _fill in_ |
| M4 | Summary Sheet | `E3` | Pre-tax EBIT, Year 1 | _fill in_ |
| M4 | Summary Sheet | `E12` | Pre-tax EBIT, Year 10 | _fill in_ |
| M4 | Summary Sheet | `F16` | FCFF, Year 1 | _fill in_ |
| M4 | Summary Sheet | `F25` | FCFF, Year 10 | _fill in_ |
| M4 | Valuation output | `C30` | Cost of capital (terminal) | _fill in_ |
| M4 | Valuation output | `C31` | Cumulated discount factor (yr 10) | _fill in_ |
| M4 | Valuation output | `B40` | Value as Going Concern (PV cash flows+terminal) | _fill in_ |
|     |     |     |     |     |
| M7 | Valuation output | `B41` | Probability of failure | _fill in_ |
| M7 | Valuation output | `B42` | Proceeds if firm fails | _fill in_ |
| M7 | Valuation output | `B43` | Value of operating assets | _fill in_ |
| M7 | Valuation output | `B44` | Subtract: Debt | _fill in_ |
| M7 | Valuation output | `B45` | Subtract: Minority interests | _fill in_ |
| M7 | Valuation output | `B46` | Add: Cash | _fill in_ |
| M7 | Valuation output | `B47` | Add: Non-operating assets | _fill in_ |
| M7 | Valuation output | `B48` | Value of equity | _fill in_ |
| M7 | Valuation output | `B49` | Subtract: Value of options | _fill in_ |
| M7 | Valuation output | `B50` | Value of equity in common stock | _fill in_ |
| M7 | Valuation output | `B51` | Number of shares | _fill in_ |
|     |     |     |     |     |
| M9 | Valuation output | `B52` | Estimated value per share | _fill in_ |
| M9 | Valuation output | `B53` | Market price | _fill in_ |
| M9 | Valuation output | `B54` | Price as % of value | _fill in_ |
|     |     |     |     |     |
| M8 | Option value | `B28` | Value per option (BSM) | _fill in_ |
| M8 | Option value | `B29` | Value of all options outstanding | _fill in_ |

**M1** = R&D / lease capitalization adjustments. **M2** = Cost of capital. **M4** = DCF projection. **M7** = Failure + bridge. **M8** = Options. **M9** = Per-share.

## E. Context (for reference only — do not paste into Ginzu)

- Ticker: `LENOVO`
- Ginzu base ERP + CRP (from Damodaran country dataset): `0.057820` (0.050060 base + 0.007760 country)
- Operating margin used (B26): LTM op-margin = `0.029053`
- Target operating margin used (B28): `0.224849` (industry median if available, else 0.9× current)

**Assumption parity.** Our backend uses the SAME assumptions as above when running the comparison. If you want to tune any assumption in Ginzu, tell Claude the new value and the backend run will be repeated with that value.
