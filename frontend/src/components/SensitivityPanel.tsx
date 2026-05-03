import { useState, useEffect, useRef, useMemo } from 'react';
import type { ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';
import { fetchSensitivity } from '../api/client';
import type { SensitivityResponse, SensitivityBar } from './sensitivity/types';
import { ARCHETYPES, closestArchetype, percentile } from './sensitivity/archetype_definitions';

/**
 * Damodaran-grade sensitivity panel.
 *
 * Three stacked sections:
 *
 *   1. Impact ranking — tornado chart: for each of the 8 canonical drivers,
 *      how much does VPS move if we flex from industry Q1 to Q3 (or canonical
 *      range). Served by POST /api/valuation/{sid}/sensitivity; re-fetches
 *      after every slider commit so the ranking adapts to the operating point.
 *
 *   2. Drivers — the same 8 drivers as sliders, ranked by impact, annotated
 *      with industry Q1/median/Q3 markers and a live percentile chip. Each
 *      slider commits (debounced 300 ms) back to the engine via PATCH.
 *
 *   3. Story archetypes — six preset buttons (Disruptor / Growth / Mature /
 *      Utility / Cyclical / Distressed), each sets all 8 drivers coherently
 *      to that story's plausible values. The button closest to the user's
 *      current dials is highlighted.
 *
 * Live impact cards (VPS, market price, P/V, operating-asset value) live on
 * the right of the sliders so the user sees their tweak land immediately.
 */

interface Props {
  data: ValuationResponse;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
  /** For multi-field patches (e.g. archetype presets). */
  onPatchMany?: (overrides: Record<string, PatchValue>) => void | Promise<void>;
}

function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null) return '—';
  return (v * 100).toFixed(digits) + '%';
}
function fmtMoney(v: number | null | undefined, ccy: string | null | undefined): string {
  if (v == null) return '—';
  const prefix = ccy ? `${ccy} ` : '';
  return prefix + v.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

export default function SensitivityPanel({ data, onPatch, onPatchMany }: Props) {
  const sessionId = data.id;
  const va = data.inputs.valuation_assumptions;
  const mc = data.inputs.methodology_choices;
  const fin0 = data.inputs.raw_financials[0];
  const industry = data.inputs.industry_data;
  const ccy = data.inputs.reporting_currency ?? '';

  // --- Tornado data ---
  const [tornado, setTornado] = useState<SensitivityResponse | null>(null);
  const [tornadoLoading, setTornadoLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setTornadoLoading(true);
    fetchSensitivity(sessionId, ctrl.signal)
      .then((resp) => { if (!ctrl.signal.aborted) setTornado(resp); })
      .catch(() => { /* aborted or errored — silent */ })
      .finally(() => { if (!ctrl.signal.aborted) setTornadoLoading(false); });
    return () => ctrl.abort();
  }, [sessionId, data]);   // re-fetches whenever data updates (e.g. after a patch)

  // --- Ranked driver list ---
  const rankedBars = useMemo<SensitivityBar[]>(() => {
    if (!tornado) return [];
    return [...tornado.bars].sort((a, b) => {
      const sa = Math.abs(a.delta_hi ?? 0) + Math.abs(a.delta_lo ?? 0);
      const sb = Math.abs(b.delta_hi ?? 0) + Math.abs(b.delta_lo ?? 0);
      return sb - sa;
    });
  }, [tornado]);

  // --- Debounced patch ---
  const commitTimer = useRef<number | null>(null);
  const scheduleCommit = (path: string, value: PatchValue) => {
    if (!onPatch) return;
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    commitTimer.current = window.setTimeout(() => {
      onPatch(path, value);
      commitTimer.current = null;
    }, 300);
  };
  useEffect(() => () => {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
  }, []);

  // --- Live impact cards ---
  const vps = data.final?.value_per_share ?? null;
  const opAssets = data.dcf?.value_of_operating_assets ?? null;
  const mktPrice = fin0?.stock_price ?? null;
  const ratio = vps != null && mktPrice != null && vps !== 0 ? mktPrice / vps : null;

  // --- Archetype tracking ---
  const currentArchetype = useMemo(() => closestArchetype(data), [data]);

  return (
    <section className="mt-6 bg-white border border-slate-200 rounded-md shadow-sm">
      <header className="px-4 py-3 border-b border-slate-200 bg-slate-50 rounded-t-md">
        <h2 className="text-sm font-semibold text-slate-800">What-if sensitivity</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Tornado ranks the 8 canonical Damodaran drivers by how much they move VPS over industry Q1–Q3 (or
          canonical) ranges. Sliders are ordered by that ranking. Archetype buttons set all 8 drivers to a
          story-coherent preset.
        </p>
      </header>

      {/* ── Section 1: Tornado ── */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11px] font-semibold text-slate-700 uppercase tracking-wide">
            Value driver impact ranking
          </div>
          <div className="text-[10px] text-slate-500">
            {tornadoLoading ? 'Recomputing…' : tornado?.baseline_vps != null ? `Baseline: ${fmtMoney(tornado.baseline_vps, tornado.currency)}` : ''}
          </div>
        </div>
        <Tornado bars={rankedBars} baseline={tornado?.baseline_vps ?? null} currency={tornado?.currency ?? ccy} />
      </div>

      {/* ── Section 2: Sliders + impact cards ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 px-4 pb-4">
        <div className="lg:col-span-2">
          <div className="text-[11px] font-semibold text-slate-700 uppercase tracking-wide mb-2">
            Drivers <span className="text-slate-500 normal-case font-normal tracking-normal">— ranked by impact, industry markers where available</span>
          </div>
          <div className="space-y-1.5">
            {rankedBars.map((bar, rank) => (
              <DriverSlider
                key={bar.driver}
                rank={rank + 1}
                bar={bar}
                data={data}
                industry={industry}
                currentValue={readDriverValue(data, bar.driver)}
                onChange={(v) => scheduleCommit(bar.patch_path, v)}
              />
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <ImpactCard label="Value per share (DCF)" value={fmtMoney(vps, ccy)} accent="emerald" />
          <ImpactCard label="Market price" value={fmtMoney(mktPrice, data.inputs.stock_price_currency)} accent="sky" />
          <ImpactCard
            label="Price / Value"
            value={ratio != null ? `${ratio.toFixed(2)}×` : '—'}
            subtle={ratio != null ? (ratio > 1 ? 'Overvalued on DCF' : 'Undervalued on DCF') : undefined}
            accent={ratio == null ? 'slate' : ratio > 1 ? 'rose' : 'emerald'}
          />
          <ImpactCard label="Operating-asset value" value={fmtMoney(opAssets, ccy)} subtle={ccy ? `${ccy} millions` : undefined} accent="slate" />
          <p className="text-[11px] text-slate-500 leading-relaxed pt-1">
            Slider commits debounce ~300 ms. Tornado re-ranks on each commit.
          </p>
        </div>
      </div>

      {/* ── Section 3: Archetype presets ── */}
      <div className="border-t border-slate-200 bg-slate-50/50 px-4 py-3 rounded-b-md">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11px] font-semibold text-slate-700 uppercase tracking-wide">Story archetypes</div>
          <div className="text-[10px] text-slate-500">
            Sets all 8 drivers to Damodaran's canonical values for that story
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {ARCHETYPES.map((a) => (
            <button
              key={a.id}
              onClick={() => {
                if (!onPatchMany) return;
                onPatchMany(a.build(data));
              }}
              className={`flex flex-col items-center justify-center min-w-[104px] px-3 py-2 rounded-md border text-xs transition-colors ${
                currentArchetype === a.id
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
              title={`Load ${a.name} preset: ${a.tagline}`}
              disabled={!onPatchMany}
            >
              <span className="text-base leading-none mb-1">{a.emoji}</span>
              <span className="font-semibold">{a.name}</span>
              <span className={`text-[10px] mt-0.5 ${currentArchetype === a.id ? 'text-slate-300' : 'text-slate-500'}`}>{a.tagline}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Tornado chart (custom SVG) ────────────────────────────────────────────

function Tornado({ bars, baseline, currency }: { bars: SensitivityBar[]; baseline: number | null; currency: string | null }) {
  if (bars.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-sm text-slate-400 border border-dashed border-slate-300 rounded">
        Computing sensitivity…
      </div>
    );
  }
  // Extents for scaling
  const maxAbs = Math.max(
    1e-6,
    ...bars.map((b) => Math.max(Math.abs(b.delta_lo ?? 0), Math.abs(b.delta_hi ?? 0))),
  );

  // Layout constants
  const LABEL_W = 150;
  const CHART_W = 380; // plotting area (half on each side, so total axis span = 2 × (CHART_W/2))
  const ROW_H = 22;
  const GAP = 4;
  const TOTAL_W = LABEL_W + CHART_W + 64; // +64 for delta labels at bar ends
  const TOTAL_H = bars.length * (ROW_H + GAP) + 24;
  const CENTER_X = LABEL_W + CHART_W / 2;

  const scaleX = (delta: number) => (delta / maxAbs) * (CHART_W / 2);

  return (
    <div className="bg-slate-50/40 border border-slate-200 rounded p-3 overflow-x-auto">
      <svg width={TOTAL_W} height={TOTAL_H} className="block min-w-full" role="img" aria-label="Sensitivity tornado chart">
        {/* Axis label */}
        <text x={LABEL_W} y={12} fontSize="10" fill="#64748b">Lower VPS</text>
        <text x={CENTER_X} y={12} textAnchor="middle" fontSize="10" fill="#0f172a" fontWeight="600">
          {baseline != null ? `${currency ?? ''} ${baseline.toFixed(2)}`.trim() : 'Baseline'}
        </text>
        <text x={LABEL_W + CHART_W - 60} y={12} fontSize="10" fill="#64748b">Higher VPS</text>

        {bars.map((b, i) => {
          const y = 20 + i * (ROW_H + GAP);
          const dLo = b.delta_lo ?? 0;
          const dHi = b.delta_hi ?? 0;
          const wLo = Math.abs(scaleX(dLo));
          const wHi = Math.abs(scaleX(dHi));
          return (
            <g key={b.driver}>
              {/* label */}
              <text x={LABEL_W - 8} y={y + ROW_H / 2 + 3} textAnchor="end" fontSize="11" fill="#334155">
                {b.label}
              </text>
              {/* lo bar (negative side — red) */}
              {dLo < 0 && (
                <rect x={CENTER_X - wLo} y={y + 2} width={wLo} height={ROW_H - 4} fill="#fca5a5" rx="2" />
              )}
              {dLo > 0 && (
                <rect x={CENTER_X} y={y + 2} width={wLo} height={ROW_H - 4} fill="#bbf7d0" rx="2" />
              )}
              {/* hi bar (positive side — green) */}
              {dHi > 0 && (
                <rect x={CENTER_X} y={y + 2} width={wHi} height={ROW_H - 4} fill="#86efac" rx="2" />
              )}
              {dHi < 0 && (
                <rect x={CENTER_X - wHi} y={y + 2} width={wHi} height={ROW_H - 4} fill="#fecaca" rx="2" />
              )}
              {/* delta value labels */}
              {dLo !== 0 && (
                <text x={CENTER_X - wLo - 4} y={y + ROW_H / 2 + 3} textAnchor="end" fontSize="10" fill="#7f1d1d" fontWeight="600">
                  {dLo >= 0 ? '+' : ''}{dLo.toFixed(1)}
                </text>
              )}
              {dHi !== 0 && (
                <text x={CENTER_X + wHi + 4} y={y + ROW_H / 2 + 3} textAnchor="start" fontSize="10" fill="#14532d" fontWeight="600">
                  {dHi >= 0 ? '+' : ''}{dHi.toFixed(1)}
                </text>
              )}
            </g>
          );
        })}
        {/* center axis line */}
        <line x1={CENTER_X} y1={16} x2={CENTER_X} y2={TOTAL_H - 4} stroke="#0f172a" strokeWidth="1.5" />
      </svg>
    </div>
  );
}

// ── Driver slider ─────────────────────────────────────────────────────────

function DriverSlider({
  rank, bar, data, industry, currentValue, onChange,
}: {
  rank: number;
  bar: SensitivityBar;
  data: ValuationResponse;
  industry: ValuationResponse['inputs']['industry_data'];
  currentValue: number;
  onChange: (v: number) => void;
}) {
  // Map the driver's patch_path back to a display format and industry reference
  const meta = useMemo(() => getDriverMeta(bar, industry), [bar, industry]);

  // Slider range = sweep range with 15% padding beyond (user might want to go outside industry Q1/Q3)
  const padSpan = (bar.range_hi - bar.range_lo) * 0.3;
  const sliderMin = bar.range_lo - padSpan;
  const sliderMax = bar.range_hi + padSpan;
  const span = sliderMax - sliderMin;

  const pct = percentile(currentValue, bar.range_lo, (bar.range_lo + bar.range_hi) / 2, bar.range_hi);

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-slate-50 border border-slate-200 rounded">
      <span className="inline-block bg-slate-900 text-white text-[10px] font-bold px-1.5 py-0.5 rounded min-w-[26px] text-center">
        #{rank}
      </span>
      <span className="text-xs text-slate-700 font-medium w-[148px] truncate">{bar.label}</span>
      <div className="flex-1 relative h-4">
        {/* industry markers */}
        <div className="absolute inset-x-0 top-1.5 h-1 bg-slate-200 rounded" />
        <MarkerTick pos={(bar.range_lo - sliderMin) / span} color="#94a3b8" label="Q1" />
        <MarkerTick pos={((bar.range_lo + bar.range_hi) / 2 - sliderMin) / span} color="#334155" label="med" bold />
        <MarkerTick pos={(bar.range_hi - sliderMin) / span} color="#94a3b8" label="Q3" />
        <input
          type="range"
          min={sliderMin}
          max={sliderMax}
          step={meta.step}
          value={currentValue}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
          style={{ zIndex: 2 }}
        />
        <div
          className="absolute top-1 h-2 bg-sky-500 rounded"
          style={{
            left: 0,
            width: `${Math.max(0, Math.min(1, (currentValue - sliderMin) / span)) * 100}%`,
          }}
        />
        <div
          className="absolute top-0 w-3 h-4 bg-sky-600 rounded-sm border-2 border-white shadow pointer-events-none"
          style={{
            left: `calc(${Math.max(0, Math.min(1, (currentValue - sliderMin) / span)) * 100}% - 6px)`,
          }}
        />
      </div>
      <span className="min-w-[56px] text-right text-xs font-semibold text-slate-900 bg-emerald-50 border border-emerald-200 rounded px-2 py-0.5 tabular-nums">
        {meta.format(currentValue)}
      </span>
      <span className="w-10 text-right text-[10px] text-slate-500 tabular-nums">
        {bar.range_source === 'industry_q1_q3' && pct != null ? `p${Math.round(pct)}` : 'n/a'}
      </span>
    </div>
  );
}

function MarkerTick({ pos, color, label, bold = false }: { pos: number; color: string; label: string; bold?: boolean }) {
  const left = `${Math.max(0, Math.min(1, pos)) * 100}%`;
  return (
    <>
      <div
        className="absolute top-0 w-[1.5px] h-3 pointer-events-none"
        style={{ left, backgroundColor: color, height: bold ? '14px' : '10px', top: bold ? '-1px' : '1px' }}
      />
      <span
        className="absolute text-[8.5px] pointer-events-none"
        style={{ left, color, transform: 'translate(-50%, 14px)' }}
      >
        {label}
      </span>
    </>
  );
}

// ── Impact card ───────────────────────────────────────────────────────────

const ACCENT_CLASSES: Record<string, string> = {
  emerald: 'border-emerald-200 bg-emerald-50',
  sky:     'border-sky-200 bg-sky-50',
  rose:    'border-rose-200 bg-rose-50',
  slate:   'border-slate-200 bg-slate-50',
};

function ImpactCard({ label, value, subtle, accent = 'slate' }: {
  label: string;
  value: string;
  subtle?: string;
  accent?: 'emerald' | 'sky' | 'rose' | 'slate';
}) {
  return (
    <div className={`rounded border px-3 py-2 ${ACCENT_CLASSES[accent]}`}>
      <div className="text-[11px] text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold text-slate-800 tabular-nums">{value}</div>
      {subtle && <div className="text-[11px] text-slate-500 mt-0.5">{subtle}</div>}
    </div>
  );
}

// ── Driver metadata helpers ────────────────────────────────────────────────

interface DriverMeta {
  step: number;
  format: (v: number) => string;
}

function getDriverMeta(bar: SensitivityBar, _industry: ValuationResponse['inputs']['industry_data']): DriverMeta {
  switch (bar.driver) {
    case 'revenue_growth_next_year':
    case 'revenue_growth_years_2_5':
    case 'growth_perpetuity_rate':
    case 'target_operating_margin':
    case 'failure_probability':
      return { step: 0.005, format: (v) => `${(v * 100).toFixed(2)}%` };
    case 'margin_convergence_year':
      return { step: 1, format: (v) => `${Math.round(v)}` };
    case 'sales_to_capital_high':
      return { step: 0.1, format: (v) => v.toFixed(2) };
    case 'wacc_level_shift_bps':
      return { step: 10, format: (v) => `${v >= 0 ? '+' : ''}${Math.round(v)}bp` };
    default:
      return { step: 0.01, format: (v) => v.toFixed(2) };
  }
}

function readDriverValue(data: ValuationResponse, driver: string): number {
  const va = data.inputs.valuation_assumptions;
  const mc = data.inputs.methodology_choices;
  switch (driver) {
    case 'revenue_growth_next_year':   return va.revenue_growth_next_year ?? 0;
    case 'revenue_growth_years_2_5':   return va.revenue_growth_years_2_5 ?? 0;
    case 'growth_perpetuity_rate':     return va.growth_perpetuity_rate ?? (data.inputs.macro_inputs?.risk_free_rate ?? 0.04);
    case 'target_operating_margin':    return va.target_operating_margin ?? 0.15;
    case 'margin_convergence_year':    return va.margin_convergence_year ?? 5;
    case 'sales_to_capital_high':      return va.sales_to_capital_high ?? 2.5;
    case 'wacc_level_shift_bps':       return (mc as any)?.wacc_level_shift_bps ?? 0;
    case 'failure_probability':        return va.failure_probability ?? 0;
    default: return 0;
  }
}
