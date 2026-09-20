import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-950 text-center">
      <p className="text-6xl font-bold text-slate-700">404</p>
      <p className="text-slate-400">Page not found.</p>
      <Link to="/dashboard" className="mt-2 rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500">
        Back to Dashboard
      </Link>
    </div>
  )
}
