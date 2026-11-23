// The backend stores and serializes timestamps as naive UTC (no "Z"/offset);
// JS would otherwise parse those as local time and shift every display.
const NAIVE_DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/

export function parseServerDate(value: string): Date {
  return new Date(NAIVE_DATETIME.test(value) ? `${value}Z` : value)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const d = parseServerDate(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = parseServerDate(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' })
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return '—'
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function detailsToText(details: string | Record<string, unknown> | null | undefined): string {
  if (!details) return ''
  if (typeof details === 'string') return details
  try {
    return JSON.stringify(details, null, 2)
  } catch {
    return String(details)
  }
}
