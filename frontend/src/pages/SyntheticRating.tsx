import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { ciq, formula, backendField } from '../lib/sources';
import { baseYear } from '../lib/baseYear';

// Interest coverage → rating lookup table (Damodaran small-firm)
const RATING_TABLE = [
  { minCoverage: -100, maxCoverage: 0.5, rating: 'D2/D', spread: 0.1486 },
  { minCoverage: 0.5, maxCoverage: 0.8, rating: 'C2/C', spread: 0.1286 },
  { minCoverage: 0.8, maxCoverage: 1.25, rating: 'Ca2/CC', spread: 0.1086 },
  { minCoverage: 1.25, maxCoverage: 1.5, rating: 'Caa/CCC', spread: 0.0886 },
  { minCoverage: 1.5, maxCoverage: 2.0, rating: 'B3/B-', spread: 0.0486 },
  { minCoverage: 2.0, maxCoverage: 2.5, rating: 'B2/B', spread: 0.0386 },
  { minCoverage: 2.5, maxCoverage: 3.0, rating: 'B1/B+', spread: 0.0336 },
  { minCoverage: 3.0, maxCoverage: 3.5, rating: 'Ba2/BB', spread: 0.0236 },
  { minCoverage: 3.5, maxCoverage: 4.5, rating: 'Ba1/BB+', spread: 0.0186 },
  { minCoverage: 4.5, maxCoverage: 6.0, rating: 'Baa2/BBB', spread: 0.0161 },
  { minCoverage: 6.0, maxCoverage: 7.5, rating: 'A3/A-', spread: 0.0136 },
  { minCoverage: 7.5, maxCoverage: 9.5, rating: 'A2/A', spread: 0.0111 },
  { minCoverage: 9.5, maxCoverage: 12.5, rating: 'A1/A+', spread: 0.0086 },
  { minCoverage: 12.5, maxCoverage: 100, rating: 'Aaa/AAA', spread: 0.0063 },
];

export default function SyntheticRating({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const fin = baseYear(data);                // LTM-rotated base year
  const ebit = data.adjusted?.adjusted_ebit ?? fin?.ebit ?? 0;
  const interest = fin?.interest_expense ?? 1;
  const coverage = interest > 0 ? ebit / interest : 999;
  const match = RATING_TABLE.find(r => coverage >= r.minCoverage && coverage < r.maxCoverage);

  return (
    <div className="max-w-5xl">
      <h2 className="text-xl font-bold mb-4">Synthetic Rating</h2>
      <ColorLegend />

      <SpreadsheetGrid title="Company Interest Coverage">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="EBIT (adjusted)" />
            <SpreadsheetCell type="calc" value={ebit}
              tooltip={backendField('adjusted.adjusted_ebit', 'Raw EBIT + R&D current − Amortization + Lease adj. Source for coverage ratio calc.')} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Interest expense" />
            <SpreadsheetCell type="financial" value={interest}
              tooltip={ciq(data.inputs.ticker, 'IQ_INTEREST_EXP', 'LTM')} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Interest coverage ratio" bold />
            <SpreadsheetCell type="calc" value={coverage.toFixed(2)} bold
              tooltip={formula('Coverage = Adjusted EBIT / Interest expense',
                               `${ebit.toLocaleString(undefined,{maximumFractionDigits:0})} / ${interest.toLocaleString(undefined,{maximumFractionDigits:0})} = ${coverage.toFixed(2)}`)} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Estimated bond rating" bold />
            <SpreadsheetCell type="calc" value={match?.rating ?? 'N/A'} bold
              tooltip="Coverage → rating via lookup table below (Damodaran small-firm). Ginzu cost_of_capital_reference.json has both 'large' and 'small' versions." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Estimated default spread" bold />
            <SpreadsheetCell type="calc" value={match?.spread ?? 0} bold
              tooltip="Spread above risk-free rate at the inferred rating. Kd_pretax = RF + spread." />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      <SpreadsheetGrid title="Rating Lookup Table">
        <thead>
          <tr>
            <SpreadsheetCell type="header" value="Min Coverage" />
            <SpreadsheetCell type="header" value="Max Coverage" />
            <SpreadsheetCell type="header" value="Rating" />
            <SpreadsheetCell type="header" value="Default Spread" />
          </tr>
        </thead>
        <tbody>
          {RATING_TABLE.map((r, i) => (
            <tr key={i} className={match === r ? 'ring-2 ring-blue-500' : ''}>
              <SpreadsheetCell type="reference" value={r.minCoverage < 0 ? '< 0.5' : r.minCoverage.toFixed(1)}
                tooltip={`Lower bound of coverage bucket for rating ${r.rating}`} />
              <SpreadsheetCell type="reference" value={r.maxCoverage >= 100 ? '> 12.5' : r.maxCoverage.toFixed(1)}
                tooltip={`Upper bound of coverage bucket for rating ${r.rating}`} />
              <SpreadsheetCell type="reference" value={r.rating} align="left"
                tooltip={`Moody's / S&P composite rating assigned when coverage ∈ [${r.minCoverage}, ${r.maxCoverage})`} />
              <SpreadsheetCell type="reference" value={r.spread}
                tooltip={`Default spread (over RF) for rating ${r.rating}. Source: Damodaran synthetic rating table (Jan 2026), cost_of_capital_reference.json`} />
            </tr>
          ))}
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
