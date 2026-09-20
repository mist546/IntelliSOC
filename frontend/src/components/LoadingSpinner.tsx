import { Loader2 } from 'lucide-react'

export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-400">
      <Loader2 className="h-8 w-8 animate-spin text-brand-500" strokeWidth={2} />
      {label && <p className="text-sm">{label}</p>}
    </div>
  )
}

export function InlineSpinner() {
  return <Loader2 className="h-4 w-4 animate-spin text-brand-500" strokeWidth={2} />
}
