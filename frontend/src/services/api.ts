// Backward-compatible barrel: existing pages import everything from
// '../services/api'. New code should import from the domain-specific
// modules directly (services/alerts, services/dashboard, etc).
export * from './client'
export * from './auth'
export * from './dashboard'
export * from './alerts'
export * from './investigations'
export * from './logs'
export * from './incidents'
export * from './agents'
export * from './scans'
export * from './reports'
export * from './threatIntelligence'
export * from './rag'
export { getSystemHealth as getHealth } from './systemHealth'
