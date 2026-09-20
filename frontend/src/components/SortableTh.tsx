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
        <span className={`text-[9px] ${active ? 'text-sky-400' : 'text-slate-700'}`}>
          {active ? (direction === 'asc' ? '▲' : '▼') : '⇅'}
        </span>
      </span>
    </th>
  )
}
