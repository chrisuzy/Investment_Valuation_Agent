# Testing Strategy

## Core Principle: Excel as Formula-Level Test Oracle

The Damodaran spreadsheet (`knowledge_base/fcffsimpleginzu.xlsx`) is the ground truth. But **never load it all at once**. Instead:

1. When implementing a specific function/formula, read **only the relevant cells** from the corresponding Excel sheet
2. Extract the input values and the expected output value for that formula
3. Write a unit test: same inputs → assert same output (within float tolerance)
4. Move on to the next formula

This keeps context small and tests precise.

---

## Excel Sheet → Module Mapping

Use this table during implementation to know which sheet to read for each module's test cases.

| Module | Excel Sheet | What to Extract |
|--------|------------|-----------------|
| **M1: R&D Capitalization** | `R& D converter` | Inputs: rows 6-13 (amortization period, R&D expenses). Outputs: rows 23-27 (unamortized portions, amortization amounts). Row 31+ for adjusted financials. |
| **M1: Operating Leases** | `Operating lease converter` | Inputs: rows 4-12 (lease expense, commitments). Outputs: rows 22-28 (PV of each commitment, total debt value). Rows 31-34 for adjustments to EBIT and debt. |
| **M2: Cost of Capital** | `Cost of capital worksheet` | Rows 18-27 for equity (shares, price, beta, Rf, ERP). Rows 30-45 for debt (BV debt, interest, cost of debt, tax). Final WACC at row 13. |
| **M2: Beta lookup** | `Industry Averages(US)` or `(Global)` | Column G = Unlevered Beta, Column L = Market Debt/Capital, by industry name (Column A). |
| **M2: ERP lookup** | `Country equity risk premiums` | Column D = Equity Risk Premium, Column E = Country Risk Premium, by country (Column A). |
| **M3: Cash Flow & Growth** | `Valuation output` | Row 5 = EBIT, Row 7 = EBIT(1-t), Row 8 = Reinvestment, Row 9 = FCFF. Row 38 = Sales/Capital, Row 39 = Invested Capital, Row 40 = ROIC. Use base year (col B) and year 1 (col C). |
| **M4: DCF** | `Valuation output` | Row 2 = Revenue growth, Row 12 = Cost of capital, Row 13 = Discount factor, Row 14 = PV(FCFF). Rows 16-21 = Terminal value, PV sum. Rows 24-33 = Equity bridge. |
| **M5: Multiples** | `Industry Averages(US)` or `(Global)` | Columns O-S = EV/Sales, EV/EBITDA, EV/EBIT, Price/Book, Trailing PE by industry. Compare intrinsic calculation against these. |
| **M6: Options (BSM)** | `Option value` | Rows 4-11 = BSM inputs (S, K, t, σ, y, r, options, shares). Rows 15-19 = adjusted values. Rows 22-26 = d1, d2, N(d1), N(d2). Rows 28-29 = value per option, total value. |

---

## Test Workflow Per Function

```
For each function you implement:

1. Read ONLY the 5-15 relevant cells from the mapped Excel sheet
2. Note the input values and expected output value
3. Write pytest test:
     def test_<function_name>_against_damodaran():
         # inputs from Excel cells
         result = my_function(input1, input2, ...)
         assert result == pytest.approx(expected, rel=1e-6)
4. Implement the function
5. Run the test
6. Move on
```

---

## Test Company: Almarai (Ginzu Default)

The spreadsheet is pre-filled with **Almarai** (Saudi Arabian food company) data as of 2026-02-01. Key reference values:

- **Input sheet:** Revenue=21765.4, EBIT=3060.9, Tax=17.5%/25%, Rf=4.58%, Shares=4315, Price=72.28
- **Valuation output:** Final Value/Share = 7.19, vs Market Price = 72.28

This is the primary test fixture. All formula-level tests should use these Almarai numbers.

---

## Test Structure

```
tests/
├── engine/
│   ├── test_module_1_rd_capitalization.py    # vs "R& D converter" sheet
│   ├── test_module_1_operating_leases.py     # vs "Operating lease converter" sheet
│   ├── test_module_2_beta.py                 # vs "Cost of capital worksheet" + industry sheets
│   ├── test_module_2_wacc.py                 # vs "Cost of capital worksheet"
│   ├── test_module_3_reinvestment.py         # vs "Valuation output" rows 7-9
│   ├── test_module_3_roic_growth.py          # vs "Valuation output" rows 38-40
│   ├── test_module_4_terminal_value.py       # vs "Valuation output" rows 16-19
│   ├── test_module_4_equity_bridge.py        # vs "Valuation output" rows 20-33
│   ├── test_module_5_multiples.py            # vs industry average sheets
│   ├── test_module_6_bsm.py                 # vs "Option value" sheet
│   └── test_orchestrator.py                  # full pipeline, sparse checks only
├── fixtures/
│   └── almarai_ginzu.json                    # Extracted cell values (created lazily per module)
└── conftest.py                               # Shared Excel reader helper
```

---

## conftest.py Helper Pattern

A small helper to read specific cells from the xlsx on demand:

```python
# conftest.py
import openpyxl, pytest

@pytest.fixture(scope="session")
def ginzu_wb():
    """Load Damodaran workbook once per test session (data_only=True for computed values)."""
    return openpyxl.load_workbook(
        "knowledge_base/fcffsimpleginzu.xlsx", data_only=True
    )

def read_cells(wb, sheet_name, cell_refs: list[str]) -> dict[str, float]:
    """Read a small set of specific cells. Use this, never read full sheets."""
    ws = wb[sheet_name]
    return {ref: ws[ref].value for ref in cell_refs}
```

---

## Constraint & Sanity Tests

Cross-module invariants that must always hold:

| Constraint | Check |
|-----------|-------|
| `Adjusted_EBIT ≥ EBIT` | When R&D is growing |
| `Cost_of_Debt_AfterTax < WACC < Cost_of_Equity` | Always |
| `Stable_Growth_Rate ≤ Risk_Free_Rate` | Hard constraint |
| `Expected_Growth_EBIT == ROIC × RIR_Firm` | Identity (float tolerance) |
| `FCFF == NOPAT - Reinvestment` | Identity |
| `Value_of_Options ≥ 0` | BSM call is always non-negative |
| `PV discount factors are decreasing` | Each year's factor < prior year |

---

## API & Frontend Tests

- **API:** FastAPI `TestClient`, test each endpoint in isolation
- **Frontend:** React Testing Library for component rendering, Jest for logic
- These are secondary — engine formula correctness is the priority
