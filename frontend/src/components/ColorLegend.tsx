const LEGEND = [
  { label: 'Manual input',         bg: 'bg-amber-50 border-amber-200' },
  { label: 'Retrieved from source',bg: 'bg-sky-50 border-sky-200' },
  { label: 'Reference data',       bg: 'bg-slate-50 border-slate-200' },
  { label: 'Calculated',           bg: 'bg-emerald-50 border-emerald-200' },
];

export default function ColorLegend() {
  return (
    <div className="flex flex-wrap gap-4 mb-4 px-3 py-2 bg-white rounded border border-slate-200 text-xs">
      {LEGEND.map(({ label, bg }) => (
        <div key={label} className="flex items-center gap-1.5">
          <span className={`inline-block w-3 h-3 border rounded-sm ${bg}`} />
          <span className="text-slate-600">{label}</span>
        </div>
      ))}
    </div>
  );
}
