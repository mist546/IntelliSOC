import { api } from './client'
import type { LlmSettings, LlmSettingsUpdate } from '../types'

export async function getLlmSettings(): Promise<LlmSettings> {
  const { data } = await api.get<LlmSettings>('/api/settings/llm')
  return data
}

export async function updateLlmSettings(payload: LlmSettingsUpdate): Promise<LlmSettings> {
  const { data } = await api.patch<LlmSettings>('/api/settings/llm', payload)
  return data
}
