import type { ReactNode } from 'react'
import { CircleAlert, CircleCheck, CircleHelp, ShieldAlert } from 'lucide-react'
import type { Reputation } from '../types'

const REPUTATION_STYLES: Record<Reputation, string> = {
  malicious: 'border-red-500/40 bg-red-500/10 text-red-300',
  suspicious: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
  clean: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  unknown: 'border-slate-600/40 bg-slate-600/10 text-slate-300',
}

const REPUTATION_ICONS: Record<Reputation, ReactNode> = {
  malicious: <ShieldAlert className="h-3.5 w-3.5" />,
  suspicious: <CircleAlert className="h-3.5 w-3.5" />,
  clean: <CircleCheck className="h-3.5 w-3.5" />,
  unknown: <CircleHelp className="h-3.5 w-3.5" />,
}

export function reputationClassName(reputation: Reputation | string | null | undefined): string {
  return REPUTATION_STYLES[(reputation as Reputation) in REPUTATION_STYLES ? (reputation as Reputation) : 'unknown']
}

export function ReputationBadge({ reputation }: { reputation: Reputation | string | null | undefined }) {
  const key: Reputation = (reputation as Reputation) in REPUTATION_STYLES ? (reputation as Reputation) : 'unknown'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded bg-black/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${REPUTATION_STYLES[key]}`}
    >
      {REPUTATION_ICONS[key]}
      {reputation ?? 'unknown'}
    </span>
  )
}
