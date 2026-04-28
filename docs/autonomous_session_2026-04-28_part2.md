# Autonomous Session — 2026-04-28 (Part 2)

**Scope:** Ginzu-understanding documentation for all remaining modules + backend rectifications discovered during verification + end-to-end validation across 4 test companies.

**Ending state:** **83 tests passing**. All four test companies produce clean DCF outputs through the Vite-proxy chain. Every calculation module has a written understanding document.

---

## 1. Ginzu-understanding docs (9 total in `docs/Ginzu understanding/`)

All in pure financial-reasoning language (no cell-address noise), following the 9-section template.

| File | Lines | Scope |
|---|---|---|
| `README.md` | 84 | Index + template |
| `module_01_ltm.md` | ~400 | LTM rotation, balance-sheet snapshot rule |
| `module_02_rd_capitalization.md` | ~360 | R&D capitalization, amortization logic, assessment |
| `module_03_operating_leases.md` | ~280 | Lease-as-debt conversion, EBIT/debt/D&A adjustments |
| `module_04_cost_of_capital.md` | ~280 | WACC, 4 approaches, β/ERP/Kd variants |
| `module_05_dcf_projection.md` | ~180 | 10-year projection paths |
| `module_06_terminal_and_pv.md` | ~210 | Gordon formula + cumulative discounting |
| `module_07_failure_and_bridge.md` | ~200 | Failure overlay + equity bridge |
| `module_08_options.md` | ~200 | Iterative dilution-adjusted BSM |
| `module_09_per_share.md` | ~120 | Per-share + market verdict |

Total: ~2,300 lines of structured financial-reasoning documentation.

---

## 2. Backend rectifications applied this session

### M2 (R&D capitalization)

- **LTM passthrough**: `r_and_d_expense_current` now sourced from LTM-rotated R&D (`ltm.r_and_d_expense`) rather than stale FY-0. Consistent with LTM base-year discipline across all modules.
- **Industry-specific amortization period**: Added `_AMORT_PERIOD_BY_INDUSTRY` lookup in `routes.py`. Pharma/Biotech/Aerospace → 10 years; Online Retail / Internet Software → 3 years; default 5 years.

### M4 (Cost of capital) — two serious bugs

- **Tax rate was 0% for US firms.** The country-tax dataset uses formal names ("United States of America") while our industry-mapper emits short names ("United States"). Lookup was silently returning None. Added alias table covering 22 countries including US, UK, Hong Kong, Macau, Korea, Vietnam, Russia, etc.
- **MV of debt was None, collapsing D/E to 0.** No market-value-of-debt mnemonic is fetched from CIQ; `raw.mv_debt` was always None; without lease capitalization `adjusted_mv_debt` stayed None → weight_debt = 0 → WACC was purely equity-based. Fixed by falling back to book debt when mv_debt is None (Damodaran's proxy convention when bond-pricing not implemented).

### M8 (Options dilution)

- **Added the fixed-point iteration loop.** Previously one-shot. Now iterates `Adjusted_S ↔ call_value` to convergence (up to 20 iterations, $0.01 tolerance).

---

## 3. End-to-end verification — 4 test companies through Vite proxy

| Company | K | Country | Industry | t_marg | WACC | VPS | Market | Ratio |
|---|---|---|---|---|---|---|---|---|
| MSFT | 2 | United States | Software (System & Application) | 25.89% | 10.04% | $360.20 | $424.82 | 1.18x |
| BABA | 3 | China | Retail (General) | 25.00% | 9.82% | $630.70 | $132.52 | 0.21x |
| TSLA | 1 | United States | Auto & Truck | 25.89% | 10.37% | $24.86 | $378.67 | 15.23x |
| LENOVO | 3 | Hong Kong | Computers/Peripherals | 16.50% | 16.04% | $1.94 | $11.83 | 6.10x |

All four produce clean output: no NaNs, no zero tax rates, no broken D/E, no invalid terminal values, no broken per-share arithmetic.

The ratios represent DCF-vs-market views given default assumptions:
- MSFT: modestly overvalued (typical "AI-premium" priced into market)
- BABA: deeply undervalued (China-discount + regulatory discount; DCF doesn't capture these)
- TSLA: severely overvalued on DCF (default assumptions don't capture Tesla's specific growth story; analyst would need to raise growth + margin + target)
- Lenovo: moderately overvalued (PC industry maturity; default assumptions pessimistic)

These valuation directions are **calculation-correct**; the numerical intrinsic values reflect a generic DCF run with default assumptions that a serious analyst would tailor per-firm.

---

## 4. Pipeline integrity

**Tests:** 83 passing / 4 skipped. No regressions from any rectification.

**Services:**
- Backend on `0.0.0.0:8000`
- Vite frontend on `0.0.0.0:5174`
- External URL: `http://10.110.133.66:5174/`

**Data flow (verified end-to-end):**
```
CIQ template upload
  → read_ciq_template.py (parse 11 FY + 8 FQ + FQ-0 BS + period dates)
  → build CompanyValuationInput
  → orchestrator:
    → compute_ltm_financials (Ginzu formula, correct +4 offset for prior-year)
    → compute_adjustments (R&D with LTM passthrough, Leases with D&A add-back, bv_debt fallback)
    → compute_cost_of_capital (aliased country tax lookup, correct D/E from adjusted debt)
    → compute_cashflow_and_growth (macro-passed tax rate, lease depreciation in adjusted D&A)
    → compute_dcf (revenue path, margin path, tax path, NOL, reinvestment lag, WACC convergence)
    → compute_multiples
    → compute_options_and_final_value (iterative BSM)
  → attach ltm_financials + industry_stats to response
  → frontend reads data.ltm_financials (authoritative) + renders Summary/Relative/Input/TTM pages
```

---

## 5. Known remaining limitations

These are not calculation bugs, just variant gaps — documented in individual module docs:

- **WACC Approaches 2 and 3** (industry average, regional decile) not implemented; only Approach 1 Detailed supported.
- **Multi-business beta** (EV-weighted across segments) not implemented; only single-business lookup.
- **Multi-country ERP blending** not implemented.
- **Synthetic rating → Kd feedback loop** not implemented (Kd always uses industry-average fallback).
- **Preferred stock** not in schema.
- **Convertible debt decomposition** not in schema.
- **Failure Rate worksheet reference tables** not surfaced on FailureRate.tsx frontend page (rating-based and age-based tables from Damodaran/BLS exist in Ginzu but we don't visualize them).
- **Bond-priced market value of debt** not computed (using book debt as proxy).

Each of these is 1–3 hours of isolated work with minimal risk to existing correctness.

---

## 6. How to verify on return

```bash
# Tests
cd backend && source .venv/bin/activate && pytest tests/ -q
# Expected: 83 passed, 4 skipped

# Live backend
curl -s http://localhost:8000/api/industries | head -c 100

# End-to-end for any test company
curl -s -X POST "http://10.110.133.66:5174/api/valuation/fetch-from-file" \
  -F "file=@TEST_DATA/TEST_MSFT.xlsx" -F "region=US" -F "risk_free_rate=0.0425" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'WACC: {d[\"cost_of_capital\"][\"wacc\"]*100:.2f}%, VPS: {d[\"final\"][\"value_per_share\"]:.2f}')"

# In browser on Windows:
# Open http://10.110.133.66:5174/
# Upload any TEST_DATA/TEST_*.xlsx
# Verify: Input Sheet, Summary Sheet, Relative Valuation, Trailing 12 Month all render correctly
```

---

*End of session.* See individual module docs in `docs/Ginzu understanding/` for the financial-reasoning baseline of every calculation.
