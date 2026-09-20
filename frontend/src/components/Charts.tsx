import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
} from 'recharts'
import type { AlertsOverTimePoint, EventTypeCount, IncidentStatusCount, Severity, TopSourceIp } from '../types'
import { SEVERITY_COLOR } from './SeverityBadge'
import { EmptyState } from './ErrorBanner'

const AXIS_COLOR = '#64748b'
const GRID_COLOR = '#1e293b'
const TOOLTIP_STYLE = {
  backgroundColor: '#0f172a',
  border: '1px solid #334155',
  borderRadius: 8,
  fontSize: 12,
  color: '#e2e8f0',
}

const PALETTE = ['#38bdf8', '#a78bfa', '#34d399', '#fb923c', '#f472b6', '#facc15', '#60a5fa', '#f87171']

export function AlertsOverTimeChart({ data }: { data: AlertsOverTimePoint[] }) {
  if (!data || data.length === 0) return <EmptyState message="No alert trend data yet." />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="alertsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" stroke={AXIS_COLOR} fontSize={11} tickLine={false} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} allowDecimals={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Area type="monotone" dataKey="count" stroke="#38bdf8" strokeWidth={2} fill="url(#alertsGradient)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function SeverityDonutChart({
  data,
  onSliceClick,
}: {
  data: Record<Severity, number>
  onSliceClick?: (severity: Severity) => void
}) {
  const chartData = (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as Severity[])
    .map((sev) => ({ name: sev, value: data?.[sev] ?? 0 }))
    .filter((d) => d.value > 0)

  if (chartData.length === 0) return <EmptyState message="No alerts recorded yet." />

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          innerRadius={60}
          outerRadius={95}
          paddingAngle={2}
          onClick={onSliceClick ? (entry) => onSliceClick(entry.name as Severity) : undefined}
          cursor={onSliceClick ? 'pointer' : undefined}
        >
          {chartData.map((entry) => (
            <Cell key={entry.name} fill={SEVERITY_COLOR[entry.name as Severity]} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function TopSourceIpsChart({
  data,
  onBarClick,
}: {
  data: TopSourceIp[]
  onBarClick?: (sourceIp: string) => void
}) {
  if (!data || data.length === 0) return <EmptyState message="No source IP activity yet." />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" stroke={AXIS_COLOR} fontSize={11} allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="source_ip"
          stroke={AXIS_COLOR}
          fontSize={11}
          width={100}
          tick={{ fontFamily: 'monospace' }}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar
          dataKey="count"
          fill="#a78bfa"
          radius={[0, 4, 4, 0]}
          onClick={onBarClick ? (entry) => onBarClick(entry.source_ip) : undefined}
          cursor={onBarClick ? 'pointer' : undefined}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function EventTypeDistributionChart({
  data,
  onBarClick,
}: {
  data: EventTypeCount[]
  onBarClick?: (eventType: string) => void
}) {
  if (!data || data.length === 0) return <EmptyState message="No log events yet." />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="event_type" stroke={AXIS_COLOR} fontSize={11} interval={0} angle={-20} textAnchor="end" height={50} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} allowDecimals={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar
          dataKey="count"
          radius={[4, 4, 0, 0]}
          onClick={onBarClick ? (entry) => onBarClick(entry.event_type) : undefined}
          cursor={onBarClick ? 'pointer' : undefined}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function IncidentStatusPieChart({
  data,
  onSliceClick,
}: {
  data: IncidentStatusCount[]
  onSliceClick?: (status: string) => void
}) {
  if (!data || data.length === 0) return <EmptyState message="No incidents yet." />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="status"
          innerRadius={0}
          outerRadius={95}
          paddingAngle={2}
          onClick={onSliceClick ? (entry) => onSliceClick(entry.status) : undefined}
          cursor={onSliceClick ? 'pointer' : undefined}
        >
          {data.map((entry, i) => (
            <Cell key={entry.status} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
