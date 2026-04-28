import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

// ---------- helpers ----------

/** Safe array access — returns undefined when data is missing */
function at(arr: number[] | undefined | null, i: number): number | undefined {
  if (!arr || i < 0 || i >= arr.length) return undefined;
  return arr[i];
}

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return (v * 100).toFixed(2) + '%';
}

function fmtNum(v: number | string | null | undefined): number | string {
  if (v === null || v === undefined) return '';
  return v;
}

// ---------- component ----------

export default function ValuationOutput({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const dcf = data.dcf;
  const inputs = data.inputs;
  const fin0 = inputs.raw_financials[0]; // base-year financials
  const assumptions = inputs.valuation_assumptions;
  const macro = inputs.macro_inputs;

  // 13 columns: base year + years 1-10 + terminal year
  const colCount = 13;
  const headers = [
    'Base year',
    ...Array.from({ length: 10 }, (_, i) => `Year ${i + 1}`),
    'Terminal year',
  ];

  // ---------- derived projection arrays (length 12 each) ----------

  // Revenues: index 0 = base-year, 1..11 from revenue_projections
  const revenues: (number | undefined)[] = Array(colCount).fill(undefined);
  revenues[0] = fin0.revenues;
  if (dcf?.revenue_projections) {
    dcf.revenue_projections.forEach((v, i) => {
      revenues[i + 1] = v;
    });
  }

  // Revenue growth rate: base year blank, year N = (rev[N]-rev[N-1]) / rev[N-1]
  const revenueGrowth: (number | undefined)[] = Array(colCount).fill(undefined);
  for (let i = 1; i < colCount; i++) {
    const prev = revenues[i - 1];
    const cur = revenues[i];
    if (prev !== undefined && cur !== undefined && prev !== 0) {
      revenueGrowth[i] = (cur - prev) / prev;
    }
  }

  // EBIT
  const ebit: (number | undefined)[] = Array(colCount).fill(undefined);
  ebit[0] = fin0.ebit;
  if (dcf?.ebit_projections) {
    dcf.ebit_projections.forEach((v, i) => {
      ebit[i + 1] = v;
    });
  }

  // EBIT margin = ebit / revenue
  const ebitMargin: (number | undefined)[] = Array(colCount).fill(undefined);
  for (let i = 0; i < colCount; i++) {
    const r = revenues[i];
    const e = ebit[i];
    if (r !== undefined && e !== undefined && r !== 0) {
      ebitMargin[i] = e / r;
    }
  }

  // Tax rate (same for every column)
  const taxRate = macro.tax_rate_marginal;

  // EBIT(1-t)
  const ebitAfterTax: (number | undefined)[] = ebit.map((e) =>
    e !== undefined ? e * (1 - taxRate) : undefined,
  );

  // Reinvestment
  const reinvestment: (number | undefined)[] = Array(colCount).fill(undefined);
  if (dcf?.reinvestment_projections) {
    dcf.reinvestment_projections.forEach((v, i) => {
      reinvestment[i + 1] = v;
    });
  }

  // FCFF
  const fcff: (number | undefined)[] = Array(colCount).fill(undefined);
  if (dcf?.fcff_projections) {
    dcf.fcff_projections.forEach((v, i) => {
      fcff[i + 1] = v;
    });
  }

  // Cost of capital (same for years 1-10, possibly different for terminal)
  const costOfCapital: (number | undefined)[] = Array(colCount).fill(undefined);
  if (data.cost_of_capital?.wacc !== undefined) {
    for (let i = 1; i < colCount; i++) {
      costOfCapital[i] = data.cost_of_capital.wacc;
    }
  }

  // Cumulated discount factor
  const discountFactor: (number | undefined)[] = Array(colCount).fill(undefined);
  if (dcf?.discount_factors) {
    dcf.discount_factors.forEach((v, i) => {
      discountFactor[i + 1] = v;
    });
  }

  // PV(FCFF)
  const pvFcff: (number | undefined)[] = Array(colCount).fill(undefined);
  if (dcf?.pv_fcff) {
    dcf.pv_fcff.forEach((v, i) => {
      pvFcff[i + 1] = v;
    });
  }

  // ---------- Section 2 value-bridge rows ----------

  const terminalCF = dcf?.fcff_projections
    ? at(dcf.fcff_projections, dcf.fcff_projections.length - 1)
    : undefined;

  const terminalCostOfCapital = data.cost_of_capital?.wacc;

  const pvCashFlows = dcf?.pv_cash_flows_sum;
  const pvTerminal = dcf?.pv_terminal_value;
  const valueOfOpAssets = dcf?.value_of_operating_assets;

  const failureProbability = assumptions.failure_probability;
  const distressProceedsPct = assumptions.distress_proceeds_pct;
  const proceedsIfFails =
    valueOfOpAssets !== undefined && valueOfOpAssets !== null
      ? valueOfOpAssets * distressProceedsPct
      : undefined;

  const adjustedOpAssets =
    valueOfOpAssets !== undefined && valueOfOpAssets !== null
      ? valueOfOpAssets * (1 - failureProbability) +
        (proceedsIfFails ?? 0) * failureProbability
      : undefined;

  const debt = fin0.bv_debt;
  const minorityInterests = 0; // not in current schema — placeholder
  const cash = fin0.cash_and_marketable_securities;
  const nonOpAssets = 0; // not in current schema — placeholder

  const equityValue = dcf?.value_of_equity;
  const optionsValue = data.final?.value_of_all_options;

  const equityInCommon =
    equityValue !== undefined && equityValue !== null && optionsValue !== undefined && optionsValue !== null
      ? equityValue - optionsValue
      : undefined;

  const sharesOutstanding = fin0.shares_outstanding;
  const valuePerShare = data.final?.value_per_share;
  const currentPrice = fin0.stock_price;
  const priceAsPctOfValue =
    currentPrice !== null &&
    currentPrice !== undefined &&
    valuePerShare !== undefined &&
    valuePerShare !== null &&
    valuePerShare !== 0
      ? currentPrice / valuePerShare
      : undefined;

  // ---------- render helpers ----------

  /** Build a row of 13 cells from a label + values array */
  function projRow(label: string, values: (number | undefined)[], format?: 'pct' | 'num') {
    return (
      <tr>
        <SpreadsheetCell value={label} type="label" align="left" width="180px" />
        {values.map((v, i) => (
          <SpreadsheetCell
            key={i}
            value={format === 'pct' ? pct(v) : fmtNum(v)}
            type="calc"
          />
        ))}
      </tr>
    );
  }

  /** Single value-bridge row: label + value */
  function bridgeRow(label: string, value: number | string | null | undefined, indent = false) {
    return (
      <tr>
        <SpreadsheetCell
          value={indent ? `  ${label}` : label}
          type="label"
          align="left"
          width="320px"
        />
        <SpreadsheetCell value={fmtNum(value)} type="calc" />
      </tr>
    );
  }

  // ---------- render ----------

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">DCF Valuation Output</h2>

      <ColorLegend />

      {/* ===== Section 1: Projection Table ===== */}
      <div className="overflow-x-auto">
        <SpreadsheetGrid title="Projection Table">
          <thead>
            <tr>
              <SpreadsheetCell value="" type="header" width="180px" />
              {headers.map((h) => (
                <SpreadsheetCell key={h} value={h} type="header" />
              ))}
            </tr>
          </thead>
          <tbody>
            {projRow('Revenue growth rate', revenueGrowth, 'pct')}
            {projRow('Revenues', revenues)}
            {projRow('EBIT margin', ebitMargin, 'pct')}
            {projRow('EBIT', ebit)}
            {projRow(
              'Tax rate',
              Array(colCount).fill(taxRate),
              'pct',
            )}
            {projRow('EBIT(1-t)', ebitAfterTax)}
            {projRow('Reinvestment', reinvestment)}
            {projRow('FCFF', fcff)}
            {projRow('Cost of capital', costOfCapital, 'pct')}
            {projRow('Cumulated discount factor', discountFactor)}
            {projRow('PV(FCFF)', pvFcff)}
          </tbody>
        </SpreadsheetGrid>
      </div>

      {/* ===== Section 2: Value Bridge ===== */}
      <SpreadsheetGrid title="Value Bridge">
        <tbody>
          {bridgeRow('Terminal cash flow', terminalCF)}
          {bridgeRow('Terminal cost of capital', pct(terminalCostOfCapital))}
          {bridgeRow('Terminal value', dcf?.terminal_value_firm)}
          {bridgeRow('PV(terminal value)', pvTerminal)}
          {bridgeRow('PV(cash flows over next 10 years)', pvCashFlows)}
          {bridgeRow('Sum of PV (operating assets)', valueOfOpAssets)}
          {bridgeRow('Probability of failure', pct(failureProbability))}
          {bridgeRow('Proceeds if firm fails', proceedsIfFails)}
          {bridgeRow('Value of operating assets (adjusted)', adjustedOpAssets)}
          {bridgeRow('Minus: Debt', debt)}
          {bridgeRow('Minus: Minority interests', minorityInterests)}
          {bridgeRow('Plus: Cash', cash)}
          {bridgeRow('Plus: Non-operating assets', nonOpAssets)}
          {bridgeRow('Value of equity', equityValue)}
          {bridgeRow('Minus: Value of options', optionsValue)}
          {bridgeRow('Value of equity in common stock', equityInCommon)}
          {bridgeRow('Number of shares', sharesOutstanding)}
          {bridgeRow('Value per share', valuePerShare)}
          {bridgeRow('Current price', currentPrice)}
          {bridgeRow('Price as % of value', pct(priceAsPctOfValue))}
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
