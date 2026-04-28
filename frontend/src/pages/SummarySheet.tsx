import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';

// Formatters
function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return (v * 100).toFixed(2) + '%';
}
function num(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
}
function dec(v: number | null | undefined, digits = 4): string {
  if (v === null || v === undefined) return '';
  return v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

// Get year label for column header
function yearLabel(t: number, baseYear: number): string {
  if (t === 0) return `FY${baseYear} (Base)`;
  if (t === 11) return 'Terminal';
  return `Year ${t}`;
}

export default function SummarySheet({ data }: { data: ValuationResponse; sessionId?: string | null }) {
  const inp = data.inputs;
  const dcf = data.dcf;
  const va = inp.valuation_assumptions;
  const macro = inp.macro_inputs;
  const coc = data.cost_of_capital;
  const fin0 = inp.raw_financials[0];

  if (!dcf) {
    return (
      <div className="max-w-[95vw] mx-auto p-4">
        <h1 className="text-xl font-bold mb-4">Summary Sheet</h1>
        <p className="text-gray-600">DCF not computed. Run a valuation first.</p>
      </div>
    );
  }

  const baseYear = fin0?.fiscal_year ?? 0;
  const n = dcf.revenue_projections.length;  // should be 10

  // Build year indices: 0 (base) + 1..n + terminal
  const years = [0];
  for (let i = 1; i <= n; i++) years.push(i);
  years.push(n + 1);  // terminal column

  // Compute derived paths (not in DCFResult but useful to display)
  // Growth %: year t growth = rev[t] / rev[t-1] - 1
  const rev = [fin0?.revenues ?? 0, ...dcf.revenue_projections];
  const growthPath: (number | null)[] = [null];  // base year has no growth
  for (let i = 1; i <= n; i++) {
    if (rev[i - 1] > 0) growthPath.push((rev[i] - rev[i - 1]) / rev[i - 1]);
    else growthPath.push(null);
  }

  // Margin %: ebit / revenue per year
  const ebit = [fin0?.ebit ?? 0, ...dcf.ebit_projections];
  const marginPath: (number | null)[] = [];
  for (let i = 0; i <= n; i++) {
    if (rev[i] > 0) marginPath.push(ebit[i] / rev[i]);
    else marginPath.push(null);
  }

  // NOPAT = EBIT(1-t). Approximate using discount_factors step to back out wacc_t → tax path unclear,
  // so compute FCFF + Reinvestment approach: NOPAT = FCFF + Reinvestment.
  const nopat: (number | null)[] = [null];  // base NOPAT not in DCFResult
  for (let i = 0; i < n; i++) {
    nopat.push(dcf.fcff_projections[i] + dcf.reinvestment_projections[i]);
  }

  // Effective tax per projected year = 1 - NOPAT/EBIT
  const taxPath: (number | null)[] = [null];  // base not applicable
  for (let i = 1; i <= n; i++) {
    const ebit_i = ebit[i];
    const nopat_i = nopat[i];
    if (ebit_i && ebit_i !== 0 && nopat_i !== null) {
      taxPath.push(1 - nopat_i / ebit_i);
    } else {
      taxPath.push(null);
    }
  }

  // WACC path inferred from discount factors: wacc_t = df[t-1]/df[t] - 1
  const waccPath: (number | null)[] = [null];  // base not applicable
  for (let i = 0; i < n; i++) {
    const df_prev = i === 0 ? 1 : dcf.discount_factors[i - 1];
    const df_t = dcf.discount_factors[i];
    if (df_t > 0 && df_prev > 0) {
      waccPath.push(df_prev / df_t - 1);
    } else {
      waccPath.push(null);
    }
  }

  // Terminal-year values (column n+1)
  // We don't have explicit terminal arrays in DCFResult, but we can derive key numbers
  // Terminal growth
  let g_terminal: number | null = null;
  if (va.override_growth_perpetuity && va.growth_perpetuity_rate != null) g_terminal = va.growth_perpetuity_rate;
  else if (va.override_riskfree && va.riskfree_after_yr10 != null) g_terminal = va.riskfree_after_yr10;
  else g_terminal = macro.risk_free_rate;

  // Terminal WACC
  let wacc_terminal: number | null = null;
  if (va.cost_of_capital_stable_override != null) wacc_terminal = va.cost_of_capital_stable_override;
  else if (va.override_riskfree && va.riskfree_after_yr10 != null) wacc_terminal = va.riskfree_after_yr10 + macro.equity_risk_premium;
  else wacc_terminal = macro.risk_free_rate + macro.equity_risk_premium;

  // Classify each year's color
  function yearCellType(t: number): 'financial' | 'calc' | 'reference' {
    if (t === 0) return 'financial';  // base (historical)
    if (t <= 5) return 'calc';        // high growth (green)
    if (t <= 10) return 'calc';       // transition (same color, shown in tooltip)
    return 'reference';               // terminal (purple)
  }

  // Column-width hint
  const COL_WIDTH = '90px';

  return (
    <div className="max-w-[95vw] mx-auto p-4">
      <h1 className="text-xl font-bold mb-1">Summary Sheet — Year-by-Year DCF</h1>
      <p className="text-sm text-gray-600 mb-4">
        Base year + 10-year explicit projection + terminal row. Columns color-coded:
        <span className="inline-block bg-blue-100 border border-blue-300 px-2 ml-2">Base</span>
        <span className="inline-block bg-green-100 border border-green-300 px-2 ml-1">High Growth (Yr 1-5)</span>
        <span className="inline-block bg-green-100 border border-green-300 px-2 ml-1">Transition (Yr 6-10)</span>
        <span className="inline-block bg-purple-100 border border-purple-300 px-2 ml-1">Terminal</span>
      </p>

      <SpreadsheetGrid title="Year-by-Year DCF Projection">
        <thead>
          <tr>
            <SpreadsheetCell value="Line Item" type="header" width="200px" />
            {years.map(t => (
              <SpreadsheetCell key={`h-${t}`} value={yearLabel(t, baseYear)} type="header" width={COL_WIDTH} />
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Revenue */}
          <tr>
            <SpreadsheetCell value="Revenue" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`rev-${t}`} value={num(fin0?.revenues)} type="financial" tooltip="FY0 actual (base year)" width={COL_WIDTH} />;
              if (t === n + 1) {
                const rev_term = rev[n] * (1 + (g_terminal ?? 0));
                return <SpreadsheetCell key={`rev-${t}`} value={num(rev_term)} type="reference" tooltip={`Terminal Revenue = Yr${n} Revenue × (1 + g_terminal) = ${num(rev[n])} × ${pct(g_terminal)}`} width={COL_WIDTH} />;
              }
              return <SpreadsheetCell key={`rev-${t}`} value={num(dcf.revenue_projections[t - 1])} type={yearCellType(t)} tooltip={`Revenue[Yr${t}] = Revenue[Yr${t - 1}] × (1 + growth_rate)`} width={COL_WIDTH} />;
            })}
          </tr>

          {/* Revenue Growth % */}
          <tr>
            <SpreadsheetCell value="  Revenue Growth %" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`g-${t}`} value="—" type="label" width={COL_WIDTH} />;
              if (t === n + 1) return <SpreadsheetCell key={`g-${t}`} value={pct(g_terminal)} type="reference" tooltip={`Terminal growth rate: ${va.override_growth_perpetuity ? 'override' : va.override_riskfree ? 'RF override' : 'risk-free rate'}`} width={COL_WIDTH} />;
              return <SpreadsheetCell key={`g-${t}`} value={pct(growthPath[t])} type={yearCellType(t)} tooltip={`growth_t = Revenue[Yr${t}]/Revenue[Yr${t - 1}] - 1`} width={COL_WIDTH} />;
            })}
          </tr>

          {/* Operating Margin % */}
          <tr>
            <SpreadsheetCell value="Operating Margin %" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`m-${t}`} value={pct(marginPath[0])} type="financial" tooltip="EBIT / Revenue (base year, adjusted for R&D if capitalized)" width={COL_WIDTH} />;
              if (t === n + 1) return <SpreadsheetCell key={`m-${t}`} value={pct(va.target_operating_margin ?? marginPath[n])} type="reference" tooltip="Terminal Op Margin = target_operating_margin (flat at maturity)" width={COL_WIDTH} />;
              return <SpreadsheetCell key={`m-${t}`} value={pct(marginPath[t])} type={yearCellType(t)} tooltip={t === 1 ? 'Year 1 = operating_margin_next_year' : `Margin[Yr${t}] = linear convergence to target by year ${va.margin_convergence_year}`} width={COL_WIDTH} />;
            })}
          </tr>

          {/* Operating Income (EBIT) */}
          <tr>
            <SpreadsheetCell value="Operating Income (EBIT)" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`ebit-${t}`} value={num(fin0?.ebit)} type="financial" width={COL_WIDTH} />;
              if (t === n + 1) {
                const rev_term = rev[n] * (1 + (g_terminal ?? 0));
                const ebit_term = rev_term * (va.target_operating_margin ?? marginPath[n] ?? 0);
                return <SpreadsheetCell key={`ebit-${t}`} value={num(ebit_term)} type="reference" tooltip="Terminal EBIT = Terminal Revenue × Target Margin" width={COL_WIDTH} />;
              }
              return <SpreadsheetCell key={`ebit-${t}`} value={num(dcf.ebit_projections[t - 1])} type={yearCellType(t)} tooltip="EBIT = Revenue × Margin (NOT compounded — rebuilt each year)" width={COL_WIDTH} />;
            })}
          </tr>

          {/* Tax Rate % */}
          <tr>
            <SpreadsheetCell value="  Tax Rate %" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`tx-${t}`} value={pct(macro.tax_rate_effective)} type="financial" tooltip="Effective tax rate (base year)" width={COL_WIDTH} />;
              if (t === n + 1) {
                const terminal_tax = va.override_tax_convergence ? macro.tax_rate_effective : macro.tax_rate_marginal;
                return <SpreadsheetCell key={`tx-${t}`} value={pct(terminal_tax)} type="reference" tooltip={va.override_tax_convergence ? 'Override: stay at effective' : 'Default: marginal'} width={COL_WIDTH} />;
              }
              return <SpreadsheetCell key={`tx-${t}`} value={pct(taxPath[t])} type={yearCellType(t)} tooltip={t <= 5 ? 'Years 1-5: effective' : 'Years 6-10: linear convergence to marginal'} width={COL_WIDTH} />;
            })}
          </tr>

          {/* After-tax Operating Income (NOPAT) */}
          <tr>
            <SpreadsheetCell value="NOPAT = EBIT × (1-t)" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`nopat-${t}`} value="—" type="label" width={COL_WIDTH} />;
              if (t === n + 1) {
                const rev_term = rev[n] * (1 + (g_terminal ?? 0));
                const terminal_tax = va.override_tax_convergence ? macro.tax_rate_effective : macro.tax_rate_marginal;
                const nopat_term = rev_term * (va.target_operating_margin ?? marginPath[n] ?? 0) * (1 - (terminal_tax ?? 0));
                return <SpreadsheetCell key={`nopat-${t}`} value={num(nopat_term)} type="reference" tooltip="NOPAT terminal = EBIT terminal × (1 - terminal tax)" width={COL_WIDTH} />;
              }
              return <SpreadsheetCell key={`nopat-${t}`} value={num(nopat[t])} type={yearCellType(t)} tooltip="NOPAT = FCFF + Reinvestment (NOL-adjusted in engine)" width={COL_WIDTH} />;
            })}
          </tr>

          {/* Reinvestment */}
          <tr>
            <SpreadsheetCell value="− Reinvestment" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`r-${t}`} value="—" type="label" width={COL_WIDTH} />;
              if (t === n + 1) {
                const rev_term = rev[n] * (1 + (g_terminal ?? 0));
                const terminal_tax = va.override_tax_convergence ? macro.tax_rate_effective : macro.tax_rate_marginal;
                const nopat_term = rev_term * (va.target_operating_margin ?? marginPath[n] ?? 0) * (1 - (terminal_tax ?? 0));
                const roic_term = va.roic_stable_override ?? (wacc_terminal ?? 0);
                const reinv_term = roic_term > 0 && (g_terminal ?? 0) > 0 ? ((g_terminal ?? 0) / roic_term) * nopat_term : 0;
                return <SpreadsheetCell key={`r-${t}`} value={num(reinv_term)} type="reference" tooltip="Terminal Reinvestment = (g_T / ROIC_T) × NOPAT_T" width={COL_WIDTH} />;
              }
              return <SpreadsheetCell key={`r-${t}`} value={num(dcf.reinvestment_projections[t - 1])} type={yearCellType(t)} tooltip="Reinvestment = ΔRevenue / Sales-to-Capital (with lag)" width={COL_WIDTH} />;
            })}
          </tr>

          {/* FCFF */}
          <tr>
            <SpreadsheetCell value="FCFF" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`f-${t}`} value="—" type="label" width={COL_WIDTH} />;
              if (t === n + 1) return <SpreadsheetCell key={`f-${t}`} value="TV formula" type="reference" tooltip={`Terminal FCFF used in Gordon: TV = FCFF_terminal / (WACC_T - g_T)\nTV = ${num(dcf.terminal_value_firm)}`} width={COL_WIDTH} />;
              return <SpreadsheetCell key={`f-${t}`} value={num(dcf.fcff_projections[t - 1])} type={yearCellType(t)} tooltip="FCFF = NOPAT - Reinvestment" width={COL_WIDTH} />;
            })}
          </tr>

          {/* WACC */}
          <tr>
            <SpreadsheetCell value="WACC" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`w-${t}`} value={pct(coc?.wacc)} type="financial" tooltip="Initial WACC" width={COL_WIDTH} />;
              if (t === n + 1) return <SpreadsheetCell key={`w-${t}`} value={pct(wacc_terminal)} type="reference" tooltip={va.cost_of_capital_stable_override != null ? 'override_cost_of_capital_stable' : 'Default: RF + ERP'} width={COL_WIDTH} />;
              return <SpreadsheetCell key={`w-${t}`} value={pct(waccPath[t])} type={yearCellType(t)} tooltip={t <= 5 ? 'Years 1-5: initial WACC (flat)' : 'Years 6-10: linear convergence to terminal'} width={COL_WIDTH} />;
            })}
          </tr>

          {/* Cumulative Discount Factor */}
          <tr>
            <SpreadsheetCell value="Cumulative DF" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`df-${t}`} value={dec(1, 4)} type="financial" tooltip="DF[0] = 1.0 by definition" width={COL_WIDTH} />;
              if (t === n + 1) return <SpreadsheetCell key={`df-${t}`} value={dec(dcf.discount_factors[n - 1], 4)} type="reference" tooltip="Terminal discounted at year-10 cumulative factor" width={COL_WIDTH} />;
              return <SpreadsheetCell key={`df-${t}`} value={dec(dcf.discount_factors[t - 1], 4)} type={yearCellType(t)} tooltip="Cumulative DF = Π 1/(1 + WACC_k), year-by-year product" width={COL_WIDTH} />;
            })}
          </tr>

          {/* PV of FCFF */}
          <tr>
            <SpreadsheetCell value="PV of FCFF" type="label" />
            {years.map(t => {
              if (t === 0) return <SpreadsheetCell key={`pv-${t}`} value="—" type="label" width={COL_WIDTH} />;
              if (t === n + 1) return <SpreadsheetCell key={`pv-${t}`} value={num(dcf.pv_terminal_value)} type="reference" tooltip="PV(Terminal Value) = TV × Cumulative DF[year 10]" width={COL_WIDTH} />;
              return <SpreadsheetCell key={`pv-${t}`} value={num(dcf.pv_fcff[t - 1])} type={yearCellType(t)} tooltip="PV = FCFF × Cumulative DF" width={COL_WIDTH} />;
            })}
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Aggregates */}
      <SpreadsheetGrid title="Value Rollup">
        <tbody>
          <tr>
            <SpreadsheetCell value="Σ PV of FCFF (Years 1-10)" type="label" width="320px" />
            <SpreadsheetCell value={num(dcf.pv_cash_flows_sum)} type="calc" tooltip="Sum of PV(FCFF) for years 1 through 10" />
          </tr>
          <tr>
            <SpreadsheetCell value="+ PV of Terminal Value" type="label" />
            <SpreadsheetCell value={num(dcf.pv_terminal_value)} type="calc" tooltip="Gordon perpetuity discounted to present" />
          </tr>
          <tr>
            <SpreadsheetCell value="= Value of Operating Assets" type="label" bold />
            <SpreadsheetCell value={num(dcf.value_of_operating_assets)} type="calc" bold tooltip={va.failure_probability > 0 ? `After failure overlay (p = ${pct(va.failure_probability)}, tie_to = ${va.failure_tie_to})` : 'No failure overlay'} />
          </tr>
          <tr>
            <SpreadsheetCell value="= Value of Equity (after bridge)" type="label" bold />
            <SpreadsheetCell value={num(dcf.value_of_equity)} type="calc" bold tooltip="V_op - Debt - Minority + Cash_usable + Cross_holdings" />
          </tr>
          <tr>
            <SpreadsheetCell value="Value per Share (pre-options)" type="label" bold />
            <SpreadsheetCell value={num(dcf.value_per_share_pre_options)} type="calc" bold />
          </tr>
          <tr>
            <SpreadsheetCell value="Value per Share (final)" type="label" bold />
            <SpreadsheetCell value={num(data.final?.value_per_share)} type="calc" bold tooltip="After subtracting option dilution" />
          </tr>
          <tr>
            <SpreadsheetCell value="Market Price" type="label" />
            <SpreadsheetCell value={num(fin0?.stock_price)} type="financial" />
          </tr>
          <tr>
            <SpreadsheetCell value="Price / Value" type="label" bold />
            <SpreadsheetCell value={(fin0?.stock_price && data.final?.value_per_share) ? pct(fin0.stock_price / data.final.value_per_share - 1) : '—'} type="calc" bold tooltip="Positive = market pays a premium to intrinsic; Negative = undervalued" />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
