import { useQuery } from '@tanstack/react-query'
import { getInvestigation, getInvestigations } from '../../services/investigations'
import { queryKeys } from './queryKeys'

// Live steps normally arrive over the event stream (useLiveEvents); this
// slower poll is only a fallback in case the stream is disconnected.
const RUNNING_POLL_MS = 5000

const LIST_POLL_MS = 20000

export function useInvestigationsQuery(live: boolean) {
  return useQuery({
    queryKey: queryKeys.investigations,
    queryFn: () => getInvestigations({ limit: 200 }),
    refetchInterval: live ? LIST_POLL_MS : false,
  })
}

export function useInvestigationQuery(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.investigation(id ?? ''),
    queryFn: () => getInvestigation(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'RUNNING' || status === 'PENDING' ? RUNNING_POLL_MS : false
    },
  })
}
