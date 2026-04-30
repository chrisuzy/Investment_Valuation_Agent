import type { ValuationResponse } from '../types/valuation';
import { fmtFxRate } from '../lib/currency';

/**
 * Top-of-page banner showing reporting ccy + listing ccy + FX rate.
 * When they match (MSFT, TSLA etc.), collapses to a single-line note.
 * When they differ (Lenovo, BABA) shows full conversion context.
 */
export default function CurrencyBanner({ data }: { data: ValuationResponse }) {
  const reporting = data.inputs.reporting_currency;
  const listing = data.inputs.stock_price_currency;
  const fxRate = data.inputs.fx_rate;
  const fxSource = data.inputs.fx_rate_source;
  const fxDate = data.inputs.fx_rate_date;

  if (!reporting && !listing) return null;

  const sameCcy = reporting && listing && reporting === listing;
  const unavailable = !sameCcy && fxRate == null;

  if (sameCcy) {
    return (
      <div className="mb-3 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded text-xs text-gray-600">
        <span className="font-semibold">Currency:</span> {reporting}
        <span className="ml-2 text-gray-400">(reporting = listing — no FX conversion)</span>
      </div>
    );
  }

  if (unavailable) {
    return (
      <div className="mb-3 px-3 py-2 bg-amber-50 border border-amber-300 rounded text-xs text-amber-900">
        <div className="font-bold mb-0.5">⚠ Currency mismatch — FX rate unavailable</div>
        <div>
          Reporting currency <span className="font-semibold">{reporting || "?"}</span> ≠ Listing currency{' '}
          <span className="font-semibold">{listing || "?"}</span>. Without an FX rate, WACC and VPS may compare numbers in different currencies.
          Re-run the CIQ template with the updated version that fetches the reporting-currency stock price.
        </div>
        <div className="mt-1 text-amber-700">FX source: {fxSource}</div>
      </div>
    );
  }

  return (
    <div className="mb-3 px-3 py-2 bg-sky-50 border border-sky-300 rounded text-xs">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <span className="font-semibold text-gray-700">Reporting:</span>{' '}
          <span className="font-mono">{reporting || '?'}</span>
        </div>
        <div className="text-gray-400">·</div>
        <div>
          <span className="font-semibold text-gray-700">Listing:</span>{' '}
          <span className="font-mono">{listing || '?'}</span>
        </div>
        <div className="text-gray-400">·</div>
        <div className="font-mono text-sky-900">
          {fmtFxRate(fxRate, listing, reporting, fxSource, fxDate)}
        </div>
      </div>
      <div className="mt-1 text-gray-500 text-[11px]">
        All DCF math (WACC, VPS, bridge) is in <span className="font-semibold">{reporting}</span>.
        Stock price displayed in <span className="font-semibold">{listing}</span> to match broker view.
      </div>
    </div>
  );
}
