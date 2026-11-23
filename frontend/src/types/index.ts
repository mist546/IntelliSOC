// ==================== Auth ====================

export type UserRole = 'ADMIN' | 'ANALYST'

export interface User {
  id: string
  username: string
  email: string
  role: UserRole
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// ==================== Logs ====================

export interface LogEvent {
  id: string
  timestamp: string
  source: string
  source_type: string
  host: string | null
  source_ip: string | null
  destination_ip: string | null
  username: string | null
  event_type: string | null
  action: string | null
  status: string | null
  message: string | null
  raw_log: string | null
  metadata?: LogEventMetadata | null
}

/** Context the Wazuh parser keeps for events that came through a Wazuh manager. */
export interface WazuhContext {
  alert_id?: string
  rule_id?: string
  rule_level?: number
  rule_description?: string
  rule_groups?: string[]
  mitre_ids?: string[]
  agent_id?: string
  agent_name?: string
  agent_ip?: string
  location?: string
}

export interface LogEventMetadata {
  wazuh?: WazuhContext
  [key: string]: unknown
}

export interface LogUploadResult {
  filename: string
  source_type: string
  events_created: number
  alerts_created: number
  incidents_created: number
  parse_errors: string[]
}

// ==================== Alerts ====================

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type AlertStatus = 'NEW' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED' | 'FALSE_POSITIVE'

export interface Alert {
  id: string
  title: string
  severity: Severity
  confidence: number
  timestamp: string
  source_ip: string | null
  username: string | null
  host: string | null
  detection_rule: string | null
  description: string | null
  evidence: string[]
  status: AlertStatus
  incident_id: string | null
}

// ==================== Incidents ====================

export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'CONTAINED' | 'CLOSED'

export interface Incident {
  id: string
  title: string
  description: string | null
  severity: Severity
  status: IncidentStatus
  created_at: string
  updated_at: string
}

export interface IncidentDetail extends Incident {
  alerts: Alert[]
}

// ==================== Investigations ====================

export type InvestigationStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface TraceStep {
  step: number | string
  action: string
  detail: string
}

export type Reputation = 'malicious' | 'suspicious' | 'clean' | 'unknown'

export interface ThreatIntelResult {
  indicator: string
  indicator_type: string
  reputation: Reputation
  classification: string | null
  source: string
  confidence: number | null
  details: string | Record<string, unknown> | null
  timestamp: string | null
}

export interface RagSource {
  content: string
  source: string
  title: string
  category: string // top-level knowledge base folder, e.g. response_playbooks, nist
  score: number
  page?: number | null // PDF page number
  heading?: string | null // markdown section, e.g. "Brute Force Response > Containment"
  match?: 'semantic' | 'keyword' // keyword = exact identifier match (T1110, CWE-89, 4625)
  id?: string // K1, K2 ... - how the AI cites it (investigations only)
  purpose?: 'investigation_playbook' | 'response_playbook' | 'background'
}

/** A knowledge source the AI cited, verified against what it was given. */
export interface AiReference {
  id: string
  source: string
  title: string | null
  page: number | null
  heading: string | null
  category: string | null
}

export interface AiAnalysis {
  attack_type: string | null
  severity: Severity | 'UNKNOWN' | null
  confidence: number | null
  summary: string | null
  evidence: string[]
  threat_context: string | null
  impact: string | null
  mitre_technique: string | null
  owasp_category: string | null
  recommended_actions: string[]
  requires_human_approval: true
  insufficient_evidence: boolean
  references?: AiReference[]
}

export interface Investigation {
  id: string
  alert_id: string | null
  incident_id: string | null
  status: InvestigationStatus
  trace: TraceStep[]
  evidence: {
    alert?: Alert | Record<string, unknown>
    related_events?: LogEvent[] | Record<string, unknown>[]
    [key: string]: unknown
  } | null
  threat_intelligence: ThreatIntelResult[]
  rag_sources: RagSource[]
  risk_score: number | null
  risk_factors: string[]
  ai_analysis: AiAnalysis | null
  llm_available: boolean
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface InvestigationTraceResponse {
  id: string
  status: InvestigationStatus
  trace: TraceStep[]
}

// ==================== RAG ====================

export interface RagSearchResult {
  available: boolean
  message: string
  results: RagSource[]
}

// ==================== Website Scans ====================

export type ScanStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface ScanFinding {
  finding: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH'
  evidence: string | null
  affected_url: string | null
  owasp_category: string | null
  description: string | null
  recommendation: string | null
}

export interface WebsiteScan {
  id: string
  target_url: string
  status: ScanStatus
  findings: ScanFinding[]
  checks_run: string[]
  error_message: string | null
  started_at: string | null
  completed_at: string | null
}

// ==================== Reports ====================

export type ReportFormat = 'json' | 'pdf'

export interface ReportContent {
  incident_summary: unknown
  alerts: unknown
  timeline: unknown
  investigations: unknown
  containment_status: unknown
}

export interface Report {
  id: string
  incident_id: string
  format: ReportFormat
  file_path: string | null
  content: ReportContent | null
  created_at: string
}

// ==================== Agents ====================

export interface CollectorAgent {
  id: string
  name: string
  hostname: string
  is_active: boolean
  last_seen_at: string | null
  created_at: string
  connection_status: AgentConnectionStatus
}

/** Derived by the backend from the last heartbeat/event time. */
export type AgentConnectionStatus = 'ONLINE' | 'STALE' | 'OFFLINE' | 'NEVER_SEEN'

export interface AgentRegisterResponse {
  id: string
  name: string
  api_key: string
}

// ==================== Dashboard ====================

export interface AlertsOverTimePoint {
  date: string
  count: number
}

export interface TopSourceIp {
  source_ip: string
  count: number
}

export interface EventTypeCount {
  event_type: string
  count: number
}

export interface IncidentStatusCount {
  status: string
  count: number
}

export interface RecentInvestigation {
  id: string
  alert_id: string | null
  incident_id: string | null
  status: InvestigationStatus
  risk_score: number | null
  created_at: string
}

export interface InvestigationSummary extends RecentInvestigation {
  completed_at: string | null
}

export interface RecentScanSummary {
  id: string
  target_url: string
  status: ScanStatus
  started_at: string | null
}

export interface DashboardStatistics {
  alert_counts_by_severity: Record<Severity, number>
  open_incidents: number
  active_agents: number
  total_alerts: number
  total_log_events: number
  recent_investigations: RecentInvestigation[]
  alerts_over_time: AlertsOverTimePoint[]
  top_source_ips: TopSourceIp[]
  event_type_distribution: EventTypeCount[]
  incident_status_distribution: IncidentStatusCount[]
  recent_website_scans: RecentScanSummary[]
}

// ==================== Health ====================

export interface HealthCheck {
  status: string
  checks: {
    database: string | boolean
    ollama: string | boolean
  }
  app: string
}

// ==================== LLM Settings ====================

export type LlmProvider = 'ollama_local' | 'ollama_cloud'

export interface LlmSettings {
  provider: LlmProvider
  ollama_model: string
  ollama_base_url: string
  ollama_cloud_model: string
  ollama_cloud_base_url: string
  ollama_cloud_api_key_configured: boolean
  reachable: boolean
}

export interface LlmSettingsUpdate {
  provider?: LlmProvider
  ollama_model?: string
  ollama_base_url?: string
  ollama_cloud_model?: string
  ollama_cloud_base_url?: string
  ollama_cloud_api_key?: string
}
