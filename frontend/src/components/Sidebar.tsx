import { NavLink } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { adminWhoami } from '../api/client';

// Order reflects the valuation workflow: inputs → adjustments & WACC → outputs → cross-checks.
const NAV = [
  // Inputs & data prep
  { to: '/',                  label: '1. Input Sheet' },
  { to: '/ttm',               label: '2. Trailing 12 Month' },
  // Adjustments & Cost of Capital
  { to: '/rd',                label: '3. R&D Converter' },
  { to: '/leases',            label: '4. Lease Converter' },
  { to: '/rating',            label: '5. Synthetic Rating' },
  { to: '/wacc',              label: '6. Cost of Capital' },
  { to: '/failure',           label: '7. Failure Rate' },
  { to: '/options',           label: '8. Option Value' },
  // Valuation output
  { to: '/valuation-output',  label: '9. Valuation Output' },
  { to: '/summary',           label: '10. Summary Sheet' },
  { to: '/stories',           label: '11. Stories to Numbers' },
  { to: '/picture',           label: '12. Valuation as Picture' },
  // Cross-checks & references
  { to: '/relative',          label: '13. Relative Valuation' },
  { to: '/diagnostics',       label: '14. Diagnostics' },
  { to: '/answers',           label: '15. Answer Keys' },
];

export default function Sidebar() {
  // The admin link only renders when the server has configured
  // AD_CC_ADMIN_TOKEN AND the browser has a stored token that matches.
  // Plain users never see the link; cloners of the open-source repo
  // start with admin disabled until they set their own token.
  const [adminVisible, setAdminVisible] = useState(false);
  useEffect(() => {
    adminWhoami().then((w) => setAdminVisible(w.configured)).catch(() => setAdminVisible(false));
  }, []);

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
        {adminVisible && (
          <>
            <div className="mt-3 mb-1 px-2 text-[10px] uppercase text-slate-400 tracking-wide">Admin</div>
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `px-3 py-1.5 rounded text-xs transition-colors ${
                  isActive
                    ? 'bg-amber-100 text-amber-800 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              ⚙ Data Sources
            </NavLink>
          </>
        )}
      </nav>
    </aside>
  );
}
