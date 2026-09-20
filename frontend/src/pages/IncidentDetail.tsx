import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner, InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import type { IncidentDetail as IncidentDetailType, Report, ReportFormat } from '../types'
import { downloadReportFile, generateReport, getApiErrorMessage, getIncident } from '../services/api'
import { formatDateTime } from '../utils/format'
import { useToast } from '../hooks/useToast'

export default function IncidentDetail() {
  const { id } = useParams()
  const toast = useToast()
  const [incident, setIncident] = useState<IncidentDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [reportFormat, setReportFormat] = useState<ReportFormat>('json')
  const [generating, setGenerating] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [downloading, setDownloading] = useState(false)

  function load() {
    if (!id) return
    setLoading(true)
    setError(null)
    getIncident(id)
      .then(setIncident)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load incident.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [id])

  async function handleGenerateReport() {
    if (!id) return
    setGenerating(true)
    setReportError(null)
    setReport(null)
    try {
      const res = await generateReport(id, reportFormat)
      setReport(res)
      toast.success(`${reportFormat.toUpperCase()} report generated.`)
    } catch (err) {
      const message = getApiErrorMessage(err, 'Failed to generate report.')
      setReportError(message)
      toast.error(message)
    } finally {
      setGenerating(false)
    }
  }

  async function handleDownload() {
    if (!report) return
    setDownloading(true)
    try {
      await downloadReportFile(report)
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to download report.'))
    } finally {
      setDownloading(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading incident..." />
  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!incident) return <EmptyState message="Incident not found." />

  return (
    <div>
      <PageHeader title={incident.title} description={`Incident #${incident.id}`} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Overview" className="lg:col-span-2">
          <dl className="grid grid-cols-2 gap-y-3 text-sm">
            <dt className="text-slate-500">Severity</dt>
            <dd>
              <SeverityBadge severity={incident.severity} />
            </dd>
            <dt className="text-slate-500">Status</dt>
            <dd>
              <StatusBadge status={incident.status} />
            </dd>
            <dt className="text-slate-500">Created</dt>
            <dd className="text-slate-200">{formatDateTime(incident.created_at)}</dd>
            <dt className="text-slate-500">Updated</dt>
            <dd className="text-slate-200">{formatDateTime(incident.updated_at)}</dd>
          </dl>
          {incident.description && (
            <div className="mt-4 border-t border-slate-800 pt-4">
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Description</p>
              <p className="text-sm text-slate-300">{incident.description}</p>
            </div>
          )}
        </Card>

        <Card title="Generate Report">
          <div className="flex flex-col gap-3">
            <select
              value={reportFormat}
              onChange={(e) => setReportFormat(e.target.value as ReportFormat)}
              className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
            >
              <option value="json">JSON</option>
              <option value="pdf">PDF</option>
            </select>
            <button
              onClick={handleGenerateReport}
              disabled={generating}
              className="flex items-center justify-center gap-2 rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {generating && <InlineSpinner />}
              Generate Report
            </button>

            {reportError && <ErrorBanner message={reportError} />}

            {report && (
              <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold">Report #{report.id} generated ({report.format})</p>
                  <button
                    onClick={handleDownload}
                    disabled={downloading}
                    className="flex shrink-0 items-center gap-2 rounded border border-emerald-500/50 px-3 py-1 text-xs font-medium text-emerald-200 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {downloading && <InlineSpinner />}
                    Download {report.format.toUpperCase()}
                  </button>
                </div>
                {report.format === 'json' && (
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-300">
                    {JSON.stringify(report.content, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-4">
        <Card title={`Alerts (${incident.alerts?.length ?? 0})`}>
          {incident.alerts && incident.alerts.length > 0 ? (
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
                  {incident.alerts.map((alert) => (
                    <tr key={alert.id} className="border-b border-slate-900 hover:bg-slate-800/40">
                      <td className="px-3 py-2">
                        <SeverityBadge severity={alert.severity} />
                      </td>
                      <td className="px-3 py-2">
                        <Link to={`/alerts/${alert.id}`} className="text-brand-400 hover:underline">
                          {alert.title}
                        </Link>
                      </td>
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
            <EmptyState message="No alerts linked to this incident." />
          )}
        </Card>
      </div>
    </div>
  )
}
