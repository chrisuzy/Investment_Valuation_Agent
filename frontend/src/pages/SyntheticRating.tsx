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

  // Surface the engine's actual WACC-side values so users can see what
  // the Cost of Capital module picked up, versus what THIS page's table
  // would suggest. Disagreement typically means the engine used the
  // 'actual_rating' branch (fetched from CIQ IQ_SP_ISSUER_RATING),
  // a different firm-type table (large/financial), or the industry
  // fallback path.
  const mc = data.inputs.methodology_choices;
  const firmType = mc?.synthetic_rating_firm_type ?? 'large';
  const engineRating = data.cost_of_capital?.synthetic_rating;
  const engineKdBranch = data.cost_of_capital?.kd_branch_used;
  const engineKdPretax = data.cost_of_capital?.cost_of_debt_pretax;
  const engineActualRating = mc?.actual_rating;

  return (
    <div className="max-w-5xl">
      <h2 className="text-xl font-bold mb-4">Synthetic Rating</h2>
      <ColorLegend />

      {firmType !== 'small' && (
        <div className="mb-3 px-3 py-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-900">
          <b>Note:</b> the reference table below is the "small firm" Damodaran
          lookup. Your current methodology selection is firm-type = <b>{firmType}</b>.
          The engine uses a different coverage-band table for {firmType} firms,
          so the "Estimated bond rating" cell on this page may disagree with
          the rating used in the actual WACC calculation. The engine's values
          are shown at the bottom of this page for cross-check.
        </div>
      )}

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

      <SpreadsheetGrid title="What the engine actually used (Cost of Capital)">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Kd approach" />
            <SpreadsheetCell type="reference" value={mc?.kd_approach ?? '—'}
              tooltip="Which cost-of-debt branch ran. 'actual_rating' = CIQ-fetched S&P rating; 'synthetic_rating' = derived from interest coverage (this page's logic); 'industry_fallback' = Damodaran industry Kd average." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Rating branch trace" />
            <SpreadsheetCell type="reference" value={engineKdBranch ?? '—'}
              tooltip="Concrete branch label from the cost-of-capital engine trace — which specific path produced the Kd that WACC is using. Useful when you want to verify (vs the Kd approach above) which rating table was consulted." />
          </tr>
          {engineActualRating && (
            <tr>
              <SpreadsheetCell type="label" value="Actual rating (CIQ)" />
              <SpreadsheetCell type="reference" value={engineActualRating}
                tooltip={`From =CIQ($B$1,"IQ_SP_ISSUER_RATING") fetched by the CIQ template, normalized to the Moody's/S&P compound key. Takes precedence over synthetic rating when available.`} />
            </tr>
          )}
          <tr>
            <SpreadsheetCell type="label" value="Rating used by engine" bold />
            <SpreadsheetCell type="calc" value={engineRating ?? match?.rating ?? '—'} bold
              tooltip="The rating the engine ultimately applied when computing Kd. Compare with the 'Estimated bond rating' in the table above — disagreement means the engine bypassed synthetic-rating logic." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Kd pre-tax (engine)" bold />
            <SpreadsheetCell type="calc" value={engineKdPretax}
              tooltip="Cost of debt pre-tax currently feeding the WACC. = RF + credit spread from the rating the engine used." />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
