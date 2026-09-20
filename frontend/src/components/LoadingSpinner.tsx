export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-sky-500" />
      {label && <p className="text-sm">{label}</p>}
    </div>
  )
}

export function InlineSpinner() {
  return <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-sky-500" />
}
