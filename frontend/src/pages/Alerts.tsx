import { useCallback, useEffect, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
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
import { getAlerts, getApiErrorMessage, updateAlertStatus } from '../services/api'
import { formatDateTime } from '../utils/format'
import { usePolling } from '../hooks/usePolling'
import { useSortableData } from '../hooks/useSortableData'
import { useToast } from '../hooks/useToast'
import { useConfirm } from '../hooks/useConfirm'

const SEVERITIES = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const STATUSES = ['', 'NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE']
const SEVERITY_RANK: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
const POLL_INTERVAL_MS = 15000
const NEW_ROW_HIGHLIGHT_MS = 4000

export default function Alerts() {
  const navigate = useNavigate()
  const toast = useToast()
  const confirm = useConfirm()
  const [searchParams, setSearchParams] = useSearchParams()
  const severity = searchParams.get('severity') ?? ''
  const status = searchParams.get('status') ?? ''
  const sourceIp = searchParams.get('source_ip') ?? ''

  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [newIds, setNewIds] = useState<Set<string>>(new Set())
  const [rowUpdating, setRowUpdating] = useState<string | null>(null)

  const previousIdsRef = useRef<Set<string> | null>(null)
  const highlightTimeoutRef = useRef<number | null>(null)

  const load = useCallback(
    (showSpinner = true) => {
      if (showSpinner) setLoading(true)
      setError(null)
      getAlerts({ severity: severity || undefined, status: status || undefined, source_ip: sourceIp || undefined, limit: 200 })
        .then((data) => {
          if (!showSpinner && previousIdsRef.current) {
            const freshIds = data.filter((a) => !previousIdsRef.current!.has(a.id)).map((a) => a.id)
            if (freshIds.length > 0) {
              setNewIds(new Set(freshIds))
              toast.info(`${freshIds.length} new alert${freshIds.length > 1 ? 's' : ''} arrived`)
              if (highlightTimeoutRef.current) window.clearTimeout(highlightTimeoutRef.current)
              highlightTimeoutRef.current = window.setTimeout(() => setNewIds(new Set()), NEW_ROW_HIGHLIGHT_MS)
            }
          }
          previousIdsRef.current = new Set(data.map((a) => a.id))
          setAlerts(data)
          setLastUpdated(new Date())
        })
        .catch((err) => setError(getApiErrorMessage(err, 'Failed to load alerts.')))
        .finally(() => setLoading(false))
    },
    // `toast` is deliberately excluded: its identity changes on every toast
    // push/dismiss anywhere in the app (see ToastProvider), and including it
    // here would recreate `load` and re-trigger the mount effect below on
    // every unrelated toast. Its methods delegate to a stable callback, so a
    // "stale" closure over `toast` is still safe to call.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [severity, status, sourceIp],
  )

  useEffect(() => load(true), [load])
  usePolling(() => load(false), POLL_INTERVAL_MS, live)

  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) window.clearTimeout(highlightTimeoutRef.current)
    }
  }, [])

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<Alert>(alerts, {
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
      const updated = await updateAlertStatus(alert.id, newStatus)
      setAlerts((prev) => prev.map((a) => (a.id === alert.id ? updated : a)))
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
        actions={<LiveToggle live={live} onToggle={() => setLive((v) => !v)} lastUpdated={lastUpdated} />}
      />

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
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
          {sourceIp && (
            <span className="flex items-center gap-1.5 rounded-md border border-purple-500/40 bg-purple-500/10 px-2.5 py-1.5 text-xs font-mono-ids text-purple-300">
              source_ip: {sourceIp}
              <button onClick={clearSourceIp} className="ml-1 opacity-70 hover:opacity-100" aria-label="Clear source IP filter">
                &times;
              </button>
            </span>
          )}
          <span className="ml-auto text-xs text-slate-500">{alerts.length} alert(s)</span>
        </div>

        {loading ? (
          <TableSkeleton columns={7} />
        ) : error ? (
          <ErrorBanner message={error} onRetry={() => load(true)} />
        ) : alerts.length === 0 ? (
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
                        <span className="ml-2 inline-flex items-center rounded-full bg-sky-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-sky-400">
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
