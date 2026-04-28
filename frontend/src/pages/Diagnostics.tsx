import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

export default function Diagnostics({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const fin = data.inputs.raw_financials;
  const assumptions = data.inputs.valuation_assumptions;
  const industry = data.inputs.industry_data;
  const macro = data.inputs.macro_inputs;
  const dcf = data.dcf;

  // ---------- Step 1 helpers ----------
  const recentRevenueGrowth =
    fin.length >= 2 && fin[0].revenues && fin[1].revenues
      ? (fin[0].revenues - fin[1].revenues) / Math.abs(fin[1].revenues)
      : null;

  // ---------- Step 2 helpers ----------
  const baseRevenue = fin.length > 0 ? fin[0].revenues : null;
  const revYear1 =
    dcf && dcf.revenue_projections.length >= 1
      ? dcf.revenue_projections[0]
      : null;
  const revYear5 =
    dcf && dcf.revenue_projections.length >= 5
      ? dcf.revenue_projections[4]
      : null;
  const revYear10 =
    dcf && dcf.revenue_projections.length >= 10
      ? dcf.revenue_projections[9]
      : null;

  // ---------- Step 3 helpers ----------
  const currentMargin =
    fin.length > 0 && fin[0].revenues
      ? fin[0].ebit / fin[0].revenues
      : null;

  // ---------- Step 6 helpers ----------
  const valuePerShare = data.final?.value_per_share ?? null;
  const stockPrice = fin.length > 0 ? fin[0].stock_price ?? null : null;
  const priceAsPctOfValue =
    valuePerShare && stockPrice ? stockPrice / valuePerShare : null;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 space-y-4">
      <h2 className="text-lg font-bold text-gray-800 mb-4">Diagnostics</h2>
      <ColorLegend />

      {/* ===== Step 1: Revenue Growth ===== */}
      <SpreadsheetGrid title="Step 1: Revenue Growth">
        <tbody>
          <tr>
            <SpreadsheetCell value="Industry avg revenue growth" type="label" width="280px" />
            <SpreadsheetCell value="N/A" type="reference" />
          </tr>
          <tr>
            <SpreadsheetCell value="Most recent revenue growth" type="label" />
            <SpreadsheetCell value={recentRevenueGrowth} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Your forecast — Year 1 growth" type="label" />
            <SpreadsheetCell value={assumptions.revenue_growth_next_year} type="hypothesis" />
          </tr>
          <tr>
            <SpreadsheetCell value="Your forecast — Years 2-5 growth" type="label" />
            <SpreadsheetCell value={assumptions.revenue_growth_years_2_5} type="hypothesis" />
          </tr>
          <tr>
            <SpreadsheetCell
              value="Is your revenue growth rate consistent with the company's competitive advantages?"
              type="hint"
              colSpan={2}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Step 2: Dollar Revenues ===== */}
      <SpreadsheetGrid title="Step 2: Dollar Revenues">
        <tbody>
          <tr>
            <SpreadsheetCell value="Base year revenues" type="label" width="280px" />
            <SpreadsheetCell value={baseRevenue} type="financial" />
          </tr>
          {dcf && (
            <>
              <tr>
                <SpreadsheetCell value="Year 1 revenues" type="label" />
                <SpreadsheetCell value={revYear1} type="calc" />
              </tr>
              <tr>
                <SpreadsheetCell value="Year 5 revenues" type="label" />
                <SpreadsheetCell value={revYear5} type="calc" />
              </tr>
              <tr>
                <SpreadsheetCell value="Year 10 revenues" type="label" />
                <SpreadsheetCell value={revYear10} type="calc" />
              </tr>
            </>
          )}
          <tr>
            <SpreadsheetCell
              value="Does the revenue in year 10 pass the 'common sense' test?"
              type="hint"
              colSpan={2}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Step 3: Operating Margins ===== */}
      <SpreadsheetGrid title="Step 3: Operating Margins">
        <tbody>
          <tr>
            <SpreadsheetCell value="Current operating margin" type="label" width="280px" />
            <SpreadsheetCell value={currentMargin} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Target operating margin" type="label" />
            <SpreadsheetCell value={assumptions.target_operating_margin} type="hypothesis" />
          </tr>
          <tr>
            <SpreadsheetCell value="Industry pretax margin" type="label" />
            <SpreadsheetCell value={industry.pretax_operating_margin} type="reference" />
          </tr>
          <tr>
            <SpreadsheetCell value="Year of convergence" type="label" />
            <SpreadsheetCell value={assumptions.margin_convergence_year} type="hypothesis" />
          </tr>
          <tr>
            <SpreadsheetCell
              value="Is your target margin achievable given industry norms?"
              type="hint"
              colSpan={2}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Step 4: Reinvestment ===== */}
      <SpreadsheetGrid title="Step 4: Reinvestment">
        <tbody>
          <tr>
            <SpreadsheetCell value="Sales/capital years 1-5" type="label" width="280px" />
            <SpreadsheetCell value={assumptions.sales_to_capital_high} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Sales/capital years 6-10" type="label" />
            <SpreadsheetCell value={assumptions.sales_to_capital_stable} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Industry sales/capital" type="label" />
            <SpreadsheetCell value={industry.sales_to_capital} type="reference" />
          </tr>
          <tr>
            <SpreadsheetCell
              value="Is reinvestment consistent with growth?"
              type="hint"
              colSpan={2}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Step 5: Risk ===== */}
      <SpreadsheetGrid title="Step 5: Risk">
        <tbody>
          <tr>
            <SpreadsheetCell value="Cost of capital (WACC)" type="label" width="280px" />
            <SpreadsheetCell value={data.cost_of_capital?.wacc ?? null} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Industry WACC" type="label" />
            <SpreadsheetCell value={industry.wacc} type="reference" />
          </tr>
          <tr>
            <SpreadsheetCell value="Risk-free rate" type="label" />
            <SpreadsheetCell value={macro.risk_free_rate} type="hypothesis" />
          </tr>
          <tr>
            <SpreadsheetCell
              value="Does the cost of capital reflect the risk?"
              type="hint"
              colSpan={2}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Step 6: Value vs Price ===== */}
      <SpreadsheetGrid title="Step 6: Value vs Price">
        <tbody>
          <tr>
            <SpreadsheetCell value="Value per share" type="label" width="280px" />
            <SpreadsheetCell value={valuePerShare} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Stock price" type="label" />
            <SpreadsheetCell value={stockPrice} type="financial" />
          </tr>
          <tr>
            <SpreadsheetCell value="Price as % of value" type="label" />
            <SpreadsheetCell value={priceAsPctOfValue} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell
              value="What would need to change to justify the current price?"
              type="hint"
              colSpan={2}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
