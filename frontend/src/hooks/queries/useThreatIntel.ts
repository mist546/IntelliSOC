import { useMutation } from '@tanstack/react-query'
import { lookupThreatIntel } from '../../services/threatIntelligence'

export function useThreatIntelLookup() {
  return useMutation({
    mutationFn: ({ indicator, type }: { indicator: string; type?: string }) => lookupThreatIntel(indicator, type),
  })
}
