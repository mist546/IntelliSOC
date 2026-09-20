export function StatCard({
  label,
  value,
  accentClassName = 'text-slate-100',
  onClick,
}: {
  label: string
  value: string | number
  accentClassName?: string
  onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-lg border border-slate-800 bg-slate-900/60 p-4 shadow-sm transition-all ${
        onClick ? 'cursor-pointer hover:-translate-y-0.5 hover:border-slate-600 hover:shadow-md' : ''
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${accentClassName}`}>{value}</p>
    </div>
  )
}
