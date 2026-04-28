import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

export default function AnswerKeys({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const fin = data.inputs.raw_financials[0];
  const assumptions = data.inputs.valuation_assumptions;
  const industry = data.inputs.industry_data;
  const macro = data.inputs.macro_inputs;
  const coc = data.cost_of_capital;
  const dcf = data.dcf;
  const final_ = data.final;

  const answers: { category: string; items: { label: string; value: string | number | null }[] }[] = [
    {
      category: 'Company Data',
      items: [
        { label: 'Company', value: data.inputs.company_name ?? data.ticker },
        { label: 'Industry', value: industry.industry_name },
        { label: 'Revenues', value: fin?.revenues ?? null },
        { label: 'EBIT', value: fin?.ebit ?? null },
        { label: 'Stock Price', value: fin?.stock_price ?? null },
        { label: 'Shares Outstanding', value: fin?.shares_outstanding ?? null },
      ],
    },
    {
      category: 'Key Assumptions',
      items: [
        { label: 'Revenue Growth (Yr 1)', value: assumptions.revenue_growth_next_year },
        { label: 'Revenue Growth (Yrs 2-5)', value: assumptions.revenue_growth_years_2_5 },
        { label: 'Target Operating Margin', value: assumptions.target_operating_margin },
        { label: 'Convergence Year', value: assumptions.margin_convergence_year },
        { label: 'Risk-free Rate', value: macro.risk_free_rate },
        { label: 'Failure Probability', value: assumptions.failure_probability },
      ],
    },
    {
      category: 'Computed Results',
      items: [
        { label: 'WACC', value: coc?.wacc ?? null },
        { label: 'Levered Beta', value: coc?.beta_l ?? null },
        { label: 'Terminal Value', value: dcf?.terminal_value_firm ?? null },
        { label: 'Value of Operating Assets', value: dcf?.value_of_operating_assets ?? null },
        { label: 'Value of Equity', value: dcf?.value_of_equity ?? null },
        { label: 'Value per Share', value: final_?.value_per_share ?? null },
      ],
    },
    {
      category: 'Industry Benchmarks',
      items: [
        { label: 'Industry Beta (unlevered)', value: industry.beta_u },
        { label: 'Industry D/E', value: industry.industry_d_e_ratio },
        { label: 'Industry WACC', value: industry.wacc },
        { label: 'Industry Operating Margin', value: industry.pretax_operating_margin },
        { label: 'Industry Sales/Capital', value: industry.sales_to_capital },
      ],
    },
  ];

  return (
    <div className="max-w-5xl">
      <h2 className="text-xl font-bold mb-4">Answer Keys</h2>
      <ColorLegend />

      <p className="text-sm text-gray-600 mb-4">
        Reference summary of all key inputs, assumptions, and computed outputs for validation.
      </p>

      {answers.map((section) => (
        <SpreadsheetGrid key={section.category} title={section.category}>
          <thead>
            <tr>
              <SpreadsheetCell type="header" value="Item" align="left" />
              <SpreadsheetCell type="header" value="Value" />
            </tr>
          </thead>
          <tbody>
            {section.items.map((item) => (
              <tr key={item.label}>
                <SpreadsheetCell type="label" value={item.label} align="left" />
                <SpreadsheetCell
                  type={
                    section.category === 'Company Data' ? 'financial' :
                    section.category === 'Key Assumptions' ? 'hypothesis' :
                    section.category === 'Industry Benchmarks' ? 'reference' : 'calc'
                  }
                  value={item.value}
                />
              </tr>
            ))}
          </tbody>
        </SpreadsheetGrid>
      ))}
    </div>
  );
}
