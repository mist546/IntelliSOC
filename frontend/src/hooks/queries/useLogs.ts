import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getLogs, uploadLogFile } from '../../services/logs'
import { queryKeys } from './queryKeys'

export function useLogsQuery(filters: { source_ip?: string; event_type?: string }) {
  return useQuery({
    queryKey: queryKeys.logs(filters),
    queryFn: () => getLogs({ ...filters, limit: 200 }),
  })
}

export function useUploadLog() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => uploadLogFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logs'] })
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats })
    },
  })
}
