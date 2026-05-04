/**
 * Validation card for one of the three stories (Growth / Margin / Capital
 * Efficiency). Renders four rows:
 *   1. Historical annual — last 5 FY values
 *   2. Averages — 3-yr and 5-yr means
 *   3. Industry — median + Q1–Q3 range
 *   4. Reverse check (optional) — factual gap statement against historical
 *
 * Grounded in `docs/Ginzu understanding/three_story_joint_examination.md §3.4`.
 */

interface ReverseCheck {
  label: string;
  required: number | null;
  actual: number | null;
  unit: 'pp' | '×';
}

interface Props {
  title: string;
  historical: (number | null)[];   // most-recent-first, up to 5
  avg3: number | null;
  avg5: number | null;
  industryMedian: number | null;
  industryQ1: number | null;
  industryQ3: number | null;
  formatAs: 'pct' | 'dec';
  reverseCheck?: ReverseCheck;
}

function format(v: number | null | undefined, mode: 'pct' | 'dec'): string {
  if (v == null || Number.isNaN(v)) return '—';
  if (mode === 'pct') return `${(v * 100).toFixed(1)}%`;
  return v.toFixed(2);
}

export default function StoryValidationBlock({
  title,
  historical,
  avg3,
  avg5,
  industryMedian,
  industryQ1,
  industryQ3,
  formatAs,
  reverseCheck,
}: Props) {
  // Labels for historical cells: FY-0 (most recent) on the left.
  const histLabels = ['FY-0', 'FY-1', 'FY-2', 'FY-3', 'FY-4'];
  const histPadded = Array.from({ length: 5 }, (_, i) => historical[i] ?? null);

  // Reverse-check gap
  let gapText = '';
  if (reverseCheck) {
    const { required, actual, unit } = reverseCheck;
    if (required != null && actual != null) {
      const delta = required - actual;
      const sign = delta >= 0 ? '+' : '';
      gapText =
        unit === 'pp'
          ? `${sign}${(delta * 100).toFixed(1)}pp`
          : `${sign}${delta.toFixed(2)}×`;
    } else {
      gapText = '—';
    }
  }

  return (
    <section className="my-3 bg-white border border-slate-200 rounded-md p-3">
      <h3 className="text-sm font-semibold text-slate-800 mb-2">{title}</h3>

      {/* Historical annual row */}
      <div className="grid grid-cols-6 gap-1 text-xs mb-1">
        <div className="text-slate-500 font-medium">Historical annual</div>
        {histPadded.map((v, i) => (
          <div
            key={i}
            className="bg-sky-50 border border-sky-200 rounded px-2 py-1 text-center font-mono"
          >
            <div className="text-[9px] text-slate-500">{histLabels[i]}</div>
            <div className="text-slate-900">{format(v, formatAs)}</div>
          </div>
        ))}
      </div>

      {/* Averages row */}
      <div className="grid grid-cols-6 gap-1 text-xs mb-1">
        <div className="text-slate-500 font-medium">Averages</div>
        <div className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">3-yr</div>
          <div className="text-slate-900">{format(avg3, formatAs)}</div>
        </div>
        <div className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">5-yr</div>
          <div className="text-slate-900">{format(avg5, formatAs)}</div>
        </div>
        <div className="col-span-3" />
      </div>

      {/* Industry row */}
      <div className="grid grid-cols-6 gap-1 text-xs mb-1">
        <div className="text-slate-500 font-medium">Industry (Damodaran)</div>
        <div className="bg-slate-100 border border-slate-300 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">Median</div>
          <div className="text-slate-900">{format(industryMedian, formatAs)}</div>
        </div>
        <div className="bg-slate-100 border border-slate-300 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">Q1</div>
          <div className="text-slate-900">{format(industryQ1, formatAs)}</div>
        </div>
        <div className="bg-slate-100 border border-slate-300 rounded px-2 py-1 text-center font-mono">
          <div className="text-[9px] text-slate-500">Q3</div>
          <div className="text-slate-900">{format(industryQ3, formatAs)}</div>
        </div>
        <div className="col-span-2" />
      </div>

      {/* Reverse-check row */}
      {reverseCheck && (
        <div className="mt-2 p-2 bg-emerald-50 border border-emerald-200 rounded text-xs">
          <span className="font-medium text-slate-700">{reverseCheck.label}: </span>
          <span className="font-mono text-emerald-800 font-semibold">
            {format(reverseCheck.required, formatAs)}
          </span>
          <span className="text-slate-500">
            {' '}| Historical 5-yr avg:{' '}
          </span>
          <span className="font-mono text-slate-800">
            {format(reverseCheck.actual, formatAs)}
          </span>
          <span className="text-slate-500"> | Gap: </span>
          <span
            className={
              gapText.startsWith('+')
                ? 'font-mono font-semibold text-amber-700'
                : gapText.startsWith('-')
                ? 'font-mono font-semibold text-sky-700'
                : 'font-mono text-slate-500'
            }
          >
            {gapText}
          </span>
        </div>
      )}
    </section>
  );
}
