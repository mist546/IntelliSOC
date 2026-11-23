import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { openLiveStream } from '../services/stream'
import type { LiveEvent } from '../services/stream'
import { useToast } from './useToast'

export type LiveStatus = 'connecting' | 'live' | 'offline'
type Listener = (event: LiveEvent) => void

interface LiveEventsContextValue {
  status: LiveStatus
  subscribe: (listener: Listener) => () => void
}

const LiveEventsContext = createContext<LiveEventsContextValue | null>(null)

const MAX_RETRY_MS = 30000

/** Which cached queries each backend event makes stale (refetched automatically). */
const INVALIDATES: Record<string, string[][]> = {
  'logs.ingested': [['logs'], ['dashboard'], ['agents']],
  'alert.created': [['alerts'], ['dashboard']],
  'alert.updated': [['alerts'], ['dashboard']],
  'incident.updated': [['incidents'], ['dashboard']],
  'investigation.started': [['investigations'], ['alerts'], ['dashboard']],
  'investigation.step': [['investigations']],
  'investigation.completed': [['investigations'], ['incidents'], ['reports'], ['dashboard']],
  'agent.heartbeat': [['agents']],
  'agent.deleted': [['agents']],
}

/**
 * Keeps one Server-Sent Events connection to the backend open while the
 * user is logged in. Every pushed event refreshes the affected React Query
 * data, so pages update within a second of something happening instead of
 * waiting for their next poll. High/critical alerts also raise a toast.
 * If the connection drops it reconnects with backoff (a fresh ticket each
 * time) and refreshes everything once it is back, to catch missed events.
 */
export function LiveEventsProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const toastRef = useRef(toast)
  toastRef.current = toast
  const listeners = useRef(new Set<Listener>())
  const [status, setStatus] = useState<LiveStatus>('connecting')

  useEffect(() => {
    let source: EventSource | null = null
    let retryTimer: number | undefined
    let retryDelay = 1000
    let stopped = false
    let hasConnectedBefore = false

    function handle(event: LiveEvent) {
      for (const queryKey of INVALIDATES[event.type] ?? []) {
        queryClient.invalidateQueries({ queryKey })
      }
      const data = event.data
      if (event.type === 'alert.created' && (data.severity === 'HIGH' || data.severity === 'CRITICAL')) {
        toastRef.current.error(`New ${data.severity} alert: ${data.title}`)
      }
      if (event.type === 'investigation.completed') {
        if (data.status === 'FAILED') toastRef.current.error('An AI investigation failed - open it for details.')
        else toastRef.current.success('AI investigation completed.')
      }
      listeners.current.forEach((listener) => listener(event))
    }

    function scheduleRetry() {
      if (stopped) return
      setStatus('offline')
      retryTimer = window.setTimeout(connect, retryDelay)
      retryDelay = Math.min(retryDelay * 2, MAX_RETRY_MS)
    }

    async function connect() {
      setStatus('connecting')
      try {
        source = await openLiveStream()
      } catch {
        scheduleRetry()
        return
      }
      if (stopped) {
        source.close()
        return
      }
      source.onopen = () => {
        setStatus('live')
        retryDelay = 1000
        if (hasConnectedBefore) queryClient.invalidateQueries()
        hasConnectedBefore = true
      }
      source.onmessage = (message) => {
        try {
          handle(JSON.parse(message.data) as LiveEvent)
        } catch {
          // ignore malformed messages
        }
      }
      source.onerror = () => {
        // Tickets are single-use, so the browser's own automatic reconnect
        // would be rejected - close and reconnect with a new ticket instead.
        source?.close()
        source = null
        scheduleRetry()
      }
    }

    connect()
    return () => {
      stopped = true
      window.clearTimeout(retryTimer)
      source?.close()
    }
  }, [queryClient])

  const subscribe = useCallback((listener: Listener) => {
    listeners.current.add(listener)
    return () => {
      listeners.current.delete(listener)
    }
  }, [])

  return <LiveEventsContext.Provider value={{ status, subscribe }}>{children}</LiveEventsContext.Provider>
}

export function useLiveStatus(): LiveStatus {
  const ctx = useContext(LiveEventsContext)
  if (!ctx) throw new Error('useLiveStatus must be used within a LiveEventsProvider')
  return ctx.status
}

/** Calls `listener` for every live event whose type is in `types`. */
export function useLiveEvent(types: string[], listener: Listener) {
  const ctx = useContext(LiveEventsContext)
  if (!ctx) throw new Error('useLiveEvent must be used within a LiveEventsProvider')
  const { subscribe } = ctx
  const saved = useRef(listener)
  saved.current = listener
  const typesKey = types.join(',')

  useEffect(() => {
    const wanted = new Set(typesKey.split(','))
    return subscribe((event) => {
      if (wanted.has(event.type)) saved.current(event)
    })
  }, [subscribe, typesKey])
}
