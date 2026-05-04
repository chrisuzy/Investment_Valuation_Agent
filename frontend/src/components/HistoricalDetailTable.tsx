/**
 * Dense 10-year × 4-metric historical table shown on Stories to Numbers
 * below the Required-ROIC / Required-S/C reverse checks.
 *
 * Addresses the analyst's need to cross-check Required figures against
 * the actual 10-year history rather than a single 5-yr average. Every
 * column corresponds to a fiscal year (FY-0 = most recent); every cell
 * has a per-year tooltip showing the exact calculation.
 *
 * For averaging methodology this component shows:
 *   - Revenue Growth: both arithmetic mean AND compound annual growth rate
 *     (CAGR). CAGR is the financially correct geometric measure; arithmetic
 *     mean is shown side-by-side so the gap is visible.
 *   - Margin: arithmetic mean (appropriate for level ratios, not growth).
 *     Labelled explicitly as "Pre-tax Operating Margin (EBIT / Revenue)".
 *   - ROIC: arithmetic mean (primary) AND NOPAT-weighted (Σ NOPAT / Σ IC).
 *     Weighted is more robust when IC varies year-to-year.
 *   - Sales/Capital: arithmetic mean (level ratio).
 */

import type { ValuationResponse, RawFinancials } from '../types/valuation';

interface Props {
  data: ValuationResponse;
}

function pct(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return '—';
  return `${(v * 100).toFixed(digits)}%`;
}
function dec(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '—';
  return `${v.toFixed(digits)}×`;
}

function fmtM(v: number | null | undefined): string {
  if (v == null) return '—';
  return `${(v / 1000).toLocaleString('en-US', { maximumFractionDigits: 1 })}B`;
}

