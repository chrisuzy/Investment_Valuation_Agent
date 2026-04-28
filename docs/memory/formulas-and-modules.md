# Formulas & Module Relationships

## Module Dependency Chain
```
M0 (Data Fetch: CapIQ + Damodaran)
  → M1 (Financial Adjustments: R&D + Leases)
    → M2 (Risk / WACC)
      → M3 (Cash Flow & Growth)
        → M4 (DCF)         ─┐
        → M5 (Multiples)    ├→ M6 (Options/BSM) → Final Value Per Share
        → M6 (Options/BSM) ─┘
```

Incremental recomputation: edit in M2 → re-run M2, M3, M4, M5, M6. Edit in M4 → re-run M4, M6 only.

## Module 0: Data Fetch
```python
def fetch_company_data(ticker, capiq_driver, damodaran_store, industry_override=None) -> CompanyValuationInput
```
1. capiq_driver.fetch(ticker, years=5) → RawFinancials[] + AdjustmentInputs
2. Map sector → Damodaran industry (via industry_mapper)
3. damodaran_store.lookup_industry(industry_name) → IndustryData
4. damodaran_store.lookup_macro(country) → MacroInputs
5. Return bundled CompanyValuationInput

## Module 1: Financial Adjustments

### R&D Capitalization
```
unamortized_r_and_d = Σ(r_and_d_expense_past_t[t] × (n - t) / n) for t=1..n
value_of_research_asset = r_and_d_expense_current + unamortized_r_and_d
amortization_r_and_d = Σ(r_and_d_expense_past_t[t] / n) for t=1..n
adjusted_ebit = ebit + r_and_d_expense_current - amortization_r_and_d
adjusted_net_income = net_income + r_and_d_expense_current - amortization_r_and_d
adjusted_bv_equity = bv_equity + value_of_research_asset
```

### Operating Lease Capitalization
```
pv_of_operating_leases = Σ(commitment_t / (1 + cost_of_debt_pretax)^t)
adjusted_mv_debt = mv_debt + pv_of_operating_leases
imputed_interest = pv_of_operating_leases × cost_of_debt_pretax
adjusted_ebit += imputed_interest
```

## Module 2: Risk & Cost of Capital
```
d_e_ratio = adjusted_mv_debt / mv_equity
beta_l = beta_u × (1 + (1 - tax_rate_marginal) × d_e_ratio)
cost_of_equity = risk_free_rate + (beta_l × equity_risk_premium)
cost_of_debt_aftertax = cost_of_debt_pretax × (1 - tax_rate_marginal)
weight_equity = mv_equity / (mv_equity + adjusted_mv_debt)
weight_debt = adjusted_mv_debt / (mv_equity + adjusted_mv_debt)
wacc = (cost_of_equity × weight_equity) + (cost_of_debt_aftertax × weight_debt)
```
Constraint: cost_of_debt_aftertax < wacc < cost_of_equity

## Module 3: Cash Flow & Growth
```
adjusted_capex = capex + r_and_d_expense_current
adjusted_d_a = d_a + amortization_r_and_d
reinvestment_firm = adjusted_capex - adjusted_d_a + change_in_noncash_wc
reinvestment_equity = reinvestment_firm - net_debt_issued

fcff = adjusted_ebit × (1 - tax_rate_marginal) - reinvestment_firm
fcfe = adjusted_net_income - reinvestment_equity

adjusted_invested_capital = adjusted_bv_equity(prior) + bv_debt(prior) - cash(prior)
roic = (adjusted_ebit × (1 - tax_rate_marginal)) / adjusted_invested_capital
roe = adjusted_net_income / adjusted_bv_equity(prior)

rir_firm = reinvestment_firm / (adjusted_ebit × (1 - tax_rate_marginal))
rir_equity = reinvestment_equity / adjusted_net_income

expected_growth_ebit = roic × rir_firm
expected_growth_ni = roe × rir_equity
```

## Module 4: DCF
### High-growth projection (years 1..n)
```
ebit_t = ebit_{t-1} × (1 + expected_growth_ebit)
fcff_t = ebit_t × (1 - tax_rate_marginal) × (1 - rir_firm)
```

### Terminal value
```
stable_growth_rate <= risk_free_rate
roic_stable = wacc_stable (excess returns vanish)
rir_firm_stable = stable_growth_rate / roic_stable

fcff_n_plus_1 = ebit_n × (1 + stable_growth_rate) × (1 - tax_rate_marginal) × (1 - rir_firm_stable)
terminal_value_firm = fcff_n_plus_1 / (wacc_stable - stable_growth_rate)
```

### PV summation
```
value_of_operating_assets = Σ(fcff_t / (1 + wacc)^t) + terminal_value_firm / (1 + wacc)^n
value_of_equity = value_of_operating_assets + cash - adjusted_mv_debt + cross_holdings - minority_interests
value_per_share_pre_options = value_of_equity / shares_outstanding
```

