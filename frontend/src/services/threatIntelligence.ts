import { api } from './client'
import type { ThreatIntelResult } from '../types'

// Conceptually "/api/threat-intelligence" - the backend exposes this under
// /api/threat-intel/{indicator}, which is what we actually call here.
export async function lookupThreatIntel(indicator: string, type?: string): Promise<ThreatIntelResult[]> {
  const { data } = await api.get<ThreatIntelResult[]>(`/api/threat-intel/${encodeURIComponent(indicator)}`, {
    params: type ? { type } : undefined,
  })
  return data
}
