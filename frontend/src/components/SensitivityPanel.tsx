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
  //
  // Currency handling: VPS is in the reporting currency (e.g. USD for a
  // firm reporting in USD). The quoted stock price can be in a DIFFERENT
  // currency (Lenovo reports USD but trades HKD). The Price/Value ratio
  // must be computed with both sides in the SAME currency — convert the
  // market price to reporting currency via the FX rate before dividing.
  // Matches the convention used by the existing ValuationOutput bridge
  // and SummarySheet "reporting-ccy basis" row.
  const vps = data.final?.value_per_share ?? null;                   // reporting ccy
  const opAssets = data.dcf?.value_of_operating_assets ?? null;      // reporting ccy
  const mktPriceListing = fin0?.stock_price ?? null;                 // listing ccy
  const listingCcy = data.inputs.stock_price_currency;
  const reportingCcy = data.inputs.reporting_currency;
  const fxRate = data.inputs.fx_rate;                                // listing → reporting
  const sameCcy = listingCcy && reportingCcy && listingCcy === reportingCcy;
  const mktPriceInReporting =
    mktPriceListing != null && (sameCcy ? mktPriceListing : fxRate != null ? mktPriceListing * fxRate : null);
  const ratio = (vps != null && mktPriceInReporting != null && vps !== 0)
    ? mktPriceInReporting / vps : null;
  const ratioUnavailable =
    !sameCcy && fxRate == null && listingCcy !== reportingCcy && listingCcy && reportingCcy;

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
              <DriverInput
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
          <ImpactCard label={`Value per share (DCF, ${reportingCcy ?? '—'})`} value={fmtMoney(vps, reportingCcy)} accent="emerald" />
          <ImpactCard
            label={`Market price (${listingCcy ?? '—'})`}
            value={fmtMoney(mktPriceListing, listingCcy)}
            subtle={
              !sameCcy && mktPriceInReporting != null && reportingCcy
                ? `≈ ${fmtMoney(mktPriceInReporting, reportingCcy)} @ FX ${fxRate?.toFixed(4)}`
                : undefined
            }
            accent="sky"
          />
          <ImpactCard
            label="Price / Value"
            value={
              ratio != null ? `${ratio.toFixed(2)}×`
              : ratioUnavailable ? 'FX unavailable'
              : '—'
            }
            subtle={
              ratio != null
                ? `${sameCcy ? 'same ccy' : `both in ${reportingCcy}`} · ${ratio > 1 ? 'Overvalued on DCF' : 'Undervalued on DCF'}`
                : ratioUnavailable
                  ? `${listingCcy}→${reportingCcy} rate missing in CIQ template`
                  : undefined
            }
            accent={ratio == null ? 'slate' : ratio > 1 ? 'rose' : 'emerald'}
          />
          <ImpactCard label="Operating-asset value" value={fmtMoney(opAssets, reportingCcy)} subtle={reportingCcy ? `${reportingCcy} millions` : undefined} accent="slate" />
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

// ── Driver input row ──────────────────────────────────────────────────────
//
// Replaces the earlier slider design: a number input box (direct edit or
// step arrows), auto-populated from the currently-committed value, with the
// industry Q1 / median / Q3 shown compactly next to it as reference numbers
// instead of as tick marks on a slider axis.

