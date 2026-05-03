import { Routes, Route } from 'react-router-dom';
import { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import OnboardingWizard from './components/OnboardingWizard';
import InputSheet from './pages/InputSheet';
import ValuationOutput from './pages/ValuationOutput';
import SummarySheet from './pages/SummarySheet';
import RelativeValuation from './pages/RelativeValuation';
import StoriesToNumbers from './pages/StoriesToNumbers';
import ValuationPicture from './pages/ValuationPicture';
import Diagnostics from './pages/Diagnostics';
import OptionValue from './pages/OptionValue';
import SyntheticRating from './pages/SyntheticRating';
import RDConverter from './pages/RDConverter';
import LeaseConverter from './pages/LeaseConverter';
import CostOfCapital from './pages/CostOfCapital';
import FailureRate from './pages/FailureRate';
import TrailingTwelveMonth from './pages/TrailingTwelveMonth';
import AnswerKeys from './pages/AnswerKeys';
import CurrencyBanner from './components/CurrencyBanner';
import UnresolvedFieldsPanel from './components/UnresolvedFieldsPanel';
import type { ValuationResponse } from './types/valuation';
import { createValuation, patchValuation, downloadFullWorkbook, type PatchValue } from './api/client';

export default function App() {
  const [data, setData] = useState<ValuationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleCellUpdate = useCallback(async (dotPath: string, value: PatchValue) => {
    if (!sessionId || !data) return;
    try {
      const resp = await patchValuation(sessionId, { [dotPath]: value });
      setData(resp);
    } catch {
      // silently ignore patch errors for now
    }
  }, [sessionId, data]);

  const handlePatchMany = useCallback(async (overrides: Record<string, PatchValue>) => {
    if (!sessionId || !data) return;
    try {
      const resp = await patchValuation(sessionId, overrides);
      setData(resp);
    } catch {
      // silently ignore
    }
  }, [sessionId, data]);

  async function handleLoadDemo() {
    setError(null);
    try {
      const resp = await createValuation(DEMO_INPUT);
      setData(resp);
      setSessionId(resp.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  }

  function handleWizardComplete(resp: ValuationResponse) {
    setData(resp);
    setSessionId(resp.id);
  }

  function handleReset() {
    setData(null);
    setError(null);
    setSessionId(null);
  }

  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        {!data ? (
          <OnboardingWizard onComplete={handleWizardComplete} onDemo={handleLoadDemo} />
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-sm text-gray-500">Valuing: </span>
                <span className="font-bold text-gray-800">{data.inputs.company_name || data.ticker}</span>
                <span className="text-gray-400 ml-2">({data.ticker})</span>
              </div>
              <div className="flex gap-3 items-center">
                {data.inputs.raw_financials.length > 0 && (
                  <button
                    onClick={() => sessionId && downloadFullWorkbook(sessionId, data.ticker)}
                    className="px-4 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                  >
                    Download Full Workbook
                  </button>
                )}
                <button
                  onClick={handleReset}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  New Valuation
                </button>
              </div>
            </div>

            {error && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}
            <CurrencyBanner data={data} />
            <UnresolvedFieldsPanel data={data} onPatch={handleCellUpdate} />
            <Routes>
              <Route path="/"                  element={<InputSheet data={data} sessionId={sessionId} onUpdate={handleCellUpdate} />} />
              <Route path="/summary"           element={<SummarySheet data={data} sessionId={sessionId} />} />
              <Route path="/valuation-output"  element={<ValuationOutput data={data} sessionId={sessionId} onPatch={handleCellUpdate} onPatchMany={handlePatchMany} />} />
              <Route path="/relative"          element={<RelativeValuation data={data} sessionId={sessionId} />} />
              <Route path="/stories"           element={<StoriesToNumbers data={data} sessionId={sessionId} />} />
              <Route path="/picture"           element={<ValuationPicture data={data} sessionId={sessionId} />} />
              <Route path="/diagnostics"       element={<Diagnostics data={data} sessionId={sessionId} />} />
              <Route path="/options"           element={<OptionValue data={data} sessionId={sessionId} />} />
              <Route path="/rating"            element={<SyntheticRating data={data} sessionId={sessionId} />} />
              <Route path="/rd"                element={<RDConverter data={data} sessionId={sessionId} />} />
              <Route path="/leases"            element={<LeaseConverter data={data} sessionId={sessionId} />} />
              <Route path="/wacc"              element={<CostOfCapital data={data} sessionId={sessionId} onPatch={handleCellUpdate} setData={setData} />} />
              <Route path="/failure"           element={<FailureRate data={data} sessionId={sessionId} onPatch={handleCellUpdate} />} />
              <Route path="/ttm"               element={<TrailingTwelveMonth data={data} sessionId={sessionId} />} />
              <Route path="/answers"           element={<AnswerKeys data={data} sessionId={sessionId} />} />
            </Routes>
          </>
        )}
      </main>
    </div>
  );
}

// Demo input for quick testing — a simplified AAPL-like company
const DEMO_INPUT = {
  ticker: 'DEMO',
  company_name: 'Demo Corp',
  country: 'United States',
  reporting_currency: 'USD',
  stock_price_currency: 'USD',
  raw_financials: [
    {
      fiscal_year: 2025,
      revenues: 383285,
      ebit: 114301,
      ebitda: 125820,
      net_income: 96995,
      interest_expense: 3933,
      capex: 10959,
      d_a: 11519,
      noncash_wc: -40328,
      change_in_noncash_wc: -6577,
      net_debt_issued: 0,
      cash_and_marketable_securities: 62482,
      bv_equity: 62146,
      bv_debt: 111088,
      mv_equity: 2800000,
      mv_debt: 111088,
      shares_outstanding: 15550,
      stock_price: 180.0,
      cross_holdings: 1200,
      minority_interests: 350,
    },
    {
      fiscal_year: 2024,
      revenues: 365817,
      ebit: 108949,
      ebitda: 119500,
      net_income: 93736,
      interest_expense: 3750,
      capex: 10708,
      d_a: 11104,
      noncash_wc: -33751,
      change_in_noncash_wc: -5200,
      net_debt_issued: -1500,
      cash_and_marketable_securities: 58000,
      bv_equity: 58200,
      bv_debt: 108000,
      mv_equity: 2650000,
      mv_debt: 108000,
      shares_outstanding: 15700,
      stock_price: 168.79,
      cross_holdings: 1100,
      minority_interests: 320,
    },
    {
      fiscal_year: 2023,
      revenues: 348500,
      ebit: 102800,
      ebitda: 113200,
      net_income: 88900,
      interest_expense: 3500,
      capex: 10200,
      d_a: 10700,
      noncash_wc: -28550,
      change_in_noncash_wc: -4800,
      net_debt_issued: -2000,
      cash_and_marketable_securities: 51000,
      bv_equity: 54000,
      bv_debt: 105000,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
    {
      fiscal_year: 2022,
      revenues: 332000,
      ebit: 96500,
      ebitda: 106800,
      net_income: 83200,
      interest_expense: 3200,
      capex: 9800,
      d_a: 10300,
      noncash_wc: -23750,
      change_in_noncash_wc: -3800,
      net_debt_issued: null,
      cash_and_marketable_securities: null,
      bv_equity: null,
      bv_debt: null,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
    {
      fiscal_year: 2021,
      revenues: 315000,
      ebit: 89500,
      ebitda: 99000,
      net_income: 77000,
      interest_expense: 2900,
      capex: 9400,
      d_a: 9800,
      noncash_wc: -19950,
      change_in_noncash_wc: null,
      net_debt_issued: null,
      cash_and_marketable_securities: null,
      bv_equity: null,
      bv_debt: null,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
  ],
  quarterly_financials: [
    {
      fiscal_year: 0,
      revenues: 98200,
      ebit: 29500,
      ebitda: 32400,
      net_income: 25100,
      interest_expense: 1000,
      capex: 2800,
      d_a: 2900,
      noncash_wc: null,
      change_in_noncash_wc: null,
      net_debt_issued: null,
      cash_and_marketable_securities: null,
      bv_equity: null,
      bv_debt: null,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
    {
      fiscal_year: 1,
      revenues: 95800,
      ebit: 28200,
      ebitda: 31000,
      net_income: 24000,
      interest_expense: 980,
      capex: 2750,
      d_a: 2880,
      noncash_wc: null,
      change_in_noncash_wc: null,
      net_debt_issued: null,
      cash_and_marketable_securities: null,
      bv_equity: null,
      bv_debt: null,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
    {
      fiscal_year: 2,
      revenues: 96500,
      ebit: 28800,
      ebitda: 31600,
      net_income: 24500,
      interest_expense: 990,
      capex: 2780,
      d_a: 2890,
      noncash_wc: null,
      change_in_noncash_wc: null,
      net_debt_issued: null,
      cash_and_marketable_securities: null,
      bv_equity: null,
      bv_debt: null,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
    {
      fiscal_year: 3,
      revenues: 92785,
      ebit: 27801,
      ebitda: 30820,
      net_income: 23395,
      interest_expense: 963,
      capex: 2631,
      d_a: 2849,
      noncash_wc: null,
      change_in_noncash_wc: null,
      net_debt_issued: null,
      cash_and_marketable_securities: null,
      bv_equity: null,
      bv_debt: null,
      mv_equity: null,
      mv_debt: null,
      shares_outstanding: null,
      stock_price: null,
      cross_holdings: null,
      minority_interests: null,
    },
  ],
  quarters_since_10k: 2,
  period_date_10k: '2025-09-30',
  period_date_10q: '2026-03-31',
  adjustment_inputs: {
    amortization_period_n: 5,
    r_and_d_expense_current: 29915,
    r_and_d_expense_past: [26251, 21914, 18752, 16217],
    operating_lease_expense_current: 2000,
    operating_lease_commitments: [2100, 2200, 2000, 1800, 1600, 3000],
    has_r_and_d: true,
    has_operating_leases: true,
  },
  macro_inputs: {
    risk_free_rate: 0.0425,
    equity_risk_premium: 0.0472,
    country_risk_premium: 0.0,
    tax_rate_marginal: 0.21,
    tax_rate_effective: 0.162,
    default_spread: 0.0063,
  },
  company_metrics: {
    revenue_growth: 0.0477,
    pretax_operating_margin: 0.2983,
    sales_to_capital: 3.5,
    marginal_sales_to_capital: 4.2,
    roic: 0.236,
    std_dev_stock: null,
    cost_of_capital: 0.093,
  },
  industry_data: {
    industry_name: 'Computers/Peripherals',
    region: 'US',
    beta_u: 1.18,
    beta_u_corrected_for_cash: 1.22,
    industry_d_e_ratio: 0.1332,
    industry_effective_tax_rate: 0.102,
    cost_of_equity: 0.0987,
    cost_of_debt_pretax: 0.0488,
    wacc: 0.093,
    pretax_operating_margin: 0.2483,
    after_tax_operating_margin: 0.2055,
    sales_to_capital: 1.62,
    revenue_growth: 0.065,
    std_dev_stock: 0.42,
    ev_ebitda: 18.5,
    ev_sales: 6.8,
    pe_ratio: 28.5,
    pbv_ratio: 35.0,
  },
  industry_data_global: {
    industry_name: 'Computers/Peripherals',
    region: 'Global',
    beta_u: 1.15,
    beta_u_corrected_for_cash: 1.19,
    industry_d_e_ratio: 0.15,
    industry_effective_tax_rate: 0.11,
    cost_of_equity: 0.095,
    cost_of_debt_pretax: 0.05,
    wacc: 0.089,
    pretax_operating_margin: 0.22,
    after_tax_operating_margin: 0.19,
    sales_to_capital: 1.55,
    revenue_growth: 0.058,
    std_dev_stock: 0.45,
    ev_ebitda: 17.0,
    ev_sales: 6.2,
    pe_ratio: 26.0,
    pbv_ratio: 30.0,
  },
  option_inputs: {
    number_of_options: 0,
    average_strike_price: 0,
    average_maturity: 0,
    stock_price_std_dev: 0.25,
    dividend_yield: 0.006,
    has_options: false,
  },
  valuation_assumptions: {
    projection_years: 10,
    high_growth_years: 5,
    stable_growth_rate: null,
    revenue_growth_next_year: 0.08,
    revenue_growth_years_2_5: 0.06,
    target_operating_margin: 0.25,
    margin_convergence_year: 5,
    sales_to_capital_high: 2.5,
    sales_to_capital_stable: 2.0,
    cost_of_capital_stable_override: null,
    roic_stable_override: null,
    failure_probability: 0.0,
    distress_proceeds_pct: 0.5,
    failure_tie_to: 'V',
    override_reinvestment_lag: false,
    reinvestment_lag_years: 1,
    override_tax_convergence: false,
    override_nol: false,
    nol_amount: 0,
    override_riskfree: false,
    riskfree_after_yr10: null,
    override_growth_perpetuity: false,
    growth_perpetuity_rate: null,
    override_trapped_cash: false,
    trapped_cash_amount: 0,
    trapped_cash_tax_rate: 0,
  },
};
