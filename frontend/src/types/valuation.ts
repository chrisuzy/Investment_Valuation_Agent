// Mirrors backend Pydantic schemas

export interface MacroInputs {
  risk_free_rate: number;
  equity_risk_premium: number;
  country_risk_premium: number;
  tax_rate_marginal: number;
  tax_rate_effective: number | null;
  default_spread: number | null;
}

export interface RawFinancials {
  fiscal_year: number;
  revenues: number;
  ebit: number;
  ebitda: number | null;
  net_income: number | null;
  interest_expense: number | null;
  capex: number | null;
  d_a: number | null;
  noncash_wc: number | null;
  change_in_noncash_wc: number | null;
  net_debt_issued: number | null;
  cash_and_marketable_securities: number | null;
  bv_equity: number | null;
  bv_debt: number | null;
  mv_equity: number | null;               // reporting currency — for WACC math
  mv_equity_listing: number | null;        // listing currency — for display
  mv_debt: number | null;
  shares_outstanding: number | null;
  stock_price: number | null;              // listing currency — matches broker view
  stock_price_reporting: number | null;    // reporting currency — for cross-ccy comparison
  cross_holdings: number | null;
  minority_interests: number | null;
  r_and_d_expense: number | null;
  earnings_before_tax: number | null;
  total_tax_expense: number | null;
}

export interface AdjustmentInputs {
  amortization_period_n: number;
  r_and_d_expense_current: number;
  r_and_d_expense_past: number[];
  operating_lease_expense_current: number;
  operating_lease_commitments: number[];
  has_r_and_d: boolean;
  has_operating_leases: boolean;
}

export interface AdjustedFinancials {
  unamortized_r_and_d: number;
  amortization_r_and_d: number;
  value_of_research_asset: number;
  pv_of_operating_leases: number;
  depreciation_on_lease_asset: number;
  lease_adjustment_to_ebit: number;
  lease_years_total: number;
  lease_n_additional_years: number;
  adjusted_ebit: number;
  adjusted_net_income: number | null;
  adjusted_bv_equity: number | null;
  adjusted_mv_debt: number | null;
}

export interface IndustryData {
  industry_name: string;
  region: string;
  beta_u: number;
  beta_u_corrected_for_cash: number | null;
  industry_d_e_ratio: number | null;
  industry_effective_tax_rate: number | null;
  cost_of_equity: number | null;
  cost_of_debt_pretax: number | null;
  wacc: number | null;
  pretax_operating_margin: number | null;
  after_tax_operating_margin: number | null;
  sales_to_capital: number | null;
  revenue_growth: number | null;
  std_dev_stock: number | null;
  roic: number | null;
  ev_ebitda: number | null;
  ev_sales: number | null;
  pe_ratio: number | null;
  pbv_ratio: number | null;
}

export interface CostOfCapital {
  approach_used: string;
  beta_branch_used: string;
  erp_branch_used: string;
  kd_branch_used: string;

  beta_u: number;
  beta_l: number;

  mv_straight_debt: number;
  mv_convertible_straight_part: number;
  equity_in_convertible: number;
  mv_leases: number;
  mv_debt_total: number;
  book_debt: number;
  d_e_ratio: number;

  mv_equity: number;
  mv_preferred: number;
  total_capital: number;

  cost_of_equity: number;
  cost_of_debt_pretax: number;
  cost_of_debt_aftertax: number;
  cost_of_preferred: number;

  weight_equity: number;
  weight_debt: number;
  weight_preferred: number;

  risk_free_rate: number;
  equity_risk_premium: number;
  interest_coverage_ratio: number | null;
  synthetic_rating: string | null;

  wacc: number;
  warnings: string[];
}

export interface BusinessSegment {
  name: string;
  industry_us: string | null;
  industry_global: string | null;
  revenue: number;
}

export interface SegmentMember {
  to: string;
  kind: string;   // "country" | "region"
  weight: number;
  erp: number | null;
}

export interface SegmentResolution {
  raw_name: string;
  mapped_to: string | null;
  mapped_kind: string;    // "country" | "region" | "composite" | "unresolved"
  erp: number | null;
  members: SegmentMember[];
  confidence: number;
  source: string;
  note: string | null;
}

export interface GeographicSegment {
  name: string;
  revenue: number;
  pct?: number | null;
  resolution?: SegmentResolution | null;
}

export interface ConvertibleDebt {
  book_value: number;
  interest_expense: number;
  maturity_years: number;
  market_value: number;
}

export interface PreferredStock {
  shares: number;
  price_per_share: number;
  dividend_per_share: number;
}

export type CostOfCapitalApproach = "direct" | "detailed" | "industry_average" | "decile";
export type BetaApproach =
  | "single_business_us"
  | "single_business_global"
  | "multi_business_us"
  | "multi_business_global"
  | "direct_levered"
  | "direct_unlevered";
export type ErpApproach =
  | "country_of_incorporation"
  | "operating_countries"
  | "operating_regions"
  | "direct";
export type KdApproach = "industry_fallback" | "direct" | "synthetic_rating" | "actual_rating";

export interface MethodologyChoices {
  cost_of_capital_approach: CostOfCapitalApproach;
  wacc_direct_input: number | null;

  beta_approach: BetaApproach;
  beta_direct_input: number | null;

  erp_approach: ErpApproach;
  erp_direct_input: number | null;

  kd_approach: KdApproach;
  kd_direct_input: number | null;
  synthetic_rating_firm_type: string;
  actual_rating: string | null;

  decile_region: string;
  decile_risk_group: string;

