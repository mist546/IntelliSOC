import { NavLink } from 'react-router-dom'
import {
  Activity,
  BookOpen,
  BrainCircuit,
  Flag,
  FileBarChart2,
  Globe,
  LayoutDashboard,
  ScanSearch,
  ScrollText,
  Radar,
  Server,
  Settings,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Overview',
    items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Detection & Response',
    items: [
      { to: '/alerts', label: 'Alerts', icon: ShieldAlert },
      { to: '/investigations', label: 'Investigations', icon: ScanSearch },
      { to: '/logs', label: 'Logs', icon: ScrollText },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/threat-intel', label: 'Threat Intelligence', icon: Radar },
      { to: '/knowledge-base', label: 'Knowledge Base', icon: BookOpen },
      { to: '/ai-analysis', label: 'AI Analysis', icon: BrainCircuit },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/incidents', label: 'Incidents', icon: Flag },
      { to: '/website-scans', label: 'Website Scans', icon: Globe },
      { to: '/agents', label: 'Agents', icon: Server },
      { to: '/reports', label: 'Reports', icon: FileBarChart2 },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/system-health', label: 'System Health', icon: Activity },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
]

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, logout } = useAuth()
  const initials = (user?.username ?? '?').slice(0, 2).toUpperCase()

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950 transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between gap-2 border-b border-slate-800 px-4 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-red-600 text-white shadow-lg shadow-brand-900/40">
              <ShieldCheck className="h-5 w-5" strokeWidth={2.25} />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight text-slate-100">IntelliSOC</p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Agentic AI SOC</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-200 lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-4">
              <p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-wider text-slate-600">
                {group.label}
              </p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `mb-0.5 flex items-center gap-3 rounded-full px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-950/40'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'
                    }`
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" strokeWidth={2} />
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-800 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-300">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-100">{user?.username ?? 'Unknown'}</p>
              <p className="text-xs text-slate-500">{user?.role ?? '—'}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-3 w-full rounded-md border border-slate-700 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
          >
            Log out
          </button>
        </div>
      </aside>
    </>
  )
}
