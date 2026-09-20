import { useEffect, useMemo, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LiveToggle } from '../components/LiveToggle'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import type { Alert, AlertStatus } from '../types'
import { getApiErrorMessage } from '../services/client'
import { formatDateTime } from '../utils/format'
import { useAlertsQuery, useUpdateAlertStatus } from '../hooks/queries/useAlerts'
import { useSortableData } from '../hooks/useSortableData'
import { useToast } from '../hooks/useToast'
import { useConfirm } from '../hooks/useConfirm'

const SEVERITIES = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const STATUSES = ['', 'NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE']
const SEVERITY_RANK: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
const NEW_ROW_HIGHLIGHT_MS = 4000

export default function Alerts() {
  const navigate = useNavigate()
  const toast = useToast()
  const confirm = useConfirm()
  const [searchParams, setSearchParams] = useSearchParams()
  const severity = searchParams.get('severity') ?? ''
  const status = searchParams.get('status') ?? ''
  const sourceIp = searchParams.get('source_ip') ?? ''

  const [live, setLive] = useState(true)
  const [detectionType, setDetectionType] = useState('')
  const [search, setSearch] = useState(() => searchParams.get('q') ?? '')
  const [newIds, setNewIds] = useState<Set<string>>(new Set())
  const [rowUpdating, setRowUpdating] = useState<string | null>(null)

  const previousIdsRef = useRef<Set<string> | null>(null)
  const highlightTimeoutRef = useRef<number | null>(null)

  const { data, isLoading, isError, error, refetch, dataUpdatedAt } = useAlertsQuery(
    { severity: severity || undefined, status: status || undefined, source_ip: sourceIp || undefined },
    live,
  )
  const alerts = data ?? []
  const updateStatus = useUpdateAlertStatus()

  useEffect(() => {
    // `data` is undefined until the first fetch resolves - skip both the
    // loading state and (via the ref check below) the first real payload,
    // so the "new alert" toast only fires for genuine subsequent arrivals.
    if (!data) return
    if (!previousIdsRef.current) {
      previousIdsRef.current = new Set(data.map((a) => a.id))
      return
    }
    const freshIds = data.filter((a) => !previousIdsRef.current!.has(a.id)).map((a) => a.id)
    if (freshIds.length > 0) {
      setNewIds(new Set(freshIds))
      toast.info(`${freshIds.length} new alert${freshIds.length > 1 ? 's' : ''} arrived`)
      if (highlightTimeoutRef.current) window.clearTimeout(highlightTimeoutRef.current)
      highlightTimeoutRef.current = window.setTimeout(() => setNewIds(new Set()), NEW_ROW_HIGHLIGHT_MS)
    }
    previousIdsRef.current = new Set(data.map((a) => a.id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) window.clearTimeout(highlightTimeoutRef.current)
    }
  }, [])

  // A topbar search while already on this page changes `q` without
  // remounting the component, so the lazy useState initializer above won't
  // re-run - pick up subsequent changes explicitly.
  useEffect(() => {
    const q = searchParams.get('q')
    if (q !== null) setSearch(q)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get('q')])

  const detectionTypes = useMemo(
    () => Array.from(new Set(alerts.map((a) => a.detection_rule).filter((v): v is string => !!v))).sort(),
    [alerts],
  )

  const filteredAlerts = useMemo(() => {
    let result = alerts
    if (detectionType) result = result.filter((a) => a.detection_rule === detectionType)
    const q = search.trim().toLowerCase()
    if (q) {
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          (a.source_ip ?? '').toLowerCase().includes(q) ||
          (a.host ?? '').toLowerCase().includes(q) ||
          (a.username ?? '').toLowerCase().includes(q),
      )
    }
    return result
  }, [alerts, detectionType, search])

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<Alert>(filteredAlerts, {
    severity: (a) => SEVERITY_RANK[a.severity] ?? 0,
    title: (a) => a.title.toLowerCase(),
    source_ip: (a) => a.source_ip ?? '',
    host: (a) => a.host ?? '',
    status: (a) => a.status,
    timestamp: (a) => new Date(a.timestamp).getTime(),
  })

  function setFilter(key: 'severity' | 'status', value: string) {
    const next = new URLSearchParams(searchParams)
    value ? next.set(key, value) : next.delete(key)
    setSearchParams(next)
  }

  function clearSourceIp() {
    const next = new URLSearchParams(searchParams)
    next.delete('source_ip')
    setSearchParams(next)
  }

  async function quickUpdateStatus(e: MouseEvent, alert: Alert, newStatus: AlertStatus) {
    e.stopPropagation()
    if (newStatus === 'RESOLVED') {
      const ok = await confirm({
        title: 'Mark alert as RESOLVED?',
        message: 'Make sure any recommended response actions have actually been carried out first.',
        confirmLabel: 'Mark as RESOLVED',
        tone: 'danger',
      })
      if (!ok) return
    }
    setRowUpdating(alert.id)
    try {
      await updateStatus.mutateAsync({ id: alert.id, status: newStatus })
      toast.success(`Alert marked ${newStatus.replace('_', ' ')}`)
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to update status.'))
    } finally {
      setRowUpdating(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Alerts"
        description="Detections raised by the correlation and rules engine"
        actions={<LiveToggle live={live} onToggle={() => setLive((v) => !v)} lastUpdated={dataUpdatedAt ? new Date(dataUpdatedAt) : null} />}
      />

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search title, IP, host, user"
              className="rounded-md border border-slate-700 bg-slate-950 py-1.5 pl-8 pr-3 text-sm text-slate-200 placeholder:text-slate-600"
            />
          </div>
          <select
            value={severity}
            onChange={(e) => setFilter('severity', e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">All severities</option>
            {SEVERITIES.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={status}
            onChange={(e) => setFilter('status', e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">All statuses</option>
            {STATUSES.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={detectionType}
            onChange={(e) => setDetectionType(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">All detection types</option>
            {detectionTypes.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          {sourceIp && (
            <span className="flex items-center gap-1.5 rounded-md border border-purple-500/40 bg-purple-500/10 px-2.5 py-1.5 text-xs font-mono-ids text-purple-300">
              source_ip: {sourceIp}
              <button onClick={clearSourceIp} className="ml-1 opacity-70 hover:opacity-100" aria-label="Clear source IP filter">
                &times;
              </button>
            </span>
          )}
          <span className="ml-auto text-xs text-slate-500">{filteredAlerts.length} alert(s)</span>
        </div>

        {isLoading ? (
          <TableSkeleton columns={7} />
        ) : isError ? (
          <ErrorBanner message={getApiErrorMessage(error, 'Failed to load alerts.')} onRetry={() => refetch()} />
        ) : filteredAlerts.length === 0 ? (
          <EmptyState message="No alerts match the current filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <SortableTh label="Severity" sortKey="severity" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Title" sortKey="title" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Source IP" sortKey="source_ip" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Host" sortKey="host" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Status" sortKey="status" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Timestamp" sortKey="timestamp" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <th className="px-3 py-2">Quick Actions</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((alert) => (
                  <tr
                    key={alert.id}
                    onClick={() => navigate(`/alerts/${alert.id}`)}
                    className={`cursor-pointer border-b border-slate-900 transition-colors hover:bg-slate-800/40 ${
                      newIds.has(alert.id) ? 'animate-[row-highlight_4s_ease-out]' : ''
                    }`}
                  >
                    <td className="px-3 py-2">
                      <SeverityBadge severity={alert.severity} />
                    </td>
                    <td className="px-3 py-2 text-slate-200">
                      {alert.title}
                      {newIds.has(alert.id) && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-brand-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-brand-400">
                          New
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 font-mono-ids text-slate-400">{alert.source_ip ?? '—'}</td>
                    <td className="px-3 py-2 text-slate-400">{alert.host ?? '—'}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={alert.status} />
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(alert.timestamp)}</td>
                    <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-1.5">
                        {alert.status === 'NEW' && (
                          <button
                            onClick={(e) => quickUpdateStatus(e, alert, 'ACKNOWLEDGED')}
                            disabled={rowUpdating === alert.id}
                            className="rounded border border-indigo-500/40 bg-indigo-500/10 px-2 py-1 text-[11px] font-medium text-indigo-300 hover:bg-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Ack
                          </button>
                        )}
                        {alert.status !== 'RESOLVED' && alert.status !== 'FALSE_POSITIVE' && (
                          <button
                            onClick={(e) => quickUpdateStatus(e, alert, 'RESOLVED')}
                            disabled={rowUpdating === alert.id}
                            className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-[11px] font-medium text-emerald-300 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Resolve
                          </button>
                        )}
                        {rowUpdating === alert.id && <InlineSpinner />}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
