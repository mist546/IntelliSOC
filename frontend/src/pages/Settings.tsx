import { useEffect, useState } from 'react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner } from '../components/ErrorBanner'
import { useAuth } from '../hooks/useAuth'
import type { User } from '../types'
import { getApiErrorMessage, getCurrentUser } from '../services/api'

export default function Settings() {
  const { user: cachedUser } = useAuth()
  const [user, setUser] = useState<User | null>(cachedUser)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function load() {
    setLoading(true)
    setError(null)
    getCurrentUser()
      .then(setUser)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load user profile.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  return (
    <div>
      <PageHeader title="Settings" description="Account details and server configuration" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Current User">
          {loading ? (
            <LoadingSpinner label="Loading profile..." />
          ) : error ? (
            <ErrorBanner message={error} onRetry={load} />
          ) : user ? (
            <dl className="grid grid-cols-2 gap-y-3 text-sm">
              <dt className="text-slate-500">Username</dt>
              <dd className="text-slate-200">{user.username}</dd>
              <dt className="text-slate-500">Email</dt>
              <dd className="text-slate-200">{user.email}</dd>
              <dt className="text-slate-500">Role</dt>
              <dd className="text-slate-200">{user.role}</dd>
              <dt className="text-slate-500">User ID</dt>
              <dd className="font-mono-ids text-slate-200">{user.id}</dd>
            </dl>
          ) : null}
        </Card>

        <Card title="LLM / AI Configuration">
          <p className="text-sm text-slate-300">
            The LLM provider and model used for AI investigations, threat classification, and RAG-based analysis is
            configured server-side via the backend's <code className="font-mono-ids text-slate-400">.env</code> file
            (e.g. Ollama host/model, embeddings model). This is not exposed via the API, so it cannot be displayed
            dynamically here.
          </p>
          <p className="mt-3 text-sm text-slate-400">
            If AI investigations report "AI analysis unavailable," check that the Ollama service configured on the
            backend is running and reachable, via{' '}
            <code className="font-mono-ids text-slate-400">GET /api/health</code>.
          </p>
        </Card>
      </div>
    </div>
  )
}
