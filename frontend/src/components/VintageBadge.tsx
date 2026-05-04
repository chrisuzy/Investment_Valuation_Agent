/**
 * Small color-coded chip showing the provenance of a base-year cell.
 *
 * Used by the ValuationOutput base-year column (Issue 3 from the Lenovo
 * anomaly audit) to tell the analyst which vintage each individual field
 * comes from when LTM is thin and per-field fallback kicks in.
 */

import type { VintageSource } from '../lib/baseYearVintage';

interface Props {
  source: VintageSource | null;
  className?: string;
}

const STYLES: Record<VintageSource, string> = {
  'LTM': 'bg-emerald-100 text-emerald-800 border-emerald-300',
  '10-K': 'bg-sky-100 text-sky-800 border-sky-300',
  '10-K-1': 'bg-amber-100 text-amber-800 border-amber-300',
};

const TITLES: Record<VintageSource, string> = {
  'LTM': 'Last Twelve Months (rotated from quarterly)',
  '10-K': 'Most recent annual filing (FY-0)',
  '10-K-1': 'Prior annual filing (FY-1) — LTM and FY-0 were missing this field',
};

export default function VintageBadge({ source, className = '' }: Props) {
  if (!source) return null;
  return (
    <span
      title={TITLES[source]}
      className={`inline-block ml-1 px-1 py-0 rounded text-[9px] leading-tight font-medium border ${STYLES[source]} ${className}`}
    >
      {source}
    </span>
  );
}
