import { FormEvent, useState } from 'react'
import { Radar, Search } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { ReputationBadge, reputationClassName } from '../components/ReputationBadge'
import { getApiErrorMessage } from '../services/client'
import { detailsToText, formatDateTime, formatPercent } from '../utils/format'
import { useThreatIntelLookup } from '../hooks/queries/useThreatIntel'

export default function ThreatIntel() {
  const [indicator, setIndicator] = useState('')
  const [type, setType] = useState('')
  const lookup = useThreatIntelLookup()

  function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!indicator.trim()) return
    lookup.mutate({ indicator: indicator.trim(), type: type || undefined })
  }

  const results = lookup.data

  return (
    <div>
      <PageHeader
        title="Threat Intelligence"
        description="Look up reputation and source information for IPs, domains, URLs, hashes, or CVEs"
      />

      <Card>
        <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-slate-400">Indicator</label>
            <input
              required
              value={indicator}
              onChange={(e) => setIndicator(e.target.value)}
              placeholder="e.g. 8.8.8.8, evil.com, https://evil.com/path, CVE-2023-1234"
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 font-mono-ids"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Type (optional)</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
            >
              <option value="">Auto-detect</option>
              <option value="ip">IP</option>
              <option value="domain">Domain / URL</option>
              <option value="hash">Hash</option>
              <option value="cve">CVE</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={lookup.isPending}
            className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {lookup.isPending ? <InlineSpinner /> : <Search className="h-4 w-4" />}
            Search
          </button>
        </form>
      </Card>

      <div className="mt-6">
        {lookup.isError && (
          <ErrorBanner
            message={getApiErrorMessage(lookup.error, 'Failed to look up threat intelligence.')}
            onRetry={() => lookup.mutate({ indicator: indicator.trim(), type: type || undefined })}
          />
        )}

        {results && results.length === 0 && <EmptyState message="No threat intelligence found for this indicator." />}

        {results && results.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {results.map((res, i) => (
              <div key={i} className={`rounded-lg border p-4 ${reputationClassName(res.reputation)}`}>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 font-mono-ids text-base font-semibold">
                    <Radar className="h-4 w-4 opacity-70" />
                    {res.indicator}
                  </span>
                  <ReputationBadge reputation={res.reputation} />
                </div>
                <p className="mt-1 text-xs opacity-80">
                  {res.indicator_type} &middot; source: {res.source}
                  {res.confidence !== null && ` · confidence: ${formatPercent(res.confidence)}`}
                </p>
                {res.classification && <p className="mt-2 text-sm font-medium opacity-90">{res.classification}</p>}
                {res.details && (
                  <pre className="mt-2 max-h-40 overflow-auto rounded bg-black/20 p-2 text-[11px] opacity-80">
                    {detailsToText(res.details)}
                  </pre>
                )}
                <p className="mt-2 text-[11px] opacity-60">{formatDateTime(res.timestamp)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
