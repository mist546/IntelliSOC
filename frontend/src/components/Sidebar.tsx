import { NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: '▦' },
  { to: '/alerts', label: 'Alerts', icon: '⚠' },
  { to: '/incidents', label: 'Incidents', icon: '⚑' },
  { to: '/logs', label: 'Logs', icon: '☷' },
  { to: '/threat-intel', label: 'Threat Intel', icon: '☢' },
  { to: '/website-scans', label: 'Website Scans', icon: '◉' },
  { to: '/agents', label: 'Agents', icon: '⚙' },
  { to: '/reports', label: 'Reports', icon: '☷☷' },
  { to: '/settings', label: 'Settings', icon: '⚙⚙' },
]

export function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950">
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded bg-sky-500/20 text-sky-400 font-bold">
          S
        </div>
        <div>
          <p className="text-sm font-bold leading-tight text-slate-100">Mini-SOC</p>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Agentic AI SOC</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `mb-1 flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-sky-500/15 text-sky-400'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'
              }`
            }
          >
            <span className="w-4 text-center text-xs">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-800 px-4 py-3">
        <p className="truncate text-sm font-semibold text-slate-100">{user?.username ?? 'Unknown'}</p>
        <p className="text-xs text-slate-500">{user?.role ?? '—'}</p>
        <button
          onClick={logout}
          className="mt-3 w-full rounded-md border border-slate-700 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
        >
          Log out
        </button>
      </div>
    </aside>
  )
}
