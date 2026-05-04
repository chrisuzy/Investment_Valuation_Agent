import type { ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import SensitivityPanel from '../components/SensitivityPanel';
import { ciq, formula, backendField, user } from '../lib/sources';
import DualCurrency from '../components/DualCurrency';
import { fmtMoneyShort } from '../lib/currency';
import { baseYear, baseYearEbit } from '../lib/baseYear';

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

interface Props {
  data: ValuationResponse;
  sessionId?: string | null;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
  onPatchMany?: (overrides: Record<string, PatchValue>) => void | Promise<void>;
}

export default function ValuationOutput({ data, onPatch, onPatchMany }: Props) {
  const dcf = data.dcf;
  const inputs = data.inputs;
  // LTM-rotated base year (falls back to raw_financials[0] when LTM absent).
  // Critical for non-calendar-year filers so the "Base year" column matches
  // what the engine's M3/M4 actually anchor on.
  const fin0 = baseYear(data) ?? inputs.raw_financials[0];
  const baseEbit = baseYearEbit(data) ?? 0;
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

  // EBIT — base year uses Damodaran-adjusted EBIT (post R&D + lease
  // capitalization). This matches what M4 uses as the starting point
  // of the margin path, so there's no artificial cliff between the
  // "Base year" column and Year 1.
  const ebit: (number | undefined)[] = Array(colCount).fill(undefined);
  ebit[0] = baseEbit;
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

  // Tax rate per year — back out from the engine's actual NOPAT / EBIT.
  // The engine transitions effective → marginal over the projection, so
  // showing a flat marginal rate here (old behavior) caused the displayed
  // EBIT(1-t) row to disagree with FCFF+Reinvestment in the same column.
  // NOPAT_t = FCFF_t + Reinvestment_t ; tax_t = 1 − NOPAT_t / EBIT_t.
  const taxRatePerYear: (number | undefined)[] = Array(colCount).fill(undefined);
  if (dcf?.fcff_projections && dcf?.reinvestment_projections) {
    for (let i = 0; i < dcf.fcff_projections.length; i++) {
      const e = ebit[i + 1];
      if (e != null && e !== 0) {
        const nopat = dcf.fcff_projections[i] + dcf.reinvestment_projections[i];
        taxRatePerYear[i + 1] = 1 - nopat / e;
      }
    }
  }
  // Base-year tax uses macro.tax_rate_effective (what the firm actually paid).
  taxRatePerYear[0] = macro.tax_rate_effective ?? macro.tax_rate_marginal;

  // EBIT(1-t) per year — matches the engine's per-year NOPAT exactly.
  const ebitAfterTax: (number | undefined)[] = ebit.map((e, i) => {
    const t = taxRatePerYear[i];
    return (e != null && t != null) ? e * (1 - t) : undefined;
  });

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

  // Equity-bridge components — read the actual engine fields, not 0.
  // Earlier version hardcoded minority/cross-holdings to 0 as placeholders,
  // which made the arithmetic shown disagree with `equityValue` below
  // (the engine DOES subtract minority and add cross-holdings).
  // Prefer the CostOfCapital.mv_debt_total (includes lease PV and
  // convertible straight part) when available, falling back to raw bv_debt.
  const debt = data.cost_of_capital?.mv_debt_total ?? fin0.bv_debt;
  const minorityInterests = fin0.minority_interests ?? 0;
  const cash = fin0.cash_and_marketable_securities;
  const nonOpAssets = fin0.cross_holdings ?? 0;

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
  function projRow(
    label: string,
    values: (number | undefined)[],
    format?: 'pct' | 'num',
    tooltip?: string | ((i: number) => string),
  ) {
    return (
      <tr>
        <SpreadsheetCell value={label} type="label" align="left" width="180px" />
        {values.map((v, i) => {
          const tip = typeof tooltip === 'function' ? tooltip(i) : tooltip;
          return (
            <SpreadsheetCell
              key={i}
              value={format === 'pct' ? pct(v) : fmtNum(v)}
              type="calc"
              tooltip={tip}
            />
          );
        })}
      </tr>
    );
  }

  /** Single value-bridge row: label + value */
  function bridgeRow(label: string, value: number | string | null | undefined, tooltip?: string, indent = false) {
    return (
      <tr>
        <SpreadsheetCell
          value={indent ? `  ${label}` : label}
          type="label"
          align="left"
          width="320px"
        />
        <SpreadsheetCell value={fmtNum(value)} type="calc" tooltip={tooltip} />
      </tr>
    );
  }

  // Tooltip composer for projection-table cells (column-aware)
  const projTip = (colLabel: string, baseDesc: string) => {
    return (i: number) => {
      if (i === 0) return `${baseDesc} — Base year (LTM from CIQ)`;
      if (i === 11) return `${baseDesc} — Terminal (year 10+1 perpetuity)`;
      return `${baseDesc} — ${colLabel.replace('{i}', String(i))}`;
    };
  };

  // ---------- render ----------

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">DCF Valuation Output</h2>

      <ColorLegend />

      {/* ===== Section 1: Projection Table ===== */}
      <div className="overflow-x-auto">
        <SpreadsheetGrid title={`Projection Table (${data.inputs.reporting_currency ?? '—'}, in millions)`}>
          <thead>
            <tr>
              <SpreadsheetCell value="" type="header" width="180px" />
              {headers.map((h) => (
                <SpreadsheetCell key={h} value={h} type="header" />
              ))}
            </tr>
          </thead>
          <tbody>
            {projRow('Revenue growth rate', revenueGrowth, 'pct',
              projTip('year {i}', 'g = (Rev_t − Rev_{t-1}) / Rev_{t-1}. Year 1 = user hypothesis; years 2-5 = CAGR user input; years 6-10 = linear decay to stable growth rate ≤ RF'))}
            {projRow('Revenues', revenues, 'num',
              projTip('year {i}', 'Rev_t = Rev_{t-1} × (1 + g_t). Base year is LTM revenue from CIQ.'))}
            {projRow('EBIT margin', ebitMargin, 'pct',
              projTip('year {i}', 'Margin path: starts at user hypothesis (yr 1), converges linearly to target_operating_margin by margin_convergence_year, then holds flat.'))}
            {projRow('EBIT', ebit, 'num',
              projTip('year {i}', 'EBIT_t = Rev_t × margin_t (Ginzu: explicit compound, not EBIT×(1+growth))'))}
            {projRow(
              'Tax rate',
              taxRatePerYear,
              'pct',
              formula(
                'Effective in base year, converges to marginal over the projection',
                `Base = ${pct(macro.tax_rate_effective)} (what the firm actually paid); terminal → ${pct(macro.tax_rate_marginal)} (marginal). Per-year value back-calculated from the engine's FCFF + Reinvestment so it reconciles exactly with the EBIT(1-t) row below.`,
              ),
            )}
            {projRow('EBIT(1-t)', ebitAfterTax, 'num',
              formula('EBIT × (1 − tax rate) using the per-year tax rate shown above (NOT a flat marginal rate). Matches the engine\'s NOPAT.'))}
            {projRow('Reinvestment', reinvestment, 'num',
              projTip('year {i}', 'Sales-to-capital method: Reinvest_t = (Rev_t − Rev_{t−lag}) / (S/C ratio). Lag = 1 year default.'))}
            {projRow('FCFF', fcff, 'num',
              projTip('year {i}', 'FCFF_t = EBIT(1−t)_t − Reinvest_t'))}
            {projRow('Cost of capital', costOfCapital, 'pct',
              'WACC from Module 2. If "stable WACC override" is set, terminal WACC may differ from years 1-10.')}
            {projRow('Cumulated discount factor', discountFactor, 'num',
              projTip('year {i}', 'CumDiscount_t = Π(1 / (1 + WACC_s)) for s=1..t. Product form handles non-constant WACC.'))}
            {projRow('PV(FCFF)', pvFcff, 'num',
              projTip('year {i}', 'PV = FCFF_t × CumDiscount_t'))}
          </tbody>
        </SpreadsheetGrid>
      </div>

      {/* ===== Section 2: Value Bridge ===== */}
      <SpreadsheetGrid title={`Value Bridge (${data.inputs.reporting_currency ?? '—'}, in millions — per-share figures on final row)`}>
        <tbody>
          {bridgeRow('Terminal cash flow', terminalCF,
            'FCFF in year 10. If override_growth_perpetuity is set, FCFF is adjusted for post-yr-10 growth rate.')}
          {bridgeRow('Terminal cost of capital', pct(terminalCostOfCapital),
            user('Stable-period WACC', 'Default = same as year-10 WACC; can be overridden (typically 8.5% for mature firms).'))}
          {bridgeRow('Terminal value', dcf?.terminal_value_firm,
            formula('TV = FCFF_yr10 × (1 + g_stable) / (WACC_stable − g_stable)', 'Gordon growth; g_stable ≤ RF per Damodaran constraint.'))}
          {bridgeRow('PV(terminal value)', pvTerminal,
            formula('PV(TV) = TV × CumDiscount_yr10'))}
          {bridgeRow('PV(cash flows over next 10 years)', pvCashFlows,
            formula('Σ PV(FCFF_t) for t=1..10') + ' — ' + backendField('dcf.pv_cash_flows_sum'))}
          {bridgeRow('Sum of PV (operating assets)', valueOfOpAssets,
            formula('V_operating = Σ PV(FCFF) + PV(TV)') + ' — ' + backendField('dcf.value_of_operating_assets'))}
          {bridgeRow('Probability of failure', pct(failureProbability),
            user('Failure probability', 'Default 0%. Override via FailureRate page. Applied as overlay to going-concern value.'))}
          {bridgeRow('Proceeds if firm fails', proceedsIfFails,
            formula('Proceeds = V_operating × distress_proceeds_pct (or BV if failure_tie_to = "B")'))}
          {bridgeRow('Value of operating assets (adjusted)', adjustedOpAssets,
            formula('V_adj = V_op × (1 − p_fail) + Proceeds × p_fail'))}
          {bridgeRow('Minus: Debt', debt,
            ciq(inputs.ticker, 'IQ_TOTAL_DEBT', 'IQ_FY-0'))}
          {bridgeRow('Minus: Minority interests', minorityInterests,
            ciq(inputs.ticker, 'IQ_MINORITY_INTEREST', 'IQ_FY-0'))}
          {bridgeRow('Plus: Cash', cash,
            ciq(inputs.ticker, 'IQ_CASH_ST_INVEST', 'IQ_FY-0'))}
          {bridgeRow('Plus: Non-operating assets', nonOpAssets,
            'Cross-holdings / investments in affiliates — placeholder in current schema')}
          {bridgeRow('Value of equity', equityValue,
            formula('V_equity = V_op (adj) − Debt − Minority + Cash + Non-op'))}
          {bridgeRow('Minus: Value of options', optionsValue,
            'Iterative Black-Scholes from Module 6 (Option value page).')}
          {bridgeRow('Value of equity in common stock', equityInCommon,
            formula('= V_equity − Options'))}
          {bridgeRow('Number of shares', sharesOutstanding,
            `Shares outstanding from the LTM base-year snapshot. CIQ mnemonic =CIQ("${inputs.ticker}","IQ_TOTAL_OUTSTANDING_FILING_DATE") — point-in-time shares at the most recent filing date. Falls back to FY-0 if the quarterly snapshot didn't provide a value.`)}
          {(() => {
            const repCcy = inputs.reporting_currency;
            const listCcy = inputs.stock_price_currency;
            const fxRate = inputs.fx_rate;
            const marketListing = currentPrice;            // stock_price — listing ccy
            const marketReporting = fxRate != null && marketListing != null ? marketListing * fxRate : marketListing;
            const vpsReporting = valuePerShare;            // VPS — reporting ccy
            const marketForCompare = marketReporting;       // both sides in reporting ccy
            const ratio = vpsReporting != null && marketForCompare != null && vpsReporting !== 0
              ? marketForCompare / vpsReporting : undefined;
            return (
              <>
                <tr>
                  <SpreadsheetCell value="Value per share (reporting ccy)" type="label" align="left" width="320px" />
                  <td className="border px-1.5 py-0.5 bg-emerald-50 border-emerald-200 text-right whitespace-nowrap"
                      title={formula('VPS = V_equity_common / shares') + ' — ' + backendField('final.value_per_share')}>
                    <DualCurrency valueReporting={vpsReporting} reportingCcy={repCcy} listingCcy={listCcy} fxRate={fxRate} />
                  </td>
                </tr>
                <tr>
                  <SpreadsheetCell value="Current market price (listing ccy)" type="label" align="left" width="320px" />
                  <td className="border px-1.5 py-0.5 bg-emerald-50 border-emerald-200 text-right whitespace-nowrap"
                      title={ciq(inputs.ticker, 'IQ_CLOSEPRICE') + ` — displayed in listing ccy ${listCcy || '?'}; also shown converted to reporting ccy ${repCcy || '?'} for apples-to-apples comparison with VPS`}>
                    <DualCurrency valueListing={marketListing} reportingCcy={repCcy} listingCcy={listCcy} fxRate={fxRate} primary="listing" />
                  </td>
                </tr>
                <tr>
                  <SpreadsheetCell value="Price / Value (reporting-ccy basis)" type="label" align="left" width="320px" />
                  <td className="border px-1.5 py-0.5 bg-emerald-50 border-emerald-200 text-right whitespace-nowrap font-bold"
                      title={`Market ${fmtMoneyShort(marketForCompare, repCcy)} / VPS ${fmtMoneyShort(vpsReporting, repCcy)} — both in ${repCcy || '?'}. > 1 = overvalued on DCF; < 1 = undervalued.`}>
                    {ratio != null ? `${ratio.toFixed(2)}x` : '—'}
                  </td>
                </tr>
              </>
            );
          })()}
        </tbody>
      </SpreadsheetGrid>

      <SensitivityPanel data={data} onPatch={onPatch} onPatchMany={onPatchMany} />
    </div>
  );
}
