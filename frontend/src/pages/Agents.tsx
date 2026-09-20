import { FormEvent, useEffect, useMemo, useState } from 'react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState, WarningBanner } from '../components/ErrorBanner'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import { CopyButton } from '../components/CopyButton'
import { useAuth } from '../hooks/useAuth'
import type { AgentRegisterResponse, CollectorAgent } from '../types'
import { getAgents, getApiErrorMessage, registerAgent } from '../services/api'
import { formatDateTime } from '../utils/format'
import { useToast } from '../hooks/useToast'
import { useSortableData } from '../hooks/useSortableData'

export default function Agents() {
  const { user } = useAuth()
  const toast = useToast()
  const isAdmin = user?.role === 'ADMIN'

  const [agents, setAgents] = useState<CollectorAgent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const [name, setName] = useState('')
  const [hostname, setHostname] = useState('')
  const [registering, setRegistering] = useState(false)
  const [registerError, setRegisterError] = useState<string | null>(null)
  const [newAgent, setNewAgent] = useState<AgentRegisterResponse | null>(null)

  function load() {
    setLoading(true)
    setError(null)
    getAgents()
      .then(setAgents)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load agents.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleRegister(e: FormEvent) {
    e.preventDefault()
    setRegistering(true)
    setRegisterError(null)
    try {
      const res = await registerAgent({ name, hostname })
      setNewAgent(res)
      setName('')
      setHostname('')
      load()
      toast.success(`Agent "${res.name}" registered - copy its API key now, it won't be shown again.`)
    } catch (err) {
      const message = getApiErrorMessage(err, 'Failed to register agent.')
      setRegisterError(message)
      toast.error(message)
    } finally {
      setRegistering(false)
    }
  }

  const filteredAgents = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return agents
    return agents.filter((a) => a.name.toLowerCase().includes(q) || a.hostname.toLowerCase().includes(q))
  }, [agents, search])

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<CollectorAgent>(filteredAgents, {
    name: (a) => a.name.toLowerCase(),
    hostname: (a) => a.hostname.toLowerCase(),
    is_active: (a) => (a.is_active ? 1 : 0),
    last_seen_at: (a) => (a.last_seen_at ? new Date(a.last_seen_at).getTime() : 0),
    created_at: (a) => new Date(a.created_at).getTime(),
  })

  return (
    <div>
      <PageHeader title="Collector Agents" description="Endpoint agents that ship logs into Mini-SOC" />

      {isAdmin && (
        <div className="mb-6">
          <Card title="Register New Agent">
            <form onSubmit={handleRegister} className="flex flex-wrap items-end gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Name</label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Hostname</label>
                <input
                  required
                  value={hostname}
                  onChange={(e) => setHostname(e.target.value)}
                  className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
                />
              </div>
              <button
                type="submit"
                disabled={registering}
                className="flex items-center gap-2 rounded-md bg-sky-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {registering && <InlineSpinner />}
                Register Agent
              </button>
            </form>

            {registerError && (
              <div className="mt-3">
                <ErrorBanner message={registerError} />
              </div>
            )}

            {newAgent && (
              <div className="mt-4 animate-[fade-in_0.15s_ease-out]">
                <WarningBanner
                  title="Save this API key now"
                  message="This key will not be shown again. Store it securely on the collector agent's configuration."
                />
                <div className="mt-2 flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950 p-3">
                  <code className="flex-1 overflow-x-auto font-mono-ids text-sm text-emerald-400">{newAgent.api_key}</code>
                  <CopyButton value={newAgent.api_key} />
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {!isAdmin && (
        <div className="mb-6">
          <WarningBanner title="Admin only" message="Only ADMIN users can register new collector agents." />
        </div>
      )}

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or hostname"
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600"
          />
          <span className="ml-auto text-xs text-slate-500">{filteredAgents.length} agent(s)</span>
        </div>

        {loading ? (
          <TableSkeleton columns={5} />
        ) : error ? (
          <ErrorBanner message={error} onRetry={load} />
        ) : agents.length === 0 ? (
          <EmptyState message="No collector agents registered yet." />
        ) : filteredAgents.length === 0 ? (
          <EmptyState message="No agents match your search." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <SortableTh label="Name" sortKey="name" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Hostname" sortKey="hostname" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Active" sortKey="is_active" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Last Seen" sortKey="last_seen_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Registered" sortKey="created_at" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                </tr>
              </thead>
              <tbody>
                {sorted.map((agent) => (
                  <tr key={agent.id} className="border-b border-slate-900 hover:bg-slate-800/40">
                    <td className="px-3 py-2 text-slate-200">{agent.name}</td>
                    <td className="px-3 py-2 font-mono-ids text-slate-400">{agent.hostname}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${
                          agent.is_active
                            ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                            : 'border-slate-600/40 bg-slate-600/10 text-slate-400'
                        }`}
                      >
                        {agent.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(agent.last_seen_at)}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(agent.created_at)}</td>
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
