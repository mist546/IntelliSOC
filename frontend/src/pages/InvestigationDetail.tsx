import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState, WarningBanner } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import type { Investigation, Reputation } from '../types'
import { getApiErrorMessage, getInvestigation } from '../services/api'
import { formatDateTime, formatPercent, titleCase } from '../utils/format'

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

export default function InvestigationDetail() {
  const { id } = useParams()
  const [investigation, setInvestigation] = useState<Investigation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function load() {
    if (!id) return
    setLoading(true)
    setError(null)
    getInvestigation(id)
      .then(setInvestigation)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load investigation.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [id])

  if (loading) return <LoadingSpinner label="Loading investigation..." />
  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!investigation) return <EmptyState message="Investigation not found." />

  const { ai_analysis } = investigation

  return (
    <div>
      <PageHeader
        title={`Investigation #${investigation.id}`}
        description={
          <>
            Alert{' '}
            <Link to={`/alerts/${investigation.alert_id}`} className="text-sky-400 hover:underline">
              #{investigation.alert_id}
            </Link>
            {investigation.incident_id && (
              <>
                {' '}
                &middot; Incident{' '}
                <Link to={`/incidents/${investigation.incident_id}`} className="text-sky-400 hover:underline">
                  #{investigation.incident_id}
                </Link>
              </>
            )}
          </>
        }
        actions={<StatusBadge status={investigation.status} />}
      />

      {!investigation.llm_available && (
        <div className="mb-4">
          <WarningBanner
            title="AI analysis unavailable"
            message={investigation.error_message ?? 'The LLM backend (Ollama) could not be reached. Showing raw evidence and trace only.'}
          />
        </div>
      )}

      {investigation.status === 'FAILED' && investigation.error_message && (
        <div className="mb-4">
          <ErrorBanner message={investigation.error_message} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Agent Trace" className="lg:col-span-2">
          {investigation.trace && investigation.trace.length > 0 ? (
            <ol className="space-y-4">
              {investigation.trace.map((step, i) => (
                <li key={i} className="relative flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-sky-500/50 bg-sky-500/10 text-xs font-semibold text-sky-300">
                      {i + 1}
                    </div>
                    {i < investigation.trace.length - 1 && <div className="mt-1 w-px flex-1 bg-slate-800" />}
                  </div>
                  <div className="pb-2">
                    <p className="text-sm font-semibold text-slate-200">{step.action}</p>
                    <p className="mt-0.5 text-sm text-slate-400">{step.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState message="No trace steps recorded." />
          )}
        </Card>

        <Card title="Risk Score">
          <div className="flex flex-col items-center py-4">
            <div
              className={`text-5xl font-bold ${
                investigation.risk_score === null
                  ? 'text-slate-500'
                  : investigation.risk_score >= 75
                  ? 'text-red-500'
                  : investigation.risk_score >= 50
                  ? 'text-orange-500'
                  : investigation.risk_score >= 25
                  ? 'text-yellow-500'
                  : 'text-blue-400'
              }`}
            >
              {investigation.risk_score ?? '—'}
            </div>
            <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">out of 100</p>
          </div>
          {investigation.risk_factors && investigation.risk_factors.length > 0 ? (
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-300">
              {investigation.risk_factors.map((factor, i) => (
                <li key={i}>{factor}</li>
              ))}
            </ul>
          ) : (
            <p className="text-center text-xs text-slate-500">No risk factors recorded.</p>
          )}
        </Card>
      </div>

      <div className="mt-4">
        <Card title="Threat Intelligence">
          {investigation.threat_intelligence && investigation.threat_intelligence.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {investigation.threat_intelligence.map((ti, i) => (
                <div key={i} className={`rounded-md border p-3 ${REPUTATION_STYLES[ti.reputation] ?? REPUTATION_STYLES.unknown}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono-ids text-sm font-semibold">{ti.indicator}</span>
                    <span className="rounded bg-black/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">
                      {ti.reputation}
                    </span>
                  </div>
                  <p className="mt-1 text-xs opacity-80">
                    {ti.indicator_type} &middot; source: {ti.source}
                    {ti.confidence !== null && ` · confidence: ${formatPercent(ti.confidence)}`}
                  </p>
                  {ti.classification && <p className="mt-1 text-xs opacity-90">{ti.classification}</p>}
                  {ti.details && (
                    <pre className="mt-2 max-h-32 overflow-auto rounded bg-black/20 p-2 text-[11px] opacity-80">
                      {detailsToText(ti.details)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="No threat intelligence indicators enriched for this alert." />
          )}
        </Card>
      </div>

      <div className="mt-4">
        <Card title="RAG Knowledge Sources">
          {investigation.rag_sources && investigation.rag_sources.length > 0 ? (
            <div className="space-y-3">
              {investigation.rag_sources.map((src, i) => (
                <div key={i} className="rounded-md border border-slate-800 bg-slate-950/60 p-3">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold text-slate-300">{src.title}</span>
                    <span>
                      {src.category} &middot; score {src.score.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">source: {src.source}</p>
                  <p className="mt-2 text-sm text-slate-300">{src.content}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="No knowledge base sources retrieved (RAG may be unavailable)." />
          )}
        </Card>
      </div>

      <div className="mt-4">
        <Card title="AI Analysis">
          {!ai_analysis ? (
            <EmptyState message="No AI analysis available for this investigation." />
          ) : (
            <div>
              {ai_analysis.insufficient_evidence && (
                <div className="mb-4">
                  <WarningBanner
                    title="Insufficient evidence"
                    message="The AI determined there was not enough evidence to draw a confident conclusion. Treat this analysis as preliminary."
                  />
                </div>
              )}

              <div className="mb-4 grid grid-cols-2 gap-y-3 text-sm md:grid-cols-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Attack Type</p>
                  <p className="text-slate-200">{ai_analysis.attack_type ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Severity</p>
                  {ai_analysis.severity ? <SeverityBadge severity={ai_analysis.severity} /> : <p className="text-slate-200">—</p>}
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Confidence</p>
                  <p className="text-slate-200">{formatPercent(ai_analysis.confidence)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">MITRE / OWASP</p>
                  <p className="font-mono-ids text-slate-200">
                    {ai_analysis.mitre_technique ?? '—'} {ai_analysis.owasp_category ? `/ ${ai_analysis.owasp_category}` : ''}
                  </p>
                </div>
              </div>

              {ai_analysis.summary && (
                <div className="mb-4 border-t border-slate-800 pt-4">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Summary</p>
                  <p className="text-sm text-slate-300">{ai_analysis.summary}</p>
                </div>
              )}

              {ai_analysis.threat_context && (
                <div className="mb-4">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Threat Context</p>
                  <p className="text-sm text-slate-300">{ai_analysis.threat_context}</p>
                </div>
              )}

              {ai_analysis.impact && (
                <div className="mb-4">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Impact</p>
                  <p className="text-sm text-slate-300">{ai_analysis.impact}</p>
                </div>
              )}

              {ai_analysis.evidence && ai_analysis.evidence.length > 0 && (
                <div className="mb-4">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Evidence</p>
                  <ul className="list-inside list-disc space-y-1 text-sm text-slate-300">
                    {ai_analysis.evidence.map((e, i) => (
                      <li key={i} className="font-mono-ids">
                        {e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {ai_analysis.recommended_actions && ai_analysis.recommended_actions.length > 0 && (
                <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-3">
                  <p className="mb-2 text-xs font-bold uppercase tracking-wide text-amber-400">
                    Recommended &mdash; Requires Human Approval
                  </p>
                  <ul className="space-y-2">
                    {ai_analysis.recommended_actions.map((action, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <input type="checkbox" disabled className="mt-1" />
                        <span>{action}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <p className="mt-4 text-xs text-slate-600">
        Created {formatDateTime(investigation.created_at)}
        {investigation.completed_at && ` · Completed ${formatDateTime(investigation.completed_at)}`}
        {' · '}
        {titleCase(investigation.status)}
      </p>
    </div>
  )
}