  debt_maturity_years: number;
  use_bond_pricing_for_debt: boolean;

  business_segments: BusinessSegment[];
  geographic_segments: GeographicSegment[];

  convertible_debt: ConvertibleDebt;
  has_convertible: boolean;

  preferred_stock: PreferredStock;
  has_preferred: boolean;

  unsupported_branch_warnings: string[];
}

export interface CashFlowMetrics {
  adjusted_capex: number;
  adjusted_d_a: number;
  reinvestment_firm: number;
  reinvestment_equity: number | null;
  fcff: number;
  fcfe: number | null;
  adjusted_invested_capital: number | null;
  roic: number | null;
  roe: number | null;
  rir_firm: number | null;
  rir_equity: number | null;
  expected_growth_ebit: number | null;
  expected_growth_ni: number | null;
}

export interface ValuationAssumptions {
  projection_years: number;
  high_growth_years: number;
  stable_growth_rate: number | null;
  revenue_growth_next_year: number | null;
  operating_margin_next_year: number | null;
  revenue_growth_years_2_5: number | null;
  target_operating_margin: number | null;
  margin_convergence_year: number;
  sales_to_capital_high: number | null;
  sales_to_capital_stable: number | null;
  cost_of_capital_stable_override: number | null;
  roic_stable_override: number | null;
  failure_probability: number;
  distress_proceeds_pct: number;
  failure_tie_to: string;
  override_reinvestment_lag: boolean;
  reinvestment_lag_years: number;
  override_tax_convergence: boolean;
  override_nol: boolean;
  nol_amount: number;
  override_riskfree: boolean;
  riskfree_after_yr10: number | null;
  override_growth_perpetuity: boolean;
  growth_perpetuity_rate: number | null;
  override_trapped_cash: boolean;
  trapped_cash_amount: number;
  trapped_cash_tax_rate: number;
}

export interface DCFResult {
  revenue_projections: number[];
  ebit_projections: number[];
  fcff_projections: number[];
  reinvestment_projections: number[];
  discount_factors: number[];
  pv_fcff: number[];
  terminal_value_firm: number | null;
  pv_terminal_value: number | null;
  pv_cash_flows_sum: number | null;
  value_of_operating_assets: number | null;
  value_of_equity: number | null;
  value_per_share_pre_options: number | null;
}

export interface MultiplesResult {
  pe_ratio_intrinsic: number | null;
  pbv_ratio_intrinsic: number | null;
  ev_ebitda_intrinsic: number | null;
  ev_sales_intrinsic: number | null;
  pe_ratio_market: number | null;
}

export interface OptionInputs {
  number_of_options: number;
  average_strike_price: number;
  average_maturity: number;
  stock_price_std_dev: number;
  dividend_yield: number;
  has_options: boolean;
}

export interface FinalValuation {
  call_value_per_option: number;
  value_of_all_options: number;
  value_per_share: number;
}

export interface CompanyMetrics {
  revenue_growth: number | null;
  pretax_operating_margin: number | null;
  sales_to_capital: number | null;
  marginal_sales_to_capital: number | null;
  roic: number | null;
  std_dev_stock: number | null;
  cost_of_capital: number | null;
}

export interface CompanyValuationInput {
  ticker: string;
  company_name: string | null;
  country: string | null;
  reporting_currency: string | null;
  stock_price_currency: string | null;
  fx_rate: number | null;                    // listing ccy → reporting ccy multiplier
  fx_rate_source: string;                    // "CIQ implied" | "same currency" | "unavailable" | "unknown"
  fx_rate_date: string | null;
  raw_financials: RawFinancials[];
  quarterly_financials: RawFinancials[];
  quarters_since_10k: number;
  period_date_10k: string | null;
  period_date_10q: string | null;
  period_dates_annual: Record<string, string | null>;
  effective_tax_rate_ciq: number | null;
  adjustment_inputs: AdjustmentInputs;
  macro_inputs: MacroInputs;
  industry_data: IndustryData;
  industry_data_global: IndustryData | null;
  company_metrics: CompanyMetrics | null;
  option_inputs: OptionInputs;
  valuation_assumptions: ValuationAssumptions;
  methodology_choices: MethodologyChoices;
}

export interface IndustryStatQuartile {
  q1: number | null;
  median: number | null;
  q3: number | null;
}

export interface IndustryStatDistributions {
  n_firms: number;
  revenue_growth_3y: IndustryStatQuartile;
  pretax_operating_margin: IndustryStatQuartile;
  sales_to_capital: IndustryStatQuartile;
  cost_of_capital: IndustryStatQuartile;
  beta_median: number | null;
  debt_to_capital: IndustryStatQuartile;
}

export interface UnresolvedField {
  path: string;                                       // e.g. "industry_data.industry_name"
  kind: "enum" | "number" | "percentage" | "currency" | "country";
  reason: string;
  options?: string[] | null;                          // for enum/currency/country
  current_value?: unknown;
  required: boolean;
  suggestion?: unknown;
}

export interface ValuationResponse {
  id: string;
  ticker: string;
  inputs: CompanyValuationInput;
  ltm_financials: RawFinancials | null;
  adjusted: AdjustedFinancials | null;
  cost_of_capital: CostOfCapital | null;
  cashflow: CashFlowMetrics | null;
  dcf: DCFResult | null;
  multiples: MultiplesResult | null;
  final: FinalValuation | null;
  warnings: string[];
  source_metadata: Record<string, string>;
  industry_stats?: IndustryStatDistributions | null;
  unresolved_fields?: UnresolvedField[];
}
