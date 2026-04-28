# Capital IQ Formula Reference

Auto-generated from `backend/data_sources/capiq_formula_map.py`.

## CIQ Formula Syntax

```
=CIQ("TICKER", "MNEMONIC", "PERIOD")
```

- **PERIOD**: `IQ_FY-0` (most recent FY), `IQ_FY-1` (prior FY), `IQ_FQ-0` (most recent quarter), `IQ_LTM` (trailing 12m)
- **Market items**: no period argument (current only)

---

## Income Statement Fields

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `revenues` | `IQ_TOTAL_REV` | FY-0..FY-N, FQ-0..FQ-3 | Total Revenue |
| `ebit` | `IQ_EBIT` | FY-0..FY-N, FQ-0..FQ-3 | Operating Income (EBIT) |
| `ebitda` | `IQ_EBITDA` | FY-0..FY-N, FQ-0..FQ-3 | EBITDA |
| `net_income` | `IQ_NI` | FY-0..FY-N, FQ-0..FQ-3 | Net Income |
| `interest_expense` | `IQ_INTEREST_EXP` | FY-0..FY-N, FQ-0..FQ-3 | Interest Expense |
| `d_a` | `IQ_DA` | FY-0..FY-N, FQ-0..FQ-3 | Depreciation & Amortization |
| `r_and_d_expense` | `IQ_RD_EXP` | FY-0..FY-10, FQ-0..FQ-3 | R&D Expense |
| `capex` | `IQ_CAPEX` | FY-0..FY-N, FQ-0..FQ-3 | Capital Expenditures |
| `operating_lease_expense` | `IQ_OPER_LEASE_EXP` | FY-0..FY-N, FQ-0..FQ-3 | Operating Lease Expense |

## Balance Sheet Fields

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `cash_and_marketable_securities` | `IQ_CASH_EQUIV` | FY-0..FY-N | Cash & Equivalents |
| `bv_equity` | `IQ_TOTAL_EQUITY` | FY-0..FY-N | Total Stockholders' Equity |
| `bv_debt` | `IQ_TOTAL_DEBT` | FY-0..FY-N | Total Debt |
| `noncash_wc` | `IQ_NCA` | FY-0..FY-N | Non-Cash Working Capital |
| `shares_outstanding` | `IQ_SHARESOUTSTANDING` | FY-0..FY-N | Basic Shares Outstanding |
| `cross_holdings` | `IQ_INVEST_AFFILIATES` | FY-0..FY-N | Investments in Affiliates |
| `minority_interests` | `IQ_MINORITY_INTEREST` | FY-0..FY-N | Minority Interests |

## Cash Flow Fields

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `net_debt_issued` | `IQ_NET_DEBT_ISSUED` | FY-0..FY-N, FQ-0..FQ-3 | Net Debt Issuance |
| `change_in_noncash_wc` | `IQ_CHANGE_NWC` | FY-0..FY-N, FQ-0..FQ-3 | Change in Non-Cash WC |

## Market / Pricing Fields (Current Only)

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `stock_price` | `IQ_CLOSEPRICE` | current | Closing Stock Price |
| `mv_equity` | `IQ_MARKETCAP` | current | Market Capitalization |
| `mv_debt` | `IQ_MV_TOTAL_DEBT` | current | Market Value of Total Debt |
| `reporting_currency` | `IQ_CURRENCY` | current | Reporting Currency |
| `primary_exchange` | `IQ_EXCHANGE` | current | Primary Exchange Listing |

## Option Fields (Current Only)

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `options_outstanding` | `IQ_OPTIONS_OUTSTANDING` | current | Options Outstanding |
| `options_avg_strike` | `IQ_OPTIONS_AVG_STRIKE` | current | Weighted Avg Strike Price |
| `options_avg_maturity` | `IQ_OPTIONS_AVG_LIFE` | current | Weighted Avg Remaining Life |

## Lease Commitment Fields (Current Only)

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `lease_commitment_yr1` | `IQ_OPER_LEASE_YR1` | current | Op Lease Commitment Year 1 |
| `lease_commitment_yr2` | `IQ_OPER_LEASE_YR2` | current | Op Lease Commitment Year 2 |
| `lease_commitment_yr3` | `IQ_OPER_LEASE_YR3` | current | Op Lease Commitment Year 3 |
| `lease_commitment_yr4` | `IQ_OPER_LEASE_YR4` | current | Op Lease Commitment Year 4 |
| `lease_commitment_yr5` | `IQ_OPER_LEASE_YR5` | current | Op Lease Commitment Year 5 |
| `lease_commitment_beyond` | `IQ_OPER_LEASE_AFTER5` | current | Op Lease Commitment Beyond Year 5 |

## Period Date Fields

| Variable | Mnemonic | Period | Description |
|----------|----------|--------|-------------|
| `period_date_annual` | `IQ_PERIODDATE` | IQ_FY-0 | 10-K period end date |
| `period_date_quarterly` | `IQ_PERIODDATE` | IQ_FQ-0 | 10-Q period end date |

---

## Notes

- N = `years_back` parameter (default 5, configurable up to 10)
- R&D expense is always fetched for 10 years back (`rd_years_back=10`)
- Quarterly data is fetched for 4 quarters (`quarterly_back=4`)
- The 6 critical fields that may need manual correction: BV Equity, BV Debt, Cash, Shares Outstanding, Stock Price, Effective Tax Rate
