import { FormEvent, useState } from 'react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import type { Reputation, ThreatIntelResult } from '../types'
import { getApiErrorMessage, lookupThreatIntel } from '../services/api'
import { formatDateTime, formatPercent } from '../utils/format'

const REPUTATION_STYLES: Record<Reputation, string> = {
  malicious: 'border-red-500/40 bg-red-500/10 text-red-300',
  suspicious: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
  clean: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  unknown: 'border-slate-600/40 bg-slate-600/10 text-slate-300',
}

function detailsToText(details: string | Record<string, unknown> | null): string {
  if (!details) return ''
  if (typeof details === 'string') return details
  try {
    return JSON.stringify(details, null, 2)
  } catch {
    return String(details)
  }
}

export default function ThreatIntel() {
  const [indicator, setIndicator] = useState('')
  const [type, setType] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<ThreatIntelResult[] | null>(null)

  async function runSearch() {
    if (!indicator.trim()) return
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await lookupThreatIntel(indicator.trim(), type || undefined)
      setResults(res)
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to look up threat intelligence.'))
    } finally {
      setLoading(false)
    }
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault()
    runSearch()
  }

  return (
    <div>
      <PageHeader title="Threat Intelligence" description="Look up reputation data for IPs, domains, hashes, or CVEs" />

      <Card>
        <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-slate-400">Indicator</label>
            <input
              required
              value={indicator}
              onChange={(e) => setIndicator(e.target.value)}
              placeholder="e.g. 8.8.8.8, evil.com, CVE-2023-1234"
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
              <option value="domain">Domain</option>
              <option value="hash">Hash</option>
              <option value="cve">CVE</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading && <InlineSpinner />}
            Search
          </button>
        </form>
      </Card>

      <div className="mt-6">
        {error && <ErrorBanner message={error} onRetry={runSearch} />}

        {results && results.length === 0 && <EmptyState message="No threat intelligence found for this indicator." />}

        {results && results.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {results.map((res, i) => (
              <div key={i} className={`rounded-lg border p-4 ${REPUTATION_STYLES[res.reputation] ?? REPUTATION_STYLES.unknown}`}>
                <div className="flex items-center justify-between">
                  <span className="font-mono-ids text-base font-semibold">{res.indicator}</span>
                  <span className="rounded bg-black/20 px-2 py-1 text-xs font-bold uppercase tracking-wide">
                    {res.reputation}
                  </span>
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
