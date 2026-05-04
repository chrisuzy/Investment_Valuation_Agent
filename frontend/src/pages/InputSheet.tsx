import type { ValuationResponse, RawFinancials } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

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

function dec(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return '';
  return v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Convert a date value (Excel serial, ISO string, or number string) to "MMM DD, YYYY" */
function fmtDate(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '';
  // Excel serial date (number or numeric string like "46047")
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (!isNaN(n) && n > 30000 && n < 60000) {
    // Excel serial: days since Dec 30, 1899
    const d = new Date(Date.UTC(1899, 11, 30 + Math.round(n)));
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
  }
  // ISO string or other date format
  const d = new Date(String(v));
  if (!isNaN(d.getTime())) {
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }
  return String(v);
}


// ---------------------------------------------------------------------------
// Select component for Yes/No toggles
// ---------------------------------------------------------------------------

function YesNoSelect({ value, dotPath, onUpdate }: {
  value: boolean;
  dotPath: string;
  onUpdate: (path: string, val: boolean) => void;
}) {
  return (
    <td className="border px-2 py-1 text-sm bg-amber-50 border-amber-200">
      <select
        value={value ? 'Yes' : 'No'}
        onChange={(e) => onUpdate(dotPath, e.target.value === 'Yes')}
        className="bg-transparent outline-none text-sm w-full"
      >
        <option value="Yes">Yes</option>
        <option value="No">No</option>
      </select>
    </td>
  );
}

// ---------------------------------------------------------------------------
// Editable number cell
// ---------------------------------------------------------------------------

function EditableNum({ value, dotPath, format, onUpdate }: {
  value: number | null | undefined;
  dotPath: string;
  format: 'num' | 'pct' | 'dec';
  onUpdate: (path: string, val: number | null) => void;
}) {
  const display = format === 'pct' ? pct(value) : format === 'num' ? num(value) : dec(value);
  return (
    <SpreadsheetCell
      value={display}
      type="hypothesis"
      editable
      onChange={(raw) => {
        const cleaned = raw.replace(/[,%\s]/g, '');
        const n = parseFloat(cleaned);
        if (isNaN(n)) { onUpdate(dotPath, null); return; }
        onUpdate(dotPath, format === 'pct' ? n / 100 : n);
      }}
    />
  );
}

// ---------------------------------------------------------------------------
// CIQ formula map: variable → mnemonic (for hover tooltips)
// ---------------------------------------------------------------------------
const CIQ_MNEMONICS: Record<string, string> = {
  revenues: 'IQ_TOTAL_REV',
  ebit: 'IQ_EBIT',
  ebitda: 'IQ_EBITDA',
  net_income: 'IQ_NI',
  interest_expense: 'IQ_INTEREST_EXP',
  d_a: 'IQ_DA_CF',
  capex: 'IQ_CAPEX',
  r_and_d_expense: 'IQ_RD_EXP',
  earnings_before_tax: 'IQ_EBT_EXCL',
  total_tax_expense: 'IQ_INC_TAX',
  cash_and_marketable_securities: 'IQ_CASH_EQUIV',
  bv_equity: 'IQ_TOTAL_EQUITY',
  bv_debt: 'IQ_TOTAL_DEBT',
  cross_holdings: 'IQ_LT_INVEST',
  minority_interests: 'IQ_MINORITY_INTEREST',
  shares_outstanding: 'IQ_TOTAL_OUTSTANDING_FILING_DATE',
  stock_price: 'IQ_CLOSEPRICE',
  mv_equity: 'IQ_MARKETCAP',
};

function ciqTooltip(key: string, ticker: string, fyOffset: number): string {
  const mnem = CIQ_MNEMONICS[key];
  if (!mnem) return key;
  return `=CIQ("${ticker}","${mnem}","IQ_FY-${fyOffset}")`;
}

function ciqLtmTooltip(key: string, ticker: string, n: number): string {
  const mnem = CIQ_MNEMONICS[key];
  if (!mnem) return 'LTM (Damodaran method)';
  if (n === 0) return `LTM = FY0 (no quarterly adjustment)`;
  const newQ = Array.from({length: n}, (_, i) => `FQ-${i}`).join('+');
  const oldQ = Array.from({length: n}, (_, i) => `FQ-${i+4}`).join('+');
  return `LTM = FY0 + (${newQ}) - (${oldQ})\nUsing CIQ("${ticker}","${mnem}","IQ_FQ-n")`;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface InputSheetProps {
  data: ValuationResponse;
  sessionId?: string | null;
  onUpdate?: (dotPath: string, value: number | string | boolean | null) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InputSheet({ data, sessionId, onUpdate }: InputSheetProps) {
  const inp = data.inputs;
  const fins = inp.raw_financials; // all years, most recent first
  const fin0 = fins[0];
  const fin1 = fins.length > 1 ? fins[1] : null;
  const adj = inp.adjustment_inputs;
  const macro = inp.macro_inputs;
  const ind = inp.industry_data;
  const indGlobal = inp.industry_data_global;
  const cm = inp.company_metrics;
  const va = inp.valuation_assumptions;
  const opt = inp.option_inputs;
  const coc = data.cost_of_capital;
  const src = data.source_metadata ?? {};

  const qFins = inp.quarterly_financials ?? [];

  // Balance sheet items are point-in-time, not flow items — use most recent value directly
  const BALANCE_SHEET_KEYS = new Set<keyof RawFinancials>([
    'bv_equity', 'bv_debt', 'cash_and_marketable_securities',
    'cross_holdings', 'minority_interests', 'shares_outstanding',
    'stock_price', 'mv_equity', 'mv_debt', 'noncash_wc',
  ]);

  // LTM values are now computed on the backend (engine/ltm_calculator.py::compute_ltm_financials).
  // Frontend just reads data.ltm_financials, falling back to FY0 if backend didn't provide one.
  function ltmVal(key: keyof RawFinancials): number | null {
    const fromBackend = data.ltm_financials ? (data.ltm_financials[key] as number | null | undefined) : undefined;
    if (fromBackend !== undefined && fromBackend !== null) return fromBackend;
    return fin0 ? (fin0[key] as number | null) ?? null : null;
  }

  const quartersSince = inp.quarters_since_10k ?? 0;
  // quarters_since_10k: 0=same period, 1=0.25yr, 2=0.5yr, 3=0.75yr, 4=1yr
  const yearsSinceDisplay = quartersSince > 0
    ? (quartersSince * 0.25).toFixed(2)
    : (inp.period_date_10k && inp.period_date_10q ? '0.00' : '');

  // All annual columns (up to 10 years)
  const annualFins = fins;

  // Wrapper so child components don't need to null-check onUpdate
  const update = (path: string, val: number | string | boolean | null) => {
    if (onUpdate) onUpdate(path, val);
  };

  return (
    <div className="max-w-[95vw] mx-auto p-4">
      <h1 className="text-xl font-bold mb-4">Input Sheet</h1>
      <ColorLegend />

      {/* ----------------------------------------------------------------- */}
      {/* Section 1 — Company Information */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="1. Company Information">
        <tbody>
          <tr>
            <SpreadsheetCell value="Date of Valuation" type="label" width="200px" />
            <SpreadsheetCell value={new Date().toLocaleDateString('en-US')} type="hypothesis" editable
              onChange={(v) => update('date_of_valuation', v)}
              tooltip="As-of date for this valuation. Auto-filled with today; editable so you can reproduce a historical valuation." />
          </tr>
          <tr><SpreadsheetCell value="Company Name" type="label" /><SpreadsheetCell value={inp.company_name ?? ''} type="financial" tooltip="From indname.xlsx industry lookup" /></tr>
          <tr><SpreadsheetCell value="Ticker" type="label" /><SpreadsheetCell value={inp.ticker} type="financial" tooltip={`CIQ identifier entered on the Upload page (cell B1 of the template). Used as the first argument of every CIQ formula.`} /></tr>
          <tr><SpreadsheetCell value="Country" type="label" /><SpreadsheetCell value={inp.country ?? ''} type="financial" tooltip="From indname.xlsx industry lookup" /></tr>
          <tr><SpreadsheetCell value="Reported Currency" type="label" /><SpreadsheetCell value={inp.reporting_currency ?? ''} type="financial" tooltip={`=CIQ("${inp.ticker}","IQ_FILING_CURRENCY")`} /></tr>
          <tr><SpreadsheetCell value="Stock Price Currency" type="label" /><SpreadsheetCell value={inp.stock_price_currency ?? ''} type="financial" tooltip="Derived from exchange prefix → currency map" /></tr>
          <tr><SpreadsheetCell value={`Industry (${ind.region})`} type="label" /><SpreadsheetCell value={ind.industry_name} type="reference" tooltip="Damodaran industry classification (regional). From indname.xlsx lookup by ticker. Drives beta, industry margin, industry S/C, industry ROIC reference values." /></tr>
          <tr><SpreadsheetCell value="Industry (Global)" type="label" /><SpreadsheetCell value={indGlobal ? indGlobal.industry_name : 'N/A'} type="reference" tooltip="Damodaran industry classification (Global aggregate). Shown as a comparison if the primary region is not Global." /></tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 2 — Base Year Financials */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title={`2. Base Year Financials (${inp.reporting_currency ?? '—'}, in millions)`}>
        <thead>
          <tr>
            <SpreadsheetCell value="" type="header" width="200px" />
            <SpreadsheetCell value={inp.period_date_10q ? `LTM (${fmtDate(inp.period_date_10q)})` : 'LTM'} type="header" />
            {annualFins.map((f, i) => {
              if (i === 0 && inp.period_date_10k) {
                return <SpreadsheetCell key={`hdr-fy-${i}`} value={fmtDate(inp.period_date_10k)} type="header" />;
              }
              return <SpreadsheetCell key={`hdr-fy-${i}`} value={String(f.fiscal_year)} type="header" />;
            })}
          </tr>
        </thead>
        <tbody>
          {/* --- All financial rows: fetched data + computed rows --- */}
          {(() => {
            // Define all rows: [label, key, type] where type is 'data' (fetched) or 'calc' (computed)
            type RowDef = { label: string; key?: keyof RawFinancials; type: 'data' | 'calc' | 'section'; calc?: (f: RawFinancials, prev?: RawFinancials) => number | null };
            const rows: RowDef[] = [
              // --- Income Statement ---
              { label: 'INCOME STATEMENT', type: 'section' },
              { label: 'Revenues', key: 'revenues', type: 'data' },
              { label: '  Revenue Growth (%)', type: 'calc', calc: (f, prev) => prev && prev.revenues ? (f.revenues - prev.revenues) / Math.abs(prev.revenues) : null },
              { label: 'EBIT (Operating Income)', key: 'ebit', type: 'data' },
              { label: '  Operating Margin (%)', type: 'calc', calc: (f) => f.revenues ? f.ebit / f.revenues : null },
              { label: 'EBITDA', key: 'ebitda', type: 'data' },
              { label: 'Net Income', key: 'net_income', type: 'data' },
              { label: 'Earnings Before Tax', key: 'earnings_before_tax', type: 'data' },
              { label: 'Tax Expense', key: 'total_tax_expense', type: 'data' },
              { label: '  Effective Tax Rate (%)', type: 'calc', calc: (f) => f.earnings_before_tax && f.earnings_before_tax > 0 && f.total_tax_expense != null ? f.total_tax_expense / f.earnings_before_tax : null },
              { label: 'Interest Expense', key: 'interest_expense', type: 'data' },
              { label: 'D&A', key: 'd_a', type: 'data' },
              { label: 'R&D Expense', key: 'r_and_d_expense', type: 'data' },
              { label: 'Capital Expenditures', key: 'capex', type: 'data' },
              // --- Balance Sheet ---
              { label: 'BALANCE SHEET', type: 'section' },
              { label: 'Cash & Marketable Securities', key: 'cash_and_marketable_securities', type: 'data' },
              { label: 'Cross Holdings', key: 'cross_holdings', type: 'data' },
              { label: 'Minority Interests', key: 'minority_interests', type: 'data' },
              { label: 'Book Value of Equity', key: 'bv_equity', type: 'data' },
              { label: 'Book Value of Debt', key: 'bv_debt', type: 'data' },
              { label: 'Shares Outstanding', key: 'shares_outstanding', type: 'data' },
              // --- Ratios (computed from Income Statement + Balance Sheet) ---
              // Each row's calc runs per-year; tooltips surface the exact formula
              // and the source CIQ fields so the user can cross-check every cell.
              { label: 'RATIOS', type: 'section' },
              {
                label: '  Invested Capital',
                type: 'calc',
                calc: (f) => (f.bv_equity != null && f.bv_debt != null && f.cash_and_marketable_securities != null)
                  ? (f.bv_equity + f.bv_debt - f.cash_and_marketable_securities)
                  : null,
              },
              {
                label: '  ROIC',
                type: 'calc',
                calc: (f, prev) => {
                  const taxRate = (f.total_tax_expense != null && f.earnings_before_tax && f.earnings_before_tax > 0)
                    ? f.total_tax_expense / f.earnings_before_tax
                    : 0.21;
                  const nopat = f.ebit != null ? f.ebit * (1 - taxRate) : null;
                  if (!prev) return null;
                  const icPrior =
                    (prev.bv_equity != null && prev.bv_debt != null && prev.cash_and_marketable_securities != null)
                      ? (prev.bv_equity + prev.bv_debt - prev.cash_and_marketable_securities)
                      : null;
                  if (nopat == null || icPrior == null || icPrior === 0) return null;
                  return nopat / icPrior;
                },
              },
              {
                label: '  Sales / Capital',
                type: 'calc',
                calc: (f) => {
                  const ic = (f.bv_equity != null && f.bv_debt != null && f.cash_and_marketable_securities != null)
                    ? (f.bv_equity + f.bv_debt - f.cash_and_marketable_securities)
                    : null;
                  if (f.revenues == null || ic == null || ic === 0) return null;
                  return f.revenues / ic;
                },
              },
              {
                label: '  Reinvestment Rate (CapEx − D&A + ΔWC) / NOPAT',
                type: 'calc',
                calc: (f, prev) => {
                  if (f.ebit == null || f.earnings_before_tax == null || f.earnings_before_tax <= 0 || f.total_tax_expense == null) return null;
                  const taxRate = f.total_tax_expense / f.earnings_before_tax;
                  const nopat = f.ebit * (1 - taxRate);
                  if (nopat === 0) return null;
                  if (f.capex == null || f.d_a == null) return null;
                  const dWC = (f.change_in_noncash_wc != null) ? f.change_in_noncash_wc : 0;
                  const reinvestment = f.capex - f.d_a + dWC;
                  return reinvestment / nopat;
                },
              },
              {
                label: '  Fundamental Growth (ROIC × RIR)',
                type: 'calc',
                calc: (f, prev) => {
                  if (f.ebit == null || f.earnings_before_tax == null || f.earnings_before_tax <= 0 || f.total_tax_expense == null) return null;
                  const taxRate = f.total_tax_expense / f.earnings_before_tax;
                  const nopat = f.ebit * (1 - taxRate);
                  if (nopat === 0 || !prev) return null;
                  const icPrior = (prev.bv_equity != null && prev.bv_debt != null && prev.cash_and_marketable_securities != null)
                    ? (prev.bv_equity + prev.bv_debt - prev.cash_and_marketable_securities) : null;
                  if (icPrior == null || icPrior === 0) return null;
                  if (f.capex == null || f.d_a == null) return null;
                  const dWC = (f.change_in_noncash_wc != null) ? f.change_in_noncash_wc : 0;
                  const reinvestment = f.capex - f.d_a + dWC;
                  const roic = nopat / icPrior;
                  const rir = reinvestment / nopat;
                  return roic * rir;
                },
              },
            ];

            return rows.map((row, ri) => {
              if (row.type === 'section') {
                return (
                  <tr key={`sec-${ri}`}>
                    <td colSpan={annualFins.length + 2} className="border px-2 py-1 bg-gray-100 font-bold text-xs text-gray-600">
                      {row.label}
                    </td>
                  </tr>
                );
              }
              if (row.type === 'calc' && row.calc) {
                // Build a synthetic LTM RawFinancials for computed rows.
                // Include balance-sheet fields too so ROIC / Sales/Capital /
                // Reinvestment row calcs work on the LTM column (they read
                // bv_equity, bv_debt, cash, capex, d_a in addition to income items).
                const ltmFake = {
                  fiscal_year: 0,
                  revenues: ltmVal('revenues') ?? 0,
                  ebit: ltmVal('ebit') ?? 0,
                  earnings_before_tax: ltmVal('earnings_before_tax'),
                  total_tax_expense: ltmVal('total_tax_expense'),
                  bv_equity: ltmVal('bv_equity'),
                  bv_debt: ltmVal('bv_debt'),
                  cash_and_marketable_securities: ltmVal('cash_and_marketable_securities'),
                  capex: ltmVal('capex'),
                  d_a: ltmVal('d_a'),
                  change_in_noncash_wc: ltmVal('change_in_noncash_wc'),
                } as RawFinancials;

                // Decide which format to render the result in: percent for
                // most rows, raw decimal for Sales/Capital and Invested
                // Capital dollar value.
                const isDec = row.label.includes('Sales / Capital');
                const isDollar = row.label.includes('Invested Capital');

                // LTM calc — needs prior-year context for ROIC / fundamental
                // growth / rev growth. Use fin0 (most recent annual) as the
                // prior-period anchor for LTM-column calcs.
                const ltmCalc = row.calc(ltmFake, fin0);

                // Formula explanation for tooltip. Shown on every cell.
                const calcFormula =
                  row.label.includes('Margin')
                    ? 'Pre-tax operating margin = EBIT / Revenue. Source: IQ_EBIT / IQ_TOTAL_REV.'
                    : row.label.includes('Effective Tax Rate')
                    ? 'Effective tax rate = Tax Expense / Earnings Before Tax. Source: IQ_INC_TAX / IQ_EBT_EXCL.'
                    : row.label.includes('Revenue Growth')
                    ? 'Year-over-year revenue growth = (Revenue[t] − Revenue[t−1]) / Revenue[t−1]. Source: IQ_TOTAL_REV across fiscal years.'
                    : row.label.includes('Invested Capital')
                    ? 'Invested Capital = BV Equity + BV Debt − Cash. Source: IQ_TOTAL_EQUITY + IQ_TOTAL_DEBT − IQ_CASH_EQUIV (current year). Does NOT include R&D capitalization here — that adjustment lives in the DCF engine\'s IC for M3 ROIC.'
                    : row.label.includes('ROIC')
                    ? 'ROIC = NOPAT / Prior-year Invested Capital. NOPAT = EBIT × (1 − effective tax). IC(prev) = BV Eq(prev) + BV Debt(prev) − Cash(prev). Effective tax = Tax Expense / EBT for the same year.'
                    : row.label.includes('Sales / Capital')
                    ? 'Sales / Capital = Revenue / Invested Capital (current year). Damodaran convention; matches reinvestment formula reinv = ΔRevenue / S/C.'
                    : row.label.includes('Reinvestment Rate')
                    ? 'Reinvestment rate = (CapEx − D&A + ΔNCWC) / NOPAT. Source: IQ_CAPEX − IQ_DA_CF + change-in-noncash-WC. NOPAT = EBIT × (1 − effective tax).'
                    : row.label.includes('Fundamental Growth')
                    ? 'Fundamental growth = ROIC × Reinvestment Rate. Damodaran identity: the growth rate the firm\'s past capital allocation mathematically supports if policies continue.'
                    : '';
                return (
                  <tr key={`calc-${ri}`}>
                    <SpreadsheetCell value={row.label} type="label" tooltip={calcFormula} />
                    <SpreadsheetCell
                      value={
                        isDollar ? num(ltmCalc)
                        : isDec ? dec(ltmCalc)
                        : pct(ltmCalc)
                      }
                      type="calc"
                      tooltip={`${calcFormula} (LTM)`}
                    />
                    {annualFins.map((f, i) => {
                      const prev = annualFins[i + 1];
                      const v = row.calc!(f, prev);
                      return (
                        <SpreadsheetCell
                          key={`c-${ri}-${i}`}
                          value={
                            isDollar ? num(v)
                            : isDec ? dec(v)
                            : pct(v)
                          }
                          type="calc"
                          tooltip={calcFormula}
                        />
                      );
                    })}
                  </tr>
                );
              }
              // Data row — CIQ formula tooltips
              const key = row.key!;
              const isBalanceSheet = BALANCE_SHEET_KEYS.has(key);
              const ticker = inp.ticker;
              return (
                <tr key={`d-${key}`}>
                  <SpreadsheetCell value={row.label} type="label" />
                  <SpreadsheetCell value={num(ltmVal(key))} type={isBalanceSheet ? 'financial' : 'calc'}
                    tooltip={isBalanceSheet
                      ? (qFins[0]?.[key] != null ? `From 10-Q (FQ-0): ${ciqTooltip(key, ticker, 0).replace('IQ_FY-0', 'IQ_FQ-0')}` : `From 10-K (FY-0): ${ciqTooltip(key, ticker, 0)}`)
                      : ciqLtmTooltip(key, ticker, quartersSince)} />
                  {annualFins.map((f, i) => (
                    <SpreadsheetCell key={`fy-${key}-${i}`} value={num(f[key] as number | null)} type="financial"
                      tooltip={ciqTooltip(key, ticker, i)} />
                  ))}
                </tr>
              );
            });
          })()}
          <tr>
            <SpreadsheetCell value="Years Since Last 10-K" type="label" tooltip="Quarters elapsed between the last annual filing (10-K) and the most recent quarterly filing (10-Q), expressed as a fraction. Drives how many quarters the LTM rotation pulls forward." />
            <SpreadsheetCell value={yearsSinceDisplay} type="calc" tooltip="= (10-Q date − 10-K date) / 365.25 days. Near 0 = 10-K is fresh; near 1 = a full year has elapsed since the last annual filing and LTM rotation substitutes 4 quarters of new data." />
            {annualFins.map((_, i) => (
              <SpreadsheetCell key={`ys-${i}`} value="" type="label" />
            ))}
          </tr>
          <tr>
            <SpreadsheetCell value="Period Date (10-K)" type="label" tooltip="Fiscal year-end date of the most recent annual report." />
            <SpreadsheetCell value={fmtDate(inp.period_date_10k)} type="financial" tooltip={`=CIQ("${inp.ticker}","IQ_PERIODDATE","IQ_FY-0")`} />
            {annualFins.map((_, i) => (
              <SpreadsheetCell key={`pd10k-${i}`} value="" type="label" />
            ))}
          </tr>
          <tr>
            <SpreadsheetCell value="Period Date (10-Q)" type="label" tooltip="Period-end date of the most recent quarterly report — endpoint of the LTM window." />
            <SpreadsheetCell value={fmtDate(inp.period_date_10q)} type="financial" tooltip={`=CIQ("${inp.ticker}","IQ_PERIODDATE","IQ_FQ-0")`} />
            {annualFins.map((_, i) => (
              <SpreadsheetCell key={`pd10q-${i}`} value="" type="label" />
            ))}
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 3 — R&D */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="3. R&D Expenses">
        <tbody>
          <tr>
            <SpreadsheetCell value="Has R&D Expenses?" type="label" width="240px" />
            <YesNoSelect value={adj.has_r_and_d} dotPath="adjustment_inputs.has_r_and_d" onUpdate={update} />
            <SpreadsheetCell value="" type="label" />
          </tr>
          {adj.has_r_and_d && (
            <>
              <tr>
                <SpreadsheetCell value="Amortization Period (years)" type="label" />
                <EditableNum value={adj.amortization_period_n} dotPath="adjustment_inputs.amortization_period_n" format="num" onUpdate={update} />
                <SpreadsheetCell value="3, 5, or 10" type="hint" />
              </tr>
              <tr>
                <SpreadsheetCell value="Current Year R&D" type="label" />
                <SpreadsheetCell value={num(adj.r_and_d_expense_current)} type="financial"
                  tooltip={`=CIQ("${inp.ticker}","IQ_RD_EXP","IQ_FY-0")`} />
              </tr>
              {Array.from({ length: adj.amortization_period_n }, (_, i) => (
                <tr key={`rd-${i}`}>
                  <SpreadsheetCell value={`R&D Year -${i + 1}`} type="label" />
                  <SpreadsheetCell
                    value={i < adj.r_and_d_expense_past.length ? num(adj.r_and_d_expense_past[i]) : ''}
                    type="financial"
                    tooltip={`=CIQ("${inp.ticker}","IQ_RD_EXP","IQ_FY-${i + 1}")`}
                  />
                </tr>
              ))}
            </>
          )}
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 4 — Operating Leases */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="4. Operating Leases">
        <tbody>
          <tr>
            <SpreadsheetCell value="Has Operating Leases?" type="label" width="240px" />
            <YesNoSelect value={adj.has_operating_leases} dotPath="adjustment_inputs.has_operating_leases" onUpdate={update} />
            <SpreadsheetCell value="" type="label" />
          </tr>
          {adj.has_operating_leases && (
            <>
              <tr>
                <SpreadsheetCell value="Current Lease Expense" type="label" />
                <SpreadsheetCell value={num(adj.operating_lease_expense_current)} type="financial"
                  tooltip={`=CIQ("${inp.ticker}","IQ_OPERATING_LEASE_PAYMENTS","IQ_FY-0")`} />
              </tr>
              {adj.operating_lease_commitments.slice(0, 5).map((v, i) => {
                const mnems = ['IQ_OL_COMM_CY','IQ_OL_COMM_CY1','IQ_OL_COMM_CY2','IQ_OL_COMM_CY3','IQ_OL_COMM_CY4'];
                return (
                <tr key={`lease-${i}`}>
                  <SpreadsheetCell value={`Commitment Year ${i + 1}`} type="label" />
                  <SpreadsheetCell value={num(v)} type="financial"
                    tooltip={`=CIQ("${inp.ticker}","${mnems[i]}")`} />
                </tr>
                );
              })}
              {adj.operating_lease_commitments.length > 5 && (
                <tr>
                  <SpreadsheetCell value="Commitment Beyond Year 5" type="label" />
                  <SpreadsheetCell value={num(adj.operating_lease_commitments[5])} type="financial"
                    tooltip={`=CIQ("${inp.ticker}","IQ_OL_COMM_NEXT_FIVE")`} />
                </tr>
              )}
            </>
          )}
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 5 — Market Data (current only) */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title={`5. Market Data`}>
        <tbody>
          <tr><SpreadsheetCell value={`Current Stock Price (${inp.stock_price_currency ?? '—'})`} type="label" width="240px" /><SpreadsheetCell value={dec(fin0?.stock_price)} type="financial" tooltip={`=CIQ("${inp.ticker}","IQ_CLOSEPRICE") — quoted in the exchange's listing currency`} /></tr>
          <tr><SpreadsheetCell value={`Market Cap (${inp.reporting_currency ?? '—'}, millions)`} type="label" /><SpreadsheetCell value={num(fin0?.mv_equity)} type="financial" tooltip={`Market cap in reporting currency ${inp.reporting_currency ?? '—'} — used for WACC weights and the Price/Value comparison. When the CIQ template doesn't ship mv_equity_reporting directly, this is derived as mv_equity_listing × fx_rate.`} /></tr>
          {fin0?.mv_equity_listing != null && inp.stock_price_currency && inp.stock_price_currency !== inp.reporting_currency && (
            <tr><SpreadsheetCell value={`Market Cap (${inp.stock_price_currency}, millions)`} type="label" /><SpreadsheetCell value={num(fin0.mv_equity_listing)} type="financial" tooltip={`=CIQ("${inp.ticker}","IQ_MARKETCAP") — raw listing-currency market cap, preserved for broker-side comparison.`} /></tr>
          )}
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 6 — Tax Rates */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="6. Tax Rates">
        <tbody>
          <tr>
            <SpreadsheetCell value="Effective Tax Rate (CIQ)" type="label" width="200px" />
            <SpreadsheetCell
              value={inp.effective_tax_rate_ciq == null ? '—' : pct(inp.effective_tax_rate_ciq)}
              type="financial"
              tooltip={inp.effective_tax_rate_ciq == null
                ? `CIQ formula =CIQ("${inp.ticker}","IQ_EFFECT_TAX_RATE","IQ_FY")/100 returned no data for this ticker (some firms don't publish an effective tax rate in CIQ's feed). The engine falls back to the "Calculated" row below, which it derives from raw financials as tax_expense / pretax_income — that is the number actually used for WACC and DCF.`
                : `=CIQ("${inp.ticker}","IQ_EFFECT_TAX_RATE","IQ_FY")/100 — S&P's derived effective tax rate.`
              }
            />
          </tr>
          <tr>
            <SpreadsheetCell value="Effective Tax Rate (Calculated)" type="label" />
            <SpreadsheetCell
              value={pct(macro.tax_rate_effective)}
              type="calc"
              tooltip={`= |total_tax_expense| / |earnings_before_tax| from FY-0 raw financials. This is the rate the engine USES for base-year NOPAT, ROIC, and EV/Sales. Independent of the CIQ row above — if that one is blank, this one is your source of truth.`}
            />
          </tr>
          <tr>
            <SpreadsheetCell value="Marginal Tax Rate" type="label" />
            <SpreadsheetCell
              value={pct(macro.tax_rate_marginal)}
              type="reference"
              tooltip="Source: countrytaxrates.xls (Damodaran). Used for DCF projections (year 1..terminal) — Damodaran's convention is effective tax for the base year, marginal for the forecast."
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 7 — Value Drivers (co-located reference columns) */}
      {/* ----------------------------------------------------------------- */}
      {(() => {
        // Compute historical statistics per metric from raw_financials[]
        // Convention: fins[0] = most recent (LTM-equivalent base year), fins[1] = last year, etc.
        const stats = data.industry_stats ?? null;

        // Revenue YoY (latest) and CAGRs
        function cagr(endVal: number | null | undefined, startVal: number | null | undefined, years: number): number | null {
          if (endVal == null || startVal == null || startVal <= 0 || endVal <= 0 || years <= 0) return null;
          return Math.pow(endVal / startVal, 1 / years) - 1;
        }
        function yoy(cur: number | null | undefined, prev: number | null | undefined): number | null {
          if (cur == null || prev == null || prev === 0) return null;
          return (cur - prev) / Math.abs(prev);
        }
        function avg(vals: (number | null | undefined)[]): number | null {
          const nums = vals.filter((v): v is number => typeof v === 'number' && !isNaN(v));
          if (nums.length === 0) return null;
          return nums.reduce((a, b) => a + b, 0) / nums.length;
        }
        function yearlyMargin(f: RawFinancials | undefined): number | null {
          if (!f || !f.revenues) return null;
          return f.ebit / f.revenues;
        }
        function yearlyEffTax(f: RawFinancials | undefined): number | null {
          if (!f || !f.earnings_before_tax || f.earnings_before_tax <= 0 || f.total_tax_expense == null) return null;
          return f.total_tax_expense / f.earnings_before_tax;
        }

        // Revenue stats
        const rev_now = fins[0]?.revenues;
        const rev_prev = fins[1]?.revenues;
        const rev_3y_prior = fins[3]?.revenues;
        const rev_5y_prior = fins[5]?.revenues;
        const rev_10y_prior = fins[9]?.revenues;
        const rev_yoy = yoy(rev_now, rev_prev);
        const rev_cagr_3 = cagr(rev_now, rev_3y_prior, 3);
        const rev_cagr_5 = cagr(rev_now, rev_5y_prior, 5);
        const rev_cagr_10 = cagr(rev_now, rev_10y_prior, 10);

        // Operating Margin stats
        const margin_now = yearlyMargin(fins[0]);
        const margin_prev = yearlyMargin(fins[1]);
        const margin_yoy_delta = (margin_now != null && margin_prev != null) ? (margin_now - margin_prev) : null;
        const marginSeries3 = fins.slice(0, 3).map(yearlyMargin);
        const marginSeries5 = fins.slice(0, 5).map(yearlyMargin);
        const marginSeries10 = fins.slice(0, 10).map(yearlyMargin);
        const margin_avg_3 = avg(marginSeries3);
        const margin_avg_5 = avg(marginSeries5);
        const margin_avg_10 = avg(marginSeries10);
        // Math.max on an empty array returns -Infinity — guard it so we
        // show '—' instead of "-∞%" when no valid margin points exist.
        const margin_max_10 = (() => {
          const nums = marginSeries10.filter((v): v is number => typeof v === 'number' && !isNaN(v));
          return nums.length ? Math.max(...nums) : null;
        })();

        // Effective tax stats (for margin convergence story)
        // (not shown but computable)

        // Sales-to-Capital stats (company implied: revenue / invested capital)
        function yearlyStoC(f: RawFinancials | undefined): number | null {
          if (!f || !f.revenues) return null;
          const ic = (f.bv_equity ?? 0) + (f.bv_debt ?? 0) - (f.cash_and_marketable_securities ?? 0);
          if (ic <= 0) return null;
          return f.revenues / ic;
        }
        const stoc_now = yearlyStoC(fins[0]);
        const stoc_avg_3 = avg(fins.slice(0, 3).map(yearlyStoC));
        const stoc_avg_5 = avg(fins.slice(0, 5).map(yearlyStoC));
        const stoc_avg_10 = avg(fins.slice(0, 10).map(yearlyStoC));

        // Tooltip helpers
        function cagrTooltip(years: number, endYr: number, startYr: number, metric: string): string {
          return `${years}Y CAGR = (${metric}[FY${endYr}] / ${metric}[FY${endYr - years}])^(1/${years}) - 1\nUsing fiscal years ${startYr} → ${endYr}`;
        }
        function avgTooltip(years: number, metric: string): string {
          return `${years}Y arithmetic average of ${metric}\nComputed over the last ${years} fiscal years`;
        }

        const latestFy = fins[0]?.fiscal_year ?? 0;

        return (
        <SpreadsheetGrid title="7. Value Drivers — with co-located reference data">
          <thead>
            <tr>
              <SpreadsheetCell value="Driver" type="header" width="230px" />
              <SpreadsheetCell value="Your Input" type="header" width="110px" />
              <SpreadsheetCell value="Co LTM / YoY" type="header" width="100px" />
              <SpreadsheetCell value="3Y CAGR/Avg" type="header" width="100px" />
              <SpreadsheetCell value="5Y CAGR/Avg" type="header" width="100px" />
              <SpreadsheetCell value="10Y CAGR/Avg" type="header" width="100px" />
              <SpreadsheetCell value={`${ind.region} Ind. Median`} type="header" width="120px" />
              <SpreadsheetCell value="Global Median" type="header" width="120px" />
              <SpreadsheetCell value="Stat Q1–Q3" type="header" width="140px" />
            </tr>
          </thead>
          <tbody>
            {/* Revenue Growth — Year 1 */}
            <tr>
              <SpreadsheetCell value="Revenue Growth — Next Year" type="label" />
              <EditableNum value={va.revenue_growth_next_year} dotPath="valuation_assumptions.revenue_growth_next_year" format="pct" onUpdate={update} />
              <SpreadsheetCell value={pct(rev_yoy)} type="calc" tooltip={`YoY = (Revenue[FY${latestFy}] - Revenue[FY${latestFy-1}]) / Revenue[FY${latestFy-1}]`} />
              <SpreadsheetCell value={pct(rev_cagr_3)} type="calc" tooltip={cagrTooltip(3, latestFy, latestFy-3, 'Revenue')} />
              <SpreadsheetCell value={pct(rev_cagr_5)} type="calc" tooltip={cagrTooltip(5, latestFy, latestFy-5, 'Revenue')} />
              <SpreadsheetCell value={pct(rev_cagr_10)} type="calc" tooltip={cagrTooltip(10, latestFy, latestFy-10, 'Revenue')} />
              <SpreadsheetCell value={pct(ind.revenue_growth)} type="reference" tooltip={`Source: fundgrEB Damodaran | Industry: ${ind.industry_name} (${ind.region})`} />
              <SpreadsheetCell value={pct(indGlobal?.revenue_growth)} type="reference" tooltip={`Source: fundgrEBGlobal | Industry: ${ind.industry_name} (Global)`} />
              <SpreadsheetCell value={stats?.revenue_growth_3y?.q1 != null && stats?.revenue_growth_3y?.q3 != null ? `${pct(stats.revenue_growth_3y.q1)}–${pct(stats.revenue_growth_3y.q3)}` : '—'} type="reference" tooltip={stats ? `Q1/Median/Q3 of ${stats.n_firms} firms in ${ind.industry_name}\n(Source: Ginzu Input Stat Distributions)` : ''} />
            </tr>

            {/* Revenue Growth — Years 2-5 */}
            <tr>
              <SpreadsheetCell value="Revenue Growth — Years 2-5" type="label" />
              <EditableNum value={va.revenue_growth_years_2_5} dotPath="valuation_assumptions.revenue_growth_years_2_5" format="pct" onUpdate={update} />
              <SpreadsheetCell value="—" type="calc" tooltip="Forward assumption — no per-year historical" />
              <SpreadsheetCell value={pct(rev_cagr_3)} type="calc" tooltip={cagrTooltip(3, latestFy, latestFy-3, 'Revenue')} />
              <SpreadsheetCell value={pct(rev_cagr_5)} type="calc" tooltip={cagrTooltip(5, latestFy, latestFy-5, 'Revenue')} />
              <SpreadsheetCell value={pct(rev_cagr_10)} type="calc" tooltip={cagrTooltip(10, latestFy, latestFy-10, 'Revenue')} />
              <SpreadsheetCell value={pct(ind.revenue_growth)} type="reference" tooltip={`Source: fundgrEB | Industry: ${ind.industry_name} (${ind.region})`} />
              <SpreadsheetCell value={pct(indGlobal?.revenue_growth)} type="reference" tooltip={`Source: fundgrEBGlobal | Industry: ${ind.industry_name} (Global)`} />
              <SpreadsheetCell value={stats?.revenue_growth_3y?.q1 != null && stats?.revenue_growth_3y?.q3 != null ? `${pct(stats.revenue_growth_3y.q1)}–${pct(stats.revenue_growth_3y.q3)}` : '—'} type="reference" tooltip={stats ? `Q1/Median/Q3 across ${stats.n_firms} firms` : ''} />
            </tr>

            {/* Operating Margin — Year 1 */}
            <tr>
              <SpreadsheetCell value="Operating Margin — Next Year" type="label" />
              <EditableNum
                value={va.operating_margin_next_year ?? margin_now}
                dotPath="valuation_assumptions.operating_margin_next_year" format="pct" onUpdate={update} />
              <SpreadsheetCell value={pct(margin_now)} type="calc" tooltip={`Current Op Margin = EBIT[FY${latestFy}] / Revenue[FY${latestFy}]\n(change YoY: ${margin_yoy_delta != null ? (margin_yoy_delta >= 0 ? '+' : '') + (margin_yoy_delta * 100).toFixed(2) + ' pp' : 'n/a'})`} />
              <SpreadsheetCell value={pct(margin_avg_3)} type="calc" tooltip={avgTooltip(3, 'Op Margin')} />
              <SpreadsheetCell value={pct(margin_avg_5)} type="calc" tooltip={avgTooltip(5, 'Op Margin')} />
              <SpreadsheetCell value={pct(margin_avg_10)} type="calc" tooltip={avgTooltip(10, 'Op Margin')} />
              <SpreadsheetCell value={pct(ind.pretax_operating_margin)} type="reference" tooltip={`Source: margin Damodaran | Industry: ${ind.industry_name} (${ind.region})`} />
              <SpreadsheetCell value={pct(indGlobal?.pretax_operating_margin)} type="reference" tooltip={`Source: marginGlobal | Industry: ${ind.industry_name} (Global)`} />
              <SpreadsheetCell value={stats?.pretax_operating_margin?.q1 != null && stats?.pretax_operating_margin?.q3 != null ? `${pct(stats.pretax_operating_margin.q1)}–${pct(stats.pretax_operating_margin.q3)}` : '—'} type="reference" tooltip={stats ? `Q1/Median/Q3 of ${stats.n_firms} firms` : ''} />
            </tr>

            {/* Target Margin */}
            <tr>
              <SpreadsheetCell value="Target Pre-tax Op Margin" type="label" />
              <EditableNum value={va.target_operating_margin} dotPath="valuation_assumptions.target_operating_margin" format="pct" onUpdate={update} />
              <SpreadsheetCell value="—" type="calc" tooltip="Terminal target — no historical analog" />
              <SpreadsheetCell value={pct(margin_avg_3)} type="calc" tooltip={avgTooltip(3, 'Op Margin')} />
              <SpreadsheetCell value={pct(margin_avg_5)} type="calc" tooltip={avgTooltip(5, 'Op Margin')} />
              <SpreadsheetCell value={`${pct(margin_avg_10)} (max ${pct(margin_max_10)})`} type="calc" tooltip={`10Y average, with peak observed: ${pct(margin_max_10)}`} />
              <SpreadsheetCell value={pct(ind.pretax_operating_margin)} type="reference" tooltip={`Source: margin | Industry: ${ind.industry_name}`} />
              <SpreadsheetCell value={pct(indGlobal?.pretax_operating_margin)} type="reference" tooltip={`Source: marginGlobal`} />
              <SpreadsheetCell value={stats?.pretax_operating_margin?.q1 != null && stats?.pretax_operating_margin?.q3 != null ? `${pct(stats.pretax_operating_margin.q1)}–${pct(stats.pretax_operating_margin.q3)}` : '—'} type="reference" tooltip={stats ? `Benchmark range across ${stats.n_firms} firms` : ''} />
            </tr>

            {/* Margin Convergence Year */}
            <tr>
              <SpreadsheetCell value="Year of Convergence (1–10)" type="label" />
              <EditableNum value={va.margin_convergence_year} dotPath="valuation_assumptions.margin_convergence_year" format="num" onUpdate={update} />
              <SpreadsheetCell value="—" type="calc" />
              <SpreadsheetCell value="—" type="calc" />
              <SpreadsheetCell value="—" type="calc" />
              <SpreadsheetCell value="5 typical" type="calc" tooltip="Damodaran convention: converge margin linearly to target by year 5" />
              <SpreadsheetCell value="—" type="reference" />
              <SpreadsheetCell value="—" type="reference" />
              <SpreadsheetCell value="—" type="reference" />
            </tr>

            {/* Sales-to-Capital Yr 1-5 */}
            <tr>
              <SpreadsheetCell
                value="Sales / Capital — Years 1-5"
                type="label"
                tooltip={'Reinvestment = ΔRevenue / Sales-to-Capital. Two values (high-growth and stable) reflect that capital efficiency typically changes as a firm matures. Folder reference: module_05_dcf_projection.md §3.6.'}
              />
              <EditableNum value={va.sales_to_capital_high} dotPath="valuation_assumptions.sales_to_capital_high" format="dec" onUpdate={update} />
              <SpreadsheetCell value={dec(stoc_now)} type="calc" tooltip={`Implied Sales/Capital = Revenue / (BV Equity + BV Debt - Cash)\nMost recent FY`} />
              <SpreadsheetCell value={dec(stoc_avg_3)} type="calc" tooltip={avgTooltip(3, 'Implied Sales/Capital')} />
              <SpreadsheetCell value={dec(stoc_avg_5)} type="calc" tooltip={avgTooltip(5, 'Implied Sales/Capital')} />
              <SpreadsheetCell value={dec(stoc_avg_10)} type="calc" tooltip={avgTooltip(10, 'Implied Sales/Capital')} />
              <SpreadsheetCell value={dec(ind.sales_to_capital)} type="reference" tooltip={`Source: capex Damodaran | Industry: ${ind.industry_name} (${ind.region})`} />
              <SpreadsheetCell value={dec(indGlobal?.sales_to_capital)} type="reference" tooltip={`Source: capexGlobal`} />
              <SpreadsheetCell value={stats?.sales_to_capital?.q1 != null && stats?.sales_to_capital?.q3 != null ? `${dec(stats.sales_to_capital.q1)}–${dec(stats.sales_to_capital.q3)}` : '—'} type="reference" tooltip={stats ? `Q1/Median/Q3 of ${stats.n_firms} firms` : ''} />
            </tr>

            {/* Sales-to-Capital Yr 6-10 */}
            <tr>
              <SpreadsheetCell
                value="Sales / Capital — Years 6-10"
                type="label"
                tooltip={'Stable-period Sales/Capital, typically closer to 1–2× for mature firms. Drives reinvestment during the convergence phase (years 6–10). Folder: module_05 §3.6.'}
              />
              <EditableNum value={va.sales_to_capital_stable} dotPath="valuation_assumptions.sales_to_capital_stable" format="dec" onUpdate={update} />
              <SpreadsheetCell value="—" type="calc" tooltip="Forward assumption — use 10Y avg or industry as anchor" />
              <SpreadsheetCell value={dec(stoc_avg_3)} type="calc" tooltip={avgTooltip(3, 'Implied Sales/Capital')} />
              <SpreadsheetCell value={dec(stoc_avg_5)} type="calc" tooltip={avgTooltip(5, 'Implied Sales/Capital')} />
              <SpreadsheetCell value={dec(stoc_avg_10)} type="calc" tooltip={avgTooltip(10, 'Implied Sales/Capital')} />
              <SpreadsheetCell value={dec(ind.sales_to_capital)} type="reference" tooltip={`Source: capex | Industry: ${ind.industry_name}`} />
              <SpreadsheetCell value={dec(indGlobal?.sales_to_capital)} type="reference" tooltip={`Source: capexGlobal`} />
              <SpreadsheetCell value={stats?.sales_to_capital?.q1 != null && stats?.sales_to_capital?.q3 != null ? `${dec(stats.sales_to_capital.q1)}–${dec(stats.sales_to_capital.q3)}` : '—'} type="reference" tooltip={stats ? `Benchmark ${stats.n_firms}-firm range` : ''} />
            </tr>
          </tbody>
        </SpreadsheetGrid>
        );
      })()}

      {/* ----------------------------------------------------------------- */}
      {/* Section 7b — Industry Comparison */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title={`7b. Company vs Industry (${ind.region} / Global)`}>
        <thead>
          <tr>
            <SpreadsheetCell value="Metric" type="header" width="180px" />
            <SpreadsheetCell value="Company" type="header" />
            <SpreadsheetCell value={`${ind.region} Industry`} type="header" />
            <SpreadsheetCell value="Global Industry" type="header" />
          </tr>
        </thead>
        <tbody>
          {(() => {
            const regionSuffix = ind.region === 'US' ? '' : ind.region === 'Emerging' ? 'emerg' : ind.region;
            const fSuffix = regionSuffix ? regionSuffix : '';
            const rows: [string, number | null | undefined, number | null | undefined, number | null | undefined, string, string, string][] = [
              ['Revenue Growth', cm?.revenue_growth, ind.revenue_growth, indGlobal?.revenue_growth, 'pct', `fundgrEB${fSuffix}.xls`, 'fundgrEBGlobal.xls'],
              ['Pre-tax Op Margin', cm?.pretax_operating_margin, ind.pretax_operating_margin, indGlobal?.pretax_operating_margin, 'pct', `margin${fSuffix}.xls`, 'marginGlobal.xls'],
              ['Sales / Capital', cm?.sales_to_capital, ind.sales_to_capital, indGlobal?.sales_to_capital, 'dec', `capex${fSuffix}.xls`, 'capexGlobal.xls'],
              ['ROIC', cm?.roic, ind.roic, indGlobal?.roic, 'pct', `EVA${fSuffix}.xls`, 'EVAGlobal.xls'],
              ['Std Dev Stock', cm?.std_dev_stock, ind.std_dev_stock, indGlobal?.std_dev_stock, 'pct', `EVA${fSuffix}.xls`, 'EVAGlobal.xls'],
              ['WACC', cm?.cost_of_capital, ind.wacc, indGlobal?.wacc, 'pct', `wacc${fSuffix}.xls`, 'waccGlobal.xls'],
              // Multiples — label them as *intrinsic* (DCF-implied) for the
              // company column so users don't confuse them with observed
              // market multiples. ind.* columns remain the Damodaran
              // industry-median reference (observed market).
              ['EV/EBITDA (intrinsic)', data.multiples?.ev_ebitda_intrinsic, ind.ev_ebitda, indGlobal?.ev_ebitda, 'dec', `vebitda${fSuffix}.xls`, 'vebitdaGlobal.xls'],
              ['PE Ratio (intrinsic)',  data.multiples?.pe_ratio_intrinsic,  ind.pe_ratio,  indGlobal?.pe_ratio,  'dec', fSuffix ? `pe${fSuffix}.xls` : 'pedata.xls', 'peGlobal.xls'],
              ['PBV Ratio (intrinsic)', data.multiples?.pbv_ratio_intrinsic, ind.pbv_ratio, indGlobal?.pbv_ratio, 'dec', fSuffix ? `pbv${fSuffix}.xls` : 'pbvdata.xls', 'pbvGlobal.xls'],
            ];
            return rows.map(([label, company, regional, global_, fmt, srcRegional, srcGlobal]) => (
              <tr key={`cmp-${label}`}>
                <SpreadsheetCell value={label} type="label" tooltip={`Row: ${label}. Left column = this firm (computed from CIQ data + LTM base year). Regional and Global columns = Damodaran industry medians.`} />
                <SpreadsheetCell value={fmt === 'pct' ? pct(company) : dec(company)} type="calc"
                  tooltip={`${label} — firm-level, computed from M3/M4 on the LTM-rotated base year. See the Ratios block above (Section 2) for the exact per-year formula.`} />
                <SpreadsheetCell value={fmt === 'pct' ? pct(regional) : dec(regional)} type="reference"
                  tooltip={`Source: ${srcRegional} | Industry: ${ind.industry_name} (${ind.region})`} />
                <SpreadsheetCell value={fmt === 'pct' ? pct(global_) : dec(global_)} type="reference"
                  tooltip={`Source: ${srcGlobal} | Industry: ${ind.industry_name} (Global)`} />
              </tr>
            ));
          })()}
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 8 — Market Numbers */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="8. Market Numbers">
        <tbody>
          <tr><SpreadsheetCell value="Risk-free Rate" type="label" width="200px" /><EditableNum value={macro.risk_free_rate} dotPath="macro_inputs.risk_free_rate" format="pct" onUpdate={update} /></tr>
          <tr><SpreadsheetCell value="Equity Risk Premium (ERP)" type="label" /><SpreadsheetCell value={pct(macro.equity_risk_premium)} type="reference" tooltip="Source: ctryprem.xlsx (Damodaran)" /></tr>
          <tr><SpreadsheetCell value="Country Risk Premium (CRP)" type="label" /><SpreadsheetCell value={pct(macro.country_risk_premium)} type="reference" tooltip="Source: ctryprem.xlsx (Damodaran)" /></tr>
          <tr><SpreadsheetCell value="Default Spread" type="label" /><SpreadsheetCell value={pct(macro.default_spread)} type="reference" tooltip="Source: ctryprem.xlsx (Damodaran)" /></tr>
          <tr>
            <SpreadsheetCell value="WACC (from Cost of Capital module)" type="label" />
            <SpreadsheetCell
              value={pct(coc?.wacc)}
              type="calc"
              tooltip={`Same value as the WACC shown on the Cost of Capital page — computed by Module 2 from the levered beta, ERP, Kd, and capital-structure weights. Summarized here as the year-1 discount rate used by the DCF. Change it by editing any upstream input (beta approach, ERP approach, Kd approach, debt/equity mix) on the Cost of Capital page.`}
            />
          </tr>
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 9 — Cost of Capital Details */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="9. Cost of Capital Details">
        <tbody>
          {(() => {
            const bSuffix = ind.region === 'US' ? '' : ind.region === 'Emerging' ? 'emerg' : ind.region;
            const betaFile = bSuffix ? `beta${bSuffix}.xls` : 'betas.xls';
            const waccFile = bSuffix ? `wacc${bSuffix}.xls` : 'wacc.xls';
            return (<>
              <tr><SpreadsheetCell value="Unlevered Beta" type="label" width="200px" /><SpreadsheetCell value={dec(ind.beta_u)} type="reference" tooltip={`Source: ${betaFile}`} /></tr>
              <tr><SpreadsheetCell value="Industry D/E Ratio" type="label" /><SpreadsheetCell value={pct(ind.industry_d_e_ratio)} type="reference" tooltip={`Source: ${betaFile}`} /></tr>
              <tr><SpreadsheetCell value="Industry Eff Tax Rate" type="label" /><SpreadsheetCell value={pct(ind.industry_effective_tax_rate)} type="reference" tooltip={`Source: ${waccFile}`} /></tr>
              <tr><SpreadsheetCell value="Pre-tax Cost of Debt" type="label" /><SpreadsheetCell value={pct(ind.cost_of_debt_pretax)} type="reference" tooltip={`Source: ${waccFile}`} /></tr>
              <tr><SpreadsheetCell value="Levered Beta" type="label" /><SpreadsheetCell value={dec(coc?.beta_l)} type="calc" /></tr>
              <tr><SpreadsheetCell value="Cost of Equity" type="label" /><SpreadsheetCell value={pct(coc?.cost_of_equity)} type="calc" /></tr>
              <tr><SpreadsheetCell value="D/E Ratio (Company)" type="label" /><SpreadsheetCell value={dec(coc?.d_e_ratio)} type="calc" /></tr>
              <tr><SpreadsheetCell value="Weight of Equity" type="label" /><SpreadsheetCell value={pct(coc?.weight_equity)} type="calc" /></tr>
              <tr><SpreadsheetCell value="Weight of Debt" type="label" /><SpreadsheetCell value={pct(coc?.weight_debt)} type="calc" /></tr>
            </>);
          })()}
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 10 — Employee Options */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="10. Employee Options">
        <tbody>
          <tr>
            <SpreadsheetCell value="Has Options Outstanding?" type="label" width="240px" />
            <YesNoSelect value={opt.has_options} dotPath="option_inputs.has_options" onUpdate={update} />
            <SpreadsheetCell value="" type="label" />
          </tr>
          {opt.has_options && (
            <>
              <tr>
                <SpreadsheetCell value="Number of Options" type="label" />
                <EditableNum value={opt.number_of_options} dotPath="option_inputs.number_of_options" format="num" onUpdate={update} />
              </tr>
              <tr>
                <SpreadsheetCell value="Average Strike Price" type="label" />
                <EditableNum value={opt.average_strike_price} dotPath="option_inputs.average_strike_price" format="dec" onUpdate={update} />
              </tr>
              <tr>
                <SpreadsheetCell value="Average Maturity (years)" type="label" />
                <EditableNum value={opt.average_maturity} dotPath="option_inputs.average_maturity" format="dec" onUpdate={update} />
              </tr>
              <tr>
                <SpreadsheetCell value="Std Dev of Stock Price" type="label" />
                <EditableNum value={opt.stock_price_std_dev} dotPath="option_inputs.stock_price_std_dev" format="pct" onUpdate={update} />
              </tr>
              <tr>
                <SpreadsheetCell value="Dividend Yield" type="label" />
                <EditableNum value={opt.dividend_yield} dotPath="option_inputs.dividend_yield" format="pct" onUpdate={update} />
              </tr>
            </>
          )}
        </tbody>
      </SpreadsheetGrid>

      {/* ----------------------------------------------------------------- */}
      {/* Section 11 — Default Assumptions & Overrides */}
      {/* ----------------------------------------------------------------- */}
      <SpreadsheetGrid title="11. Default Assumptions">
        <tbody>
          {/* --- Stable Growth Rate --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            In stable growth, the growth rate used for your firm will be capped at the risk-free rate
            ({pct(macro.risk_free_rate)}). If you disagree, enter a different stable growth rate below.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Do you want to change the stable growth rate?" type="label" width="360px" />
            <YesNoSelect value={va.stable_growth_rate !== null} dotPath="" onUpdate={(_, val) => {
              if (!val) update('valuation_assumptions.stable_growth_rate', null);
              else update('valuation_assumptions.stable_growth_rate', macro.risk_free_rate);
            }} />
            <SpreadsheetCell value={`Default: ${pct(macro.risk_free_rate)}`} type="hint" />
          </tr>
          {va.stable_growth_rate !== null && (
            <tr>
              <SpreadsheetCell value="Stable Growth Rate" type="label" />
              <EditableNum value={va.stable_growth_rate} dotPath="valuation_assumptions.stable_growth_rate" format="pct" onUpdate={update} />
              <SpreadsheetCell value="" type="hint" />
            </tr>
          )}

          {/* --- Cost of Capital in Stable Growth --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            In stable growth, I will assume your firm will have a cost of capital similar to typical mature companies
            (8-10%). If you disagree, enter your own cost of capital.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Do you want to override the stable cost of capital?" type="label" />
            <YesNoSelect value={va.cost_of_capital_stable_override !== null} dotPath="" onUpdate={(_, val) => {
              if (!val) update('valuation_assumptions.cost_of_capital_stable_override', null);
              else update('valuation_assumptions.cost_of_capital_stable_override', 0.09);
            }} />
            <SpreadsheetCell value="Default: computed from WACC convergence" type="hint" />
          </tr>
          {va.cost_of_capital_stable_override !== null && (
            <tr>
              <SpreadsheetCell value="Stable Cost of Capital" type="label" />
              <EditableNum value={va.cost_of_capital_stable_override} dotPath="valuation_assumptions.cost_of_capital_stable_override" format="pct" onUpdate={update} />
              <SpreadsheetCell value="" type="hint" />
            </tr>
          )}

          {/* --- ROIC in Stable Growth --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            In stable growth, I will assume your firm will earn a return on capital equal to its cost of capital,
            so that excess returns go to zero. If you disagree, enter your own return on capital.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Do you want to override the stable ROIC?" type="label" />
            <YesNoSelect value={va.roic_stable_override !== null} dotPath="" onUpdate={(_, val) => {
              if (!val) update('valuation_assumptions.roic_stable_override', null);
              else update('valuation_assumptions.roic_stable_override', 0.10);
            }} />
            <SpreadsheetCell value="Default: ROIC = Cost of Capital" type="hint" />
          </tr>
          {va.roic_stable_override !== null && (
            <tr>
              <SpreadsheetCell value="Stable ROIC" type="label" />
              <EditableNum value={va.roic_stable_override} dotPath="valuation_assumptions.roic_stable_override" format="pct" onUpdate={update} />
              <SpreadsheetCell value="" type="hint" />
            </tr>
          )}

          {/* --- Tax Convergence --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            I will move the tax rate from the effective rate ({pct(macro.tax_rate_effective)}) toward the marginal rate
            ({pct(macro.tax_rate_marginal)}) over the transition period. If you disagree, you can lock the effective tax rate.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Do you want to override tax convergence?" type="label" />
            <YesNoSelect value={va.override_tax_convergence} dotPath="valuation_assumptions.override_tax_convergence" onUpdate={update} />
            <SpreadsheetCell value="Yes = lock effective tax rate" type="hint" />
          </tr>

          {/* --- NOL --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            If your firm has net operating losses (NOLs), I can use them to shelter income in the early years
            of the valuation rather than making the firm pay taxes immediately.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Does your firm have NOLs?" type="label" />
            <YesNoSelect value={va.override_nol} dotPath="valuation_assumptions.override_nol" onUpdate={update} />
            <SpreadsheetCell value="" type="hint" />
          </tr>
          {va.override_nol && (
            <tr>
              <SpreadsheetCell value="NOL Amount" type="label" />
              <EditableNum value={va.nol_amount} dotPath="valuation_assumptions.nol_amount" format="num" onUpdate={update} />
              <SpreadsheetCell value="Net operating loss carryforward" type="hint" />
            </tr>
          )}

          {/* --- Failure Probability --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            If there is a chance this firm will not survive as a going concern, you can adjust the value
            by specifying a probability of failure and what you expect to recover in distress.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Failure Probability" type="label" />
            <EditableNum value={va.failure_probability} dotPath="valuation_assumptions.failure_probability" format="pct" onUpdate={update} />
            <SpreadsheetCell value="0% = no failure risk" type="hint" />
          </tr>
          {va.failure_probability > 0 && (
            <>
              <tr>
                <SpreadsheetCell value="Distress Proceeds (% of BV)" type="label" />
                <EditableNum value={va.distress_proceeds_pct} dotPath="valuation_assumptions.distress_proceeds_pct" format="pct" onUpdate={update} />
                <SpreadsheetCell value="% of book value recovered" type="hint" />
              </tr>
              <tr>
                <SpreadsheetCell value="Failure Tied To" type="label" />
                <td className="border px-2 py-1 text-sm bg-amber-50 border-amber-200">
                  <select
                    value={va.failure_tie_to}
                    onChange={(e) => update('valuation_assumptions.failure_tie_to', e.target.value)}
                    className="bg-transparent outline-none text-sm w-full"
                  >
                    <option value="V">Fair Value (V)</option>
                    <option value="B">Book Value (B)</option>
                  </select>
                </td>
                <SpreadsheetCell value="B=book, V=fair value" type="hint" />
              </tr>
            </>
          )}

          {/* --- Risk-free Rate Override --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            The current risk-free rate ({pct(macro.risk_free_rate)}) will be used for both the cost of capital and
            as the terminal growth rate constraint. If you expect rates to normalize, enter a different long-term rate.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Do you want to override the risk-free rate after year 10?" type="label" />
            <YesNoSelect value={va.override_riskfree} dotPath="valuation_assumptions.override_riskfree" onUpdate={update} />
            <SpreadsheetCell value="" type="hint" />
          </tr>
          {va.override_riskfree && (
            <tr>
              <SpreadsheetCell value="Risk-free Rate After Year 10" type="label" />
              <EditableNum value={va.riskfree_after_yr10} dotPath="valuation_assumptions.riskfree_after_yr10" format="pct" onUpdate={update} />
              <SpreadsheetCell value="Overrides terminal Rf" type="hint" />
            </tr>
          )}

          {/* --- Trapped Cash --- */}
          <tr><td colSpan={3} className="border px-3 py-2 text-sm bg-gray-50 italic">
            If a portion of cash is trapped overseas or restricted, you may want to discount it
            by any repatriation tax or illiquidity discount.
          </td></tr>
          <tr>
            <SpreadsheetCell value="Does your firm have trapped cash?" type="label" />
            <YesNoSelect value={va.override_trapped_cash} dotPath="valuation_assumptions.override_trapped_cash" onUpdate={update} />
            <SpreadsheetCell value="" type="hint" />
          </tr>
          {va.override_trapped_cash && (
            <>
              <tr>
                <SpreadsheetCell value="Trapped Cash Amount" type="label" />
                <EditableNum value={va.trapped_cash_amount} dotPath="valuation_assumptions.trapped_cash_amount" format="num" onUpdate={update} />
                <SpreadsheetCell value="Cash held overseas / restricted" type="hint" />
              </tr>
              <tr>
                <SpreadsheetCell value="Trapped Cash Tax Rate" type="label" />
                <EditableNum value={va.trapped_cash_tax_rate} dotPath="valuation_assumptions.trapped_cash_tax_rate" format="pct" onUpdate={update} />
                <SpreadsheetCell value="Tax on repatriation" type="hint" />
              </tr>
            </>
          )}

          {/* --- General Settings --- */}
          <tr>
            <SpreadsheetCell value="Projection Years" type="label" />
            <EditableNum value={va.projection_years} dotPath="valuation_assumptions.projection_years" format="num" onUpdate={update} />
            <SpreadsheetCell value="Default 10" type="hint" />
          </tr>
          <tr>
            <SpreadsheetCell value="High Growth Years" type="label" />
            <EditableNum value={va.high_growth_years} dotPath="valuation_assumptions.high_growth_years" format="num" onUpdate={update} />
            <SpreadsheetCell value="Default 5" type="hint" />
          </tr>
        </tbody>
      </SpreadsheetGrid>
    </div>
  );
}
