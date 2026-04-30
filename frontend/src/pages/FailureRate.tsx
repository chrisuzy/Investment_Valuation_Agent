import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { user, formula, backendField } from '../lib/sources';

// Cumulative default rates by rating (10-year)
const DEFAULT_RATES = [
  { rating: 'Aaa/AAA', prob1: 0.0001, prob5: 0.0012, prob10: 0.0050 },
  { rating: 'Aa2/AA', prob1: 0.0008, prob5: 0.0050, prob10: 0.0100 },
  { rating: 'A1/A+', prob1: 0.0020, prob5: 0.0100, prob10: 0.0200 },
  { rating: 'A2/A', prob1: 0.0050, prob5: 0.0200, prob10: 0.0400 },
  { rating: 'Baa2/BBB', prob1: 0.0120, prob5: 0.0350, prob10: 0.0700 },
  { rating: 'Ba1/BB+', prob1: 0.0200, prob5: 0.0700, prob10: 0.1100 },
  { rating: 'Ba2/BB', prob1: 0.0350, prob5: 0.1100, prob10: 0.1800 },
  { rating: 'B1/B+', prob1: 0.0500, prob5: 0.1500, prob10: 0.2500 },
  { rating: 'B2/B', prob1: 0.0650, prob5: 0.2000, prob10: 0.3200 },
  { rating: 'B3/B-', prob1: 0.0800, prob5: 0.2500, prob10: 0.3800 },
  { rating: 'Caa/CCC', prob1: 0.1200, prob5: 0.3500, prob10: 0.5000 },
  { rating: 'Ca2/CC', prob1: 0.2000, prob5: 0.4500, prob10: 0.6500 },
  { rating: 'C2/C', prob1: 0.3000, prob5: 0.6000, prob10: 0.8000 },
  { rating: 'D2/D', prob1: 1.0000, prob5: 1.0000, prob10: 1.0000 },
];

export default function FailureRate({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const failProb = data.inputs.valuation_assumptions.failure_probability;
  const proceedsPct = data.inputs.valuation_assumptions.distress_proceeds_pct;
  const opAssets = data.dcf?.value_of_operating_assets ?? 0;

  return (
    <div className="max-w-5xl">
      <h2 className="text-xl font-bold mb-4">Failure Rate Worksheet</h2>
      <ColorLegend />

      <SpreadsheetGrid title="Failure Probability Inputs">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Probability of failure" />
            <SpreadsheetCell type="hypothesis" value={failProb} editable
              tooltip={user('Probability of failure over the DCF horizon', 'Default = 0%. Analyst sets based on bond rating, cash-burn runway, or distress flags. See cumulative default rates below for rating-based benchmarks.')} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Proceeds as % of book value if failure" />
            <SpreadsheetCell type="hypothesis" value={proceedsPct} editable
              tooltip={user('Distress sale proceeds fraction', 'Default 50%. Liquidation recovery rate on assets in failure. 0% if you believe assets will be worthless.')} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Failure tie-to (Book value / fair Value)" />
            <SpreadsheetCell type="hypothesis" value={data.inputs.valuation_assumptions.failure_tie_to} editable
              tooltip={user('What to tie failure proceeds to', '"B" = book value of capital; "V" = estimated fair value. Default V.')} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      <SpreadsheetGrid title="Impact on Valuation">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Value of operating assets (going concern)" />
            <SpreadsheetCell type="calc" value={opAssets}
              tooltip={backendField('dcf.value_of_operating_assets', 'Σ PV(FCFF) + PV(Terminal Value) before failure overlay')} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Probability of failure" />
            <SpreadsheetCell type="calc" value={failProb}
              tooltip="Echoed from Failure Probability Inputs above" />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Distress sale proceeds" />
            <SpreadsheetCell type="calc" value={opAssets * proceedsPct}
              tooltip={formula('Proceeds = V_op × distress_proceeds_pct',
                               `${opAssets.toLocaleString('en-US',{maximumFractionDigits:0})} × ${(proceedsPct*100).toFixed(0)}% = ${(opAssets*proceedsPct).toLocaleString('en-US',{maximumFractionDigits:0})}`)} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Expected operating asset value" bold />
            <SpreadsheetCell type="calc" value={opAssets * (1 - failProb) + opAssets * proceedsPct * failProb} bold
              tooltip={formula('V_expected = V_op × (1 − p_fail) + Proceeds × p_fail', 'Probability-weighted blend of going-concern + distress scenarios.')} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      <SpreadsheetGrid title="Cumulative Default Rates by Rating">
        <thead>
          <tr>
            <SpreadsheetCell type="header" value="Bond Rating" />
            <SpreadsheetCell type="header" value="1-Year" />
            <SpreadsheetCell type="header" value="5-Year" />
            <SpreadsheetCell type="header" value="10-Year" />
          </tr>
        </thead>
        <tbody>
          {DEFAULT_RATES.map((r, i) => (
            <tr key={i}>
              <SpreadsheetCell type="reference" value={r.rating} align="left"
                tooltip="Moody's / S&P composite rating" />
              <SpreadsheetCell type="reference" value={r.prob1}
                tooltip={`1-year cumulative default probability for ${r.rating} (Damodaran failure rate worksheet, 2025 update)`} />
              <SpreadsheetCell type="reference" value={r.prob5}
                tooltip={`5-year cumulative default probability for ${r.rating} — multi-year projection of 1-yr rate`} />
              <SpreadsheetCell type="reference" value={r.prob10}
                tooltip={`10-year cumulative default probability for ${r.rating} — typical choice for DCF horizon`} />
            </tr>
          ))}
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
