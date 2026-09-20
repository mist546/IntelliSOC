import { Pause, Radio } from 'lucide-react'

export function LiveToggle({
  live,
  onToggle,
  lastUpdated,
}: {
  live: boolean
  onToggle: () => void
  lastUpdated: Date | null
}) {
  return (
    <button
      onClick={onToggle}
      title={live ? 'Auto-refreshing - click to pause' : 'Auto-refresh paused - click to resume'}
      className={`flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
        live
          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
          : 'border-slate-700 text-slate-400 hover:bg-slate-800'
      }`}
    >
      {live ? (
        <Radio className="h-3.5 w-3.5" style={{ animation: 'pulse-dot 1.6s ease-in-out infinite' }} />
      ) : (
        <Pause className="h-3.5 w-3.5" />
      )}
      {live ? 'Live' : 'Paused'}
      {lastUpdated && (
        <span className="text-slate-500">
          &middot; {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
      )}
    </button>
  )
}
