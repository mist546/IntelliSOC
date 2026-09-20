import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState, WarningBanner } from '../components/ErrorBanner'
import { StatusBadge } from '../components/StatusBadge'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import type { WebsiteScan } from '../types'
import { createScan, getApiErrorMessage, getScans } from '../services/api'
import { formatDateTime } from '../utils/format'
import { useToast } from '../hooks/useToast'
import { useSortableData } from '../hooks/useSortableData'

export default function WebsiteScans() {
  const navigate = useNavigate()
  const toast = useToast()
  const [scans, setScans] = useState<WebsiteScan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [targetUrl, setTargetUrl] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)

  function load() {
    setLoading(true)
    setError(null)
    getScans({ limit: 100 })
      .then(setScans)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load scans.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<WebsiteScan>(scans, {
    target_url: (s) => s.target_url.toLowerCase(),
    status: (s) => s.status,
    findings: (s) => s.findings?.length ?? 0,
    started_at: (s) => (s.started_at ? new Date(s.started_at).getTime() : 0),
    completed_at: (s) => (s.completed_at ? new Date(s.completed_at).getTime() : 0),
  })

  async function handleScan(e: FormEvent) {
    e.preventDefault()
    setScanning(true)
    setScanError(null)
    try {
      const scan = await createScan(targetUrl.trim())
      setTargetUrl('')
      load()
      const findingCount = scan.findings?.length ?? 0
      if (scan.status === 'COMPLETED') {
        toast.success(`Scan complete: ${findingCount} finding(s) for ${scan.target_url}`)
      } else if (scan.status === 'FAILED') {
        toast.error(scan.error_message ?? 'Scan failed.')
      }
      navigate(`/website-scans/${scan.id}`)
    } catch (err) {
      const message = getApiErrorMessage(err, 'Failed to run website scan.')
      setScanError(message)
      toast.error(message)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div>
      <PageHeader title="Website Scans" description="Lightweight web vulnerability scans (OWASP-oriented checks)" />

      <div className="mb-6">
        <Card title="New Scan">
          <form onSubmit={handleScan} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[240px]">
              <label className="mb-1 block text-xs font-medium text-slate-400">Target URL</label>
              <input
                required
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="http://localhost:8080"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 font-mono-ids"
              />
            </div>
            <button
              type="submit"
              disabled={scanning}
              className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {scanning && <InlineSpinner />}
              Start Scan
            </button>
          </form>
          <div className="mt-3">
            <WarningBanner
              title="Scope restriction"
              message="Only targets resolving to localhost or 127.0.0.1 are allowed by default (SSRF protection)."
            />
          </div>
          {scanError && (
            <div className="mt-3">
              <ErrorBanner message={scanError} />
            </div>
          )}
        </Card>
      </div>

      <Card>
        {loading ? (
          <TableSkeleton columns={5} />
        ) : error ? (
          <ErrorBanner message={error} onRetry={load} />
        ) : scans.length === 0 ? (
          <EmptyState message="No website scans have been run yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <SortableTh label="Target" sortKey="target_url" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Status" sortKey="status" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Findings" sortKey="findings" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Started" sortKey="started_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Completed" sortKey="completed_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                </tr>
              </thead>
              <tbody>
                {sorted.map((scan) => (
                  <tr
                    key={scan.id}
                    onClick={() => navigate(`/website-scans/${scan.id}`)}
                    className="cursor-pointer border-b border-slate-900 hover:bg-slate-800/40"
                  >
                    <td className="px-3 py-2 font-mono-ids text-slate-200">{scan.target_url}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={scan.status} />
                    </td>
                    <td className="px-3 py-2 text-slate-400">{scan.findings?.length ?? 0}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(scan.started_at)}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(scan.completed_at)}</td>
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
