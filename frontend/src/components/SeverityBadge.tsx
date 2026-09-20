import type { Severity } from '../types'

const STYLES: Record<Severity, string> = {
  CRITICAL: 'bg-red-500/15 text-red-400 border-red-500/40',
  HIGH: 'bg-orange-500/15 text-orange-400 border-orange-500/40',
  MEDIUM: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/40',
  LOW: 'bg-blue-500/15 text-blue-400 border-blue-500/40',
}

export const SEVERITY_COLOR: Record<Severity, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#60a5fa',
}

export function SeverityBadge({ severity }: { severity: Severity | string | null | undefined }) {
  const key = (severity as Severity) in STYLES ? (severity as Severity) : undefined
  const style = key ? STYLES[key] : 'bg-slate-500/15 text-slate-400 border-slate-500/40'
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold tracking-wide ${style}`}
    >
      {severity ?? 'UNKNOWN'}
    </span>
  )
}
