import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LiveToggle } from '../components/LiveToggle'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import type { Incident } from '../types'
import { getApiErrorMessage, getIncidents } from '../services/api'
import { formatDateTime } from '../utils/format'
import { usePolling } from '../hooks/usePolling'
import { useSortableData } from '../hooks/useSortableData'
import { useToast } from '../hooks/useToast'

const STATUSES = ['', 'OPEN', 'INVESTIGATING', 'CONTAINED', 'CLOSED']
const SEVERITY_RANK: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
const POLL_INTERVAL_MS = 15000
const NEW_ROW_HIGHLIGHT_MS = 4000

export default function Incidents() {
  const navigate = useNavigate()
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') ?? ''

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [newIds, setNewIds] = useState<Set<string>>(new Set())

  const previousIdsRef = useRef<Set<string> | null>(null)
  const highlightTimeoutRef = useRef<number | null>(null)

  const load = useCallback(
    (showSpinner = true) => {
      if (showSpinner) setLoading(true)
      setError(null)
      getIncidents({ status: status || undefined, limit: 200 })
        .then((data) => {
          if (!showSpinner && previousIdsRef.current) {
            const freshIds = data.filter((i) => !previousIdsRef.current!.has(i.id)).map((i) => i.id)
            if (freshIds.length > 0) {
              setNewIds(new Set(freshIds))
              toast.info(`${freshIds.length} new incident${freshIds.length > 1 ? 's' : ''} opened`)
              if (highlightTimeoutRef.current) window.clearTimeout(highlightTimeoutRef.current)
              highlightTimeoutRef.current = window.setTimeout(() => setNewIds(new Set()), NEW_ROW_HIGHLIGHT_MS)
            }
          }
          previousIdsRef.current = new Set(data.map((i) => i.id))
          setIncidents(data)
          setLastUpdated(new Date())
        })
        .catch((err) => setError(getApiErrorMessage(err, 'Failed to load incidents.')))
        .finally(() => setLoading(false))
    },
    // See Alerts.tsx for why `toast` is intentionally excluded here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [status],
  )

  useEffect(() => load(true), [load])
  usePolling(() => load(false), POLL_INTERVAL_MS, live)

  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) window.clearTimeout(highlightTimeoutRef.current)
    }
  }, [])

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<Incident>(incidents, {
    severity: (i) => SEVERITY_RANK[i.severity] ?? 0,
    title: (i) => i.title.toLowerCase(),
    status: (i) => i.status,
    created_at: (i) => new Date(i.created_at).getTime(),
    updated_at: (i) => new Date(i.updated_at).getTime(),
  })

  function setStatus(value: string) {
    const next = new URLSearchParams(searchParams)
    value ? next.set('status', value) : next.delete('status')
    setSearchParams(next)
  }

  return (
    <div>
      <PageHeader
        title="Incidents"
        description="Correlated groups of alerts requiring response"
        actions={<LiveToggle live={live} onToggle={() => setLive((v) => !v)} lastUpdated={lastUpdated} />}
      />

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">All statuses</option>
            {STATUSES.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <span className="ml-auto text-xs text-slate-500">{incidents.length} incident(s)</span>
        </div>

        {loading ? (
          <TableSkeleton columns={5} />
        ) : error ? (
          <ErrorBanner message={error} onRetry={() => load(true)} />
        ) : incidents.length === 0 ? (
          <EmptyState message="No incidents match the current filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <SortableTh label="Severity" sortKey="severity" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Title" sortKey="title" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Status" sortKey="status" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Created" sortKey="created_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Updated" sortKey="updated_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                </tr>
              </thead>
              <tbody>
                {sorted.map((incident) => (
                  <tr
                    key={incident.id}
                    onClick={() => navigate(`/incidents/${incident.id}`)}
                    className={`cursor-pointer border-b border-slate-900 transition-colors hover:bg-slate-800/40 ${
                      newIds.has(incident.id) ? 'animate-[row-highlight_4s_ease-out]' : ''
                    }`}
                  >
                    <td className="px-3 py-2">
                      <SeverityBadge severity={incident.severity} />
                    </td>
                    <td className="px-3 py-2 text-slate-200">
                      {incident.title}
                      {newIds.has(incident.id) && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-sky-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-sky-400">
                          New
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={incident.status} />
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(incident.created_at)}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(incident.updated_at)}</td>
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
