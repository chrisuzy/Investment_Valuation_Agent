import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

export default function RDConverter({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const adj = data.inputs.adjustment_inputs;
  const adjusted = data.adjusted;

  const n = adj.amortization_period_n;
  const currentRD = adj.r_and_d_expense_current;
  const pastRD = adj.r_and_d_expense_past;

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
            <SpreadsheetCell value={currentRD} type="hypothesis" />
          </tr>
          {pastRD.map((expense, i) => (
            <tr key={i}>
              <SpreadsheetCell value={`t-${i + 1}`} type="label" />
              <SpreadsheetCell value={expense} type="hypothesis" />
            </tr>
          ))}
          <tr>
            <SpreadsheetCell value="Amortization Period (years)" type="label" bold />
            <SpreadsheetCell value={n} type="hypothesis" />
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
            <SpreadsheetCell value={currentRD} type="hypothesis" />
            <SpreadsheetCell value="1.00" type="calc" />
            <SpreadsheetCell value={currentRD} type="calc" />
            <SpreadsheetCell value={null} type="label" />
          </tr>
          {scheduleRows.map((row, i) => (
            <tr key={i}>
              <SpreadsheetCell value={row.label} type="label" />
              <SpreadsheetCell value={row.expense} type="hypothesis" />
              <SpreadsheetCell
                value={row.unamortizedFraction > 0 ? row.unamortizedFraction.toFixed(2) : '0.00'}
                type="calc"
              />
              <SpreadsheetCell value={row.unamortizedAmount} type="calc" />
              <SpreadsheetCell value={row.amortizationThisYear} type="calc" />
            </tr>
          ))}
          {/* Totals row */}
          <tr>
            <SpreadsheetCell value="Total" type="label" bold />
            <SpreadsheetCell value={null} type="label" />
            <SpreadsheetCell value={null} type="label" />
            <SpreadsheetCell value={totalUnamortized + currentRD} type="calc" bold />
            <SpreadsheetCell value={totalAmortization} type="calc" bold />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* Section 3: Summary */}
      <SpreadsheetGrid title="Section 3: Summary">
        <tbody>
          <tr>
            <SpreadsheetCell value="Value of Research Asset" type="label" bold width="280px" />
            <SpreadsheetCell value={adjusted?.value_of_research_asset} type="calc" width="200px" />
          </tr>
          <tr>
            <SpreadsheetCell value="Unamortized R&D" type="label" bold />
            <SpreadsheetCell value={adjusted?.unamortized_r_and_d} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Amortization of R&D" type="label" bold />
            <SpreadsheetCell value={adjusted?.amortization_r_and_d} type="calc" />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjusted EBIT" type="label" bold />
            <SpreadsheetCell value={adjusted?.adjusted_ebit} type="calc" />
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
