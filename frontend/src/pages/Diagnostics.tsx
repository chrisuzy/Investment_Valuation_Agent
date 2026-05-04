import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { baseYear, priorYear, baseYearMargin } from '../lib/baseYear';

export default function Diagnostics({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const by = baseYear(data);
  const py = priorYear(data);
  const assumptions = data.inputs.valuation_assumptions;
  const industry = data.inputs.industry_data;
  const macro = data.inputs.macro_inputs;
  const dcf = data.dcf;

  // ---------- Step 1 helpers ----------
  const recentRevenueGrowth =
    by && py && by.revenues && py.revenues
      ? (by.revenues - py.revenues) / Math.abs(py.revenues)
      : null;

  // ---------- Step 2 helpers ----------
  const baseRevenue = by?.revenues ?? null;
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
  // Adjusted margin — matches Damodaran's convention and what the engine
  // uses as the base-year margin in M4. Using raw EBIT here made the
  // "current margin" appear discontinuous with Yr1 projected margin.
  const currentMargin = baseYearMargin(data);

  // ---------- Step 6 helpers ----------
  // FX-aware price/value: convert market price to reporting currency
  // before dividing. Skips the comparison if currencies differ and
  // no FX rate is available.
  const valuePerShare = data.final?.value_per_share ?? null;
  const stockPriceListing = by?.stock_price ?? null;
  const listingCcy = data.inputs.stock_price_currency;
  const reportingCcy = data.inputs.reporting_currency;
  const fxRate = data.inputs.fx_rate;
  const sameCcy = listingCcy && reportingCcy && listingCcy === reportingCcy;
  const stockPriceInReporting =
    stockPriceListing != null && (sameCcy ? stockPriceListing : fxRate != null ? stockPriceListing * fxRate : null);
  const priceAsPctOfValue =
    valuePerShare && valuePerShare !== 0 && stockPriceInReporting != null
      ? stockPriceInReporting / valuePerShare
      : null;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 space-y-4">
      <h2 className="text-lg font-bold text-gray-800 mb-4">Diagnostics</h2>
      <ColorLegend />

      {/* ===== Step 1: Revenue Growth ===== */}
      <SpreadsheetGrid title="Step 1: Revenue Growth">
        <tbody>
          <tr>
            <SpreadsheetCell value="Industry avg revenue growth" type="label" width="280px" />
            <SpreadsheetCell value="N/A" type="reference" tooltip="Reserved for industry-growth benchmark. See Input Sheet §7 or Stories to Numbers Growth block for the industry median + Q1/Q3 range." />
          </tr>
          <tr>
            <SpreadsheetCell value="Most recent revenue growth" type="label" />
            <SpreadsheetCell value={recentRevenueGrowth} type="calc" tooltip="= (FY-0 Revenue − FY-1 Revenue) / FY-1 Revenue. Source: IQ_TOTAL_REV × IQ_FY-0 and IQ_FY-1." />
          </tr>
          <tr>
            <SpreadsheetCell value="Your forecast — Year 1 growth" type="label" />
            <SpreadsheetCell value={assumptions.revenue_growth_next_year} type="hypothesis" tooltip="Analyst input: valuation_assumptions.revenue_growth_next_year." />
          </tr>
          <tr>
            <SpreadsheetCell value="Your forecast — Years 2-5 growth" type="label" />
            <SpreadsheetCell value={assumptions.revenue_growth_years_2_5} type="hypothesis" tooltip="Analyst input: valuation_assumptions.revenue_growth_years_2_5. Single flat rate applied across years 2–5." />
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
            <SpreadsheetCell value={baseRevenue} type="financial" tooltip="LTM revenue. Source: rotated from IQ_TOTAL_REV × IQ_FY-0 with quarterly deltas (Module 0 / LTM calculator)." />
          </tr>
          {dcf && (
            <>
              <tr>
                <SpreadsheetCell value="Year 1 revenues" type="label" />
                <SpreadsheetCell value={revYear1} type="calc" tooltip="Projected year-1 revenue from the DCF engine: dcf.revenue_projections[0]. = Base × (1 + revenue_growth_next_year)." />
              </tr>
              <tr>
                <SpreadsheetCell value="Year 5 revenues" type="label" />
                <SpreadsheetCell value={revYear5} type="calc" tooltip="Projected year-5 revenue: dcf.revenue_projections[4]. Compounds year-1 growth with years 2–5 growth." />
              </tr>
              <tr>
                <SpreadsheetCell value="Year 10 revenues" type="label" />
                <SpreadsheetCell value={revYear10} type="calc" tooltip="Projected year-10 revenue: dcf.revenue_projections[9]. Years 6–10 converge linearly from years 2–5 growth to terminal growth (risk-free by default)." />
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
            <SpreadsheetCell value={currentMargin} type="calc" tooltip="= Adjusted EBIT / LTM Revenue. Adjusted EBIT includes R&D add-back + lease add-back from Module 1." />
          </tr>
          <tr>
            <SpreadsheetCell value="Target operating margin" type="label" />
            <SpreadsheetCell value={assumptions.target_operating_margin} type="hypothesis" tooltip="Analyst input: valuation_assumptions.target_operating_margin. The mature-state margin the firm converges to." />
          </tr>
          <tr>
            <SpreadsheetCell value="Industry pretax margin" type="label" />
            <SpreadsheetCell value={industry.pretax_operating_margin} type="reference" tooltip={`Damodaran industry median pre-tax operating margin. Industry: ${industry.industry_name} (${industry.region}). Source: margin${industry.region === 'Global' ? 'Global' : ''}.xls.`} />
          </tr>
          <tr>
            <SpreadsheetCell value="Year of convergence" type="label" />
            <SpreadsheetCell value={assumptions.margin_convergence_year} type="hypothesis" tooltip="Analyst input: valuation_assumptions.margin_convergence_year (K). Years 2..K interpolate linearly from current margin to target; years K+1..10 flat at target." />
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
            <SpreadsheetCell value={assumptions.sales_to_capital_high} type="calc" tooltip="Analyst input: valuation_assumptions.sales_to_capital_high. Used in reinvestment = ΔRevenue / S/C for years 1–5." />
          </tr>
          <tr>
            <SpreadsheetCell value="Sales/capital years 6-10" type="label" />
            <SpreadsheetCell value={assumptions.sales_to_capital_stable} type="calc" tooltip="Analyst input: valuation_assumptions.sales_to_capital_stable. Used for years 6–10 during convergence to the stable state." />
          </tr>
          <tr>
            <SpreadsheetCell value="Industry sales/capital" type="label" />
            <SpreadsheetCell value={industry.sales_to_capital} type="reference" tooltip={`Damodaran industry median Sales/Capital. Industry: ${industry.industry_name}. Source: capex${industry.region === 'Global' ? 'Global' : ''}.xls.`} />
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
            <SpreadsheetCell value={data.cost_of_capital?.wacc ?? null} type="calc" tooltip="Source: cost_of_capital.wacc from Module 2. WACC = Ke × E/V + Kd(1−t) × D/V." />
          </tr>
          <tr>
            <SpreadsheetCell value="Industry WACC" type="label" />
            <SpreadsheetCell value={industry.wacc} type="reference" tooltip={`Damodaran industry median WACC for ${industry.industry_name}. Source: wacc${industry.region === 'Global' ? 'Global' : ''}.xls.`} />
          </tr>
          <tr>
            <SpreadsheetCell value="Risk-free rate" type="label" />
            <SpreadsheetCell value={macro.risk_free_rate} type="hypothesis" tooltip="Analyst input (set on upload): macro_inputs.risk_free_rate. 10Y treasury rate." />
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
            <SpreadsheetCell value={valuePerShare} type="calc" tooltip="Intrinsic value per share in reporting currency. Source: final.value_per_share. = (Value of Equity − Options) / Shares." />
          </tr>
          <tr>
            <SpreadsheetCell value={`Stock price (${listingCcy ?? '—'}, listing ccy)`} type="label" />
            <SpreadsheetCell value={stockPriceListing} type="financial"
              tooltip={fxRate != null && !sameCcy && stockPriceInReporting != null
                ? `≈ ${stockPriceInReporting.toFixed(2)} ${reportingCcy} at FX ${fxRate.toFixed(4)}`
                : undefined}
            />
          </tr>
          <tr>
            <SpreadsheetCell value="Price as % of value (same currency)" type="label" />
            <SpreadsheetCell value={priceAsPctOfValue} type="calc"
              tooltip={`Market price converted to ${reportingCcy ?? 'reporting ccy'} and divided by VPS, so both sides are in the same currency.`}
            />
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
