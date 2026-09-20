import { FormEvent, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, Menu, Search, Settings as SettingsIcon, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useSystemHealthQuery } from '../hooks/queries/useSystemHealth'
import { useDashboardStats } from '../hooks/queries/useDashboard'

const TITLE_OVERRIDES: Record<string, string> = {
  dashboard: 'Dashboard',
  alerts: 'Alerts',
  investigations: 'Investigations',
  logs: 'Logs',
  'threat-intel': 'Threat Intelligence',
  'knowledge-base': 'Knowledge Base',
  'ai-analysis': 'AI Analysis',
  incidents: 'Incidents',
  'website-scans': 'Website Scans',
  agents: 'Agents',
  reports: 'Reports',
  'system-health': 'System Health',
  settings: 'Settings',
}

function useBreadcrumb() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)
  const root = segments[0] ?? 'dashboard'
  const title = TITLE_OVERRIDES[root] ?? root
  if (segments.length > 1) {
    return `${title} / ${segments[1]}`
  }
  return title
}

export function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const breadcrumb = useBreadcrumb()
  const { data: health } = useSystemHealthQuery(true)
  const { data: stats } = useDashboardStats(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleSearch(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    navigate(`/alerts?q=${encodeURIComponent(q)}`)
  }

  const online = health?.status === 'ok'
  const statusKnown = !!health
  const criticalCount = stats?.alert_counts_by_severity?.CRITICAL ?? 0
  const totalAlerts = stats?.total_alerts

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-slate-800 bg-slate-950/90 px-4 backdrop-blur">
      <button
        onClick={onMenuClick}
        className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      <p className="hidden truncate text-sm font-semibold text-slate-300 lg:block">{breadcrumb}</p>

      <form onSubmit={handleSearch} className="relative ml-2 hidden max-w-xs flex-1 sm:block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search alerts, IPs, hosts..."
          className="w-full rounded-full border border-slate-800 bg-slate-900/70 py-1.5 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-brand-500/60 focus:outline-none"
        />
      </form>

      <div className="ml-auto flex items-center gap-3">
        {totalAlerts !== undefined && (
          <Link
            to="/alerts"
            className={`hidden items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold sm:flex ${
              criticalCount > 0
                ? 'border-red-500/40 bg-red-500/10 text-red-300'
                : 'border-slate-700 bg-slate-900/60 text-slate-300'
            }`}
          >
            {totalAlerts} Alert{totalAlerts === 1 ? '' : 's'}
            {criticalCount > 0 && <span className="text-red-400">· {criticalCount} Critical</span>}
          </Link>
        )}
        <span
          title={statusKnown ? `Backend status: ${health.status}` : 'Checking backend status...'}
          className={`hidden items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium sm:flex ${
            !statusKnown
              ? 'border-slate-700 text-slate-500'
              : online
              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
              : 'border-red-500/40 bg-red-500/10 text-red-300'
          }`}
        >
          {!statusKnown ? (
            <ShieldCheck className="h-3.5 w-3.5 opacity-50" />
          ) : online ? (
            <ShieldCheck className="h-3.5 w-3.5" />
          ) : (
            <ShieldAlert className="h-3.5 w-3.5" />
          )}
          {!statusKnown ? 'Checking...' : online ? 'API Online' : 'API Degraded'}
        </span>

        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold text-slate-300">
              {(user?.username ?? '?').slice(0, 2).toUpperCase()}
            </div>
            <span className="hidden max-w-[8rem] truncate md:inline">{user?.username ?? 'Unknown'}</span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 overflow-hidden rounded-lg border border-slate-800 bg-slate-900 py-1 shadow-xl animate-[scale-in_0.1s_ease-out]">
              <div className="border-b border-slate-800 px-3 py-2">
                <p className="truncate text-sm font-semibold text-slate-100">{user?.username}</p>
                <p className="text-xs text-slate-500">{user?.role}</p>
              </div>
              <Link
                to="/settings"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
              >
                <SettingsIcon className="h-4 w-4" /> Settings
              </Link>
              <button
                onClick={logout}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-300 hover:bg-red-500/10"
              >
                <LogOut className="h-4 w-4" /> Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
