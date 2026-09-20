import { api } from './client'
import type { DashboardStatistics } from '../types'

// Conceptually "/api/dashboard/stats" - the backend exposes this under
// /api/dashboard/statistics, which is what we actually call here.
export async function getDashboardStats(): Promise<DashboardStatistics> {
  const { data } = await api.get<DashboardStatistics>('/api/dashboard/statistics')
  return data
}
