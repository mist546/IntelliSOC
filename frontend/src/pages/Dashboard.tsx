import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { StatCard } from '../components/StatCard'
import { Card } from '../components/Card'
import { LiveToggle } from '../components/LiveToggle'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { StatusBadge } from '../components/StatusBadge'
import {
  AlertsOverTimeChart,
  SeverityDonutChart,
  TopSourceIpsChart,
  EventTypeDistributionChart,
  IncidentStatusPieChart,
} from '../components/Charts'
import type { DashboardStatistics } from '../types'
import { getApiErrorMessage, getDashboardStatistics } from '../services/api'
import { formatDateTime } from '../utils/format'
import { usePolling } from '../hooks/usePolling'

const POLL_INTERVAL_MS = 20000

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const load = useCallback((showSpinner = true) => {
    if (showSpinner) setLoading(true)
    setError(null)
    getDashboardStatistics()
      .then((data) => {
        setStats(data)
        setLastUpdated(new Date())
      })
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load dashboard statistics.')))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => load(true), [load])
  usePolling(() => load(false), POLL_INTERVAL_MS, live)

  if (loading) return <LoadingSpinner label="Loading dashboard..." />
  if (error) return <ErrorBanner message={error} onRetry={() => load(true)} />
  if (!stats) return <EmptyState message="No statistics available." />

  const counts = stats.alert_counts_by_severity ?? { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Real-time overview of security posture - click any chart to drill in"
        actions={<LiveToggle live={live} onToggle={() => setLive((v) => !v)} lastUpdated={lastUpdated} />}
      />

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Critical Alerts"
          value={counts.CRITICAL ?? 0}
          accentClassName="text-red-500"
          onClick={() => navigate('/alerts?severity=CRITICAL')}
        />
        <StatCard
          label="High Alerts"
          value={counts.HIGH ?? 0}
          accentClassName="text-orange-500"
          onClick={() => navigate('/alerts?severity=HIGH')}
        />
        <StatCard
          label="Medium Alerts"
          value={counts.MEDIUM ?? 0}
          accentClassName="text-yellow-500"
          onClick={() => navigate('/alerts?severity=MEDIUM')}
        />
        <StatCard
          label="Low Alerts"
          value={counts.LOW ?? 0}
          accentClassName="text-blue-400"
          onClick={() => navigate('/alerts?severity=LOW')}
        />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Open Incidents" value={stats.open_incidents} onClick={() => navigate('/incidents?status=OPEN')} />
        <StatCard label="Active Agents" value={stats.active_agents} onClick={() => navigate('/agents')} />
        <StatCard label="Total Alerts" value={stats.total_alerts} onClick={() => navigate('/alerts')} />
        <StatCard label="Total Log Events" value={stats.total_log_events} onClick={() => navigate('/logs')} />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Alerts Over Time">
          <AlertsOverTimeChart data={stats.alerts_over_time} />
        </Card>
        <Card title="Severity Distribution" actions={<span className="text-[11px] text-slate-600">click a slice</span>}>
          <SeverityDonutChart data={counts} onSliceClick={(severity) => navigate(`/alerts?severity=${severity}`)} />
        </Card>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Top Source IPs" actions={<span className="text-[11px] text-slate-600">click a bar</span>}>
          <TopSourceIpsChart data={stats.top_source_ips} onBarClick={(ip) => navigate(`/alerts?source_ip=${encodeURIComponent(ip)}`)} />
        </Card>
        <Card title="Event Type Distribution" actions={<span className="text-[11px] text-slate-600">click a bar</span>}>
          <EventTypeDistributionChart
            data={stats.event_type_distribution}
            onBarClick={(eventType) => navigate(`/logs?event_type=${encodeURIComponent(eventType)}`)}
          />
        </Card>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Incident Status Distribution" actions={<span className="text-[11px] text-slate-600">click a slice</span>}>
          <IncidentStatusPieChart data={stats.incident_status_distribution} onSliceClick={(status) => navigate(`/incidents?status=${status}`)} />
        </Card>

        <Card title="Recent Investigations">
          {stats.recent_investigations?.length ? (
            <ul className="divide-y divide-slate-800">
              {stats.recent_investigations.map((inv) => (
                <li key={inv.id} className="flex items-center justify-between py-2 text-sm">
                  <Link to={`/investigations/${inv.id}`} className="font-mono-ids text-sky-400 hover:underline">
                    INV-{inv.id}
                  </Link>
                  <span className="text-slate-500">Alert #{inv.alert_id}</span>
                  <StatusBadge status={inv.status} />
                  <span className="text-slate-400">{inv.risk_score ?? '—'}</span>
                  <span className="text-xs text-slate-500">{formatDateTime(inv.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="No investigations run yet." />
          )}
        </Card>
      </div>

      <Card title="Recent Website Scans">
        {stats.recent_website_scans?.length ? (
          <ul className="divide-y divide-slate-800">
            {stats.recent_website_scans.map((scan) => (
              <li key={scan.id} className="flex items-center justify-between py-2 text-sm">
                <Link to={`/website-scans/${scan.id}`} className="font-mono-ids text-sky-400 hover:underline">
                  {scan.target_url}
                </Link>
                <StatusBadge status={scan.status} />
                <span className="text-xs text-slate-500">{formatDateTime(scan.started_at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="No website scans run yet." />
        )}
      </Card>
    </div>
  )
}
