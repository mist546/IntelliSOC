import axios, { AxiosError } from 'axios'
import type {
  Alert,
  AlertStatus,
  AgentRegisterResponse,
  CollectorAgent,
  DashboardStatistics,
  HealthCheck,
  Incident,
  IncidentDetail,
  Investigation,
  InvestigationTraceResponse,
  LoginResponse,
  LogEvent,
  LogUploadResult,
  RagSearchResult,
  Report,
  ReportFormat,
  ThreatIntelResult,
  User,
  WebsiteScan,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const TOKEN_KEY = 'mini_soc_token'
export const USER_KEY = 'mini_soc_user'

export const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export function getApiErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: unknown; message?: string } | undefined
    if (data?.detail) {
      if (typeof data.detail === 'string') return data.detail
      try {
        return JSON.stringify(data.detail)
      } catch {
        return fallback
      }
    }
    if (data?.message) return data.message
    if (err.code === 'ECONNABORTED') return 'Request timed out.'
    if (!err.response) return 'Cannot reach the backend server. Is it running?'
    return `${err.response.status} ${err.response.statusText}`
  }
  if (err instanceof Error) return err.message
  return fallback
}

// ==================== Auth ====================

export async function registerUser(payload: { username: string; email: string; password: string }): Promise<User> {
  const { data } = await api.post<User>('/api/auth/register', payload)
  return data
}

export async function loginUser(username: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)
  const { data } = await api.post<LoginResponse>('/api/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get<User>('/api/auth/me')
  return data
}

// ==================== Logs ====================

export async function uploadLogFile(file: File): Promise<LogUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<LogUploadResult>('/api/logs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

export async function getLogs(params: {
  skip?: number
  limit?: number
  source_ip?: string
  event_type?: string
}): Promise<LogEvent[]> {
  const { data } = await api.get<LogEvent[]>('/api/logs', { params })
  return data
}

export async function getLog(id: number | string): Promise<LogEvent> {
  const { data } = await api.get<LogEvent>(`/api/logs/${id}`)
  return data
}

// ==================== Alerts ====================

export async function getAlerts(params: {
  severity?: string
  status?: string
  source_ip?: string
  skip?: number
  limit?: number
}): Promise<Alert[]> {
  const { data } = await api.get<Alert[]>('/api/alerts', { params })
  return data
}

export async function getAlert(id: number | string): Promise<Alert> {
  const { data } = await api.get<Alert>(`/api/alerts/${id}`)
  return data
}

export async function updateAlertStatus(id: number | string, status: AlertStatus): Promise<Alert> {
  const { data } = await api.patch<Alert>(`/api/alerts/${id}/status`, { status })
  return data
}

export async function investigateAlert(id: number | string): Promise<Investigation> {
  // Must exceed the backend's own worst-case budget: OLLAMA_TIMEOUT (default
  // 240s) plus RAG/threat-intel overhead. A shorter client timeout would
  // abort the UI request while the backend investigation keeps running and
  // completes successfully, showing the user a false failure.
  const { data } = await api.post<Investigation>(
    `/api/alerts/${id}/investigate`,
    {},
    { timeout: 300000 },
  )
  return data
}

// ==================== Incidents ====================

export async function getIncidents(params: { status?: string; skip?: number; limit?: number }): Promise<Incident[]> {
  const { data } = await api.get<Incident[]>('/api/incidents', { params })
  return data
}

export async function getIncident(id: number | string): Promise<IncidentDetail> {
  const { data } = await api.get<IncidentDetail>(`/api/incidents/${id}`)
  return data
}

// ==================== Investigations ====================

export async function getInvestigation(id: number | string): Promise<Investigation> {
  const { data } = await api.get<Investigation>(`/api/investigations/${id}`)
  return data
}

export async function getInvestigationTrace(id: number | string): Promise<InvestigationTraceResponse> {
  const { data } = await api.get<InvestigationTraceResponse>(`/api/investigations/${id}/trace`)
  return data
}

// ==================== RAG ====================

export async function searchRag(query: string, top_k = 4): Promise<RagSearchResult> {
  const { data } = await api.post<RagSearchResult>('/api/rag/search', { query, top_k })
  return data
}

// ==================== Threat Intel ====================

export async function lookupThreatIntel(indicator: string, type?: string): Promise<ThreatIntelResult[]> {
  const { data } = await api.get<ThreatIntelResult[]>(`/api/threat-intel/${encodeURIComponent(indicator)}`, {
    params: type ? { type } : undefined,
  })
  return data
}

// ==================== Website Scans ====================

export async function createScan(target_url: string): Promise<WebsiteScan> {
  const { data } = await api.post<WebsiteScan>('/api/scans', { target_url }, { timeout: 120000 })
  return data
}

export async function getScans(params: { skip?: number; limit?: number }): Promise<WebsiteScan[]> {
  const { data } = await api.get<WebsiteScan[]>('/api/scans', { params })
  return data
}

export async function getScan(id: number | string): Promise<WebsiteScan> {
  const { data } = await api.get<WebsiteScan>(`/api/scans/${id}`)
  return data
}

// ==================== Reports ====================

export async function generateReport(incidentId: number | string, format: ReportFormat): Promise<Report> {
  const { data } = await api.post<Report>(`/api/reports/${incidentId}`, { format })
  return data
}

export function getReportDownloadUrl(reportId: number | string): string {
  return `${API_BASE_URL}/api/reports/${reportId}/download`
}

// ==================== Agents ====================

export async function getAgents(): Promise<CollectorAgent[]> {
  const { data } = await api.get<CollectorAgent[]>('/api/agents')
  return data
}

export async function registerAgent(payload: { name: string; hostname: string }): Promise<AgentRegisterResponse> {
  const { data } = await api.post<AgentRegisterResponse>('/api/agents/register', payload)
  return data
}

// ==================== Dashboard ====================

export async function getDashboardStatistics(): Promise<DashboardStatistics> {
  const { data } = await api.get<DashboardStatistics>('/api/dashboard/statistics')
  return data
}

// ==================== Health ====================

export async function getHealth(): Promise<HealthCheck> {
  const { data } = await api.get<HealthCheck>('/api/health')
  return data
}
