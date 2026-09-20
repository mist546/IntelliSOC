export function TableSkeleton({ columns, rows = 6 }: { columns: number; rows?: number }) {
  return (
    <div className="animate-pulse" aria-hidden="true">
      <div className="mb-2 flex gap-4 border-b border-slate-800 pb-3">
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="h-3 flex-1 rounded bg-slate-800" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 border-b border-slate-900 py-3.5">
          {Array.from({ length: columns }).map((_, c) => (
            <div key={c} className="h-3 flex-1 rounded bg-slate-800/50" />
          ))}
        </div>
      ))}
    </div>
  )
}
