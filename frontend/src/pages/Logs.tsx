import { ChangeEvent, DragEvent, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ExternalLink, UploadCloud, X } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { CopyButton } from '../components/CopyButton'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import type { LogEvent, WazuhContext } from '../types'
import { getApiErrorMessage } from '../services/client'
import { formatDateTime } from '../utils/format'
import { useToast } from '../hooks/useToast'
import { useSortableData } from '../hooks/useSortableData'
import { useLogsQuery, useUploadLog } from '../hooks/queries/useLogs'

const SUPPORTED_FORMATS = [
  'auth.log',
  'Apache',
  'Nginx',
  'Syslog',
  'CSV',
  'JSON',
  'Windows Security (JSON export)',
  'Wazuh alerts/archives (JSON)',
]

// "wazuh" means "arrived through a Wazuh manager", whatever the underlying
// log type; the rest filter on the stored source type.
const SOURCE_FILTERS: { value: string; label: string }[] = [
  { value: '', label: 'All sources' },
  { value: 'wazuh', label: 'Via Wazuh' },
  { value: 'AUTH_LOG', label: 'Auth log' },
  { value: 'WINDOWS_EVENT', label: 'Windows event' },
  { value: 'NGINX_ACCESS', label: 'Nginx access' },
  { value: 'APACHE_ACCESS', label: 'Apache access' },
  { value: 'SYSLOG', label: 'Syslog' },
  { value: 'WAZUH', label: 'Other Wazuh alerts' },
  { value: 'CSV', label: 'CSV' },
  { value: 'JSON', label: 'JSON' },
]

function wazuhOf(log: LogEvent): WazuhContext | undefined {
  return log.metadata?.wazuh
}

function sourceLabel(log: LogEvent): string {
  return wazuhOf(log) ? `Wazuh ${log.source_type}` : log.source_type
}

/** Wazuh rule levels run 0-15; 12+ is Wazuh's "high importance" band. */
function levelClass(level: number | undefined): string {
  if (level === undefined) return 'border-slate-700 text-slate-400'
  if (level >= 12) return 'border-red-500/50 bg-red-500/10 text-red-300'
  if (level >= 7) return 'border-amber-500/50 bg-amber-500/10 text-amber-300'
  return 'border-slate-700 bg-slate-800/60 text-slate-300'
}

function mitreUrl(id: string): string {
  return `https://attack.mitre.org/techniques/${id.replace('.', '/')}/`
}

