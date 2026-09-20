import { ChangeEvent, DragEvent, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { UploadCloud } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { SortableTh } from '../components/SortableTh'
import { TableSkeleton } from '../components/TableSkeleton'
import type { LogEvent } from '../types'
import { getApiErrorMessage } from '../services/client'
import { formatDateTime } from '../utils/format'
import { useToast } from '../hooks/useToast'
import { useSortableData } from '../hooks/useSortableData'
import { useLogsQuery, useUploadLog } from '../hooks/queries/useLogs'

const SUPPORTED_FORMATS = ['auth.log', 'Apache', 'Nginx', 'Syslog', 'CSV', 'JSON']

export default function Logs() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sourceIp, setSourceIp] = useState(searchParams.get('source_ip') ?? '')
  const [eventType, setEventType] = useState(searchParams.get('event_type') ?? '')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: logs = [], isLoading, isError, error, refetch } = useLogsQuery({
    source_ip: sourceIp || undefined,
    event_type: eventType || undefined,
  })
  const upload = useUploadLog()

  const { sorted, sortKey, sortDir, requestSort } = useSortableData<LogEvent>(logs, {
    timestamp: (l) => new Date(l.timestamp).getTime(),
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
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceIp, eventType])

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
          <span className="text-xs text-slate-500">{logs.length} event(s)</span>
        </div>

        {isLoading ? (
          <TableSkeleton columns={8} />
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
                  <tr key={log.id} className="border-b border-slate-900 hover:bg-slate-800/40">
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(log.timestamp)}</td>
                    <td className="px-3 py-2 text-slate-300">{log.host ?? '—'}</td>
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
    </div>
  )
}
