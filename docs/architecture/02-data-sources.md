# Data Sources — Capital IQ & Damodaran Integration

## Overview

The system has two data sources. Both are automated — the user only provides a ticker.

```
User: "AAPL"
    │
    ├─→ Capital IQ Excel Plugin (via COM automation)
    │   → Company-specific financial data (multi-year)
    │
    └─→ Damodaran Dataset Store (pre-loaded)
        → Industry betas, ERP, tax rates, macro data
```

---

## 1. Capital IQ Excel Plugin Automation

### Architecture

```
capiq_excel_automation.py
    │
    ├── CapIQFormulaGenerator
    │   Maps Data Dictionary variables → CapIQ formula identifiers
    │   e.g., revenues → =CIQ("{ticker}","IQ_TOTAL_REV","IQ_FY-{n}")
    │
    ├── ExcelCOMDriver
    │   Uses pywin32 (win32com.client) to:
    │   1. Open Excel application
    │   2. Create workbook
    │   3. Write formulas into cells
    │   4. Wait for CapIQ plugin to resolve
    │   5. Read back numeric values
    │   6. Close workbook
    │
    └── CapIQDataMapper
        Validates and maps resolved values → RawFinancials schema
```

### CapIQ Formula Mapping Table

| Data Dictionary Variable | CapIQ Identifier | Notes |
|-------------------------|------------------|-------|
| `revenues` | `IQ_TOTAL_REV` | Total revenue |
| `ebit` | `IQ_EBIT` | Operating income |
| `ebitda` | `IQ_EBITDA` | EBITDA |
| `net_income` | `IQ_NI` | Net income |
| `interest_expense` | `IQ_INTEREST_EXP` | Interest expense |
| `capex` | `IQ_CAPEX` | Capital expenditures |
| `d_a` | `IQ_DA` | Depreciation & amortization |
| `r_and_d_expense_current` | `IQ_RD_EXP` | R&D expense |
| `shares_outstanding` | `IQ_SHARESOUTSTANDING` | Basic shares |
| `mv_equity` | `IQ_MARKETCAP` | Market capitalization |
| `bv_equity` | `IQ_TOTAL_EQUITY` | Total stockholders' equity |
| `bv_debt` | `IQ_TOTAL_DEBT` | Total debt |
| ... | ... | Full mapping in implementation |

Note: Exact CapIQ formula identifiers need to be verified against Capital IQ documentation. The above are representative.

### Fetch Flow

1. **Generate formulas** — For each Data Dictionary variable, for each required fiscal year (FY-0 through FY-5), generate the CIQ formula.
2. **Batch into workbook** — Write all formulas into a single Excel workbook (one column per fiscal year, one row per variable).
3. **Execute** — Open workbook in Excel via COM. CapIQ plugin auto-resolves formulas.
4. **Wait & poll** — Check cell values every 2 seconds. Timeout after 60 seconds.
5. **Extract** — Read all numeric values. Handle errors (`#N/A`, `#ERROR`) gracefully.
6. **Map** — Convert to `RawFinancials` and `AdjustmentInputs` Pydantic models.

### Manual Fallback

If COM automation fails (Excel not available, plugin timeout, etc.):
1. System generates a pre-filled Excel template with CapIQ formulas
2. Frontend prompts: "Automatic data fetch failed. Download this template, open in Excel with CapIQ, save, and upload."
3. Upload endpoint parses the filled Excel and extracts values

---

## 2. Damodaran Dataset Management

### Architecture

```
damodaran_store.py
    │
    ├── DamodaranDatasetManager
    │   Manages uploaded datasets (CRUD)
    │   Stores parsed data as JSON index files
    │
    ├── DamodaranParser (per dataset type)
    │   Parses Damodaran Excel files into structured data
    │   Each parser knows the specific Excel layout
    │
    └── DamodaranLookup
        Queries by industry name or country
        Returns typed MacroInputs / IndustryData
```

### Damodaran Datasets Used

| Dataset | File (typical) | Variables Extracted | Key Column |
|---------|---------------|--------------------|----|
| Equity Risk Premium | `ERPs.xls` | `equity_risk_premium`, `country_risk_premium` | Country |
| Betas by Industry | `betas.xls` | `beta_u`, `industry_d_e_ratio` | Industry |
| Cost of Capital | `wacc.xls` | `cost_of_debt_pretax`, benchmark WACC | Industry |
| Tax Rates | `taxrate.xls` | `tax_rate_marginal`, `tax_rate_effective` | Country |
| Risk-Free Rate | `riskfree.xls` or manual | `risk_free_rate` | Global |
| R&D Amortization | (derived from industry) | `amortization_period_n` | Industry |

### Data Loading Flow

1. **Annual upload** — User downloads latest datasets from [Damodaran's page](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html) and uploads via admin UI.
2. **Parse** — Each dataset type has a dedicated parser that understands the Excel layout (Damodaran's files have specific header rows, merged cells, etc.).
3. **Index** — Parsed data is stored as JSON files on disk:
   ```
   data/damodaran/
   ├── erp_by_country.json       # {"US": {"erp": 0.05, "crp": 0.0}, "China": {...}}
   ├── betas_by_industry.json    # {"Software": {"beta_u": 1.28, "d_e": 0.05}, ...}
   ├── tax_by_country.json
   └── metadata.json             # Last updated dates, source file hashes
   ```
4. **Lookup** — When Module 0 needs data, it queries by industry name or country.

### Industry Mapping

The system needs to map a company's sector (from CapIQ) to Damodaran's industry classification:

```
CapIQ sector/SIC code → Damodaran industry name

Examples:
  AAPL (SIC: 3571) → "Computers/Peripherals"
  MSFT (SIC: 7372) → "Software (System & Application)"
  TSLA (SIC: 3711) → "Auto & Truck"
```

Implementation:
- Maintain a mapping table: `industry_mapper.json` — SIC/GICS codes → Damodaran industry names
- Allow user override in the UI if auto-mapping is wrong
- This mapping only needs to be built once and updated when Damodaran changes his categories

---

## 3. Data Flow Summary

```
                 Ticker: "AAPL"
                      │
    ┌─────────────────┴─────────────────┐
    ▼                                   ▼
CapIQ COM Automation              Damodaran Store Lookup
    │                                   │
    ▼                                   ▼
RawFinancials                     MacroInputs
AdjustmentInputs                  IndustryData
    │                                   │
    └─────────────────┬─────────────────┘
                      ▼
            Module 0 Output:
            CompanyValuationInput {
                raw_financials: list[RawFinancials]  # multi-year
                adjustment_inputs: AdjustmentInputs
                macro_inputs: MacroInputs
                industry_data: IndustryData
            }
                      │
                      ▼
              Module 1 (Adjustments)
```
