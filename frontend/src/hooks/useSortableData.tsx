import { useMemo, useState } from 'react'

export type SortDirection = 'asc' | 'desc'
export type SortAccessors<T> = Record<string, (item: T) => string | number>

export function useSortableData<T>(
  items: T[],
  accessors: SortAccessors<T>,
  initialKey: string | null = null,
  initialDir: SortDirection = 'asc',
) {
  const [sortKey, setSortKey] = useState<string | null>(initialKey)
  const [sortDir, setSortDir] = useState<SortDirection>(initialDir)

  const sorted = useMemo(() => {
    if (!sortKey || !accessors[sortKey]) return items
    const accessor = accessors[sortKey]
    const withValues = items.map((item) => ({ item, value: accessor(item) }))
    withValues.sort((a, b) => {
      if (a.value < b.value) return sortDir === 'asc' ? -1 : 1
      if (a.value > b.value) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return withValues.map((w) => w.item)
    // accessors is intentionally excluded: callers pass a fresh object each
    // render, and re-sorting on every render is cheap for list sizes here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, sortKey, sortDir])

  function requestSort(key: string) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return { sorted, sortKey, sortDir, requestSort }
}
