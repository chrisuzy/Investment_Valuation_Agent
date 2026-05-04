/**
 * Currency Information panel — surfaces the two currencies (filing /
 * reporting and listing / trading) plus an editable FX rate so the
 * analyst can reconcile cross-listed firms whose market data comes
 * through in the listing currency even when "Reported Currency" was
 * selected in CIQ.
 *
 * Typical row:
 *   Filing: USD     Listing: HKD     FX (HKD→USD): 0.128  [edit]
 *                                    source: CIQ implied / manual / …
 *
 * Editing the FX cell patches `fx_rate` + sets `fx_rate_source = "manual"`.
 * The orchestrator's manual-FX derivation step (orchestrator.py) then
 * re-computes stock_price_reporting = stock_price × fx and
 * mv_equity = mv_equity_listing × fx on the next PATCH cycle.
 */

import { useState, useEffect } from 'react';
import type { ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';

interface Props {
  data: ValuationResponse;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
}

export default function CurrencyInfoPanel({ data, onPatch }: Props) {
  const inputs = data.inputs;
  const filing = inputs.reporting_currency ?? '—';
  const listing = inputs.stock_price_currency ?? '—';
  const fx = inputs.fx_rate;
  const fxSource = inputs.fx_rate_source ?? 'unknown';
  const sameCcy = filing !== '—' && listing !== '—' && filing === listing;

  // Local editable state for the FX rate input. Commit on Enter / blur.
  const [draft, setDraft] = useState<string>(fx != null ? fx.toFixed(6) : '');
  useEffect(() => {
    setDraft(fx != null ? fx.toFixed(6) : '');
  }, [fx]);

  const commit = (raw: string) => {
    if (!onPatch) return;
    const trimmed = raw.trim();
    if (trimmed === '') {
      void onPatch('fx_rate', null);
      return;
    }
    const n = parseFloat(trimmed);
    if (Number.isNaN(n) || n <= 0) return;
    void onPatch('fx_rate', n);
    // Mark as manual so the orchestrator knows to re-derive market reporting values.
    void onPatch('fx_rate_source', 'manual');
  };

  // Source-badge color. CIQ implied = trust; same currency = trust; manual =
  // analyst responsibility; unavailable / unknown = warn.
  const sourceBadge = (() => {
    if (sameCcy) return { label: 'same currency', cls: 'bg-slate-100 text-slate-700 border-slate-300' };
    switch (fxSource) {
      case 'CIQ implied':
        return { label: 'CIQ implied', cls: 'bg-sky-100 text-sky-800 border-sky-300' };
      case 'manual':
        return { label: 'manual override', cls: 'bg-amber-100 text-amber-800 border-amber-300' };
      case 'same currency':
        return { label: 'same currency', cls: 'bg-slate-100 text-slate-700 border-slate-300' };
      case 'unavailable':
      case 'unavailable (CIQ template missing stock_price_reporting)':
        return { label: 'unavailable — please set', cls: 'bg-rose-100 text-rose-800 border-rose-300' };
      default:
        return { label: fxSource || 'unknown', cls: 'bg-slate-100 text-slate-700 border-slate-300' };
    }
  })();

  return (
    <section className="my-3 bg-white border border-slate-200 rounded-md p-3">
      <h3 className="text-sm font-semibold text-slate-800 mb-1">
        Currency — filing, listing, and exchange rate
      </h3>
      <p className="text-xs text-slate-500 mb-2">
        CIQ's &quot;Reported Currency&quot; modifier is inert for some market fields (stock price, market cap,
        option strike) — these always arrive in the listing currency. The analyst sets the
        listing→reporting FX rate below; the orchestrator re-derives stock_price_reporting and
        mv_equity on the next run.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs items-start">
        <div>
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">Filing / Reporting</div>
          <div
            title="Currency of the company's financial statements. Income statement, balance sheet, cash flow, WACC math all use this."
            className="bg-sky-50 border border-sky-200 rounded px-2 py-1 font-mono text-slate-900 cursor-help"
          >
            {filing}
          </div>
        </div>
        <div>
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">Listing / Trading</div>
          <div
            title="Currency the stock trades in on its primary exchange. Quoted stock prices, market cap (as-traded), option strike prices come in this currency."
            className="bg-sky-50 border border-sky-200 rounded px-2 py-1 font-mono text-slate-900 cursor-help"
          >
            {listing}
          </div>
        </div>
        <div className={sameCcy ? 'opacity-60' : ''}>
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">
            FX rate ({listing} → {filing})
          </div>
          {sameCcy ? (
            <div
              title="Listing and filing currency are the same; no conversion needed."
              className="bg-slate-50 border border-slate-200 rounded px-2 py-1 font-mono text-slate-500 cursor-help"
            >
              1.000000
            </div>
          ) : (
            <input
              type="number"
              step="0.000001"
              min="0"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={() => commit(draft)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') commit(draft);
              }}
              title={`Multiplier converting ${listing} to ${filing}. Example — Lenovo (listed HKD, files USD): 1 HKD ≈ 0.128 USD, so fx = 0.128.`}
              placeholder="— (unset)"
              className="bg-amber-50 border border-amber-300 rounded px-2 py-1 font-mono text-slate-900 w-full cursor-help"
            />
          )}
        </div>
        <div>
          <div className="text-[9px] text-slate-500 uppercase tracking-wide">Source</div>
          <span
            title="How fx_rate was obtained. 'CIQ implied' = derived from CIQ template's dual price fields. 'manual override' = analyst set it explicitly. 'unavailable' = CIQ template didn't supply a reporting-ccy price for implied derivation."
            className={`inline-block px-2 py-1 rounded text-[10px] font-medium border ${sourceBadge.cls} cursor-help`}
          >
            {sourceBadge.label}
          </span>
        </div>
        <div>
          <button
            onClick={() => {
              if (!onPatch) return;
              void onPatch('fx_rate', null);
              void onPatch('fx_rate_source', 'unknown');
              setDraft('');
            }}
            disabled={sameCcy || fx == null}
            className="px-2 py-1 text-[11px] border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40 w-full"
            title="Clear manual override and revert to CIQ-implied (if available)."
          >
            Clear override
          </button>
        </div>
      </div>
    </section>
  );
}
