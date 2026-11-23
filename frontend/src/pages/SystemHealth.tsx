import { useState } from 'react'
import { Database, Radar, Server, ShieldCheck, Wifi, WifiOff } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LiveToggle } from '../components/LiveToggle'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner } from '../components/ErrorBanner'
import { getApiErrorMessage } from '../services/client'
import { useSystemHealthQuery, useVectorDbStatusQuery } from '../hooks/queries/useSystemHealth'

const TI_PROVIDERS = [
  { name: 'VirusTotal', description: 'External reputation lookups for IPs, domains, hashes (requires API key)' },
  { name: 'NVD (NIST)', description: 'CVE metadata and severity scoring' },
  { name: 'Local Intel Store', description: 'Curated known-bad IPs/domains bundled with the backend' },
]

function StatusTile({
  label,
  ok,
  detail,
  icon: Icon,
}: {
  label: string
  ok: boolean | null
  detail?: string
  icon: LucideIcon
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg ${
            ok === null ? 'bg-slate-800 text-slate-500' : ok ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
          }`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-200">{label}</p>
          <p
            className={`text-xs font-medium ${
              ok === null ? 'text-slate-500' : ok ? 'text-emerald-400' : 'text-red-400'
            }`}
          >
            {ok === null ? 'Unknown' : ok ? 'Operational' : 'Degraded'}
          </p>
        </div>
      </div>
      {detail && <p className="mt-2 truncate font-mono-ids text-xs text-slate-500" title={detail}>{detail}</p>}
    </div>
  )
}

export default function SystemHealth() {
  const [live, setLive] = useState(true)
  const { data: health, isLoading, isError, error, refetch, dataUpdatedAt } = useSystemHealthQuery(live)
  const vectorDb = useVectorDbStatusQuery(live)

  if (isLoading) return <LoadingSpinner label="Checking system health..." />
  if (isError) return <ErrorBanner message={getApiErrorMessage(error, 'Failed to load system health.')} onRetry={() => refetch()} />

  const dbOk = health?.checks.database === 'ok' || health?.checks.database === true
  const ollamaOk = health?.checks.ollama === 'ok' || health?.checks.ollama === true
  const overallOk = health?.status === 'ok'

  return (
    <div>
      <PageHeader
        title="System Health"
        description="Live status of core services backing the SOC platform"
        actions={
          <LiveToggle live={live} onToggle={() => setLive((v) => !v)} lastUpdated={dataUpdatedAt ? new Date(dataUpdatedAt) : null} />
        }
      />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatusTile label="FastAPI Backend" ok={overallOk} detail={health?.app} icon={Server} />
        <StatusTile label="Database" ok={dbOk} detail={typeof health?.checks.database === 'string' ? health.checks.database : undefined} icon={Database} />
        <StatusTile label="Ollama (LLM)" ok={ollamaOk} detail={typeof health?.checks.ollama === 'string' ? health.checks.ollama : undefined} icon={ollamaOk ? Wifi : WifiOff} />
        <StatusTile
          label="Vector DB (Chroma)"
          ok={vectorDb.isSuccess ? vectorDb.data.available : vectorDb.isError ? false : null}
          detail={vectorDb.data?.message || undefined}
          icon={ShieldCheck}
        />
      </div>

      <Card title="Threat Intelligence Services">
        <p className="mb-3 text-xs text-slate-500">
          Providers integrated by the backend's threat intelligence service. Availability of external providers
          depends on API keys configured server-side.
        </p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {TI_PROVIDERS.map((p) => (
            <div key={p.name} className="rounded-md border border-slate-800 bg-slate-950/60 p-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                <Radar className="h-4 w-4 text-purple-400" />
                {p.name}
              </div>
              <p className="mt-1 text-xs text-slate-500">{p.description}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
