import { Link } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'

export default function Reports() {
  return (
    <div>
      <PageHeader title="Reports" description="Incident reports for stakeholders and record-keeping" />
      <Card>
        <p className="text-sm text-slate-300">
          Reports are generated per-incident. Open an incident and use the "Generate Report" action to produce a
          JSON or PDF report summarizing its alerts, timeline, investigations, and containment status.
        </p>
        <Link
          to="/incidents"
          className="mt-4 inline-block rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500"
        >
          Go to Incidents
        </Link>
      </Card>
    </div>
  )
}
