import { ArrowUpDown, ChevronDown, ChevronUp } from 'lucide-react'
import type { SortDirection } from '../hooks/useSortableData'

export function SortableTh({
  label,
  sortKey,
  activeKey,
  direction,
  onSort,
  className = '',
}: {
  label: string
  sortKey: string
  activeKey: string | null
  direction: SortDirection
  onSort: (key: string) => void
  className?: string
}) {
  const active = activeKey === sortKey
  return (
    <th
      onClick={() => onSort(sortKey)}
      aria-sort={active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'}
      className={`cursor-pointer select-none px-3 py-2 transition-colors hover:text-slate-300 ${className}`}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active ? (
          direction === 'asc' ? (
            <ChevronUp className="h-3 w-3 text-brand-400" />
          ) : (
            <ChevronDown className="h-3 w-3 text-brand-400" />
          )
        ) : (
          <ArrowUpDown className="h-3 w-3 text-slate-700" />
        )}
      </span>
    </th>
  )
}
