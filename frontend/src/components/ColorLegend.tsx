const LEGEND = [
  { label: 'Hypothesis / User Input', bg: 'bg-yellow-100 border-yellow-300' },
  { label: 'Retrieved Financial Data', bg: 'bg-blue-100 border-blue-300' },
  { label: 'Retrieved Reference Data', bg: 'bg-purple-100 border-purple-300' },
  { label: 'Calculated Output', bg: 'bg-green-100 border-green-300' },
];

export default function ColorLegend() {
  return (
    <div className="flex gap-4 mb-4 p-2 bg-gray-50 rounded border border-gray-200 text-xs">
      {LEGEND.map(({ label, bg }) => (
        <div key={label} className="flex items-center gap-1.5">
          <span className={`inline-block w-4 h-4 border rounded ${bg}`} />
          <span className="text-gray-600">{label}</span>
        </div>
      ))}
    </div>
  );
}
