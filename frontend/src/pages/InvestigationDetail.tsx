import { Link, useParams } from 'react-router-dom'
import { BookOpen, FileText, Radar, Sparkles } from 'lucide-react'
import type { TraceStep } from '../types'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { EvidenceSection } from '../components/EvidenceSection'
import { InlineSpinner, LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState, WarningBanner } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import { ReputationBadge, reputationClassName } from '../components/ReputationBadge'
import { getApiErrorMessage } from '../services/client'
import { detailsToText, formatDateTime, formatPercent, titleCase } from '../utils/format'
import { useInvestigationQuery } from '../hooks/queries/useInvestigation'

const PURPOSE_LABEL: Record<string, string> = { investigation_playbook: 'Investigation playbook', response_playbook: 'Response playbook', background: 'Background' }

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function field(record: Record<string, unknown>, key: string): string {
  const value = record[key]
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function InvestigationTimeline({ trace, running }: { trace: TraceStep[]; running: boolean }) {
  if (!trace?.length && !running) return <EmptyState message="No timeline steps recorded." />
  return (
    <ol className="space-y-4">
      {trace.map((step, i) => (
        <li key={i} className="relative flex gap-3 animate-[fade-in_0.2s_ease-out]">
          <div className="flex flex-col items-center">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-brand-500/50 bg-brand-500/10 text-xs font-semibold text-brand-300">
              {i + 1}
            </div>
            {(i < trace.length - 1 || running) && <div className="mt-1 w-px flex-1 bg-slate-800" />}
          </div>
          <div className="pb-2">
            <p className="text-sm font-semibold text-slate-200">{step.action}</p>
            <p className="mt-0.5 text-sm text-slate-400">{step.detail}</p>
          </div>
        </li>
      ))}
      {running && (
        <li className="flex items-center gap-3 text-sm text-slate-400">
          <div className="flex h-6 w-6 items-center justify-center">
            <InlineSpinner />
          </div>
          Agent is working on the next step...
        </li>
      )}
    </ol>
  )
}

export default function InvestigationDetail() {
  const { id } = useParams()
  const { data: investigation, isLoading, isError, error, refetch } = useInvestigationQuery(id)

  if (isLoading) return <LoadingSpinner label="Loading investigation..." />
  if (isError) return <ErrorBanner message={getApiErrorMessage(error, 'Failed to load investigation.')} onRetry={() => refetch()} />
  if (!investigation) return <EmptyState message="Investigation not found." />

  const running = investigation.status === 'RUNNING' || investigation.status === 'PENDING'
  if (running) {
    return (
      <div>
        <PageHeader
          title={`Investigation #${investigation.id}`}
          description={
            <>
              Alert{' '}
              {investigation.alert_id ? (
                <Link to={`/alerts/${investigation.alert_id}`} className="text-brand-400 hover:underline">
                  #{investigation.alert_id}
                </Link>
              ) : (
                '(deleted)'
              )}
            </>
          }
          actions={<StatusBadge status={investigation.status} />}
        />
        <div className="mb-4">
          <WarningBanner
            title="AI investigation in progress"
            message="The agent is gathering evidence, threat intelligence and knowledge, then asking the LLM for its analysis. Each step appears below as it happens; the full results appear here when it finishes. You can leave this page - you will be notified when it completes."
          />
        </div>
        <Card title={`Live Investigation Timeline (${investigation.trace.length} step${investigation.trace.length === 1 ? '' : 's'})`}>
          <InvestigationTimeline trace={investigation.trace} running />
        </Card>
      </div>
    )
  }

  const { ai_analysis } = investigation
  const citedIds = new Set((ai_analysis?.references ?? []).map((r) => r.id))
  const alertEvidence = asRecord(investigation.evidence?.alert)
  const relatedEvents = Array.isArray(investigation.evidence?.related_events)
    ? (investigation.evidence!.related_events as Record<string, unknown>[])
    : []

  return (
    <div>
      <PageHeader
        title={`Investigation #${investigation.id}`}
        description={
          <>
            Alert{' '}
            {investigation.alert_id ? (
              <Link to={`/alerts/${investigation.alert_id}`} className="text-brand-400 hover:underline">
                #{investigation.alert_id}
              </Link>
            ) : (
              '(deleted)'
            )}
            {investigation.incident_id && (
              <>
                {' '}
                &middot; Incident{' '}
                <Link to={`/incidents/${investigation.incident_id}`} className="text-brand-400 hover:underline">
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

      {/* Observed Evidence - directly extracted from logs */}
      <div className="mb-4">
        <EvidenceSection tone="observed" title="Alert Summary & Raw Log Evidence" icon={FileText}>
          {Object.keys(alertEvidence).length > 0 ? (
            <dl className="mb-4 grid grid-cols-2 gap-y-3 text-sm md:grid-cols-4">
              <dt className="text-slate-500">Title</dt>
              <dd className="col-span-3 text-slate-200">{field(alertEvidence, 'title')}</dd>
              <dt className="text-slate-500">Severity</dt>
              <dd>
                <SeverityBadge severity={String(alertEvidence.severity ?? '')} />
              </dd>
              <dt className="text-slate-500">Source IP</dt>
              <dd className="font-mono-ids text-slate-200">{field(alertEvidence, 'source_ip')}</dd>
              <dt className="text-slate-500">Host</dt>
              <dd className="font-mono-ids text-slate-200">{field(alertEvidence, 'host')}</dd>
              <dt className="text-slate-500">Username</dt>
              <dd className="text-slate-200">{field(alertEvidence, 'username')}</dd>
              <dt className="text-slate-500">Detection Rule</dt>
              <dd className="font-mono-ids text-slate-200">{field(alertEvidence, 'detection_rule')}</dd>
              <dt className="text-slate-500">Timestamp</dt>
              <dd className="text-slate-200">{formatDateTime(String(alertEvidence.timestamp ?? ''))}</dd>
            </dl>
          ) : (
            <p className="mb-4 text-sm text-slate-500">No structured alert snapshot recorded for this investigation.</p>
          )}

          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Related Log Events ({relatedEvents.length})
          </p>
          {relatedEvents.length > 0 ? (
            <div className="space-y-2">
              {relatedEvents.slice(0, 20).map((ev, i) => (
                <div key={i} className="rounded-md border border-slate-800 bg-slate-950/60 p-2.5">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>{formatDateTime(String(ev.timestamp ?? ''))}</span>
                    {ev.host ? <span className="font-mono-ids">{String(ev.host)}</span> : null}
                    {ev.source_ip ? <span className="font-mono-ids">{String(ev.source_ip)}</span> : null}
                    {ev.event_type ? <span>{String(ev.event_type)}</span> : null}
                  </div>
                  {ev.raw_log ? (
                    <pre className="mt-1.5 max-h-24 overflow-auto rounded bg-black/30 p-2 text-[11px] text-slate-400">
                      {String(ev.raw_log)}
                    </pre>
                  ) : ev.message ? (
                    <p className="mt-1 text-sm text-slate-300">{String(ev.message)}</p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="No related log events captured for this investigation." />
          )}
        </EvidenceSection>
      </div>

      {/* Threat Intelligence - external / local intelligence */}
      <div className="mb-4">
        <EvidenceSection tone="intel" title="Threat Intelligence" icon={Radar}>
          {investigation.threat_intelligence && investigation.threat_intelligence.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {investigation.threat_intelligence.map((ti, i) => (
                <div key={i} className={`rounded-md border p-3 ${reputationClassName(ti.reputation)}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono-ids text-sm font-semibold">{ti.indicator}</span>
                    <ReputationBadge reputation={ti.reputation} />
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
        </EvidenceSection>
      </div>

      {/* RAG Knowledge - retrieved cybersecurity documentation */}
      <div className="mb-4">
        <EvidenceSection tone="rag" title="RAG Knowledge Sources" icon={BookOpen}>
          {investigation.rag_sources && investigation.rag_sources.length > 0 ? (
            <div className="space-y-3">
              {investigation.rag_sources.map((src, i) => {
                const cited = !!src.id && citedIds.has(src.id)
                return (
                <div
                  key={i}
                  className={`rounded-md border bg-slate-950/60 p-3 ${cited ? 'border-brand-500/50' : 'border-slate-800'}`}
                >
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold text-slate-300">
                      {src.id && <span className="mr-1.5 font-mono-ids text-brand-400">[{src.id}]</span>}
                      {src.title}
                      {cited && <span className="ml-2 rounded bg-brand-500/15 px-1.5 text-[10px] text-brand-300">cited by AI</span>}
                    </span>
                    <span>
                      {src.purpose ? PURPOSE_LABEL[src.purpose] : src.category} &middot; score {src.score.toFixed(2)}
                      {src.match === 'keyword' && ' · exact ID match'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    source: {src.source}
                    {src.page ? `, page ${src.page}` : ''}
                  </p>
                  <p className="mt-2 text-sm text-slate-300">{src.content}</p>
                </div>
                )
              })}
            </div>
          ) : (
            <EmptyState message="No knowledge base sources retrieved (RAG may be unavailable)." />
          )}
        </EvidenceSection>
      </div>

      {/* AI Analysis - LLM-generated interpretation, no chain-of-thought exposed */}
      <div className="mb-4">
        <EvidenceSection tone="ai" title="AI Analysis" icon={Sparkles}>
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
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Evidence Cited</p>
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
                    Recommended Response &mdash; Requires Human Approval
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

              <div className="rounded-md border border-slate-800 p-3">
                <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Sources cited by the AI</p>
                {ai_analysis.references && ai_analysis.references.length > 0 ? (
                  <ul className="space-y-1 text-sm text-slate-300">
                    {ai_analysis.references.map((ref) => (
                      <li key={ref.id}>
                        <span className="mr-1.5 font-mono-ids text-brand-400">[{ref.id}]</span>
                        {ref.title ?? ref.source}
                        <span className="text-slate-500">
                          {' '}
                          &mdash; {ref.source}
                          {ref.page ? `, page ${ref.page}` : ''}
                          {ref.heading && !ref.page ? ` (${ref.heading})` : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-500">
                    The AI did not cite any knowledge base source for this analysis.
                  </p>
                )}
              </div>
            </div>
          )}
        </EvidenceSection>
      </div>

      <Card title="Investigation Timeline">
        <InvestigationTimeline trace={investigation.trace} running={false} />
      </Card>

      <p className="mt-4 text-xs text-slate-600">
        Created {formatDateTime(investigation.created_at)}
        {investigation.completed_at && ` · Completed ${formatDateTime(investigation.completed_at)}`}
        {' · '}
        {titleCase(investigation.status)}
      </p>
    </div>
  )
}
