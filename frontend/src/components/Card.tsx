import type { ReactNode } from 'react'

export function Card({ title, actions, children, className = '' }: {
  title?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-lg border border-slate-800 bg-slate-900/60 p-4 shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between">
          {title && <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h3>}
          {actions}
        </div>
      )}
      {children}
    </div>
  )
}
