import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, Flag, ScrollText, ShieldAlert, Siren, Zap } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { StatCard } from '../components/StatCard'
import { Card } from '../components/Card'
import { LiveToggle } from '../components/LiveToggle'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { StatusBadge } from '../components/StatusBadge'
import { SeverityBadge } from '../components/SeverityBadge'
import {
  AlertsOverTimeChart,
  SeverityDonutChart,
  TopSourceIpsChart,
  EventTypeDistributionChart,
  IncidentStatusPieChart,
} from '../components/Charts'
import { getApiErrorMessage } from '../services/client'
import { formatDateTime } from '../utils/format'
import { useDashboardStats } from '../hooks/queries/useDashboard'
import { useRecentAlertsQuery } from '../hooks/queries/useAlerts'

export default function Dashboard() {
  const navigate = useNavigate()
  const [live, setLive] = useState(true)

  const { data: stats, isLoading, isError, error, refetch, dataUpdatedAt } = useDashboardStats(live)
  const { data: recentAlerts } = useRecentAlertsQuery(live)

  if (isLoading) return <LoadingSpinner label="Loading dashboard..." />
  if (isError) return <ErrorBanner message={getApiErrorMessage(error, 'Failed to load dashboard statistics.')} onRetry={() => refetch()} />
  if (!stats) return <EmptyState message="No statistics available." />

  const counts = stats.alert_counts_by_severity ?? { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : null

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
          icon={Siren}
          onClick={() => navigate('/alerts?severity=CRITICAL')}
        />
        <StatCard
          label="High Alerts"
          value={counts.HIGH ?? 0}
          accentClassName="text-orange-500"
          icon={AlertTriangle}
          onClick={() => navigate('/alerts?severity=HIGH')}
        />
        <StatCard
          label="Medium Alerts"
          value={counts.MEDIUM ?? 0}
          accentClassName="text-yellow-500"
          icon={ShieldAlert}
          onClick={() => navigate('/alerts?severity=MEDIUM')}
        />
        <StatCard
          label="Low Alerts"
          value={counts.LOW ?? 0}
          accentClassName="text-blue-400"
          icon={ShieldAlert}
          onClick={() => navigate('/alerts?severity=LOW')}
        />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Open Incidents" value={stats.open_incidents} icon={Flag} onClick={() => navigate('/incidents?status=OPEN')} />
        <StatCard label="Active Agents" value={stats.active_agents} icon={Zap} onClick={() => navigate('/agents')} />
        <StatCard label="Total Alerts" value={stats.total_alerts} icon={ShieldAlert} onClick={() => navigate('/alerts')} />
        <StatCard label="Logs Processed" value={stats.total_log_events} icon={ScrollText} onClick={() => navigate('/logs')} />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Alert Timeline">
          <AlertsOverTimeChart data={stats.alerts_over_time} />
        </Card>
        <Card title="Alert Severity Distribution" actions={<span className="text-[11px] text-slate-600">click a slice</span>}>
          <SeverityDonutChart data={counts} onSliceClick={(severity) => navigate(`/alerts?severity=${severity}`)} />
        </Card>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Attack Type Distribution" actions={<span className="text-[11px] text-slate-600">click a bar</span>}>
          <EventTypeDistributionChart
            data={stats.event_type_distribution}
            onBarClick={(eventType) => navigate(`/logs?event_type=${encodeURIComponent(eventType)}`)}
          />
        </Card>
        <Card title="Top Source IPs" actions={<span className="text-[11px] text-slate-600">click a bar</span>}>
          <TopSourceIpsChart data={stats.top_source_ips} onBarClick={(ip) => navigate(`/alerts?source_ip=${encodeURIComponent(ip)}`)} />
        </Card>
      </div>

      <div className="mb-6">
        <Card title="Recent Alerts" actions={<Link to="/alerts" className="text-xs text-brand-400 hover:underline">View all</Link>}>
          {recentAlerts && recentAlerts.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2">Title</th>
                    <th className="px-3 py-2">Source IP</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {recentAlerts.map((alert) => (
                    <tr
                      key={alert.id}
                      onClick={() => navigate(`/alerts/${alert.id}`)}
                      className="cursor-pointer border-b border-slate-900 hover:bg-slate-800/40"
                    >
                      <td className="px-3 py-2">
                        <SeverityBadge severity={alert.severity} />
                      </td>
                      <td className="px-3 py-2 text-slate-200">{alert.title}</td>
                      <td className="px-3 py-2 font-mono-ids text-slate-400">{alert.source_ip ?? '—'}</td>
                      <td className="px-3 py-2">
                        <StatusBadge status={alert.status} />
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(alert.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message="No alerts recorded yet." />
          )}
        </Card>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Incident Status Distribution" actions={<span className="text-[11px] text-slate-600">click a slice</span>}>
          <IncidentStatusPieChart data={stats.incident_status_distribution} onSliceClick={(status) => navigate(`/incidents?status=${status}`)} />
        </Card>

        <Card title="Recent Investigations" actions={<Link to="/investigations" className="text-xs text-brand-400 hover:underline">View all</Link>}>
          {stats.recent_investigations?.length ? (
            <ul className="divide-y divide-slate-800">
              {stats.recent_investigations.map((inv) => (
                <li key={inv.id} className="grid grid-cols-[auto_1fr_auto_auto_auto] items-center gap-3 py-2 text-sm">
                  <Link
                    to={`/investigations/${inv.id}`}
                    title={inv.id}
                    className="truncate font-mono-ids text-brand-400 hover:underline"
                  >
                    INV-{inv.id.slice(0, 8)}
                  </Link>
                  <span className="truncate text-slate-500">{inv.alert_id ? `Alert #${inv.alert_id}` : '—'}</span>
                  <StatusBadge status={inv.status} />
                  <span className="text-slate-400">{inv.risk_score ?? '—'}</span>
                  <span className="whitespace-nowrap text-xs text-slate-500">{formatDateTime(inv.created_at)}</span>
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
                <Link to={`/website-scans/${scan.id}`} className="font-mono-ids text-brand-400 hover:underline">
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
