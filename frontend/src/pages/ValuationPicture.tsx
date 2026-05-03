import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { baseYear, baseYearMargin } from '../lib/baseYear';

export default function ValuationPicture({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const fin = baseYear(data);                   // LTM-rotated base year
  const assumptions = data.inputs.valuation_assumptions;
  const dcf = data.dcf;
  const final_ = data.final;
  const coc = data.cost_of_capital;

  const baseRevenue = fin?.revenues ?? 0;
  // Damodaran-adjusted margin (post R&D + lease capitalization). Matches
  // what the engine uses as the starting point for the margin path.
  const currentMargin = baseYearMargin(data) ?? 0;
  const terminalRevenue = dcf?.revenue_projections?.[dcf.revenue_projections.length - 1] ?? 0;
  const terminalEbit = dcf?.ebit_projections?.[dcf.ebit_projections.length - 1] ?? 0;

  return (
    <div className="max-w-6xl">
      <h2 className="text-xl font-bold mb-4">Valuation as Picture</h2>
      <ColorLegend />

      <p className="text-sm text-gray-600 mb-4">
        A visual summary of the valuation flow from inputs through to value per share.
      </p>

      {/* Revenue Growth Flow */}
      <SpreadsheetGrid title="Revenue Growth Path">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Current revenues" />
            <SpreadsheetCell type="financial" value={baseRevenue} />
            <SpreadsheetCell type="label" value="→ Growth yr 1" />
            <SpreadsheetCell type="hypothesis" value={assumptions.revenue_growth_next_year} />
            <SpreadsheetCell type="label" value="→ Growth yrs 2-5" />
            <SpreadsheetCell type="hypothesis" value={assumptions.revenue_growth_years_2_5} />
            <SpreadsheetCell type="label" value="→ Terminal revenues" />
            <SpreadsheetCell type="calc" value={terminalRevenue} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Margin Path */}
      <SpreadsheetGrid title="Operating Margin Path">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Current EBIT margin" />
            <SpreadsheetCell type="calc" value={currentMargin} />
            <SpreadsheetCell type="label" value="→ Target margin" />
            <SpreadsheetCell type="hypothesis" value={assumptions.target_operating_margin} />
            <SpreadsheetCell type="label" value="→ Converge year" />
            <SpreadsheetCell type="hypothesis" value={assumptions.margin_convergence_year} />
            <SpreadsheetCell type="label" value="→ Terminal EBIT" />
            <SpreadsheetCell type="calc" value={terminalEbit} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Cost of Capital */}
      <SpreadsheetGrid title="Cost of Capital">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Risk-free rate" />
            <SpreadsheetCell type="hypothesis" value={data.inputs.macro_inputs.risk_free_rate} />
            <SpreadsheetCell type="label" value="+ Beta × ERP" />
            <SpreadsheetCell type="reference" value={data.inputs.macro_inputs.equity_risk_premium} />
            <SpreadsheetCell type="label" value="→ WACC" />
            <SpreadsheetCell type="calc" value={coc?.wacc ?? null} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Value Bridge */}
      <SpreadsheetGrid title="Value Bridge">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="PV(Cash Flows)" />
            <SpreadsheetCell type="calc" value={dcf?.pv_cash_flows_sum ?? null} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="+ PV(Terminal Value)" />
            <SpreadsheetCell type="calc" value={dcf?.pv_terminal_value ?? null} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="= Operating Assets" bold />
            <SpreadsheetCell type="calc" value={dcf?.value_of_operating_assets ?? null} bold />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="- Debt" />
            <SpreadsheetCell type="financial" value={fin?.bv_debt ?? null} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="+ Cash" />
            <SpreadsheetCell type="financial" value={fin?.cash_and_marketable_securities ?? null} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="= Value of Equity" bold />
            <SpreadsheetCell type="calc" value={dcf?.value_of_equity ?? null} bold />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="- Options" />
            <SpreadsheetCell type="calc" value={final_?.value_of_all_options ?? 0} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="/ Shares Outstanding" />
            <SpreadsheetCell type="financial" value={fin?.shares_outstanding ?? null} />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="= Value per Share" bold />
            <SpreadsheetCell type="calc" value={final_?.value_per_share ?? null} bold />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Current Stock Price" />
            <SpreadsheetCell type="financial" value={fin?.stock_price ?? null} />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
