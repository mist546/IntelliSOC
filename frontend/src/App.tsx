import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Alerts from './pages/Alerts'
import AlertDetail from './pages/AlertDetail'
import Incidents from './pages/Incidents'
import IncidentDetail from './pages/IncidentDetail'
import Investigations from './pages/Investigations'
import InvestigationDetail from './pages/InvestigationDetail'
import Logs from './pages/Logs'
import Agents from './pages/Agents'
import ThreatIntel from './pages/ThreatIntel'
import KnowledgeBase from './pages/KnowledgeBase'
import AIAnalysis from './pages/AIAnalysis'
import WebsiteScans from './pages/WebsiteScans'
import WebsiteScanDetail from './pages/WebsiteScanDetail'
import Reports from './pages/Reports'
import SystemHealth from './pages/SystemHealth'
import Settings from './pages/Settings'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />

        <Route path="/alerts" element={<Alerts />} />
        <Route path="/alerts/:id" element={<AlertDetail />} />

        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:id" element={<IncidentDetail />} />

        <Route path="/investigations" element={<Investigations />} />
        <Route path="/investigations/:id" element={<InvestigationDetail />} />

        <Route path="/logs" element={<Logs />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/threat-intel" element={<ThreatIntel />} />
        <Route path="/knowledge-base" element={<KnowledgeBase />} />
        <Route path="/ai-analysis" element={<AIAnalysis />} />

        <Route path="/website-scans" element={<WebsiteScans />} />
        <Route path="/website-scans/:id" element={<WebsiteScanDetail />} />

        <Route path="/reports" element={<Reports />} />
        <Route path="/system-health" element={<SystemHealth />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