export default function Logs() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sourceIp, setSourceIp] = useState(searchParams.get('source_ip') ?? '')
  const [eventType, setEventType] = useState(searchParams.get('event_type') ?? '')
  const [source, setSource] = useState(searchParams.get('source') ?? '')
  const [selected, setSelected] = useState<LogEvent | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: logs = [], isLoading, isError, error, refetch } = useLogsQuery({
    source_ip: sourceIp || undefined,
    event_type: eventType || undefined,
    source_type: source && source !== 'wazuh' ? source : undefined,
    wazuh: source === 'wazuh' ? 'true' : undefined,
  })
  const upload = useUploadLog()

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<LogEvent>(logs, {
    timestamp: (l) => new Date(l.timestamp).getTime(),
    source: sourceLabel,
    host: (l) => l.host ?? '',
    source_ip: (l) => l.source_ip ?? '',
    destination_ip: (l) => l.destination_ip ?? '',
    event_type: (l) => l.event_type ?? '',
    action: (l) => l.action ?? '',
    status: (l) => l.status ?? '',
  })

  // Keep the URL in sync with the filter inputs so a chart drill-through
  // link (e.g. /logs?event_type=HTTP_REQUEST) and manual edits both work,
  // and the current filter state is shareable/bookmarkable.
  useEffect(() => {
    const next = new URLSearchParams()
    if (sourceIp) next.set('source_ip', sourceIp)
    if (eventType) next.set('event_type', eventType)
    if (source) next.set('source', source)
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceIp, eventType, source])

  async function handleUpload(file: File) {
    try {
      const result = await upload.mutateAsync(file)
      toast.success(
        `${result.filename}: ${result.events_created} event(s), ${result.alerts_created} alert(s), ${result.incidents_created} incident(s) created`,
      )
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to upload log file.'))
    }
  }

  function onFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
    e.target.value = ''
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleUpload(file)
  }

  const uploadResult = upload.data
  const uploadError = upload.isError ? getApiErrorMessage(upload.error, 'Failed to upload log file.') : null

  return (
    <div>
      <PageHeader title="Log Events" description="Ingested events from collector agents and manual uploads" />

      <div className="mb-6">
        <Card title="Upload Log File">
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragOver ? 'border-brand-500 bg-brand-500/5' : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".log,.txt,.csv,.json"
              className="hidden"
              onChange={onFileInputChange}
            />
            {upload.isPending ? (
              <div className="flex items-center gap-2 text-slate-300">
                <InlineSpinner />
                Uploading and parsing...
              </div>
            ) : (
              <>
                <UploadCloud className="mb-2 h-8 w-8 text-slate-600" />
                <p className="text-sm font-medium text-slate-300">Drag and drop a log file here, or click to browse</p>
                <div className="mt-2 flex flex-wrap justify-center gap-1.5">
                  {SUPPORTED_FORMATS.map((f) => (
                    <span key={f} className="rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400">
                      {f}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>

          {uploadError && (
            <div className="mt-3">
              <ErrorBanner message={uploadError} />
            </div>
          )}

          {uploadResult && (
            <div className="mt-3 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">
              <p className="font-semibold">
                Ingested "{uploadResult.filename}" ({uploadResult.source_type})
              </p>
              <p className="mt-1">
                {uploadResult.events_created} event(s) &middot; {uploadResult.alerts_created} alert(s) &middot;{' '}
                {uploadResult.incidents_created} incident(s) created
              </p>
              {uploadResult.parse_errors?.length > 0 && (
                <div className="mt-2 text-amber-300">
                  <p className="font-medium">{uploadResult.parse_errors.length} parse warning(s):</p>
                  <ul className="list-inside list-disc">
                    {uploadResult.parse_errors.slice(0, 5).map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input
            value={sourceIp}
            onChange={(e) => setSourceIp(e.target.value)}
            placeholder="Filter by source IP"
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600"
          />
          <input
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            placeholder="Filter by event type"
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600"
          />
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200"
          >
            {SOURCE_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
          <span className="text-xs text-slate-500">{logs.length} event(s) &middot; click a row for details</span>
        </div>

        {isLoading ? (
          <TableSkeleton columns={9} />
        ) : isError ? (
          <ErrorBanner message={getApiErrorMessage(error, 'Failed to load logs.')} onRetry={() => refetch()} />
        ) : logs.length === 0 ? (
          <EmptyState message="No log events match the current filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <SortableTh label="Timestamp" sortKey="timestamp" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Source" sortKey="source" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Host" sortKey="host" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Source IP" sortKey="source_ip" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Dest IP" sortKey="destination_ip" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Event Type" sortKey="event_type" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Action" sortKey="action" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <SortableTh label="Status" sortKey="status" activeKey={sortKey} direction={sortDir} onSort={requestSort} />
                  <th className="px-3 py-2">Message</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((log) => (
                  <tr
                    key={log.id}
                    onClick={() => setSelected(log)}
                    className="cursor-pointer border-b border-slate-900 hover:bg-slate-800/40"
                  >
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(log.timestamp)}</td>
                    <td className="px-3 py-2">
                      <SourceCell log={log} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-slate-300">{log.host ?? '—'}</td>
                    <td className="px-3 py-2 font-mono-ids text-slate-400">{log.source_ip ?? '—'}</td>
                    <td className="px-3 py-2 font-mono-ids text-slate-400">{log.destination_ip ?? '—'}</td>
                    <td className="px-3 py-2 text-slate-300">{log.event_type ?? '—'}</td>
                    <td className="px-3 py-2 text-slate-400">{log.action ?? '—'}</td>
                    <td className="px-3 py-2 text-slate-400">{log.status ?? '—'}</td>
                    <td className="max-w-xs truncate px-3 py-2 text-slate-400" title={log.message ?? ''}>
                      {log.message ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selected && <LogDetailModal log={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function SourceCell({ log }: { log: LogEvent }) {
  const wazuh = wazuhOf(log)
  if (!wazuh) return <span className="text-xs text-slate-400">{log.source_type}</span>
  return (
    <div className="flex flex-col gap-0.5">
      <span className="w-fit rounded border border-violet-500/50 bg-violet-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-violet-300">
        Wazuh
      </span>
      <span className="whitespace-nowrap text-[11px] text-slate-500">
        {wazuh.rule_id ? `rule ${wazuh.rule_id}` : 'no rule'}
        {wazuh.rule_level !== undefined && ` · L${wazuh.rule_level}`}
      </span>
    </div>
  )
}

function Field({ label, value, mono }: { label: string; value: string | number | null | undefined; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`mt-0.5 break-words text-sm text-slate-200 ${mono ? 'font-mono-ids' : ''}`}>
        {value === null || value === undefined || value === '' ? '—' : value}
      </dd>
    </div>
  )
}

function LogDetailModal({ log, onClose }: { log: LogEvent; onClose: () => void }) {
  const wazuh = wazuhOf(log)
  const otherMetadata = Object.entries(log.metadata ?? {}).filter(
    ([key, value]) => key !== 'wazuh' && value !== null && value !== undefined && value !== '',
  )

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 animate-[fade-in_0.1s_ease-out]"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 p-5 shadow-xl animate-[scale-in_0.12s_ease-out]"
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-100">{log.event_type ?? 'Log event'}</h3>
            <p className="mt-0.5 text-xs text-slate-500">
              {formatDateTime(log.timestamp)} &middot; {sourceLabel(log)} &middot; received from {log.source}
            </p>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-200" title="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        {wazuh && (
          <section className="mb-5 rounded-md border border-violet-500/40 bg-violet-500/5 p-4">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded border border-violet-500/50 bg-violet-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-violet-300">
                Wazuh
              </span>
              {wazuh.rule_id && <span className="text-sm font-medium text-slate-200">Rule {wazuh.rule_id}</span>}
              {wazuh.rule_level !== undefined && (
                <span className={`rounded border px-1.5 py-0.5 text-[11px] font-semibold ${levelClass(wazuh.rule_level)}`}>
                  Level {wazuh.rule_level}
                </span>
              )}
            </div>
            <p className="mb-3 text-sm text-slate-300">
              {wazuh.rule_description ?? 'Event matched no Wazuh rule (archived by the manager).'}
            </p>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-slate-500">MITRE ATT&CK</dt>
                <dd className="mt-0.5 flex flex-wrap gap-1">
                  {wazuh.mitre_ids?.length
                    ? wazuh.mitre_ids.map((id) => (
                        <a
                          key={id}
                          href={mitreUrl(id)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 rounded bg-slate-800 px-1.5 py-0.5 font-mono-ids text-xs text-brand-300 hover:bg-slate-700"
                        >
                          {id}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ))
                    : <span className="text-sm text-slate-200">—</span>}
                </dd>
              </div>
              <Field label="Rule groups" value={wazuh.rule_groups?.join(', ')} />
              <Field label="Wazuh agent" value={[wazuh.agent_name, wazuh.agent_id && `#${wazuh.agent_id}`].filter(Boolean).join(' ')} />
              <Field label="Agent IP" value={wazuh.agent_ip} mono />
              <Field label="Location" value={wazuh.location} mono />
              <Field label="Wazuh alert ID" value={wazuh.alert_id} mono />
            </dl>
          </section>
        )}

        <dl className="mb-5 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          <Field label="Host" value={log.host} />
          <Field label="Source IP" value={log.source_ip} mono />
          <Field label="Dest IP" value={log.destination_ip} mono />
          <Field label="Username" value={log.username} />
          <Field label="Action" value={log.action} />
          <Field label="Status" value={log.status} />
          {otherMetadata.map(([key, value]) => (
            <Field key={key} label={key.replace(/_/g, ' ')} value={typeof value === 'object' ? JSON.stringify(value) : String(value)} />
          ))}
        </dl>

        <Field label="Message" value={log.message} />

        {log.raw_log && (
          <div className="mt-4">
            <div className="mb-1 flex items-center">
              <span className="text-[11px] uppercase tracking-wide text-slate-500">Raw log</span>
              <CopyButton value={log.raw_log} />
            </div>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md border border-slate-800 bg-slate-950 p-3 font-mono-ids text-xs text-slate-300">
              {log.raw_log}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