function DriverInput({
  rank, bar, data, industry, currentValue, onChange,
}: {
  rank: number;
  bar: SensitivityBar;
  data: ValuationResponse;
  industry: ValuationResponse['inputs']['industry_data'];
  currentValue: number;
  onChange: (v: number) => void;
}) {
  const meta = useMemo(() => getDriverMeta(bar, industry), [bar, industry]);
  const wide = getDriverWideBounds(bar.driver, data);

  // Draft string tracks what the user is typing; only commits on blur /
  // enter / arrow-click so the backend isn't hammered per keystroke.
  const [draft, setDraft] = useState<string>(() => meta.edit(currentValue));
  useEffect(() => { setDraft(meta.edit(currentValue)); }, [currentValue, meta]);

  const median = (bar.range_lo + bar.range_hi) / 2;
  const pct = percentile(currentValue, bar.range_lo, median, bar.range_hi);

  const commit = (raw: string) => {
    const parsed = meta.parse(raw);
    if (parsed == null) { setDraft(meta.edit(currentValue)); return; }
    const clamped = Math.max(wide.min, Math.min(wide.max, parsed));
    setDraft(meta.edit(clamped));
    if (clamped !== currentValue) onChange(clamped);
  };

  const step = (direction: 1 | -1) => {
    const next = +(currentValue + direction * meta.arrowStep).toFixed(6);
    const clamped = Math.max(wide.min, Math.min(wide.max, next));
    if (clamped !== currentValue) onChange(clamped);
  };

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded">
      <span className="inline-block bg-slate-900 text-white text-[10px] font-bold px-1.5 py-0.5 rounded min-w-[26px] text-center">
        #{rank}
      </span>
      <span className="text-xs text-slate-700 font-medium w-[148px] truncate" title={bar.label}>
        {bar.label}
      </span>

      {/* Editable input + arrow buttons */}
      <div className="flex items-center">
        <input
          type="text"
          inputMode="decimal"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={(e) => commit(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { (e.target as HTMLInputElement).blur(); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); step(1); }
            else if (e.key === 'ArrowDown') { e.preventDefault(); step(-1); }
          }}
          className="w-[84px] text-right text-xs font-semibold text-slate-900 bg-white border border-slate-300 rounded-l px-2 py-0.5 tabular-nums focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-sky-400"
          aria-label={`${bar.label} value`}
        />
        <div className="flex flex-col border border-l-0 border-slate-300 rounded-r overflow-hidden">
          <button
            type="button"
            onClick={() => step(1)}
            className="px-1 text-[9px] leading-none h-[13px] bg-white text-slate-600 hover:bg-slate-200 border-b border-slate-200"
            aria-label="Increase"
            title={`+${meta.arrowLabel}`}
          >▲</button>
          <button
            type="button"
            onClick={() => step(-1)}
            className="px-1 text-[9px] leading-none h-[13px] bg-white text-slate-600 hover:bg-slate-200"
            aria-label="Decrease"
            title={`−${meta.arrowLabel}`}
          >▼</button>
        </div>
      </div>

      {/* Industry reference — numbers, not tick marks */}
      <div className="flex-1 flex items-center gap-2 text-[10px] text-slate-500 tabular-nums pl-1 overflow-hidden">
        {bar.range_source === 'industry_q1_q3' ? (
          <>
            <ReferenceChip label="Q1"  value={meta.display(bar.range_lo)} />
            <ReferenceChip label="med" value={meta.display(median)} emphasis />
            <ReferenceChip label="Q3"  value={meta.display(bar.range_hi)} />
          </>
        ) : (
          <span className="text-slate-400 italic text-[10px]">no industry data</span>
        )}
      </div>

      {/* Percentile chip — narrow, right-aligned */}
      <span className="w-9 text-right text-[10px] text-slate-500 tabular-nums">
        {bar.range_source === 'industry_q1_q3' && pct != null ? `p${Math.round(pct)}` : ''}
      </span>
    </div>
  );
}

function ReferenceChip({ label, value, emphasis = false }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <span className={`inline-flex items-baseline gap-0.5 ${emphasis ? 'text-slate-700 font-semibold' : 'text-slate-500'}`}>
      <span className="text-[9px] uppercase tracking-wide text-slate-400">{label}</span>
      <span className="text-[10px] tabular-nums">{value}</span>
    </span>
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
  /** Increment applied by the ▲/▼ arrow buttons. */
  arrowStep: number;
  /** Short label shown in arrow button tooltip (e.g. "0.5%"). */
  arrowLabel: string;
  /** Full formatted value for display (e.g. "22.00%"). */
  display: (v: number) => string;
  /** Short formatted value used in the edit input itself (e.g. "22"). */
  edit: (v: number) => string;
  /** Parse the user's typed string back to a number. Returns null on junk. */
  parse: (raw: string) => number | null;
}

