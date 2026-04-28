# CIQ Data Issues — Almarai (SASE:2280) Ground Truth Comparison

## Ground Truth Source
File: `knowledge_base/groud_truth/ground_truth.xlsx`, sheet "Input sheet"
Pre-filled Damodaran fcffsimpleginzu.xlsx for Almarai, date of valuation: 2026-02-01

## GT Values (Input Sheet)

### Company Info
| Row | Field | GT Value |
|-----|-------|----------|
| B3 | Date of valuation | 2026-02-01 |
| B4 | Company name | Almarai |
| B7 | Country | Saudi Arabia |
| B8 | Industry (US) | Food Processing |
| B9 | Industry (Global) | Food Processing |

### Financials (LTM vs Last 10K)
| Row | Field | LTM (B col) | Last 10K (C col) | Years Since (D col) |
|-----|-------|-------------|------------------|---------------------|
| 11 | Revenues | 21,765.4 | 20,979.5 | 0.5 |
| 12 | EBIT | 3,060.9 | 3,064.1 | — |
| 13 | Interest Expense | 493.4 | 562.7 | — |
| 14 | BV Equity | 10,667.8 | 13,111.1 | — |
| 15 | BV Debt | 45,063 | 44,544 | — |

### Adjustment Toggles
| Row | Field | GT Value |
|-----|-------|----------|
| B16 | Has R&D? | No |
| B17 | Has Operating Leases? | No |

### Balance Sheet
| Row | Field | LTM (B col) | Last 10K (C col) |
|-----|-------|-------------|------------------|
| 18 | Cash & Marketable Securities | 19,000 | 13,663 |
| 19 | Cross Holdings / Non-operating Assets | 21,119 | 21,644 |
| 20 | Minority Interests | 1,558 | 1,539 |

### Market Data
| Row | Field | GT Value |
|-----|-------|----------|
| B21 | Shares Outstanding | 4,315 |
| B22 | Current Stock Price | 72.28 SAR |

### Tax Rates
| Row | Field | GT Value |
|-----|-------|----------|
| B23 | Effective Tax Rate | 17.5% |
| B24 | Marginal Tax Rate | 25% |

### Value Drivers
| Row | Field | GT Value |
|-----|-------|----------|
| B26 | Revenue Growth Next Year | 5% |
| B27 | Operating Margin Next Year | 14.06% (calculated) |
| B28 | Revenue Growth Years 2-5 | 5% |
| B29 | Target Pre-tax Operating Margin | 14.06% |
| B30 | Year of Convergence | 5 |
| B31 | Sales/Capital (Years 1-5) | 1.7085 |
| B32 | Sales/Capital (Years 6-10) | 1.7085 |

### Market Numbers
| Row | Field | GT Value |
|-----|-------|----------|
| B34 | Risk-free Rate | 4.58% |
| B35 | Initial Cost of Capital (WACC) | 7.055% (calculated) |

### Options
| Row | Field | GT Value |
|-----|-------|----------|
| B37 | Has Options? | No |
| B38 | Number of Options | 7.72 |
| B39 | Average Strike Price | 1.29 |
| B40 | Average Maturity | 7 years |
| B41 | Std Dev of Stock Price | 45% |

### Default Assumptions
| Row | Field | GT Value |
|-----|-------|----------|
| B45 | Override Stable CoC? | No |
| B46 | CoC after year 10 | 7.055% (same as current) |
| B48 | Override ROIC? | No |
| B49 | ROIC after year 10 | 15% |
| B51 | Override Failure? | No |
| B52 | Failure Probability | 12% |
| B53 | Distress Proceeds Tie To | V (fair value) |
| B54 | Distress Proceeds % | 50% |
| B56 | Override Reinvestment Lag? | No |
| B57 | Reinvestment Lag | 1 year |
| B59 | Override Tax Rate Convergence? | No |
| B61 | Override NOL? | No |
| B62 | NOL Carried Forward | 731.4 |
| B64 | Override Risk-free Rate? | No |
| B65 | Risk-free Rate after yr 10 | 2% |
| B67 | Override Growth in Perpetuity? | No |
| B68 | Growth in Perpetuity | -5% |
| B70 | Override Trapped Cash? | No |
| B71 | Trapped Cash | 140,000 |
| B72 | Avg Tax Rate Foreign Markets | 15% |

## 22 Mismatched CIQ Fields

### Critical (Block entire valuation)

| # | Field | GT Value | CIQ Returns | CIQ Mnemonic Used | Problem |
|---|-------|----------|-------------|-------------------|---------|
| 1 | BV Equity | 10,667.8 | 20,527 | IQ_TOTAL_EQUITY | Returns total equity incl. minority interests, GT wants stockholders' equity only |
| 2 | BV Debt | 45,063 | 13,039 | IQ_TOTAL_DEBT | Too narrow — only interest-bearing debt; GT uses broader definition incl. all liabilities |
| 3 | Cash & Marketable Securities | 19,000 | 523 | IQ_CASH_EQUIV | Too narrow — misses investments, deposits, murabaha receivables |
| 4 | Shares Outstanding | 4,315 | "Invalid Date" error | IQ_SHARESOUTSTANDING | Formula fails entirely |
| 5 | Stock Price | 72.28 | 42.5 | IQ_CLOSEPRICE | Date/currency mismatch — need price as of 2026-02-01 in SAR |
| 6 | Effective Tax Rate | 17.5% | N/A (fails) | IQ_EFFECTIVE_TAX_RATE | Returns nothing |

### Important (Affect accuracy)

| # | Field | GT Value | CIQ Returns | Problem |
|---|-------|----------|-------------|---------|
| 7 | Cross Holdings | 21,119 | N/A | IQ_INVEST_AFFILIATES fails — no working mnemonic found |
| 8 | Minority Interests | 1,558 | -0.24 | IQ_MINORITY_INTEREST returns wrong value |
| 9 | Revenues (LTM) | 21,765.4 | 22,064.9 | We fetch IQ_FY-0, need IQ_LTM period instead |
| 10 | D&A | needed | 0 | IQ_DA returns zero for Almarai (IFRS reporting issue) |
| 11 | Interest Expense (LTM) | 493.4 | 474.4 | Close but FY vs LTM mismatch |

### Not in CIQ (Manual input needed)

| # | Field | GT Value | Notes |
|---|-------|----------|-------|
| 12 | Marginal Tax Rate | 25% | Saudi corporate tax rate — manual input |
| 13 | Average Maturity of Debt | 3 years | User input |
| 14 | Bond Rating | A1/A+ | User input |
| 15 | Years Since Last 10K | 0.5 | Computed from dates |
| 16-22 | Regional Revenue Breakdown | Various | 7 regional revenue figures driving weighted ERP = 5.58% |

## Revenue by Region (Cost of Capital Worksheet)
These drive the weighted Equity Risk Premium calculation:
| Region | GT Value |
|--------|----------|
| US | 193,636 |
| China | 500 |
| Asia | 5,455 |
| Central/S America | 5,830 |
| North America | 16,774 |
| EMEA | 8,078 |
| Rest of World | 10,924 |
| **Weighted ERP** | **5.58%** |

## User's Proposed Workflow to Fix
1. We generate an Excel file with CIQ formulas + GT values + discrepancy notes
2. User opens it in Excel with CIQ plugin installed
3. CIQ formulas resolve automatically
4. User corrects wrong formulas, enters manual values
5. User saves the file
6. We read the corrected file and update our formula map
