import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { ciq, formula, damodaran, backendField } from '../lib/sources';

export default function LeaseConverter({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const adj = data.inputs.adjustment_inputs;
  const industry = data.inputs.industry_data;
  const adjusted = data.adjusted;
  const ticker = data.inputs.ticker;

  const commitments = adj.operating_lease_commitments; // index 0-4 = Year 1-5, index 5 = Beyond
  const costOfDebt = industry.cost_of_debt_pretax;
  const leaseExpense = adj.operating_lease_expense_current;

  // Compute n_additional using Damodaran method: round(beyond / avg(yr1..yr5))
  const yr1to5 = commitments.slice(0, 5);
  const avgYr1to5 = yr1to5.length > 0 ? yr1to5.reduce((a, b) => a + b, 0) / yr1to5.length : 0;
  const beyond = commitments.length > 5 ? commitments[5] : 0;
  const nAdditional = avgYr1to5 > 0 && beyond > 0 ? Math.max(1, Math.round(beyond / avgYr1to5)) : (beyond > 0 ? 1 : 0);
  const totalLeaseYears = Math.min(commitments.length, 5) + nAdditional;

  // Build PV rows for years 1-5 + annuity years
  const pvRows: { label: string; commitment: number; pv: number }[] = [];
  if (costOfDebt !== null && costOfDebt !== undefined && costOfDebt !== 0) {
    for (let i = 0; i < Math.min(commitments.length, 5); i++) {
      const c = commitments[i];
      const pv = c / Math.pow(1 + costOfDebt, i + 1);
      pvRows.push({ label: `Year ${i + 1}`, commitment: c, pv });
    }

    // Beyond year 5: annuity spread across nAdditional years
    if (nAdditional > 0 && beyond > 0) {
      const annualAmount = beyond / nAdditional;
      let beyondPV = 0;
      for (let j = 0; j < nAdditional; j++) {
        beyondPV += annualAmount / Math.pow(1 + costOfDebt, 6 + j);
      }
      pvRows.push({
        label: `6 - ${5 + nAdditional}`,
        commitment: annualAmount,
        pv: beyondPV,
      });
    }
  }

  const totalPV = pvRows.reduce((sum, r) => sum + r.pv, 0);
  const debtValue = adjusted?.pv_of_operating_leases ?? totalPV;
  const depreciation = totalLeaseYears > 0 ? debtValue / totalLeaseYears : 0;
  const ebitAdj = leaseExpense - depreciation;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 space-y-4">
      <h2 className="text-lg font-bold text-gray-800 mb-4">Operating Lease Converter</h2>
      <ColorLegend />

      {/* ===== Section 1: Inputs ===== */}
      <SpreadsheetGrid title="Operating Lease Inputs">
        <thead>
          <tr>
            <SpreadsheetCell value="" type="header" width="280px" />
            <SpreadsheetCell value="" type="header" />
          </tr>
        </thead>
        <tbody>
          <tr>
            <SpreadsheetCell value="Operating lease expense (current year)" type="label" />
            <SpreadsheetCell value={leaseExpense} type="hypothesis"
              tooltip={ciq(ticker, "IQ_OPERATING_LEASE_PAYMENTS", "IQ_FY-0")} />
          </tr>
          {yr1to5.map((c, i) => (
            <tr key={i}>
              <SpreadsheetCell value={`Year ${i + 1} commitment`} type="label" />
              <SpreadsheetCell value={c} type="hypothesis"
                tooltip={ciq(ticker, `IQ_OL_COMM_YR_${i + 1}`) + " — footnote to 10-K contractual commitments"} />
            </tr>
          ))}
          {commitments.length > 5 && (
            <tr>
              <SpreadsheetCell value="Year 6 and beyond commitment" type="label" />
              <SpreadsheetCell value={beyond} type="hypothesis"
                tooltip={ciq(ticker, "IQ_OL_COMM_BEYOND")} />
            </tr>
          )}
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Section 2: Parameters ===== */}
      <SpreadsheetGrid title="Lease Conversion Parameters">
        <tbody>
          <tr>
            <SpreadsheetCell value="Pre-tax cost of debt" type="label" width="280px" />
            <SpreadsheetCell value={costOfDebt} type="reference"
              tooltip={damodaran("wacc.xls", "Cost of Debt (pre-tax)", industry.industry_name)} />
          </tr>
          <tr>
            <SpreadsheetCell value="Number of years embedded in yr 6 estimate" type="label" />
            <SpreadsheetCell value={adjusted?.lease_n_additional_years ?? nAdditional} type="calc"
              tooltip={formula("n_additional = round(beyond / avg(yr1..yr5))",
                               `round(${beyond.toLocaleString()} / ${avgYr1to5.toLocaleString(undefined,{maximumFractionDigits:0})}) = ${nAdditional}`)} />
          </tr>
          <tr>
            <SpreadsheetCell value="" type="label" />
            <SpreadsheetCell
              value="= round(beyond / avg(yr1..yr5))"
              type="label"
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Section 3: Converting Operating Leases into Debt ===== */}
      <SpreadsheetGrid title="Converting Operating Leases into Debt">
        <thead>
          <tr>
            <SpreadsheetCell value="Year" type="header" width="160px" />
            <SpreadsheetCell value="Commitment" type="header" />
            <SpreadsheetCell value="Present Value" type="header" />
          </tr>
        </thead>
        <tbody>
          {pvRows.map((row, i) => (
            <tr key={i}>
              <SpreadsheetCell value={row.label} type="label" />
              <SpreadsheetCell value={row.commitment} type="calc"
                tooltip={i < 5 ? `Commitment from 10-K footnote (CIQ IQ_OL_COMM_YR_${i+1})`
                                : `Beyond-yr-5 commitment spread evenly over ${nAdditional} years: ${beyond.toLocaleString(undefined,{maximumFractionDigits:0})} / ${nAdditional}`} />
              <SpreadsheetCell value={row.pv} type="calc"
                tooltip={i < 5
                  ? formula(`PV = C / (1 + Kd)^t`,
                            `${row.commitment.toLocaleString(undefined,{maximumFractionDigits:0})} / (1 + ${(costOfDebt||0)*100}%)^${i+1}`)
                  : formula(`PV = Σ annual / (1 + Kd)^t for t = 6..${5+nAdditional}`,
                            `Annuity of ${row.commitment.toLocaleString(undefined,{maximumFractionDigits:0})} discounted from yr 6 onward`)} />
            </tr>
          ))}
          <tr>
            <SpreadsheetCell value="Debt Value of leases" type="label" bold />
            <SpreadsheetCell value="" type="label" />
            <SpreadsheetCell value={debtValue} type="calc" bold
              tooltip={backendField("adjusted.pv_of_operating_leases", "Σ of all PV rows above. Added to total debt.")} />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ===== Section 4: Restated Financials ===== */}
      <SpreadsheetGrid title="Effect on Financial Statements">
        <tbody>
          <tr>
            <SpreadsheetCell value="Depreciation on lease asset" type="label" width="280px" />
            <SpreadsheetCell
              value={adjusted?.depreciation_on_lease_asset ?? depreciation}
              type="calc"
              tooltip={formula("Depreciation = PV / total years",
                               `${debtValue.toLocaleString(undefined,{maximumFractionDigits:0})} / ${adjusted?.lease_years_total ?? totalLeaseYears} = ${(adjusted?.depreciation_on_lease_asset ?? depreciation).toLocaleString(undefined,{maximumFractionDigits:0})}`)}
            />
            <SpreadsheetCell value={`= PV / ${adjusted?.lease_years_total ?? totalLeaseYears} years`} type="label" />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjustment to Operating Earnings" type="label" />
            <SpreadsheetCell
              value={adjusted?.lease_adjustment_to_ebit ?? ebitAdj}
              type="calc"
              tooltip={formula("EBIT adj = Lease expense − Lease depreciation",
                               "Positive = add to EBIT. Treating leases as debt removes the rent from opex but adds depreciation of the capitalized asset.")}
            />
            <SpreadsheetCell value="= Lease expense − Depreciation" type="label" />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjustment to Total Debt" type="label" />
            <SpreadsheetCell value={debtValue} type="calc"
              tooltip="Same as Debt Value of leases above — added to book debt in Module 1 → feeds WACC D/E." />
            <SpreadsheetCell value="= PV of leases" type="label" />
          </tr>
          <tr>
            <SpreadsheetCell value="Adjustment to Depreciation" type="label" />
            <SpreadsheetCell
              value={adjusted?.depreciation_on_lease_asset ?? depreciation}
              type="calc"
              tooltip="Same lease depreciation — added to D&A in Module 3 for cash flow (non-cash add-back)"
            />
            <SpreadsheetCell value="" type="label" />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
