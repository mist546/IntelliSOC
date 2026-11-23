import { api, getApiBaseUrl } from './client'

/** One message pushed by the backend over GET /api/stream. */
export interface LiveEvent {
  type: string
  data: Record<string, unknown>
  timestamp?: string
}

/**
 * EventSource cannot send an Authorization header, so the stream is opened
 * with a short-lived single-use ticket obtained through a normal
 * authenticated request (the JWT never appears in a URL).
 */
export async function openLiveStream(): Promise<EventSource> {
  const { data } = await api.post<{ ticket: string }>('/api/stream/ticket')
  return new EventSource(`${getApiBaseUrl()}/api/stream?ticket=${encodeURIComponent(data.ticket)}`)
}
