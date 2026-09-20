import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ScanSearch, Search } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { StatusBadge } from '../components/StatusBadge'
import { getApiErrorMessage } from '../services/client'
import { formatDateTime } from '../utils/format'
import { useDashboardStats } from '../hooks/queries/useDashboard'
import { getInvestigation } from '../services/investigations'
import { useToast } from '../hooks/useToast'

export default function Investigations() {
  const navigate = useNavigate()
  const toast = useToast()
  const { data: stats, isLoading, isError, error, refetch } = useDashboardStats(true)
  const [jumpId, setJumpId] = useState('')
  const [jumping, setJumping] = useState(false)

  async function handleJump(e: FormEvent) {
    e.preventDefault()
    const id = jumpId.trim()
    if (!id) return
    setJumping(true)
    try {
      await getInvestigation(id)
      navigate(`/investigations/${id}`)
    } catch (err) {
      toast.error(getApiErrorMessage(err, `Investigation #${id} not found.`))
    } finally {
      setJumping(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Investigations"
        description="AI-driven investigations launched from alerts - evidence, threat intel, RAG, and analysis in one trace"
      />

      <div className="mb-6">
        <Card title="Open an Investigation">
          <form onSubmit={handleJump} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1 block text-xs font-medium text-slate-400">Investigation ID</label>
              <input
                value={jumpId}
                onChange={(e) => setJumpId(e.target.value)}
                placeholder="e.g. 12"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 font-mono-ids"
              />
            </div>
            <button
              type="submit"
              disabled={jumping || !jumpId.trim()}
              className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {jumping ? <InlineSpinner /> : <Search className="h-4 w-4" />}
              Open
            </button>
          </form>
          <p className="mt-3 text-xs text-slate-500">
            Investigations are launched from an alert's "Investigate with AI" action and run the full{' '}
            <span className="text-slate-400">Alert → Evidence → Threat Intel → RAG → LLM → Analysis → Recommendation</span> pipeline.
          </p>
        </Card>
      </div>

      <Card title="Recent Investigations">
        {isLoading ? (
          <div className="py-10 text-center text-sm text-slate-500">Loading...</div>
        ) : isError ? (
          <ErrorBanner message={getApiErrorMessage(error, 'Failed to load investigations.')} onRetry={() => refetch()} />
        ) : stats?.recent_investigations && stats.recent_investigations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Alert</th>
                  <th className="px-3 py-2">Incident</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Risk Score</th>
                  <th className="px-3 py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_investigations.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => navigate(`/investigations/${inv.id}`)}
                    className="cursor-pointer border-b border-slate-900 hover:bg-slate-800/40"
                  >
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1.5 font-mono-ids text-brand-400" title={inv.id}>
                        <ScanSearch className="h-3.5 w-3.5 shrink-0" /> INV-{inv.id.slice(0, 8)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/alerts/${inv.alert_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-slate-300 hover:underline"
                      >
                        Alert #{inv.alert_id}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-slate-400">{inv.incident_id ? `INC-${inv.incident_id}` : '—'}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="px-3 py-2 text-slate-300">{inv.risk_score ?? '—'}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(inv.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No investigations run yet. Open an alert and use 'Investigate with AI' to start one." />
        )}
      </Card>
    </div>
  )
}
