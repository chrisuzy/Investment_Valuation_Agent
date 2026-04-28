import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

export default function StoriesToNumbers({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const assumptions = data.inputs.valuation_assumptions;
  const industry = data.inputs.industry_data;
  const fin = data.inputs.raw_financials[0];

  const stories: { narrative: string; driver: string; input: string; value: string | number | null; type: 'hypothesis' | 'calc' | 'reference' }[] = [
    {
      narrative: 'How fast will the company grow revenues?',
      driver: 'Revenue growth rate (next year)',
      input: 'revenue_growth_next_year',
      value: assumptions.revenue_growth_next_year,
      type: 'hypothesis',
    },
    {
      narrative: 'How fast will it grow after year 1?',
      driver: 'Revenue growth rate (years 2-5)',
      input: 'revenue_growth_years_2_5',
      value: assumptions.revenue_growth_years_2_5,
      type: 'hypothesis',
    },
    {
      narrative: 'How profitable will the company be at maturity?',
      driver: 'Target pre-tax operating margin',
      input: 'target_operating_margin',
      value: assumptions.target_operating_margin,
      type: 'hypothesis',
    },
    {
      narrative: 'How long will it take to reach target margin?',
      driver: 'Year of convergence to target margin',
      input: 'margin_convergence_year',
      value: assumptions.margin_convergence_year,
      type: 'hypothesis',
    },
    {
      narrative: 'How efficiently will the company reinvest?',
      driver: 'Sales/Capital ratio (years 1-5)',
      input: 'sales_to_capital_high',
      value: assumptions.sales_to_capital_high,
      type: 'calc',
    },
    {
      narrative: 'What about reinvestment in stable growth?',
      driver: 'Sales/Capital ratio (years 6-10)',
      input: 'sales_to_capital_stable',
      value: assumptions.sales_to_capital_stable,
      type: 'calc',
    },
    {
      narrative: 'How risky is this company?',
      driver: 'Cost of capital',
      input: 'wacc',
      value: data.cost_of_capital?.wacc ?? null,
      type: 'calc',
    },
    {
      narrative: 'What is the long-term growth rate?',
      driver: 'Stable growth rate',
      input: 'stable_growth_rate',
      value: assumptions.stable_growth_rate ?? data.inputs.macro_inputs.risk_free_rate,
      type: 'hypothesis',
    },
    {
      narrative: 'Could this company fail?',
      driver: 'Probability of failure',
      input: 'failure_probability',
      value: assumptions.failure_probability,
      type: 'hypothesis',
    },
    {
      narrative: 'What are industry margins like?',
      driver: 'Industry pre-tax operating margin',
      input: 'pretax_operating_margin',
      value: industry.pretax_operating_margin,
      type: 'reference',
    },
    {
      narrative: 'What is the industry reinvestment?',
      driver: 'Industry sales/capital',
      input: 'sales_to_capital',
      value: industry.sales_to_capital,
      type: 'reference',
    },
    {
      narrative: 'What does the market value look like?',
      driver: 'Current stock price',
      input: 'stock_price',
      value: fin?.stock_price ?? null,
      type: 'reference',
    },
  ];

  return (
    <div className="max-w-6xl">
      <h2 className="text-xl font-bold mb-4">Stories to Numbers</h2>
      <ColorLegend />

      <p className="text-sm text-gray-600 mb-4">
        This worksheet maps your narrative about the company to the numerical inputs used in the valuation.
        Each row links a qualitative question to its quantitative driver.
      </p>

      <SpreadsheetGrid>
        <thead>
          <tr>
            <SpreadsheetCell type="header" value="Narrative Question" align="left" />
            <SpreadsheetCell type="header" value="Value Driver" align="left" />
            <SpreadsheetCell type="header" value="Input Field" align="left" />
            <SpreadsheetCell type="header" value="Current Value" />
            <SpreadsheetCell type="header" value="Source" />
          </tr>
        </thead>
        <tbody>
          {stories.map((s, i) => (
            <tr key={i}>
              <SpreadsheetCell type="label" value={s.narrative} align="left" />
              <SpreadsheetCell type="label" value={s.driver} align="left" />
              <SpreadsheetCell type="hint" value={s.input} align="left" />
              <SpreadsheetCell type={s.type} value={s.value} />
              <SpreadsheetCell type="label" value={
                s.type === 'hypothesis' ? 'User Input' :
                s.type === 'reference' ? 'Industry/Market' : 'Calculated'
              } align="center" />
            </tr>
          ))}
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
