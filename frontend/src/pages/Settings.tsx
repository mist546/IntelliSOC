import { useEffect, useState } from 'react'
import { Cloud, Server, ShieldCheck, UserCircle2, Wifi, WifiOff } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner, InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner } from '../components/ErrorBanner'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import type { LlmProvider, User } from '../types'
import { getApiErrorMessage } from '../services/client'
import { getCurrentUser } from '../services/auth'
import { useLlmSettingsQuery, useUpdateLlmSettings } from '../hooks/queries/useLlmSettings'

export default function Settings() {
  const { user: cachedUser } = useAuth()
  const toast = useToast()
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

  const isAdmin = user?.role === 'ADMIN'
  const { data: llmSettings, isLoading: llmLoading, isError: llmIsError, error: llmError, refetch: refetchLlm } = useLlmSettingsQuery()
  const updateLlm = useUpdateLlmSettings()

  const [provider, setProvider] = useState<LlmProvider | null>(null)
  const [localModel, setLocalModel] = useState('')
  const [localBaseUrl, setLocalBaseUrl] = useState('')
  const [cloudModel, setCloudModel] = useState('')
  const [cloudBaseUrl, setCloudBaseUrl] = useState('')
  const [cloudApiKey, setCloudApiKey] = useState('')

  useEffect(() => {
    if (llmSettings && provider === null) {
      setProvider(llmSettings.provider)
      setLocalModel(llmSettings.ollama_model)
      setLocalBaseUrl(llmSettings.ollama_base_url)
      setCloudModel(llmSettings.ollama_cloud_model)
      setCloudBaseUrl(llmSettings.ollama_cloud_base_url)
    }
  }, [llmSettings, provider])

  async function handleSaveLlm() {
    if (!provider) return
    if (provider === 'ollama_cloud' && !llmSettings?.ollama_cloud_api_key_configured && !cloudApiKey.trim()) {
      toast.error('Set an Ollama Cloud API key before switching to the cloud provider.')
      return
    }
    try {
      await updateLlm.mutateAsync({
        provider,
        ollama_model: localModel,
        ollama_base_url: localBaseUrl,
        ollama_cloud_model: cloudModel,
        ollama_cloud_base_url: cloudBaseUrl,
        ...(cloudApiKey.trim() ? { ollama_cloud_api_key: cloudApiKey.trim() } : {}),
      })
      setCloudApiKey('')
      toast.success('AI model provider updated.')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to update AI model provider.'))
    }
  }

  const inputClass =
    'w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600 disabled:cursor-not-allowed disabled:opacity-60'

  return (
    <div>
      <PageHeader title="Settings" description="Account details and server configuration" />

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Current User" actions={<UserCircle2 className="h-4 w-4 text-slate-600" />}>
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

        <Card title="AI Model Provider" actions={<ShieldCheck className="h-4 w-4 text-slate-600" />}>
          {llmLoading ? (
            <LoadingSpinner label="Loading AI configuration..." />
          ) : llmIsError ? (
            <ErrorBanner message={getApiErrorMessage(llmError, 'Failed to load AI configuration.')} onRetry={() => refetchLlm()} />
          ) : llmSettings && provider ? (
            <div>
              <div className="mb-4 flex items-center gap-2 text-xs font-medium">
                {llmSettings.reachable ? (
                  <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-emerald-300">
                    <Wifi className="h-3 w-3" /> Reachable
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 rounded-full border border-red-500/40 bg-red-500/10 px-2.5 py-1 text-red-300">
                    <WifiOff className="h-3 w-3" /> Unreachable
                  </span>
                )}
                <span className="text-slate-500">Active provider: {llmSettings.provider === 'ollama_cloud' ? 'Ollama Cloud' : 'Ollama Local'}</span>
              </div>

              <div className="mb-4 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={!isAdmin}
                  onClick={() => setProvider('ollama_local')}
                  className={`flex flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm font-medium transition-colors disabled:cursor-not-allowed ${
                    provider === 'ollama_local'
                      ? 'border-brand-500/60 bg-brand-500/10 text-brand-300'
                      : 'border-slate-700 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <Server className="h-4 w-4" />
                  Local (Ollama)
                </button>
                <button
                  type="button"
                  disabled={!isAdmin}
                  onClick={() => setProvider('ollama_cloud')}
                  className={`flex flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm font-medium transition-colors disabled:cursor-not-allowed ${
                    provider === 'ollama_cloud'
                      ? 'border-brand-500/60 bg-brand-500/10 text-brand-300'
                      : 'border-slate-700 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <Cloud className="h-4 w-4" />
                  Cloud (Ollama Cloud)
                </button>
              </div>

              {provider === 'ollama_local' ? (
                <div className="space-y-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-400">Model</label>
                    <input value={localModel} onChange={(e) => setLocalModel(e.target.value)} disabled={!isAdmin} className={inputClass} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-400">Base URL</label>
                    <input value={localBaseUrl} onChange={(e) => setLocalBaseUrl(e.target.value)} disabled={!isAdmin} className={`${inputClass} font-mono-ids`} />
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-400">Model</label>
                    <input value={cloudModel} onChange={(e) => setCloudModel(e.target.value)} disabled={!isAdmin} className={inputClass} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-400">Base URL</label>
                    <input value={cloudBaseUrl} onChange={(e) => setCloudBaseUrl(e.target.value)} disabled={!isAdmin} className={`${inputClass} font-mono-ids`} />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-400">
                      API Key {llmSettings.ollama_cloud_api_key_configured && <span className="text-emerald-400">(configured)</span>}
                    </label>
                    <input
                      type="password"
                      value={cloudApiKey}
                      onChange={(e) => setCloudApiKey(e.target.value)}
                      disabled={!isAdmin}
                      placeholder={llmSettings.ollama_cloud_api_key_configured ? 'Leave blank to keep current key' : 'Paste your ollama.com API key'}
                      className={inputClass}
                    />
                  </div>
                </div>
              )}

              {isAdmin ? (
                <button
                  onClick={handleSaveLlm}
                  disabled={updateLlm.isPending}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-md bg-brand-600 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {updateLlm.isPending && <InlineSpinner />}
                  Save Changes
                </button>
              ) : (
                <p className="mt-4 text-xs text-slate-500">Only ADMIN users can change the AI model provider.</p>
              )}
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  )
}
