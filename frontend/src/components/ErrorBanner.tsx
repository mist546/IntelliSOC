export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 rounded border border-red-500/40 px-2 py-1 text-xs font-medium text-red-200 hover:bg-red-500/20"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function WarningBanner({ title, message }: { title: string; message?: string | null }) {
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
      <p className="font-semibold">{title}</p>
      {message && <p className="mt-1 text-amber-200/90">{message}</p>}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 px-4 py-10 text-center text-sm text-slate-500">
      {message}
    </div>
  )
}
