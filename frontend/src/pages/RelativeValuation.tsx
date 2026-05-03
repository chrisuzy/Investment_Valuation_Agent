import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import { baseYear } from '../lib/baseYear';

function dec(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return '';
  return v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return (v * 100).toFixed(2) + '%';
}

export default function RelativeValuation({ data }: { data: ValuationResponse; sessionId?: string | null }) {
  const multiples = data.multiples;
  const fin0 = baseYear(data);          // LTM-rotated base year
  const ind = data.inputs.industry_data;
  const indGlobal = data.inputs.industry_data_global;
  const adj = data.adjusted;

  // Compute company market-value multiples
  const mvEquity = fin0?.mv_equity ?? 0;
  const mvDebt = adj?.adjusted_mv_debt ?? fin0?.bv_debt ?? 0;
  const cash = fin0?.cash_and_marketable_securities ?? 0;
  const ev = mvEquity + mvDebt - cash;

  const rev = fin0?.revenues ?? 0;
  const ebitda = fin0?.ebitda ?? 0;
  const netIncome = fin0?.net_income ?? 0;
  const bvEquity = adj?.adjusted_bv_equity ?? fin0?.bv_equity ?? 0;

  const pe_market = netIncome > 0 ? mvEquity / netIncome : null;
  const pbv_market = bvEquity > 0 ? mvEquity / bvEquity : null;
  const ev_ebitda_market = ebitda > 0 ? ev / ebitda : null;
  const ev_sales_market = rev > 0 ? ev / rev : null;

  function premium(market: number | null, intrinsic: number | null): number | null {
    if (market == null || intrinsic == null || intrinsic === 0) return null;
    return market / intrinsic - 1;
  }

  const rows: Array<{
    label: string;
    intrinsic: number | null | undefined;
    market: number | null;
    regional: number | null | undefined;
    global: number | null | undefined;
    formula: string;
    sourceRegional: string;
    sourceGlobal: string;
  }> = [
    {
      label: 'PE Ratio',
      intrinsic: multiples?.pe_ratio_intrinsic,
      market: pe_market,
      regional: ind.pe_ratio,
      global: indGlobal?.pe_ratio,
      formula: 'PE_intrinsic = Value_of_Equity / Adjusted Net Income',
      sourceRegional: 'pedata.xls',
      sourceGlobal: 'peGlobal.xls',
    },
    {
      label: 'PBV Ratio',
      intrinsic: multiples?.pbv_ratio_intrinsic,
      market: pbv_market,
      regional: ind.pbv_ratio,
      global: indGlobal?.pbv_ratio,
      formula: 'PBV_intrinsic = Value_of_Equity / Adjusted BV Equity',
      sourceRegional: 'pbvdata.xls',
      sourceGlobal: 'pbvGlobal.xls',
    },
    {
      label: 'EV / EBITDA',
      intrinsic: multiples?.ev_ebitda_intrinsic,
      market: ev_ebitda_market,
      regional: ind.ev_ebitda,
      global: indGlobal?.ev_ebitda,
      formula: 'EV/EBITDA_intrinsic = Value_of_Operating_Assets / EBITDA',
      sourceRegional: 'vebitda.xls',
      sourceGlobal: 'vebitdaGlobal.xls',
    },
    {
      label: 'EV / Sales',
      intrinsic: multiples?.ev_sales_intrinsic,
      market: ev_sales_market,
      regional: ind.ev_sales,
      global: indGlobal?.ev_sales,
      formula: 'EV/Sales_intrinsic = Value_of_Operating_Assets / Revenue',
      sourceRegional: 'psdata.xls',
      sourceGlobal: 'psGlobal.xls',
    },
  ];

  return (
    <div className="max-w-[95vw] mx-auto p-4">
      <h1 className="text-xl font-bold mb-1">Relative Valuation — Intrinsic vs Market Multiples</h1>
      <p className="text-sm text-gray-600 mb-4">
        Compare what the market prices this firm at versus what our intrinsic valuation implies.
        <span className="inline-block bg-emerald-50 border border-emerald-200 px-2 ml-2 rounded-sm">Intrinsic (DCF)</span>
        <span className="inline-block bg-sky-50 border border-sky-200 px-2 ml-1 rounded-sm">Market-observed</span>
        <span className="inline-block bg-slate-50 border border-slate-200 px-2 ml-1 rounded-sm">Industry benchmark</span>
      </p>

      <SpreadsheetGrid title="Multiples Comparison">
        <thead>
          <tr>
            <SpreadsheetCell value="Multiple" type="header" width="160px" />
            <SpreadsheetCell value="Intrinsic (DCF)" type="header" width="130px" />
            <SpreadsheetCell value="Market" type="header" width="130px" />
            <SpreadsheetCell value="Market vs Intrinsic" type="header" width="150px" />
            <SpreadsheetCell value={`${ind.region} Industry`} type="header" width="130px" />
            <SpreadsheetCell value="Global Industry" type="header" width="130px" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const prem = premium(r.market, r.intrinsic ?? null);
            return (
              <tr key={`rv-${i}`}>
                <SpreadsheetCell value={r.label} type="label" />
                <SpreadsheetCell value={dec(r.intrinsic)} type="calc" tooltip={r.formula} />
                <SpreadsheetCell value={dec(r.market)} type="financial" tooltip="From market cap, EV, and reported financials" />
                <SpreadsheetCell
                  value={pct(prem)}
                  type="calc"
                  tooltip={prem == null ? '' : prem > 0 ? 'Market pays a PREMIUM over intrinsic (possibly overvalued)' : 'Market pays a DISCOUNT vs intrinsic (possibly undervalued)'}
                />
                <SpreadsheetCell value={dec(r.regional)} type="reference" tooltip={`Source: ${r.sourceRegional} | Industry: ${ind.industry_name} (${ind.region})`} />
                <SpreadsheetCell value={dec(r.global)} type="reference" tooltip={`Source: ${r.sourceGlobal} | Industry: ${ind.industry_name} (Global)`} />
              </tr>
            );
          })}
        </tbody>
      </SpreadsheetGrid>

      <SpreadsheetGrid title="Underlying Inputs">
        <tbody>
          <tr>
            <SpreadsheetCell value="Market Cap (MV Equity)" type="label" width="280px" />
            <SpreadsheetCell value={dec(mvEquity, 0)} type="financial" tooltip={`=CIQ("${data.ticker}","IQ_MARKETCAP")`} />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjusted MV Debt (incl lease PV)" type="label" />
            <SpreadsheetCell value={dec(mvDebt, 0)} type="calc" tooltip="BV Debt + PV of operating leases (from M1)" />
          </tr>
          <tr>
            <SpreadsheetCell value="Cash & Marketable Securities" type="label" />
            <SpreadsheetCell value={dec(cash, 0)} type="financial" />
          </tr>
          <tr>
            <SpreadsheetCell value="Enterprise Value = MV_E + MV_D − Cash" type="label" bold />
            <SpreadsheetCell value={dec(ev, 0)} type="calc" bold />
          </tr>
          <tr>
            <SpreadsheetCell value="Revenue" type="label" />
            <SpreadsheetCell value={dec(rev, 0)} type="financial" />
          </tr>
          <tr>
            <SpreadsheetCell value="EBITDA" type="label" />
            <SpreadsheetCell value={dec(ebitda, 0)} type="financial" />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjusted Net Income" type="label" />
            <SpreadsheetCell value={dec(adj?.adjusted_net_income, 0)} type="calc" tooltip="Net Income + R&D add-back − amortization (from M1)" />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjusted BV Equity" type="label" />
            <SpreadsheetCell value={dec(bvEquity, 0)} type="calc" tooltip="BV Equity + Value of Research Asset (from M1)" />
          </tr>
          <tr>
            <SpreadsheetCell value="Value of Operating Assets (DCF)" type="label" />
            <SpreadsheetCell value={dec(data.dcf?.value_of_operating_assets, 0)} type="calc" tooltip="Σ PV(FCFF) + PV(TV), after failure overlay" />
          </tr>
          <tr>
            <SpreadsheetCell value="Value of Equity (DCF)" type="label" />
            <SpreadsheetCell value={dec(data.dcf?.value_of_equity, 0)} type="calc" tooltip="V_op − debt − minority + cash_usable + cross_holdings" />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
