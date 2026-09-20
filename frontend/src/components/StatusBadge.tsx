const STYLES: Record<string, string> = {
  NEW: 'bg-sky-500/15 text-sky-400 border-sky-500/40',
  ACKNOWLEDGED: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/40',
  INVESTIGATING: 'bg-purple-500/15 text-purple-400 border-purple-500/40',
  RESOLVED: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40',
  FALSE_POSITIVE: 'bg-slate-500/15 text-slate-400 border-slate-500/40',
  OPEN: 'bg-red-500/15 text-red-400 border-red-500/40',
  CONTAINED: 'bg-amber-500/15 text-amber-400 border-amber-500/40',
  CLOSED: 'bg-slate-500/15 text-slate-400 border-slate-500/40',
  PENDING: 'bg-slate-500/15 text-slate-400 border-slate-500/40',
  RUNNING: 'bg-purple-500/15 text-purple-400 border-purple-500/40',
  COMPLETED: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40',
  FAILED: 'bg-red-500/15 text-red-400 border-red-500/40',
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const style = status && STYLES[status] ? STYLES[status] : 'bg-slate-500/15 text-slate-400 border-slate-500/40'
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold tracking-wide ${style}`}>
      {status ?? 'UNKNOWN'}
    </span>
  )
}
