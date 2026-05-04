/**
 * Top-of-page summary strip for the three-story joint examination.
 *
 * Displays the implied ROIC and implied S/C that the analyst's three
 * stories require, alongside historical (5-yr avg), industry median,
 * and WACC anchors. No severity scoring — raw numbers plus a factual
 * gap statement. Analyst reads the comparison and judges.
 *
 * Grounded in `docs/Ginzu understanding/three_story_joint_examination.md §3`.
 */

import type { ValuationResponse } from '../types/valuation';
import { requiredROIC, requiredSC, gapStatement } from '../lib/reverseChecks';

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

export default function ClosedLoopStrip({ data }: Props) {
  const cf = data.cashflow;
  const va = data.inputs.valuation_assumptions;
  const ind = data.inputs.industry_data;
  const wacc = data.cost_of_capital?.wacc ?? null;

  // Story-implied required values — from the analyst's inputs.
  const impliedROIC = requiredROIC(
    va.target_operating_margin,
    va.sales_to_capital_high,
  );
  // ROIC anchor for required-S/C: prefer roic_stable_override, then hist 5yr avg, else WACC.
  const roicAnchor =
    va.roic_stable_override ?? cf?.historical_roic_avg_5yr ?? wacc;
  const impliedSCReq = requiredSC(roicAnchor, va.target_operating_margin);

  // Historical (5yr avg) and industry references
  const histROIC = cf?.historical_roic_avg_5yr ?? null;
  const histSC = cf?.historical_s_c_avg_5yr ?? null;
  const indROIC = ind?.roic ?? null;
  const indSC = ind?.sales_to_capital ?? null;

  // Gaps
  const roicGapHist = gapStatement(impliedROIC, histROIC, 'pp');
  const roicGapInd = gapStatement(impliedROIC, indROIC, 'pp');
  const roicGapWacc = gapStatement(impliedROIC, wacc, 'pp');
  const scGapHist = gapStatement(impliedSCReq, histSC, '×');
  const scGapInd = gapStatement(impliedSCReq, indSC, '×');

  // Terminal state invariant
  const terminalImplied = data.dcf?.implied_roic_terminal ?? null;
  const terminalWACC = va.cost_of_capital_stable_override ?? wacc;

  return (
    <section className="my-4 bg-white border border-slate-300 rounded-md shadow-sm p-3">
      <h3 className="text-sm font-semibold text-slate-800 mb-2">
        Closed-loop summary — what your three stories require
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-6 gap-2 text-xs">
        {/* ROIC row */}
        <div className="md:col-span-6 border-b border-slate-200 pb-2">
          <div className="font-semibold text-slate-700 mb-1">Required ROIC</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 items-baseline">
            <span className="text-emerald-700 font-mono font-semibold text-sm">
              {pct(impliedROIC)}
            </span>
            <span className="text-slate-500">
              vs Historical 5-yr avg: <span className="font-mono text-slate-800">{pct(histROIC)}</span> <span className="text-slate-400">({roicGapHist})</span>
            </span>
            <span className="text-slate-500">
              vs Industry median: <span className="font-mono text-slate-800">{pct(indROIC)}</span> <span className="text-slate-400">({roicGapInd})</span>
            </span>
            <span className="text-slate-500">
              vs WACC: <span className="font-mono text-slate-800">{pct(wacc)}</span> <span className="text-slate-400">({roicGapWacc})</span>
            </span>
          </div>
        </div>

        {/* S/C row */}
        <div className="md:col-span-6 border-b border-slate-200 pb-2">
          <div className="font-semibold text-slate-700 mb-1">Required Sales/Capital</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 items-baseline">
            <span className="text-emerald-700 font-mono font-semibold text-sm">
              {dec(impliedSCReq)}
            </span>
            <span className="text-slate-500">
              vs Historical 5-yr avg: <span className="font-mono text-slate-800">{dec(histSC)}</span> <span className="text-slate-400">({scGapHist})</span>
            </span>
            <span className="text-slate-500">
              vs Industry median: <span className="font-mono text-slate-800">{dec(indSC)}</span> <span className="text-slate-400">({scGapInd})</span>
            </span>
            <span className="text-slate-400 italic">
              (anchor ROIC: {pct(roicAnchor)})
            </span>
          </div>
        </div>

        {/* Terminal row */}
        <div className="md:col-span-6">
          <div className="font-semibold text-slate-700 mb-1">Terminal state</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 items-baseline">
            <span className="text-slate-500">
              Implied terminal ROIC: <span className="font-mono text-slate-800">{pct(terminalImplied)}</span>
            </span>
            <span className="text-slate-500">
              vs Terminal WACC: <span className="font-mono text-slate-800">{pct(terminalWACC)}</span> <span className="text-slate-400">({gapStatement(terminalImplied, terminalWACC, 'pp')})</span>
            </span>
            <span className="text-slate-400 italic">
              (Damodaran: terminal ROIC should converge to WACC — no excess returns in perpetuity)
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
