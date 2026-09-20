import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

export type EvidenceSourceTone = 'observed' | 'intel' | 'rag' | 'ai'

const TONE_STYLES: Record<EvidenceSourceTone, { tag: string; label: string; border: string }> = {
  observed: {
    tag: 'border-brand-500/40 bg-brand-500/10 text-brand-300',
    label: 'Observed Evidence · From Logs',
    border: 'border-brand-500/20',
  },
  intel: {
    tag: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
    label: 'Threat Intelligence · External / Local Feeds',
    border: 'border-purple-500/20',
  },
  rag: {
    tag: 'border-teal-500/40 bg-teal-500/10 text-teal-300',
    label: 'RAG Knowledge · Retrieved Documentation',
    border: 'border-teal-500/20',
  },
  ai: {
    tag: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
    label: 'AI Analysis · LLM-Generated Interpretation',
    border: 'border-amber-500/20',
  },
}

// Renders one of the four evidence categories the SOC UX rule requires to be
// visually distinct: what came straight from logs, what came from external
// intel, what came from the knowledge base, and what the LLM concluded from
// all of the above. The colored tag is the load-bearing part - an analyst
// should never have to guess which bucket a fact came from.
export function EvidenceSection({
  tone,
  title,
  icon: Icon,
  actions,
  children,
}: {
  tone: EvidenceSourceTone
  title: string
  icon?: LucideIcon
  actions?: ReactNode
  children: ReactNode
}) {
  const style = TONE_STYLES[tone]
  return (
    <div className={`rounded-lg border bg-slate-900/60 p-4 shadow-sm ${style.border}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4 text-slate-400" />}
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          {actions}
          <span className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${style.tag}`}>
            {style.label}
          </span>
        </div>
      </div>
      {children}
    </div>
  )
}
