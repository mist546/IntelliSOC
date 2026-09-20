import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, FileBarChart2 } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import type { Report, ReportFormat } from '../types'
import { getApiErrorMessage } from '../services/client'
import { formatDateTime } from '../utils/format'
import { useToast } from '../hooks/useToast'
import { useSortableData } from '../hooks/useSortableData'
import {
  useDownloadReport,
  useGenerateReport,
  useIncidentsForReports,
  useReportsQuery,
} from '../hooks/queries/useReports'

export default function Reports() {
  const toast = useToast()
  const { data: incidents = [], isLoading, isError, error, refetch } = useIncidentsForReports()
  const {
    data: reportHistory = [],
    isLoading: historyLoading,
    isError: historyIsError,
    error: historyError,
    refetch: refetchHistory,
  } = useReportsQuery()
  const generate = useGenerateReport()
  const download = useDownloadReport()

  const [incidentId, setIncidentId] = useState('')
  const [format, setFormat] = useState<ReportFormat>('json')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  const incidentById = useMemo(() => new Map(incidents.map((i) => [i.id, i])), [incidents])
  const selectedIncident = incidentById.get(incidentId)
  const report = generate.data
  const content = report?.content

  async function handleGenerate() {
    if (!incidentId) return
    try {
      await generate.mutateAsync({ incidentId, format })
      toast.success(`${format.toUpperCase()} report generated.`)
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to generate report.'))
    }
  }

  async function handleDownload(r: Pick<Report, 'id' | 'incident_id' | 'format'>) {
    setDownloadingId(r.id)
    try {
      await download.mutateAsync(r)
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to download report.'))
    } finally {
      setDownloadingId(null)
    }
  }

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<Report>(reportHistory, {
    incident: (r) => (incidentById.get(r.incident_id)?.title ?? r.incident_id).toLowerCase(),
    format: (r) => r.format,
    created_at: (r) => new Date(r.created_at).getTime(),
  })

  return (
    <div>
      <PageHeader title="Reports" description="Incident reports - evidence, timeline, AI findings, and recommendations" />

      <div className="mb-6">
        <Card title="Generate Incident Report">
          {isLoading ? (
            <p className="text-sm text-slate-500">Loading incidents...</p>
          ) : isError ? (
            <ErrorBanner message={getApiErrorMessage(error, 'Failed to load incidents.')} onRetry={() => refetch()} />
          ) : incidents.length === 0 ? (
            <EmptyState message="No incidents exist yet - reports are generated per incident." />
          ) : (
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[260px] flex-1">
                <label className="mb-1 block text-xs font-medium text-slate-400">Incident</label>
                <select
                  value={incidentId}
                  onChange={(e) => setIncidentId(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                >
                  <option value="">Select an incident...</option>
                  {incidents.map((inc) => (
                    <option key={inc.id} value={inc.id}>
                      #{inc.id} - {inc.title} ({inc.severity})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Format</label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value as ReportFormat)}
                  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                >
                  <option value="json">JSON</option>
                  <option value="pdf">PDF</option>
                </select>
              </div>
              <button
                onClick={handleGenerate}
                disabled={!incidentId || generate.isPending}
                className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {generate.isPending ? <InlineSpinner /> : <FileBarChart2 className="h-4 w-4" />}
                Generate Report
              </button>
            </div>
          )}

          {generate.isError && (
            <div className="mt-3">
              <ErrorBanner message={getApiErrorMessage(generate.error, 'Failed to generate report.')} />
            </div>
          )}
        </Card>
      </div>

      {report && content && (
        <div className="mb-6 space-y-4">
          <Card
            title={`Report #${report.id} · ${selectedIncident?.title ?? `Incident #${report.incident_id}`}`}
            actions={
              <button
                onClick={() => handleDownload(report)}
                disabled={downloadingId === report.id}
                className="flex items-center gap-1.5 rounded border border-emerald-500/50 px-3 py-1 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {downloadingId === report.id ? <InlineSpinner /> : <Download className="h-3.5 w-3.5" />}
                Download {report.format.toUpperCase()}
              </button>
            }
          >
            <p className="text-xs text-slate-500">Generated {formatDateTime(report.created_at)}</p>
          </Card>

          <Card title="Evidence (Alerts)">
            {Array.isArray(content.alerts) && content.alerts.length > 0 ? (
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
                    {(content.alerts as Array<Record<string, unknown>>).map((a, i) => (
                      <tr key={i} className="border-b border-slate-900">
                        <td className="px-3 py-2">
                          <SeverityBadge severity={String(a.severity ?? '')} />
                        </td>
                        <td className="px-3 py-2">
                          <Link to={`/alerts/${a.id}`} className="text-brand-400 hover:underline">
                            {String(a.title ?? '')}
                          </Link>
                        </td>
                        <td className="px-3 py-2 font-mono-ids text-slate-400">{String(a.source_ip ?? '—')}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={String(a.status ?? '')} />
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(String(a.timestamp ?? ''))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState message="No alerts recorded on this incident." />
            )}
          </Card>

          <Card title="Timeline">
            {Array.isArray(content.timeline) && content.timeline.length > 0 ? (
              <ol className="space-y-2">
                {(content.timeline as Array<Record<string, unknown>>).map((t, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm">
                    <span className="mt-0.5 shrink-0 font-mono-ids text-xs text-slate-500">
                      {formatDateTime(String(t.timestamp ?? ''))}
                    </span>
                    <span className="text-slate-300">{String(t.event ?? '')}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState message="No timeline events recorded." />
            )}
          </Card>

          <Card title="AI Findings & Recommendations">
            {Array.isArray(content.investigations) && content.investigations.length > 0 ? (
              <div className="space-y-4">
                {(content.investigations as Array<Record<string, unknown>>).map((inv, i) => (
                  <div key={i} className="rounded-md border border-slate-800 bg-slate-950/60 p-3">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <Link to={`/investigations/${inv.id}`} className="font-mono-ids text-sm text-brand-400 hover:underline">
                        INV-{String(inv.id)}
                      </Link>
                      <span className="text-xs text-slate-500">Risk score: {inv.risk_score !== null && inv.risk_score !== undefined ? String(inv.risk_score) : '—'}</span>
                    </div>
                    {inv.ai_summary ? (
                      <p className="text-sm text-slate-300">{String(inv.ai_summary)}</p>
                    ) : (
                      <p className="text-sm text-slate-500">No AI summary available for this investigation.</p>
                    )}
                    {Array.isArray(inv.recommended_actions) && (inv.recommended_actions as unknown[]).length > 0 && (
                      <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-amber-300/90">
                        {(inv.recommended_actions as string[]).map((action, j) => (
                          <li key={j}>{action}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="No AI investigations have been run for this incident yet." />
            )}
          </Card>

          <Card title="Containment Status">
            <p className="text-sm text-slate-300">{String(content.containment_status ?? '—')}</p>
          </Card>
        </div>
      )}

      <Card title="Report History">
        {historyLoading ? (
          <TableSkeleton columns={4} />
        ) : historyIsError ? (
          <ErrorBanner
            message={getApiErrorMessage(historyError, 'Failed to load report history.')}
            onRetry={() => refetchHistory()}
          />
        ) : reportHistory.length === 0 ? (
          <EmptyState message="No reports generated yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <SortableTh label="Incident" sortKey="incident" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Format" sortKey="format" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Generated" sortKey="created_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <th className="px-3 py-2">Download</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => {
                  const inc = incidentById.get(r.incident_id)
                  return (
                    <tr key={r.id} className="border-b border-slate-900 hover:bg-slate-800/40">
                      <td className="px-3 py-2">
                        {inc ? (
                          <Link to={`/incidents/${r.incident_id}`} className="text-brand-400 hover:underline">
                            {inc.title}
                          </Link>
                        ) : (
                          <span className="text-slate-400">Incident #{r.incident_id}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 uppercase text-slate-400">{r.format}</td>
                      <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(r.created_at)}</td>
                      <td className="px-3 py-2">
                        <button
                          onClick={() => handleDownload(r)}
                          disabled={downloadingId === r.id}
                          className="flex items-center gap-1.5 rounded border border-slate-700 px-2 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {downloadingId === r.id ? <InlineSpinner /> : <Download className="h-3.5 w-3.5" />}
                          Download
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
