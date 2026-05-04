/**
 * Tax-rate override for years 1–5 (Issue 1 from the Lenovo anomaly audit).
 *
 * Shows the firm's last 5 historical annual effective tax rates + 3-yr and
 * 5-yr averages, then exposes an editable override cell with preset buttons
 * so the analyst can replace the aberrant FY-0 effective with a smoothed
 * historical anchor. Years 6–10 convergence to marginal is unchanged.
 *
 * Grounded in user direction in the brainstorm session + the folder's
 * `module_05_dcf_projection.md §3.4` which prescribes the years 1–5
 * flat-at-effective behavior this override customizes.
 */

import { useState, useEffect } from 'react';
import type { ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';

interface Props {
  data: ValuationResponse;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
}

const OVERRIDE_PATH = 'valuation_assumptions.effective_tax_rate_override_years_1_5';

function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '—';
  return `${(v * 100).toFixed(digits)}%`;
}

export default function TaxOverridePanel({ data, onPatch }: Props) {
  const th = data.inputs.tax_history;
  const macroEff = data.inputs.macro_inputs?.tax_rate_effective ?? null;
  const marginal = data.inputs.macro_inputs?.tax_rate_marginal ?? null;
  const current = data.inputs.valuation_assumptions.effective_tax_rate_override_years_1_5;

  // Local editable state (debounce applied via onBlur commit)
  const [draft, setDraft] = useState<string>(
    current != null ? `${(current * 100).toFixed(2)}` : '',
  );

  useEffect(() => {
    setDraft(current != null ? `${(current * 100).toFixed(2)}` : '');
  }, [current]);

  const commitPct = (pctStr: string) => {
    if (!onPatch) return;
    const trimmed = pctStr.trim();
    if (trimmed === '') {
      void onPatch(OVERRIDE_PATH, null);
      return;
    }
    const asNum = parseFloat(trimmed);
    if (Number.isNaN(asNum)) return;
    void onPatch(OVERRIDE_PATH, asNum / 100);
  };

  const applyPreset = (value: number | null) => {
    if (!onPatch) return;
    void onPatch(OVERRIDE_PATH, value);
  };

  const yearly = th?.yearly ?? [];
  const avg3 = th?.avg_3yr ?? null;
  const avg5 = th?.avg_5yr ?? null;
  const yearLabels = ['FY-0', 'FY-1', 'FY-2', 'FY-3', 'FY-4'];
  const yearlyPadded = Array.from({ length: 5 }, (_, i) => yearly[i] ?? null);

  return (
    <section className="my-3 bg-white border border-slate-200 rounded-md p-3">
      <h3 className="text-sm font-semibold text-slate-800 mb-1">
        Tax rate — years 1–5 override
      </h3>
      <p className="text-xs text-slate-500 mb-3">
        Folder default: hold the firm's current effective rate flat for years 1–5, then
        linearly converge to the marginal rate over years 6–10. When the most-recent
        effective rate is an outlier (NOL use, one-time items, etc.), the analyst can
        override the years 1–5 value here. Base year display is unchanged;
        years 6–10 convergence is unchanged.
      </p>

      {/* Historical annual row */}
      <div className="grid grid-cols-7 gap-1 text-xs mb-2">
        <div className="text-slate-500 font-medium">Historical</div>
        {yearlyPadded.map((v, i) => (
          <div
            key={i}
            className="bg-sky-50 border border-sky-200 rounded px-2 py-1 text-center font-mono"
          >
            <div className="text-[9px] text-slate-500">{yearLabels[i]}</div>
            <div className="text-slate-900">{fmtPct(v)}</div>
          </div>
        ))}
        <div className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">Marginal</div>
          <div className="text-slate-900">{fmtPct(marginal)}</div>
        </div>
      </div>

      {/* Averages row */}
      <div className="grid grid-cols-7 gap-1 text-xs mb-3">
        <div className="text-slate-500 font-medium">Averages</div>
        <div className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">3-yr avg</div>
          <div className="text-slate-900">{fmtPct(avg3)}</div>
        </div>
        <div className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">5-yr avg</div>
          <div className="text-slate-900">{fmtPct(avg5)}</div>
        </div>
        <div className="col-span-4" />
      </div>

      {/* Override row */}
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-xs font-medium text-slate-700">
          Override (years 1–5):
        </label>
        <input
          type="number"
          step="0.1"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => commitPct(draft)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitPct(draft);
          }}
          placeholder="— (using base-year effective)"
          className="px-2 py-1 border border-amber-300 bg-amber-50 rounded font-mono text-xs w-32"
        />
        <span className="text-xs text-slate-500">%</span>
        <span className="text-xs text-slate-400 italic">
          Current: {current != null ? fmtPct(current) : `base-year (${fmtPct(macroEff)})`}
        </span>
      </div>

      {/* Preset buttons */}
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-xs text-slate-500">Presets:</span>
        <button
          onClick={() => applyPreset(macroEff)}
          disabled={macroEff == null}
          className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40"
        >
          Use base year ({fmtPct(macroEff)})
        </button>
        <button
          onClick={() => applyPreset(avg3)}
          disabled={avg3 == null}
          className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40"
        >
          Use 3-yr avg ({fmtPct(avg3)})
        </button>
        <button
          onClick={() => applyPreset(avg5)}
          disabled={avg5 == null}
          className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40"
        >
          Use 5-yr avg ({fmtPct(avg5)})
        </button>
        <button
          onClick={() => applyPreset(marginal)}
          disabled={marginal == null}
          className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40"
        >
          Use marginal ({fmtPct(marginal)})
        </button>
        <button
          onClick={() => applyPreset(null)}
          className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100"
        >
          Clear override
        </button>
      </div>
    </section>
  );
}
