import { NavLink } from 'react-router-dom';

const NAV = [
  { to: '/',                  label: '1. Input Sheet' },
  { to: '/summary',           label: '2. Summary Sheet' },
  { to: '/valuation-output',  label: '3. Valuation Output' },
  { to: '/relative',          label: '4. Relative Valuation' },
  { to: '/stories',           label: '5. Stories to Numbers' },
  { to: '/picture',           label: '6. Valuation as Picture' },
  { to: '/diagnostics',       label: '7. Diagnostics' },
  { to: '/options',           label: '8. Option Value' },
  { to: '/rating',            label: '9. Synthetic Rating' },
  { to: '/rd',                label: '10. R&D Converter' },
  { to: '/leases',            label: '11. Lease Converter' },
  { to: '/wacc',              label: '12. Cost of Capital' },
  { to: '/failure',           label: '13. Failure Rate' },
  { to: '/ttm',               label: '14. Trailing 12 Month' },
  { to: '/answers',           label: '15. Answer Keys' },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 min-h-screen p-3">
      <h1 className="text-base font-bold mb-4 px-2">Valuation Sheets</h1>
      <nav className="flex flex-col gap-0.5">
        {NAV.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded text-xs transition-colors ${
                isActive
                  ? 'bg-blue-100 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
