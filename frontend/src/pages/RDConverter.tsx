import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { ciq, formula, backendField, user } from '../lib/sources';

export default function RDConverter({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const adj = data.inputs.adjustment_inputs;
  const adjusted = data.adjusted;
  const ticker = data.inputs.ticker;

  const n = adj.amortization_period_n;
  const currentRD = adj.r_and_d_expense_current;
  // Truncate to the amortization window. Entries older than N contribute zero
  // to both unamortized-balance and current-year amortization, so rendering
  // them is visual noise. Matches the Input Sheet which iterates exactly N
  // rows via Array.from({ length: amortization_period_n }).
  const pastRD = adj.r_and_d_expense_past.slice(0, n);

  // Build amortization schedule rows.
  // For each past year i (0-indexed, where i=0 is t-1, i=1 is t-2, ...):
  //   - Unamortized portion = (n - i - 1) / n  (straight-line, 1/n amortized per year)
  //   - Amortization this year = expense / n
  const scheduleRows = pastRD.map((expense, i) => {
    const yearsSinceSpend = i + 1;
    const unamortizedFraction = Math.max(0, (n - yearsSinceSpend) / n);
    const unamortizedAmount = expense * unamortizedFraction;
    const amortizationThisYear = yearsSinceSpend <= n ? expense / n : 0;
    return {
      label: `t-${yearsSinceSpend}`,
      expense,
      unamortizedFraction,
      unamortizedAmount,
      amortizationThisYear,
    };
  });

  // Totals for the schedule
  const totalUnamortized = scheduleRows.reduce((sum, r) => sum + r.unamortizedAmount, 0);
  const totalAmortization = scheduleRows.reduce((sum, r) => sum + r.amortizationThisYear, 0);

  return (
    <div className="max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">R&D Converter</h1>
      <p className="text-sm text-gray-500">
        Converts R&D expenses from an operating expense to a capital asset using
        Damodaran's straight-line amortization approach.
      </p>

      <ColorLegend />

      {/* Section 1: R&D Expenses */}
      <SpreadsheetGrid title="Section 1: R&D Expenses">
        <thead>
          <tr>
            <SpreadsheetCell value="Year" type="header" width="160px" />
            <SpreadsheetCell value="R&D Expense" type="header" width="200px" />
          </tr>
        </thead>
        <tbody>
          <tr>
            <SpreadsheetCell value="Current Year" type="label" />
            <SpreadsheetCell value={currentRD} type="hypothesis"
              tooltip={ciq(ticker, "IQ_RD_EXP", "LTM") + " — sourced from LTM rotation (Module 1 passthrough from ltm.r_and_d_expense)"} />
          </tr>
          {pastRD.map((expense, i) => (
            <tr key={i}>
              <SpreadsheetCell value={`t-${i + 1}`} type="label" />
              <SpreadsheetCell value={expense} type="hypothesis"
                tooltip={ciq(ticker, "IQ_RD_EXP", `IQ_FY-${i + 1}`)} />
            </tr>
          ))}
          <tr>
            <SpreadsheetCell value="Amortization Period (years)" type="label" bold />
            <SpreadsheetCell value={n} type="hypothesis"
              tooltip={user('R&D amortization period N', 'Damodaran industry default: Pharma/Biotech/Aerospace = 10y; Online Retail / Internet Software = 3y; all others = 5y.')} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Section 2: Amortization Schedule */}
      <SpreadsheetGrid title="Section 2: Amortization Schedule">
        <thead>
          <tr>
            <SpreadsheetCell value="Year" type="header" width="100px" />
            <SpreadsheetCell value="R&D Expense" type="header" width="160px" />
            <SpreadsheetCell value="Unamortized %" type="header" width="140px" />
            <SpreadsheetCell value="Unamortized Amount" type="header" width="180px" />
            <SpreadsheetCell value="Amortization This Year" type="header" width="180px" />
          </tr>
        </thead>
        <tbody>
          <tr>
            <SpreadsheetCell value="Current" type="label" />
            <SpreadsheetCell value={currentRD} type="hypothesis"
              tooltip={ciq(ticker, "IQ_RD_EXP", "LTM")} />
            <SpreadsheetCell value="1.00" type="calc"
              tooltip="Current-year R&D: 100% unamortized (no years have passed since spend)" />
            <SpreadsheetCell value={currentRD} type="calc"
              tooltip={formula("Unamortized = expense × fraction", `${currentRD.toLocaleString()} × 1.00`)} />
            <SpreadsheetCell value={null} type="label" />
          </tr>
          {scheduleRows.map((row, i) => (
            <tr key={i}>
              <SpreadsheetCell value={row.label} type="label" />
              <SpreadsheetCell value={row.expense} type="hypothesis"
                tooltip={ciq(ticker, "IQ_RD_EXP", `IQ_FY-${i + 1}`)} />
              <SpreadsheetCell
                value={row.unamortizedFraction > 0 ? row.unamortizedFraction.toFixed(2) : '0.00'}
                type="calc"
                tooltip={formula("Unamortized fraction = max(0, (N − t) / N)",
                                 `(${n} − ${i + 1}) / ${n} = ${row.unamortizedFraction.toFixed(4)}`)} />
              <SpreadsheetCell value={row.unamortizedAmount} type="calc"
                tooltip={formula("= expense × fraction",
                                 `${row.expense.toLocaleString()} × ${row.unamortizedFraction.toFixed(2)} = ${row.unamortizedAmount.toLocaleString(undefined,{maximumFractionDigits:0})}`)} />
              <SpreadsheetCell value={row.amortizationThisYear} type="calc"
                tooltip={formula("Straight-line annual amortization = expense / N",
                                 row.amortizationThisYear > 0 ? `${row.expense.toLocaleString()} / ${n} = ${row.amortizationThisYear.toLocaleString(undefined,{maximumFractionDigits:0})}` : `Year ${i+1} > N=${n}, fully amortized`)} />
            </tr>
          ))}
          {/* Totals row */}
          <tr>
            <SpreadsheetCell value="Total" type="label" bold />
            <SpreadsheetCell value={null} type="label" />
            <SpreadsheetCell value={null} type="label" />
            <SpreadsheetCell value={totalUnamortized + currentRD} type="calc" bold
              tooltip={formula("Research asset = current R&D + Σ unamortized past R&D",
                               "This is the capitalized value added to Invested Capital for ROIC calc")} />
            <SpreadsheetCell value={totalAmortization} type="calc" bold
              tooltip="Σ annual amortization across past years within the N-year window" />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Section 3: Summary */}
      <SpreadsheetGrid title="Section 3: Summary">
        <tbody>
          <tr>
            <SpreadsheetCell value="Value of Research Asset" type="label" bold width="280px" />
            <SpreadsheetCell value={adjusted?.value_of_research_asset} type="calc" width="200px"
              tooltip={backendField("adjusted.value_of_research_asset", "Current R&D + Σ unamortized past R&D. Added to Invested Capital.")} />
          </tr>
          <tr>
            <SpreadsheetCell value="Unamortized R&D" type="label" bold />
            <SpreadsheetCell value={adjusted?.unamortized_r_and_d} type="calc"
              tooltip={backendField("adjusted.unamortized_r_and_d", "Σ past R&D × (N−t)/N. Capital-asset component.")} />
          </tr>
          <tr>
            <SpreadsheetCell value="Amortization of R&D" type="label" bold />
            <SpreadsheetCell value={adjusted?.amortization_r_and_d} type="calc"
              tooltip={backendField("adjusted.amortization_r_and_d", "Σ past R&D / N. Becomes D&A expense.")} />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjusted EBIT" type="label" bold />
            <SpreadsheetCell value={adjusted?.adjusted_ebit} type="calc"
              tooltip={formula("Adjusted EBIT = Raw EBIT + R&D current − Amortization + Lease adj",
                               "Recognizes R&D as capex. Positive adjustment when current R&D > amortization (growing R&D firms).")} />
          </tr>
          <tr>
            <SpreadsheetCell
              value="Tax effect: EBIT adjustment is pre-tax. Apply marginal tax rate to compute after-tax impact on net income."
              type="hint"
              colSpan={2}
              align="left"
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
