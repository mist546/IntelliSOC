import type { LucideIcon } from 'lucide-react'

export function StatCard({
  label,
  value,
  accentClassName = 'text-slate-100',
  icon: Icon,
  onClick,
}: {
  label: string
  value: string | number
  accentClassName?: string
  icon?: LucideIcon
  onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-lg border border-slate-800 bg-slate-900/60 p-4 shadow-sm transition-all ${
        onClick ? 'cursor-pointer hover:-translate-y-0.5 hover:border-slate-600 hover:shadow-md' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        {Icon && <Icon className={`h-4 w-4 ${accentClassName} opacity-70`} strokeWidth={2} />}
      </div>
      <p className={`mt-2 text-3xl font-bold ${accentClassName}`}>{value}</p>
    </div>
  )
}