export default function HistoricalDetailTable({ data }: Props) {
  const cf = data.cashflow;
  const history: RawFinancials[] = data.inputs.raw_financials ?? [];
  const nYears = Math.min(10, cf?.historical_roic_by_year?.length ?? 0);
  const yearLabels = Array.from({ length: nYears }, (_, i) => `FY-${i}`);

  // Per-year tooltip builders drawn from raw_financials for transparency.
  const growthTip = (i: number) => {
    const cur = history[i]?.revenues;
    const prev = history[i + 1]?.revenues;
    if (cur == null || prev == null) return `FY-${i}: insufficient data (need FY-${i} and FY-${i + 1} revenues).`;
    return `FY-${i} growth = (${fmtM(cur)} − ${fmtM(prev)}) / ${fmtM(prev)} = ${((cur / prev - 1) * 100).toFixed(2)}%\nSource: IQ_TOTAL_REV × IQ_FY-${i} and IQ_FY-${i + 1}.`;
  };
  const marginTip = (i: number) => {
    const ebit = history[i]?.ebit;
    const rev = history[i]?.revenues;
    if (ebit == null || rev == null) return `FY-${i}: insufficient data.`;
    return `FY-${i} pre-tax op margin = EBIT / Revenue = ${fmtM(ebit)} / ${fmtM(rev)} = ${((ebit / rev) * 100).toFixed(2)}%\nSource: IQ_EBIT / IQ_TOTAL_REV × IQ_FY-${i}.`;
  };
  const scTip = (i: number) => {
    const rev = history[i]?.revenues;
    const eq = history[i]?.bv_equity;
    const debt = history[i]?.bv_debt;
    const cash = history[i]?.cash_and_marketable_securities;
    if (rev == null || eq == null || debt == null || cash == null) return `FY-${i}: insufficient data.`;
    const ic = eq + debt - cash;
    return `FY-${i} S/C = Revenue / IC (current-year)\nIC = BV Equity + BV Debt − Cash = ${fmtM(eq)} + ${fmtM(debt)} − ${fmtM(cash)} = ${fmtM(ic)}\nS/C = ${fmtM(rev)} / ${fmtM(ic)} = ${(rev / ic).toFixed(3)}×\nSources: IQ_TOTAL_REV, IQ_TOTAL_EQUITY, IQ_TOTAL_DEBT, IQ_CASH_EQUIV × IQ_FY-${i}.`;
  };
  const roicTip = (i: number) => {
    const f = history[i];
    const prev = history[i + 1];
    if (!f || !prev || f.ebit == null || prev.bv_equity == null || prev.bv_debt == null || prev.cash_and_marketable_securities == null) {
      return `FY-${i} ROIC: need EBIT_${i} + prior-year (FY-${i + 1}) BV Equity, BV Debt, Cash.`;
    }
    const eff = f.total_tax_expense != null && f.earnings_before_tax && f.earnings_before_tax > 0
      ? f.total_tax_expense / f.earnings_before_tax
      : 0.21;
    const nopat = f.ebit * (1 - eff);
    const icPrev = prev.bv_equity + prev.bv_debt - prev.cash_and_marketable_securities;
    return `FY-${i} ROIC = NOPAT / prior-year IC\nNOPAT = EBIT × (1 − eff.tax)\n      = ${fmtM(f.ebit)} × (1 − ${(eff * 100).toFixed(2)}%) = ${fmtM(nopat)}\nIC[FY-${i + 1}] = ${fmtM(prev.bv_equity)} + ${fmtM(prev.bv_debt)} − ${fmtM(prev.cash_and_marketable_securities)} = ${fmtM(icPrev)}\nROIC = ${fmtM(nopat)} / ${fmtM(icPrev)} = ${icPrev !== 0 ? ((nopat / icPrev) * 100).toFixed(2) : '—'}%`;
  };

  return (
    <section className="my-4 bg-white border border-slate-200 rounded-md p-3">
      <h3 className="text-sm font-semibold text-slate-800 mb-1">
        Historical detail — 10 years of every metric
      </h3>
      <p className="text-xs text-slate-500 mb-3">
        Every cell hover shows the exact per-year calculation pulled from CIQ historical fields.
        Averages on the right use both arithmetic (simple mean, each year = 1 data point) and,
        where financially warranted, a second method: <strong>CAGR</strong> for revenue growth
        (geometric, immune to volatility) and <strong>NOPAT-weighted</strong> for ROIC
        (Σ NOPAT / Σ IC, robust when IC varies year-to-year).
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="text-left px-2 py-1 bg-slate-100 border border-slate-300 font-semibold text-slate-700">Metric</th>
              {yearLabels.map((lbl) => (
                <th key={lbl} className="px-1 py-1 bg-slate-100 border border-slate-300 font-mono font-semibold text-slate-700">{lbl}</th>
              ))}
              <th className="px-2 py-1 bg-emerald-100 border border-emerald-300 font-semibold text-emerald-800">3-yr avg</th>
              <th className="px-2 py-1 bg-emerald-100 border border-emerald-300 font-semibold text-emerald-800">5-yr avg</th>
              <th className="px-2 py-1 bg-emerald-100 border border-emerald-300 font-semibold text-emerald-800">10-yr avg</th>
              <th className="px-2 py-1 bg-amber-100 border border-amber-300 font-semibold text-amber-800">Secondary</th>
            </tr>
          </thead>
          <tbody>
            {/* Revenue Growth */}
            <tr>
              <td className="px-2 py-1 border border-slate-300 bg-slate-50 text-slate-700">
                Revenue Growth
                <div className="text-[9px] text-slate-500 italic">(Rev[t] − Rev[t−1]) / Rev[t−1]</div>
              </td>
              {yearLabels.map((_, i) => (
                <td key={i} title={growthTip(i)} className="px-1 py-1 border border-slate-300 bg-sky-50 text-center font-mono cursor-help">
                  {pct(cf?.historical_revenue_growth_by_year?.[i], 1)}
                </td>
              ))}
              <td title="Arithmetic mean of last 3 annual growth rates." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_revenue_growth_avg_3yr)}</td>
              <td title="Arithmetic mean of last 5 annual growth rates." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_revenue_growth_avg_5yr)}</td>
              <td title="Arithmetic mean of last 10 annual growth rates." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_revenue_growth_avg_10yr)}</td>
              <td title="CAGR (geometric) = (Rev[FY-0] / Rev[FY-5])^(1/5) − 1.&#10;Financially correct multi-period growth measure; immune to volatility. Use when comparing against a single forward growth rate." className="px-2 py-1 border border-amber-300 bg-amber-50 text-center font-mono cursor-help">
                <div className="text-[9px] text-amber-700">CAGR 5-yr</div>
                <div>{pct(cf?.historical_revenue_cagr_5yr)}</div>
              </td>
            </tr>

            {/* Pre-tax Operating Margin */}
            <tr>
              <td className="px-2 py-1 border border-slate-300 bg-slate-50 text-slate-700">
                Pre-tax Op Margin
                <div className="text-[9px] text-slate-500 italic">EBIT / Revenue</div>
              </td>
              {yearLabels.map((_, i) => (
                <td key={i} title={marginTip(i)} className="px-1 py-1 border border-slate-300 bg-sky-50 text-center font-mono cursor-help">
                  {pct(cf?.historical_margin_by_year?.[i], 1)}
                </td>
              ))}
              <td title="Arithmetic mean of last 3 annual margins." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_margin_avg_3yr)}</td>
              <td title="Arithmetic mean of last 5 annual margins." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_margin_avg_5yr)}</td>
              <td title="Arithmetic mean of last 10 annual margins." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_margin_avg_10yr)}</td>
              <td className="px-2 py-1 border border-amber-300 bg-amber-50 text-center font-mono text-slate-400">—</td>
            </tr>

            {/* Sales / Capital */}
            <tr>
              <td className="px-2 py-1 border border-slate-300 bg-slate-50 text-slate-700">
                Sales / Capital
                <div className="text-[9px] text-slate-500 italic">Revenue / (BV Eq + R&D + BV Debt − Cash)</div>
              </td>
              {yearLabels.map((_, i) => (
                <td key={i} title={scTip(i)} className="px-1 py-1 border border-slate-300 bg-sky-50 text-center font-mono cursor-help">
                  {dec(cf?.historical_s_c_by_year?.[i], 2)}
                </td>
              ))}
              <td title="Arithmetic mean of last 3 annual S/C ratios." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{dec(cf?.historical_s_c_avg_3yr)}</td>
              <td title="Arithmetic mean of last 5 annual S/C ratios." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{dec(cf?.historical_s_c_avg_5yr)}</td>
              <td title="Arithmetic mean of last 10 annual S/C ratios." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{dec(cf?.historical_s_c_avg_10yr)}</td>
              <td className="px-2 py-1 border border-amber-300 bg-amber-50 text-center font-mono text-slate-400">—</td>
            </tr>

            {/* ROIC */}
            <tr>
              <td className="px-2 py-1 border border-slate-300 bg-slate-50 text-slate-700">
                ROIC
                <div className="text-[9px] text-slate-500 italic">NOPAT / prior-year IC, per-year effective tax</div>
              </td>
              {yearLabels.map((_, i) => (
                <td key={i} title={roicTip(i)} className="px-1 py-1 border border-slate-300 bg-sky-50 text-center font-mono cursor-help">
                  {pct(cf?.historical_roic_by_year?.[i], 1)}
                </td>
              ))}
              <td title="Arithmetic mean of last 3 annual ROICs." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_roic_avg_3yr)}</td>
              <td title="Arithmetic mean of last 5 annual ROICs." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_roic_avg_5yr)}</td>
              <td title="Arithmetic mean of last 10 annual ROICs." className="px-2 py-1 border border-slate-300 bg-emerald-50 text-center font-mono">{pct(cf?.historical_roic_avg_10yr)}</td>
              <td title="NOPAT-weighted ROIC = Σ NOPAT / Σ prior-year IC over 5 years.&#10;More robust than arithmetic mean when IC varies year-to-year." className="px-2 py-1 border border-amber-300 bg-amber-50 text-center font-mono cursor-help">
                <div className="text-[9px] text-amber-700">Weighted 5-yr</div>
                <div>{pct(cf?.historical_roic_weighted_5yr)}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
