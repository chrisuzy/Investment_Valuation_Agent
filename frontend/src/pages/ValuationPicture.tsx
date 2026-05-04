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
            <SpreadsheetCell type="financial" value={baseRevenue} tooltip="LTM revenue (base year). Source: IQ_TOTAL_REV rotated from FY-0 + quarterly delta." />
            <SpreadsheetCell type="label" value="→ Growth yr 1" />
            <SpreadsheetCell type="hypothesis" value={assumptions.revenue_growth_next_year} tooltip="Analyst input: revenue_growth_next_year. Year-1 growth rate applied to base revenue." />
            <SpreadsheetCell type="label" value="→ Growth yrs 2-5" />
            <SpreadsheetCell type="hypothesis" value={assumptions.revenue_growth_years_2_5} tooltip="Analyst input: revenue_growth_years_2_5. Single flat rate applied to years 2–5 per folder §3.1." />
            <SpreadsheetCell type="label" value="→ Terminal revenues" />
            <SpreadsheetCell type="calc" value={terminalRevenue} tooltip="Year-10 projected revenue from the DCF engine (dcf.revenue_projections[9]). Compound growth through yr-1, yrs 2–5, then linear convergence yrs 6–10." />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Margin Path */}
      <SpreadsheetGrid title="Operating Margin Path">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Current EBIT margin" />
            <SpreadsheetCell type="calc" value={currentMargin} tooltip="Base-year operating margin = adjusted EBIT / LTM revenue. Uses R&D- and lease-adjusted EBIT." />
            <SpreadsheetCell type="label" value="→ Target margin" />
            <SpreadsheetCell type="hypothesis" value={assumptions.target_operating_margin} tooltip="Analyst input: target_operating_margin. The mature-state margin the firm converges to by year K." />
            <SpreadsheetCell type="label" value="→ Converge year" />
            <SpreadsheetCell type="hypothesis" value={assumptions.margin_convergence_year} tooltip="Analyst input: margin_convergence_year (K). Years 2..K interpolate linearly from year-1 margin to target; years K+1..10 flat at target." />
            <SpreadsheetCell type="label" value="→ Terminal EBIT" />
            <SpreadsheetCell type="calc" value={terminalEbit} tooltip="Terminal revenue × target margin — EBIT at the end of the projection window." />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Cost of Capital */}
      <SpreadsheetGrid title="Cost of Capital">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="Risk-free rate" />
            <SpreadsheetCell type="hypothesis" value={data.inputs.macro_inputs.risk_free_rate} tooltip="10Y treasury rate (analyst input on upload page). Anchor for WACC and terminal growth cap." />
            <SpreadsheetCell type="label" value="+ Beta × ERP" />
            <SpreadsheetCell type="reference" value={data.inputs.macro_inputs.equity_risk_premium} tooltip="Mature-market equity risk premium. Source: Damodaran annual update (ctryprem). Multiplied by levered beta to give equity risk premium component of Ke." />
            <SpreadsheetCell type="label" value="→ WACC" />
            <SpreadsheetCell type="calc" value={coc?.wacc ?? null} tooltip="WACC = Ke × E/V + Kd(1−t) × D/V. Source: cost_of_capital.wacc from Module 2." />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Value Bridge */}
      <SpreadsheetGrid title="Value Bridge">
        <tbody>
          <tr>
            <SpreadsheetCell type="label" value="PV(Cash Flows)" />
            <SpreadsheetCell type="calc" value={dcf?.pv_cash_flows_sum ?? null} tooltip="Σ PV(FCFF_t) for t=1..10. Source: dcf.pv_cash_flows_sum." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="+ PV(Terminal Value)" />
            <SpreadsheetCell type="calc" value={dcf?.pv_terminal_value ?? null} tooltip="Gordon-growth terminal value discounted to present. TV = FCFF_terminal / (WACC − g); PV = TV × CumDiscount_10. Source: dcf.pv_terminal_value." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="→ Operating Assets" bold />
            <SpreadsheetCell type="calc" value={dcf?.value_of_operating_assets ?? null} bold tooltip="PV of all future FCFF + PV of terminal value, adjusted for failure probability if set. Source: dcf.value_of_operating_assets." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="− Debt (MV)" />
            <SpreadsheetCell type="financial" value={coc?.mv_debt_total ?? fin?.bv_debt ?? null}
              tooltip="Market value of debt — includes PV of operating leases and the straight portion of convertible debt. Falls back to book debt if MV unavailable." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="− Minority interests" />
            <SpreadsheetCell type="financial" value={fin?.minority_interests ?? 0} tooltip="Base-year minority interests. Source: IQ_MINORITY_INTEREST × IQ_FY-0." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="+ Cash" />
            <SpreadsheetCell type="financial" value={fin?.cash_and_marketable_securities ?? null} tooltip="Base-year cash & marketable securities. Source: IQ_CASH_EQUIV × IQ_FY-0 (or LTM if rotated)." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="+ Cross-holdings" />
            <SpreadsheetCell type="financial" value={fin?.cross_holdings ?? 0} tooltip="Long-term investments in other firms. Source: IQ_LT_INVEST × IQ_FY-0." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="→ Value of Equity" bold />
            <SpreadsheetCell type="calc" value={dcf?.value_of_equity ?? null} bold
              tooltip="Value of equity = V_operating − MV debt − minority + cash + cross-holdings. Bridge rows above reconcile to this total (rounding may give ±1 unit)." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="- Options" />
            <SpreadsheetCell type="calc" value={final_?.value_of_all_options ?? 0} tooltip="Black-Scholes value of outstanding employee options (Module 6). Diluted out of equity value before per-share division." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="÷ Shares Outstanding" />
            <SpreadsheetCell type="financial" value={fin?.shares_outstanding ?? null} tooltip="Base-year shares outstanding. Source: IQ_TOTAL_OUTSTANDING_FILING_DATE (point-in-time, most recent filing)." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="→ Value per Share" bold />
            <SpreadsheetCell type="calc" value={final_?.value_per_share ?? null} bold tooltip="(Value of Equity − Options) / Shares Outstanding. Source: final.value_per_share." />
          </tr>
          <tr>
            <SpreadsheetCell type="label" value="Current Stock Price" />
            <SpreadsheetCell type="financial" value={fin?.stock_price ?? null} tooltip="Current stock price in listing currency. Source: IQ_CLOSEPRICE. Note: value per share above is in reporting currency — for P/V ratio, use stock_price_reporting (same currency as VPS)." />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