## Module 5: Multiples
```
payout_ratio = 1 - rir_equity
pe_ratio_intrinsic = payout_ratio / (cost_of_equity - stable_growth_rate)
pbv_ratio_intrinsic = (roe - stable_growth_rate) / (cost_of_equity - stable_growth_rate)

after_tax_margin = (adjusted_ebit × (1 - tax_rate_marginal)) / revenues
ev_sales_intrinsic = after_tax_margin × (1 - rir_firm) / (wacc - stable_growth_rate)

pe_ratio_market = mv_equity / adjusted_net_income
```

## Module 6: Black-Scholes Options
```
d1 = (ln(S/K) + (r - y + σ²/2) × t) / (σ × √t)
d2 = d1 - σ × √t

call_value = S × e^(-y×t) × N(d1) - K × e^(-r×t) × N(d2)

value_of_options = call_value × number_of_options
value_per_share = (value_of_equity - value_of_options) / shares_outstanding
```
Where N(x) = standard normal CDF (scipy.stats.norm.cdf)

## CIQ Formula Map (Current)
See `backend/data_sources/capiq_formula_map.py`

### Income Statement (multi-year FY-0..FY-5)
| Variable | Mnemonic |
|----------|----------|
| revenues | IQ_TOTAL_REV |
| ebit | IQ_EBIT |
| ebitda | IQ_EBITDA |
| net_income | IQ_NI |
| interest_expense | IQ_INTEREST_EXP |
| d_a | IQ_DA |
| r_and_d_expense | IQ_RD_EXP |
| capex | IQ_CAPEX |
| operating_lease_expense | IQ_OPER_LEASE_EXP |

### Balance Sheet (multi-year FY-0..FY-5)
| Variable | Mnemonic |
|----------|----------|
| cash_and_marketable_securities | IQ_CASH_EQUIV |
| bv_equity | IQ_TOTAL_EQUITY |
| bv_debt | IQ_TOTAL_DEBT |
| noncash_wc | IQ_NCA |
| shares_outstanding | IQ_SHARESOUTSTANDING |

### Market (current only)
| Variable | Mnemonic |
|----------|----------|
| stock_price | IQ_CLOSEPRICE |
| mv_equity | IQ_MARKETCAP |
| mv_debt | IQ_MV_TOTAL_DEBT |

### Cash Flow (multi-year)
| Variable | Mnemonic |
|----------|----------|
| net_debt_issued | IQ_NET_DEBT_ISSUED |
| change_in_noncash_wc | IQ_CHANGE_NWC |

### Options (current only)
| Variable | Mnemonic |
|----------|----------|
| options_outstanding | IQ_OPTIONS_OUTSTANDING |
| options_avg_strike | IQ_OPTIONS_AVG_STRIKE |
| options_avg_maturity | IQ_OPTIONS_AVG_LIFE |

### Lease Commitments (current only)
| Variable | Mnemonic |
|----------|----------|
| lease_commitment_yr1-5 | IQ_OPER_LEASE_YR1..YR5 |
| lease_commitment_beyond | IQ_OPER_LEASE_AFTER5 |

### NEEDS TO BE ADDED
| Variable | Proposed Mnemonic |
|----------|-------------------|
| cross_holdings | IQ_INVEST_AFFILIATES (failed — needs user to find correct one) |
| minority_interests | IQ_MINORITY_INTEREST (returns wrong value — needs fix) |

## Damodaran Datasets Used
| Dataset | Variables | Lookup Key |
|---------|-----------|------------|
| ERPs | equity_risk_premium, country_risk_premium | Country |
| Betas | beta_u, industry_d_e_ratio | Industry |
| WACC | cost_of_debt_pretax, benchmark WACC | Industry |
| Tax Rates | tax_rate_marginal, tax_rate_effective | Country |
| Risk-Free Rate | risk_free_rate | Global |
| Operating Margins | pretax_operating_margin, after_tax_operating_margin | Industry |
| Sales/Capital | sales_to_capital | Industry |

## GT Sheet → Module Mapping
| Sheet | Module |
|-------|--------|
| R& D converter | M1 R&D capitalization |
| Operating lease converter | M1 lease conversion |
| Cost of capital worksheet | M2 WACC |
| Industry Averages (US/Global) | M2 beta/ERP lookup |
| Country equity risk premiums | M2 ERP/CRP |
| Valuation output | M3 cash flow + M4 DCF |
| Option value | M6 Black-Scholes |
| Synthetic rating | M2 debt rating |
| Failure Rate worksheet | M4 failure probability |
| Stories to Numbers | User assumptions |
| Valuation as picture | M4 bridge visualization |
