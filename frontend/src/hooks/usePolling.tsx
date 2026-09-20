import { useEffect, useRef } from 'react'

/**
 * Calls `callback` immediately and then every `intervalMs` while `enabled`
 * is true, pausing automatically when the browser tab is hidden so an idle
 * background tab doesn't keep hammering the API.
 */
export function usePolling(callback: () => void, intervalMs: number, enabled: boolean) {
  const savedCallback = useRef(callback)
  savedCallback.current = callback

  useEffect(() => {
    if (!enabled) return

    function tick() {
      if (document.visibilityState === 'visible') savedCallback.current()
    }

    const id = window.setInterval(tick, intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs, enabled])
}
