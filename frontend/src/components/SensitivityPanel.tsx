import { useState, useEffect, useRef, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import type { ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';

/**
 * Interactive what-if sensitivity for the core growth / margin assumptions.
 *
 * Four sliders, each bound to a single input on valuation_assumptions:
 *   - revenue_growth_next_year       → year-1 growth
 *   - revenue_growth_years_2_5       → years 2-5 CAGR
 *   - target_operating_margin        → asymptotic margin
 *   - margin_convergence_year        → which year margin reaches target
 *
 * Each slider previews the implied 10-year path as a line chart. On commit
 * (mouseup / keyup), the value is patched and the backend re-runs; the
 * panel's summary cards then update with the new VPS and P/V ratio.
 *
 * The panel intentionally displays only the client-side *implied path*.
 * Authoritative year-by-year numbers live on the Summary Sheet.
 */

interface Props {
  data: ValuationResponse;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
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

/** Build the revenue-growth path the backend's engine uses.
 *  Year 1 = g1, Years 2-5 = g25, Years 6-10 = linear decay to g_stable. */
function growthPath(g1: number, g25: number, gStable: number): { year: number; growth: number }[] {
  const pts: { year: number; growth: number }[] = [];
  pts.push({ year: 1, growth: g1 });
  for (let y = 2; y <= 5; y++) pts.push({ year: y, growth: g25 });
  // Linear decay yrs 6-10 from g25 → g_stable
  for (let y = 6; y <= 10; y++) {
    const t = (y - 5) / 5; // 0.2, 0.4, ..., 1.0
    pts.push({ year: y, growth: g25 + (gStable - g25) * t });
  }
  return pts;
}

/** Build the operating-margin path. Year 1 = base margin, converges linearly
 *  to target by convergence year, holds flat after. */
function marginPath(base: number, target: number, convYear: number): { year: number; margin: number }[] {
  const pts: { year: number; margin: number }[] = [];
  for (let y = 1; y <= 10; y++) {
    let m: number;
    if (y >= convYear) m = target;
    else m = base + (target - base) * (y / convYear);
    pts.push({ year: y, margin: m });
  }
  return pts;
}

/** Hook: draft state + debounced commit. Keeps slider snappy while not
 *  hammering the backend; patch fires on commit() only. */
function useDraft<T>(incoming: T): {
  draft: T;
  setDraft: (v: T) => void;
  reset: () => void;
} {
  const [draft, setDraft] = useState(incoming);
  // When the backend settles and `data` changes, sync the draft.
  useEffect(() => { setDraft(incoming); /* eslint-disable-next-line */ }, [incoming]);
  return { draft, setDraft, reset: () => setDraft(incoming) };
}

export default function SensitivityPanel({ data, onPatch }: Props) {
  const va = data.inputs.valuation_assumptions;
  const macro = data.inputs.macro_inputs;
  const fin0 = data.inputs.raw_financials[0];
  const ccy = data.inputs.reporting_currency ?? '';

  // Base margin = LTM ebit / revenue (year-0 margin). Used as the starting
  // point of the margin convergence path.
  const baseMargin = useMemo(() => {
    if (!fin0 || !fin0.revenues) return 0;
    return (fin0.ebit ?? 0) / fin0.revenues;
  }, [fin0]);

  // Stable-period growth cap (Damodaran constraint: g_stable ≤ RF)
  const gStable = va.override_growth_perpetuity && va.growth_perpetuity_rate != null
    ? va.growth_perpetuity_rate
    : (macro.risk_free_rate ?? 0);

  const g1 = useDraft(va.revenue_growth_next_year);
  const g25 = useDraft(va.revenue_growth_years_2_5);
  const mTarget = useDraft(va.target_operating_margin);
  const mConv = useDraft(va.margin_convergence_year);

  // Rate-limit patch dispatch — also used if the user drags rapidly.
  const commitTimer = useRef<number | null>(null);
  const scheduleCommit = (path: string, value: number) => {
    if (!onPatch) return;
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
    commitTimer.current = window.setTimeout(() => {
      onPatch(path, value);
      commitTimer.current = null;
    }, 250);
  };
  useEffect(() => () => {
    if (commitTimer.current) window.clearTimeout(commitTimer.current);
  }, []);

  const growthData = growthPath(g1.draft, g25.draft, gStable);
  const marginData = marginPath(baseMargin, mTarget.draft, mConv.draft);

  const vps = data.final?.value_per_share ?? null;
  const opAssets = data.dcf?.value_of_operating_assets ?? null;
  const mktPrice = fin0?.stock_price ?? null;
  const ratio = vps != null && mktPrice != null && vps !== 0 ? mktPrice / vps : null;

  return (
    <section className="mt-6 bg-white border border-slate-200 rounded-md shadow-sm">
      <header className="px-4 py-3 border-b border-slate-200 bg-slate-50 rounded-t-md">
        <h2 className="text-sm font-semibold text-slate-800">What-if sensitivity</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Drag the sliders to preview how the core growth and margin assumptions reshape the 10-year projection.
          Each commit re-runs the engine and updates Value per Share, to the right.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4">
        {/* ── Left: growth controls + chart ── */}
        <div className="lg:col-span-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SliderControl
              label="Next-year revenue growth"
              value={g1.draft}
              min={-0.10} max={0.50} step={0.005}
              format="pct"
              onChange={(v) => { g1.setDraft(v); scheduleCommit('valuation_assumptions.revenue_growth_next_year', v); }}
            />
            <SliderControl
              label="Years 2–5 revenue growth (CAGR)"
              value={g25.draft}
              min={-0.05} max={0.35} step={0.005}
              format="pct"
              onChange={(v) => { g25.setDraft(v); scheduleCommit('valuation_assumptions.revenue_growth_years_2_5', v); }}
            />
          </div>

          <ChartFrame title={`Revenue growth path (decays to ${fmtPct(gStable)} stable)`}>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={growthData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <XAxis dataKey="year" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis tickFormatter={(v) => (v * 100).toFixed(0) + '%'} stroke="#64748b" fontSize={11} tickLine={false} width={38} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 4 }}
                  formatter={(v: number) => fmtPct(v)}
                  labelFormatter={(y) => `Year ${y}`}
                />
                <ReferenceLine y={gStable} stroke="#94a3b8" strokeDasharray="3 3"
                  label={{ value: 'Stable', fontSize: 10, fill: '#64748b', position: 'insideTopRight' }} />
                <Line type="monotone" dataKey="growth" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3, fill: '#0ea5e9' }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SliderControl
              label="Target operating margin"
              value={mTarget.draft}
              min={0.0} max={0.60} step={0.005}
              format="pct"
              onChange={(v) => { mTarget.setDraft(v); scheduleCommit('valuation_assumptions.target_operating_margin', v); }}
            />
            <SliderControl
              label="Margin convergence year"
              value={mConv.draft}
              min={1} max={10} step={1}
              format="num"
              onChange={(v) => { mConv.setDraft(v); scheduleCommit('valuation_assumptions.margin_convergence_year', v); }}
            />
          </div>

          <ChartFrame title={`Operating margin path (base ${fmtPct(baseMargin)} → target)`}>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={marginData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <XAxis dataKey="year" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis tickFormatter={(v) => (v * 100).toFixed(0) + '%'} stroke="#64748b" fontSize={11} tickLine={false} width={38} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 4 }}
                  formatter={(v: number) => fmtPct(v)}
                  labelFormatter={(y) => `Year ${y}`}
                />
                <ReferenceLine y={mTarget.draft} stroke="#94a3b8" strokeDasharray="3 3"
                  label={{ value: 'Target', fontSize: 10, fill: '#64748b', position: 'insideTopRight' }} />
                <Line type="monotone" dataKey="margin" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </div>

        {/* ── Right: live valuation impact ── */}
        <div className="space-y-3">
          <ImpactCard label="Value per share (DCF)"  value={fmtMoney(vps, ccy)} accent="emerald" />
          <ImpactCard label="Market price"            value={fmtMoney(mktPrice, data.inputs.stock_price_currency)} accent="sky" />
          <ImpactCard
            label="Price / Value"
            value={ratio != null ? `${ratio.toFixed(2)}×` : '—'}
            subtle={ratio != null ? (ratio > 1 ? 'Overvalued on DCF' : 'Undervalued on DCF') : undefined}
            accent={ratio == null ? 'slate' : ratio > 1 ? 'rose' : 'emerald'}
          />
          <ImpactCard
            label="Operating-asset value"
            value={fmtMoney(opAssets, ccy)}
            subtle={ccy ? `${ccy} millions` : undefined}
            accent="slate"
          />
          <p className="text-[11px] text-slate-500 leading-relaxed pt-1">
            Changes are committed to the engine ~250 ms after you release the slider.
            Full year-by-year numbers are on the Summary Sheet.
          </p>
        </div>
      </div>
    </section>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function SliderControl({ label, value, min, max, step, format, onChange }: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: 'pct' | 'num';
  onChange: (v: number) => void;
}) {
  const display = format === 'pct' ? fmtPct(value) : String(value);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs text-slate-600">{label}</label>
        <span className="text-xs font-semibold text-slate-800 tabular-nums">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-sky-600"
      />
      <div className="flex justify-between text-[10px] text-slate-400 mt-0.5 tabular-nums">
        <span>{format === 'pct' ? fmtPct(min, 0) : min}</span>
        <span>{format === 'pct' ? fmtPct(max, 0) : max}</span>
      </div>
    </div>
  );
}

function ChartFrame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-slate-200 rounded p-2 bg-slate-50/40">
      <div className="text-[11px] text-slate-600 font-medium mb-1 px-1">{title}</div>
      {children}
    </div>
  );
}

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
