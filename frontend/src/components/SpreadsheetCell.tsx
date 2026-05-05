import { useState, useCallback } from 'react';

export type CellType = 'hypothesis' | 'financial' | 'reference' | 'calc' | 'label' | 'hint' | 'header';

interface SpreadsheetCellProps {
  value: string | number | null | undefined;
  type: CellType;
  editable?: boolean;
  onChange?: (value: string) => void;
  className?: string;
  colSpan?: number;
  rowSpan?: number;
  bold?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
  tooltip?: string;
  /**
   * Allow the cell content to wrap across multiple lines instead of
   * forcing the column wider. Useful for long row labels.
   */
  wrap?: boolean;
  /** Pin this cell to the top of the nearest scrolling ancestor. */
  sticky?: boolean;
}

// Soft, low-saturation tints. Each cell type keeps a distinct color family
// so the Input vs Retrieved vs Computed distinction stays readable, but the
// overall palette is calm enough for extended analyst use.
//
//   hypothesis (manual input)  → amber    — "you can change this"
//   financial  (CIQ / raw)     → sky      — "pulled in as-is"
//   reference  (Damodaran etc) → slate    — "external reference, no color"
//   calc       (engine output) → emerald  — "we computed this"
const TYPE_STYLES: Record<CellType, string> = {
  hypothesis: 'bg-amber-50 border-amber-200 text-slate-800',
  financial:  'bg-sky-50 border-sky-200 text-slate-800',
  reference:  'bg-slate-50 border-slate-200 text-slate-700',
  calc:       'bg-emerald-50 border-emerald-200 text-slate-900',
  label:      'bg-white border-slate-200 text-slate-700',
  hint:       'bg-amber-50/60 border-slate-200 text-amber-700 text-xs italic',
  header:     'bg-slate-100 border-slate-300 font-semibold text-center text-slate-700',
};

const ALIGN_MAP = { left: 'text-left', center: 'text-center', right: 'text-right' };

function formatValue(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1e6) return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (Math.abs(v) < 0.01 && v !== 0) return (v * 100).toFixed(2) + '%';
    if (Math.abs(v) < 1 && v !== 0) return (v * 100).toFixed(2) + '%';
    return v.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
  return String(v);
}

export default function SpreadsheetCell({
  value,
  type,
  editable = false,
  onChange,
  className = '',
  colSpan,
  rowSpan,
  bold = false,
  align = type === 'label' || type === 'hint' ? 'left' : 'right',
  width,
  tooltip,
  wrap = false,
  sticky = false,
}: SpreadsheetCellProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const startEdit = useCallback(() => {
    if (!editable) return;
    setDraft(value === null || value === undefined ? '' : String(value));
    setEditing(true);
  }, [editable, value]);

  const commit = useCallback(() => {
    setEditing(false);
    if (onChange) onChange(draft);
  }, [draft, onChange]);

  const wrapClass = wrap ? 'whitespace-normal leading-tight' : 'whitespace-nowrap';
  const stickyClass = sticky ? 'sticky top-0 z-20' : '';
  const baseClasses = `border px-1.5 py-0.5 ${wrapClass} ${stickyClass} ${TYPE_STYLES[type]} ${ALIGN_MAP[align]} ${bold ? 'font-bold' : ''} ${className}`;

  if (editing) {
    return (
      <td colSpan={colSpan} rowSpan={rowSpan} className={baseClasses} style={width ? { width } : undefined}>
        <input
          autoFocus
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false); }}
          className="w-full bg-transparent outline-none text-sm"
        />
      </td>
    );
  }

  const hasTip = Boolean(tooltip && tooltip.length > 0);

  return (
    <td
      colSpan={colSpan}
      rowSpan={rowSpan}
      className={`relative group ${baseClasses} ${editable ? 'cursor-pointer hover:ring-2 hover:ring-amber-400' : ''} ${hasTip ? 'cursor-help hover:ring-1 hover:ring-slate-400' : ''}`}
      onDoubleClick={startEdit}
      style={width ? { width } : undefined}
      title={tooltip || undefined}
    >
      {formatValue(value)}
      {hasTip && (
        <span
          aria-hidden="true"
          className="absolute top-0 right-0 w-1.5 h-1.5 rounded-full bg-sky-500 opacity-60 group-hover:opacity-100 pointer-events-none"
          style={{ transform: 'translate(35%, -35%)' }}
        />
      )}
    </td>
  );
}
