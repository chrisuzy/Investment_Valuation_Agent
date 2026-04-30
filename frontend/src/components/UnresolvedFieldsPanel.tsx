import { useState } from 'react';
import type { UnresolvedField, ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';

/**
 * Top-of-page banner + inline resolution panel for fields that couldn't be
 * auto-resolved during CIQ ingestion. Surfaces:
 *   - Industry (when ticker not in indname.xlsx + not in supplemental_companies.json)
 *   - Country (when CIQ returns blank or unknown country)
 *   - Stock-price currency (when exchange prefix unmapped)
 *   - Effective tax rate (when CIQ returns #N/A)
 *   - Marginal tax rate (when country not in countrytaxrates.xls)
 *   - FX rate (when currencies differ but CIQ template didn't return reporting-ccy price)
 *   - Shares outstanding (when CIQ returns blank)
 *
 * On submit, PATCHes all resolved fields and the backend re-runs the valuation.
 */

interface Props {
  data: ValuationResponse;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
}

export default function UnresolvedFieldsPanel({ data, onPatch }: Props) {
  const unresolved = data.unresolved_fields ?? [];
  const [expanded, setExpanded] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (unresolved.length === 0) return null;

  const requiredCount = unresolved.filter(f => f.required).length;
  const infoCount = unresolved.length - requiredCount;

  async function submit() {
    if (!onPatch) return;
    setSubmitting(true);
    try {
      for (const field of unresolved) {
        const raw = drafts[field.path];
        if (raw === undefined || raw === '') continue;
        let value: PatchValue = raw;
        if (field.kind === 'number') {
          const n = parseFloat(raw);
          if (!Number.isNaN(n)) value = n;
        } else if (field.kind === 'percentage') {
          // Accept "15" (→0.15) or "0.15". Heuristic: if > 1, divide by 100.
          const n = parseFloat(raw);
          if (!Number.isNaN(n)) value = n > 1 ? n / 100 : n;
        }
        await onPatch(field.path, value);
      }
      setDrafts({});
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={`mb-3 px-3 py-2 rounded border text-xs ${
      requiredCount > 0
        ? 'bg-amber-50 border-amber-300 text-amber-900'
        : 'bg-sky-50 border-sky-300 text-sky-900'
    }`}>
      <div className="flex items-center justify-between">
        <div>
          <span className="font-bold mr-2">
            {requiredCount > 0 ? '⚠' : 'ℹ'} {requiredCount} field{requiredCount === 1 ? '' : 's'} need your input
          </span>
          {infoCount > 0 && <span className="text-gray-600">({infoCount} informational)</span>}
          <span className="ml-3 text-gray-700">
            — {unresolved.map(f => f.path.split('.').pop()).join(', ')}
          </span>
        </div>
        <button
          onClick={() => setExpanded(e => !e)}
          className="px-2 py-0.5 text-xs bg-white border border-amber-400 rounded hover:bg-amber-100"
        >
          {expanded ? 'Hide' : 'Resolve now'}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 bg-white border border-amber-200 rounded p-3 text-gray-800 space-y-3">
          {unresolved.map(field => (
            <FieldRow
              key={field.path}
              field={field}
              draft={drafts[field.path] ?? ''}
              onChange={val => setDrafts(d => ({ ...d, [field.path]: val }))}
            />
          ))}
          <div className="flex justify-end pt-2 border-t border-gray-100">
            <button
              onClick={submit}
              disabled={submitting || Object.keys(drafts).length === 0 || !onPatch}
              className="px-3 py-1 text-xs font-semibold bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300"
            >
              {submitting ? 'Saving…' : `Submit ${Object.keys(drafts).filter(k => drafts[k] !== '').length} value(s)`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function FieldRow({
  field,
  draft,
  onChange,
}: {
  field: UnresolvedField;
  draft: string;
  onChange: (v: string) => void;
}) {
  const label = field.path.split('.').pop() || field.path;

  // Choose input widget based on kind
  let input: React.ReactNode;
  const hasOptions = field.options && field.options.length > 0;
  if (hasOptions) {
    input = (
      <select
        value={draft}
        onChange={e => onChange(e.target.value)}
        className="w-full max-w-md border border-gray-300 rounded px-2 py-1 text-xs"
      >
        <option value="">— select —</option>
        {field.options!.map(o => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    );
  } else if (field.kind === 'percentage') {
    input = (
      <div className="inline-flex items-center gap-1">
        <input
          type="number"
          step="0.01"
          value={draft}
          onChange={e => onChange(e.target.value)}
          placeholder={field.suggestion != null ? `suggestion: ${(Number(field.suggestion) * 100).toFixed(2)}` : 'e.g. 25 for 25%'}
          className="w-48 border border-gray-300 rounded px-2 py-1 text-xs"
        />
        <span className="text-gray-500">%</span>
      </div>
    );
  } else {
    input = (
      <input
        type="number"
        step="any"
        value={draft}
        onChange={e => onChange(e.target.value)}
        placeholder={field.suggestion != null ? `suggestion: ${field.suggestion}` : ''}
        className="w-48 border border-gray-300 rounded px-2 py-1 text-xs"
      />
    );
  }

  return (
    <div className="grid grid-cols-[200px_1fr] gap-3 items-start">
      <div>
        <div className="font-semibold">{label}</div>
        <div className="text-[10px] text-gray-500 font-mono">{field.path}</div>
        {field.current_value != null && (
          <div className="text-[10px] text-gray-400">current: {String(field.current_value)}</div>
        )}
        {!field.required && <div className="text-[10px] text-sky-600 mt-0.5">informational</div>}
      </div>
      <div>
        <div className="text-gray-700 mb-1">{field.reason}</div>
        {input}
      </div>
    </div>
  );
}