/** Parse "22" / "22%" / "0.22" / " 0.22 " → 0.22 for percentage drivers. */
function parsePct(raw: string): number | null {
  const cleaned = raw.replace(/[,\s%]/g, '').trim();
  if (!cleaned) return null;
  const n = parseFloat(cleaned);
  if (isNaN(n)) return null;
  // Heuristic: if the user typed a value > 1, they meant percent points.
  return Math.abs(n) > 1 ? n / 100 : n;
}
function parseNum(raw: string): number | null {
  const cleaned = raw.replace(/[,\s]/g, '').trim();
  if (!cleaned) return null;
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
}
function parseBps(raw: string): number | null {
  // accept "50", "50bp", "50 bps", "+50"
  const cleaned = raw.replace(/[,\s]|bps?/gi, '').trim();
  if (!cleaned) return null;
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
}

function getDriverMeta(bar: SensitivityBar, _industry: ValuationResponse['inputs']['industry_data']): DriverMeta {
  switch (bar.driver) {
    case 'revenue_growth_next_year':
    case 'revenue_growth_years_2_5':
    case 'growth_perpetuity_rate':
    case 'target_operating_margin':
    case 'failure_probability':
      return {
        arrowStep: 0.005, arrowLabel: '0.50%',
        display: (v) => `${(v * 100).toFixed(2)}%`,
        edit:    (v) => `${(v * 100).toFixed(2)}%`,
        parse:   parsePct,
      };
    case 'margin_convergence_year':
      return {
        arrowStep: 1, arrowLabel: '1 yr',
        display: (v) => `${Math.round(v)} yr`,
        edit:    (v) => `${Math.round(v)}`,
        parse:   parseNum,
      };
    case 'sales_to_capital_high':
      return {
        arrowStep: 0.1, arrowLabel: '0.1×',
        display: (v) => `${v.toFixed(2)}×`,
        edit:    (v) => v.toFixed(2),
        parse:   parseNum,
      };
    case 'wacc_level_shift_bps':
      return {
        arrowStep: 10, arrowLabel: '10 bps',
        display: (v) => `${v >= 0 ? '+' : ''}${Math.round(v)} bps`,
        edit:    (v) => `${Math.round(v)}`,
        parse:   parseBps,
      };
    default:
      return {
        arrowStep: 0.01, arrowLabel: '0.01',
        display: (v) => v.toFixed(2),
        edit:    (v) => v.toFixed(2),
        parse:   parseNum,
      };
  }
}

/** Wide, driver-specific hard bounds for the slider.
 *
 * These intentionally go far beyond industry Q1/Q3 so the user can model
 * outlier cases (distressed companies at negative margins, disruptors at
 * 80% margins, capital-intensive firms at 0.3× sales-to-capital, etc.).
 * Damodaran industry markers remain as visual tick marks on the track,
 * but they do NOT constrain the slider.
 */
function getDriverWideBounds(driver: string, data: ValuationResponse): { min: number; max: number } {
  const rf = data.inputs.macro_inputs?.risk_free_rate ?? 0.04;
  switch (driver) {
    case 'revenue_growth_next_year':    return { min: -0.30, max: 1.00 };   // -30% to +100%
    case 'revenue_growth_years_2_5':    return { min: -0.20, max: 0.60 };   // -20% to +60%
    case 'growth_perpetuity_rate':      return { min: 0.0,   max: Math.max(0.10, rf + 0.05) };  // 0% to (RF+5%)
    case 'target_operating_margin':     return { min: -0.30, max: 0.80 };   // -30% to +80%
    case 'margin_convergence_year':     return { min: 1,     max: 20 };     // 1 to 20 years
    case 'sales_to_capital_high':       return { min: 0.1,   max: 15.0 };   // 0.1× to 15×
    case 'wacc_level_shift_bps':        return { min: -500,  max: 500 };    // ±500 bps
    case 'failure_probability':         return { min: 0.0,   max: 1.0 };    // 0% to 100%
    default:                            return { min: 0,     max: 1 };
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
