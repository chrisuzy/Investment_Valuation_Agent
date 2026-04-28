import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

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
            <SpreadsheetCell type="hypothesis" value={failProb} editable />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Proceeds as % of book value if failure" />
            <SpreadsheetCell type="hypothesis" value={proceedsPct} editable />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      <SpreadsheetGrid title="Impact on Valuation">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Value of operating assets (going concern)" />
            <SpreadsheetCell type="calc" value={opAssets} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Probability of failure" />
            <SpreadsheetCell type="calc" value={failProb} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Distress sale proceeds" />
            <SpreadsheetCell type="calc" value={opAssets * proceedsPct} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Expected operating asset value" bold />
            <SpreadsheetCell type="calc" value={opAssets * (1 - failProb) + opAssets * proceedsPct * failProb} bold />
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
              <SpreadsheetCell type="reference" value={r.rating} align="left" />
              <SpreadsheetCell type="reference" value={r.prob1} />
              <SpreadsheetCell type="reference" value={r.prob5} />
              <SpreadsheetCell type="reference" value={r.prob10} />
            </tr>
          ))}
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
