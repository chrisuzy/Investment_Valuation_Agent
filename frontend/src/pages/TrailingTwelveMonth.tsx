import type { ValuationResponse, RawFinancials } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return (v * 100).toFixed(2) + '%';
}

function num(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function fmtDate(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (!isNaN(n) && n > 30000 && n < 60000) {
    const d = new Date(Date.UTC(1899, 11, 30 + Math.round(n)));
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
  }
  const d = new Date(String(v));
  if (!isNaN(d.getTime())) return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  return String(v);
}

// Flow items for LTM calculation
const FLOW_ITEMS: [string, keyof RawFinancials][] = [
  ['Revenues', 'revenues'],
  ['EBIT (Operating Income)', 'ebit'],
  ['EBITDA', 'ebitda'],
  ['Net Income', 'net_income'],
  ['Earnings Before Tax', 'earnings_before_tax'],
  ['Tax Expense', 'total_tax_expense'],
  ['Interest Expense', 'interest_expense'],
  ['D&A', 'd_a'],
  ['R&D Expense', 'r_and_d_expense'],
  ['Capital Expenditures', 'capex'],
];

// Balance sheet items (point-in-time)
const BS_ITEMS: [string, keyof RawFinancials][] = [
  ['Cash & Marketable Securities', 'cash_and_marketable_securities'],
  ['Cross Holdings', 'cross_holdings'],
  ['Minority Interests', 'minority_interests'],
  ['Book Value of Equity', 'bv_equity'],
  ['Book Value of Debt', 'bv_debt'],
  ['Shares Outstanding', 'shares_outstanding'],
];

// CIQ mnemonics for tooltips
const CIQ_MNEMONICS: Record<string, string> = {
  revenues: 'IQ_TOTAL_REV', ebit: 'IQ_EBIT', ebitda: 'IQ_EBITDA',
  net_income: 'IQ_NI', interest_expense: 'IQ_INTEREST_EXP', d_a: 'IQ_DA_CF',
  capex: 'IQ_CAPEX', r_and_d_expense: 'IQ_RD_EXP',
  earnings_before_tax: 'IQ_EBT_EXCL', total_tax_expense: 'IQ_INC_TAX',
  cash_and_marketable_securities: 'IQ_CASH_EQUIV', bv_equity: 'IQ_TOTAL_EQUITY',
  bv_debt: 'IQ_TOTAL_DEBT', cross_holdings: 'IQ_LT_INVEST',
  minority_interests: 'IQ_MINORITY_INTEREST',
  shares_outstanding: 'IQ_TOTAL_OUTSTANDING_FILING_DATE',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TrailingTwelveMonth({ data }: { data: ValuationResponse; sessionId?: string | null }) {
  const inp = data.inputs;
  const fin0 = inp.raw_financials[0];
  const qFins = inp.quarterly_financials ?? [];
  const n = inp.quarters_since_10k ?? 0;
  const ticker = inp.ticker;
  // Authoritative LTM — computed by backend (engine/ltm_calculator.py) per Ginzu formula.
  // Frontend does NOT recompute; it only displays the component breakdown for audit transparency.
  const ltmBackend = data.ltm_financials;

  function qVal(qIdx: number, key: keyof RawFinancials): number | null {
    if (qIdx >= qFins.length) return null;
    const v = qFins[qIdx]?.[key];
    return typeof v === 'number' ? v : null;
  }

  // Is quarterly data sufficient to actually rotate? Mirrors backend's guard.
  const sufficient = n === 0 || qFins.length >= n + 4;

  // Displays the derivation components (FY0 + Σnew − Σold) for transparency — NOT the final LTM value.
  // Final LTM comes from ltmBackend. If backend had to fall back to FY0 (insufficient data), new/old = 0.
  function ltmBreakdown(key: keyof RawFinancials) {
    const fy0 = typeof fin0?.[key] === 'number' ? (fin0[key] as number) : 0;
    const ltm = ltmBackend ? (ltmBackend[key] as number | null) ?? fy0 : fy0;
    if (n === 0 || !sufficient) return { fy0, newSum: 0, oldSum: 0, ltm };
    let newSum = 0, oldSum = 0;
    for (let i = 0; i < n; i++) {
      newSum += qVal(i, key) ?? 0;
      oldSum += qVal(i + 4, key) ?? 0;
    }
    return { fy0, newSum, oldSum, ltm };
  }

  // Balance sheet: backend-authoritative (from ltm_financials which holds FQ-0 snapshot when available).
  function bsValue(key: keyof RawFinancials) {
    const backendV = ltmBackend ? (ltmBackend[key] as number | null) : null;
    const qv = qVal(0, key);
    // source label: if FQ-0 had the value, backend uses it (10-Q); else backend kept FY0 (10-K)
    if (qv !== null) return { value: backendV ?? qv, source: '10-Q' as const };
    const fv = fin0 ? (fin0[key] as number | null) : null;
    return { value: backendV ?? fv, source: '10-K' as const };
  }

  const maxQ = Math.min(8, qFins.length);

  return (
    <div className="max-w-[95vw] mx-auto p-4">
      <h2 className="text-xl font-bold mb-2">Trailing 12 Month (LTM) Worksheet</h2>
      <p className="text-xs text-gray-500 mb-2">
        Ginzu formula: LTM = FY0 (annual 10-K) + new quarters since 10-K − same quarters from prior year.
        LTM values below are computed in the backend (<code className="bg-gray-100 px-1">engine/ltm_calculator.py</code>).
        The FY0 / +New / −Old breakdown is shown for audit transparency.
      </p>
      {!sufficient && n > 0 && (
        <div className="mb-4 p-3 rounded bg-amber-50 border border-amber-300 text-sm">
          <strong>⚠ Insufficient quarterly data for LTM rotation:</strong>{' '}
          K = {n}, but only {qFins.length} quarter{qFins.length === 1 ? '' : 's'} available
          (Ginzu formula needs K + 4 = {n + 4}). Backend fell back to FY-0 values for flow items;
          LTM shown below equals FY-0 until a fuller template is uploaded.
        </div>
      )}

      {/* ── Section A: Period Information ── */}
      <SpreadsheetGrid title="A. Period Information">
        <tbody>
          <tr><SpreadsheetCell value="Latest 10-K Period" type="label" width="220px" /><SpreadsheetCell value={fmtDate(inp.period_date_10k)} type="financial" /></tr>
          <tr><SpreadsheetCell value="Latest 10-Q Period" type="label" /><SpreadsheetCell value={fmtDate(inp.period_date_10q)} type="financial" /></tr>
          <tr>
            <SpreadsheetCell value="Quarters Since 10-K (n)" type="label" />
            <SpreadsheetCell value={String(n)} type="calc" tooltip="= months between 10-Q and 10-K / 3" />
          </tr>
          <tr>
            <SpreadsheetCell value="LTM Formula" type="label" />
            <td className="border px-2 py-1 bg-gray-50 text-xs font-mono">
              {n === 0
                ? 'LTM = FY0 (no new quarters since 10-K)'
                : `LTM = FY0 + (${Array.from({length: n}, (_, i) => `FQ-${i}`).join(' + ')}) - (${Array.from({length: n}, (_, i) => `FQ-${i+4}`).join(' + ')})`
              }
            </td>
          </tr>
          {n > 0 && (<>
            <tr>
              <SpreadsheetCell value="New quarters (added)" type="label" />
              <td className="border px-2 py-1 bg-green-50 text-xs font-medium text-green-800">
                {Array.from({length: n}, (_, i) => `FQ-${i}`).join(', ')} (most recent {n} quarter{n > 1 ? 's' : ''})
              </td>
            </tr>
            <tr>
              <SpreadsheetCell value="Old quarters (subtracted)" type="label" />
              <td className="border px-2 py-1 bg-red-50 text-xs font-medium text-red-800">
                {Array.from({length: n}, (_, i) => `FQ-${i+4}`).join(', ')} (same quarter{n > 1 ? 's' : ''}, one year earlier)
              </td>
            </tr>
          </>)}
        </tbody>
      </SpreadsheetGrid>

      {/* ── Section B: Quarterly Detail (all 8 quarters) ── */}
      {maxQ > 0 && (
        <SpreadsheetGrid title="B. Quarterly Data">
          <thead>
            <tr>
              <SpreadsheetCell value="Item" type="header" width="180px" />
              {Array.from({length: maxQ}, (_, i) => {
                const isNew = i < n;
                const isOld = i >= 4 && i < 4 + n;
                const bg = isNew ? 'bg-green-100' : isOld ? 'bg-red-100' : 'bg-gray-50';
                const label = isNew ? `FQ-${i} (+)` : isOld ? `FQ-${i} (-)` : `FQ-${i}`;
                return <th key={`qh-${i}`} className={`border px-1.5 py-0.5 text-xs font-bold text-center whitespace-nowrap ${bg}`}>{label}</th>;
              })}
            </tr>
          </thead>
          <tbody>
            {FLOW_ITEMS.map(([label, key]) => (
              <tr key={`qd-${key}`}>
                <SpreadsheetCell value={label} type="label" />
                {Array.from({length: maxQ}, (_, i) => {
                  const isNew = i < n;
                  const isOld = i >= 4 && i < 4 + n;
                  const mnem = CIQ_MNEMONICS[key] || key;
                  return (
                    <SpreadsheetCell key={`q-${key}-${i}`}
                      value={num(qVal(i, key))}
                      type={isNew ? 'calc' : isOld ? 'reference' : 'financial'}
                      tooltip={`=CIQ("${ticker}","${mnem}","IQ_FQ-${i}")`} />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </SpreadsheetGrid>
      )}

      {/* ── Section C: LTM Calculation ── */}
      <SpreadsheetGrid title="C. LTM Calculation (Damodaran Method)">
        <thead>
          <tr>
            <SpreadsheetCell value="Item" type="header" width="180px" />
            <SpreadsheetCell value="FY0 (10-K)" type="header" />
            {n > 0 && <SpreadsheetCell value="+ New Quarters" type="header" />}
            {n > 0 && <SpreadsheetCell value="- Old Quarters" type="header" />}
            <SpreadsheetCell value="= LTM" type="header" />
          </tr>
        </thead>
        <tbody>
          {FLOW_ITEMS.map(([label, key]) => {
            const c = ltmBreakdown(key);
            const mnem = CIQ_MNEMONICS[key] || key;
            const newDetail = Array.from({length: n}, (_, i) => `FQ-${i}: ${num(qVal(i, key))}`).join('\n');
            const oldDetail = Array.from({length: n}, (_, i) => `FQ-${i+4}: ${num(qVal(i+4, key))}`).join('\n');
            return (
              <tr key={`ltm-${key}`}>
                <SpreadsheetCell value={label} type="label" />
                <SpreadsheetCell value={num(c.fy0)} type="financial" tooltip={`=CIQ("${ticker}","${mnem}","IQ_FY-0")`} />
                {n > 0 && (
                  <td className="border px-1.5 py-0.5 text-right bg-green-50 text-xs whitespace-nowrap" title={newDetail}>
                    +{num(c.newSum)}
                  </td>
                )}
                {n > 0 && (
                  <td className="border px-1.5 py-0.5 text-right bg-red-50 text-xs whitespace-nowrap" title={oldDetail}>
                    -{num(c.oldSum)}
                  </td>
                )}
                <SpreadsheetCell value={num(c.ltm)} type="calc"
                  tooltip={n === 0 ? '= FY0' : `= ${num(c.fy0)} + ${num(c.newSum)} - ${num(c.oldSum)}`} />
              </tr>
            );
          })}
          {/* Computed ratios */}
          {(() => {
            const rev = ltmBreakdown('revenues');
            const ebit = ltmBreakdown('ebit');
            const ebt = ltmBreakdown('earnings_before_tax');
            const tax = ltmBreakdown('total_tax_expense');
            const margin = rev.ltm ? ebit.ltm / rev.ltm : null;
            const effTax = ebt.ltm > 0 ? tax.ltm / ebt.ltm : null;
            const fy0Margin = fin0 && fin0.revenues ? fin0.ebit / fin0.revenues : null;
            const fy0Tax = fin0?.earnings_before_tax && (fin0.earnings_before_tax as number) > 0
              ? (fin0.total_tax_expense as number) / (fin0.earnings_before_tax as number) : null;
            return (<>
              <tr>
                <SpreadsheetCell value="  Operating Margin (%)" type="label" />
                <SpreadsheetCell value={pct(fy0Margin)} type="calc" tooltip="= FY0 EBIT / FY0 Revenue" />
                {n > 0 && <td className="border bg-gray-50" />}
                {n > 0 && <td className="border bg-gray-50" />}
                <SpreadsheetCell value={pct(margin)} type="calc" tooltip="= LTM EBIT / LTM Revenue" />
              </tr>
              <tr>
                <SpreadsheetCell value="  Effective Tax Rate (%)" type="label" />
                <SpreadsheetCell value={pct(fy0Tax)} type="calc" tooltip="= FY0 Tax / FY0 EBT" />
                {n > 0 && <td className="border bg-gray-50" />}
                {n > 0 && <td className="border bg-gray-50" />}
                <SpreadsheetCell value={pct(effTax)} type="calc" tooltip="= LTM Tax / LTM EBT" />
              </tr>
            </>);
          })()}
        </tbody>
      </SpreadsheetGrid>

      {/* ── Section D: Balance Sheet (Point-in-Time) ── */}
      <SpreadsheetGrid title="D. Balance Sheet (Point-in-Time)">
        <thead>
          <tr>
            <SpreadsheetCell value="Item" type="header" width="180px" />
            <SpreadsheetCell value="10-Q (FQ-0)" type="header" />
            <SpreadsheetCell value="10-K (FY-0)" type="header" />
            <SpreadsheetCell value="Used Value" type="header" />
            <SpreadsheetCell value="Source" type="header" />
          </tr>
        </thead>
        <tbody>
          {BS_ITEMS.map(([label, key]) => {
            const bs = bsValue(key);
            const mnem = CIQ_MNEMONICS[key] || key;
            return (
              <tr key={`bs-${key}`}>
                <SpreadsheetCell value={label} type="label" />
                <SpreadsheetCell value={num(qVal(0, key))} type="financial" tooltip={`=CIQ("${ticker}","${mnem}","IQ_FQ-0")`} />
                <SpreadsheetCell value={num(fin0?.[key] as number | null)} type="financial" tooltip={`=CIQ("${ticker}","${mnem}","IQ_FY-0")`} />
                <SpreadsheetCell value={num(bs.value)} type="calc" />
                <td className={`border px-1.5 py-0.5 text-xs font-medium ${bs.source === '10-Q' ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'}`}>
                  {bs.source === '10-Q' ? '10-Q (most recent)' : '10-K (no quarterly data)'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
