import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner, InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState, WarningBanner } from '../components/ErrorBanner'
import { SeverityBadge } from '../components/SeverityBadge'
import { StatusBadge } from '../components/StatusBadge'
import { CopyButton } from '../components/CopyButton'
import type { Alert, AlertStatus } from '../types'
import { getAlert, getApiErrorMessage, investigateAlert, updateAlertStatus } from '../services/api'
import { formatDateTime, formatPercent } from '../utils/format'
import { useToast } from '../hooks/useToast'
import { useConfirm } from '../hooks/useConfirm'

const STATUS_OPTIONS: AlertStatus[] = ['NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE']
const CONFIRM_BEFORE: AlertStatus[] = ['RESOLVED', 'FALSE_POSITIVE']

export default function AlertDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const confirm = useConfirm()
  const [alert, setAlert] = useState<Alert | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusUpdating, setStatusUpdating] = useState(false)
  const [investigating, setInvestigating] = useState(false)
  const [investigateError, setInvestigateError] = useState<string | null>(null)

  function load() {
    if (!id) return
    setLoading(true)
    setError(null)
    getAlert(id)
      .then(setAlert)
      .catch((err) => setError(getApiErrorMessage(err, 'Failed to load alert.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [id])

  async function handleStatusChange(newStatus: AlertStatus) {
    if (!id) return

    if (CONFIRM_BEFORE.includes(newStatus)) {
      const ok = await confirm({
        title: `Mark alert as ${newStatus.replace('_', ' ')}?`,
        message:
          newStatus === 'FALSE_POSITIVE'
            ? 'This marks the detection as a false positive. You can still change it back later if needed.'
            : 'This marks the alert as resolved. Make sure any recommended response actions have actually been carried out first.',
        confirmLabel: `Mark as ${newStatus.replace('_', ' ')}`,
        tone: 'danger',
      })
      if (!ok) return
    }

    setStatusUpdating(true)
    try {
      const updated = await updateAlertStatus(id, newStatus)
      setAlert(updated)
      toast.success(`Status changed to ${newStatus.replace('_', ' ')}`)
    } catch (err) {
      const message = getApiErrorMessage(err, 'Failed to update status.')
      setError(message)
      toast.error(message)
    } finally {
      setStatusUpdating(false)
    }
  }

  async function handleInvestigate() {
    if (!id) return
    setInvestigating(true)
    setInvestigateError(null)
    toast.info('AI investigation started - this can take up to a couple of minutes on local hardware.')
    try {
      const investigation = await investigateAlert(id)
      toast.success('Investigation completed - opening results.')
      navigate(`/investigations/${investigation.id}`)
    } catch (err) {
      const message = getApiErrorMessage(err, 'Investigation failed to complete.')
      setInvestigateError(message)
      toast.error(message)
    } finally {
      setInvestigating(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading alert..." />
  if (error) return <ErrorBanner message={error} onRetry={load} />
  if (!alert) return <EmptyState message="Alert not found." />

  return (
    <div>
      <PageHeader
        title={alert.title}
        description={`Alert #${alert.id}`}
        actions={
          <button
            onClick={handleInvestigate}
            disabled={investigating}
            className="flex items-center gap-2 rounded-md bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {investigating && <InlineSpinner />}
            {investigating ? 'Investigating...' : 'Investigate with AI'}
          </button>
        }
      />

      {investigating && (
        <div className="mb-4">
          <WarningBanner
            title="AI investigation running"
            message="This may take up to 2 minutes on local hardware. Please keep this tab open."
          />
        </div>
      )}
      {investigateError && (
        <div className="mb-4">
          <ErrorBanner message={investigateError} onRetry={handleInvestigate} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Overview" className="lg:col-span-2">
          <dl className="grid grid-cols-2 gap-y-3 text-sm">
            <dt className="text-slate-500">Severity</dt>
            <dd>
              <SeverityBadge severity={alert.severity} />
            </dd>
            <dt className="text-slate-500">Confidence</dt>
            <dd className="text-slate-200">{formatPercent(alert.confidence)}</dd>
            <dt className="text-slate-500">Status</dt>
            <dd>
              <StatusBadge status={alert.status} />
            </dd>
            <dt className="text-slate-500">Timestamp</dt>
            <dd className="text-slate-200">{formatDateTime(alert.timestamp)}</dd>
            <dt className="text-slate-500">Host</dt>
            <dd className="flex items-center font-mono-ids text-slate-200">
              {alert.host ?? '—'}
              {alert.host && <CopyButton value={alert.host} />}
            </dd>
            <dt className="text-slate-500">Source IP</dt>
            <dd className="flex items-center font-mono-ids text-slate-200">
              {alert.source_ip ?? '—'}
              {alert.source_ip && <CopyButton value={alert.source_ip} />}
            </dd>
            <dt className="text-slate-500">Username</dt>
            <dd className="text-slate-200">{alert.username ?? '—'}</dd>
            <dt className="text-slate-500">Detection Rule</dt>
            <dd className="font-mono-ids text-slate-200">{alert.detection_rule ?? '—'}</dd>
            {alert.incident_id && (
              <>
                <dt className="text-slate-500">Incident</dt>
                <dd>
                  <Link to={`/incidents/${alert.incident_id}`} className="text-sky-400 hover:underline">
                    INC-{alert.incident_id}
                  </Link>
                </dd>
              </>
            )}
          </dl>

          {alert.description && (
            <div className="mt-4 border-t border-slate-800 pt-4">
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Description</p>
              <p className="text-sm text-slate-300">{alert.description}</p>
            </div>
          )}
        </Card>

        <Card title="Change Status">
          <div className="flex flex-col gap-2">
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleStatusChange(s)}
                disabled={statusUpdating || alert.status === s}
                className={`rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                  alert.status === s
                    ? 'border-sky-500/60 bg-sky-500/10 text-sky-300'
                    : 'border-slate-700 text-slate-300 hover:bg-slate-800'
                } disabled:cursor-not-allowed disabled:opacity-60`}
              >
                {s}
              </button>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-4">
        <Card title="Evidence">
          {alert.evidence && alert.evidence.length > 0 ? (
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-300">
              {alert.evidence.map((e, i) => (
                <li key={i} className="font-mono-ids">
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="No evidence recorded for this alert." />
          )}
        </Card>
      </div>
    </div>
  )
}
