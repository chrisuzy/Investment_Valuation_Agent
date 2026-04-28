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
}

const TYPE_STYLES: Record<CellType, string> = {
  hypothesis: 'bg-yellow-100 border-yellow-300',
  financial: 'bg-blue-100 border-blue-300',
  reference: 'bg-purple-100 border-purple-300',
  calc: 'bg-green-100 border-green-300',
  label: 'bg-white border-gray-200',
  hint: 'bg-white border-gray-200 text-red-500 text-xs italic',
  header: 'bg-gray-100 border-gray-300 font-bold text-center',
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

  const baseClasses = `border px-1.5 py-0.5 whitespace-nowrap ${TYPE_STYLES[type]} ${ALIGN_MAP[align]} ${bold ? 'font-bold' : ''} ${className}`;

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

  return (
    <td
      colSpan={colSpan}
      rowSpan={rowSpan}
      className={`${baseClasses} ${editable ? 'cursor-pointer hover:ring-2 hover:ring-yellow-400' : ''} ${tooltip ? 'cursor-help' : ''}`}
      onDoubleClick={startEdit}
      style={width ? { width } : undefined}
      title={tooltip}
    >
      {formatValue(value)}
    </td>
  );
}
