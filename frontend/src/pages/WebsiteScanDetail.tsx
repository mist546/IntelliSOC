import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { StatusBadge } from '../components/StatusBadge'
import type { ScanFinding, WebsiteScan } from '../types'
import { getApiErrorMessage, getScan } from '../services/api'
import { formatDateTime } from '../utils/format'

const SEVERITY_STYLES: Record<ScanFinding['severity'], string> = {
  HIGH: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
  MEDIUM: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300',
  LOW: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
}

export default function WebsiteScanDetail() {
  const { id } = useParams()
  const [scan, setScan] = useState<WebsiteScan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function load() {
    if (!id) return
    setLoading(true)
    setError(null)
    getScan(id)
      .then(setScan)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load scan.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [id])

  if (loading) return <LoadingSpinner label="Loading scan..." />
  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!scan) return <EmptyState message="Scan not found." />

  return (
    <div>
      <PageHeader
        title={scan.target_url}
        description={`Scan #${scan.id}`}
        actions={<StatusBadge status={scan.status} />}
      />

      {scan.status === 'FAILED' && scan.error_message && (
        <div className="mb-4">
          <ErrorBanner message={scan.error_message} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Overview" className="lg:col-span-1">
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Started</dt>
              <dd className="text-slate-200">{formatDateTime(scan.started_at)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Completed</dt>
              <dd className="text-slate-200">{formatDateTime(scan.completed_at)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Checks Run</dt>
              <dd className="mt-1 flex flex-wrap gap-1">
                {scan.checks_run && scan.checks_run.length > 0 ? (
                  scan.checks_run.map((c, i) => (
                    <span key={i} className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                      {c}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-500">—</span>
                )}
              </dd>
            </div>
          </dl>
        </Card>

        <Card title={`Findings (${scan.findings?.length ?? 0})`} className="lg:col-span-2">
          {scan.findings && scan.findings.length > 0 ? (
            <div className="space-y-3">
              {scan.findings.map((f, i) => (
                <div key={i} className={`rounded-md border p-3 ${SEVERITY_STYLES[f.severity]}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-semibold">{f.finding}</span>
                    <div className="flex items-center gap-2">
                      {f.owasp_category && (
                        <span className="rounded bg-black/20 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide">
                          {f.owasp_category}
                        </span>
                      )}
                      <span className="rounded bg-black/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
                        {f.severity}
                      </span>
                    </div>
                  </div>
                  {f.affected_url && <p className="mt-1 font-mono-ids text-xs opacity-80">{f.affected_url}</p>}
                  {f.description && <p className="mt-2 text-sm opacity-90">{f.description}</p>}
                  {f.evidence && (
                    <pre className="mt-2 max-h-32 overflow-auto rounded bg-black/20 p-2 text-[11px] opacity-80">
                      {f.evidence}
                    </pre>
                  )}
                  {f.recommendation && (
                    <p className="mt-2 text-xs opacity-80">
                      <span className="font-semibold">Recommendation: </span>
                      {f.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="No findings reported for this scan." />
          )}
        </Card>
      </div>
    </div>
  )
}
