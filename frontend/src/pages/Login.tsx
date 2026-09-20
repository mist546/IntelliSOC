import { FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { getApiErrorMessage } from '../services/client'
import { ErrorBanner } from '../components/ErrorBanner'
import { InlineSpinner } from '../components/LoadingSpinner'

export default function Login() {
  const { login, register, user, token, isLoading } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isLoading && token && user) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        await register(username, email, password)
      }
      navigate('/dashboard')
    } catch (err) {
      setError(getApiErrorMessage(err, mode === 'login' ? 'Login failed.' : 'Registration failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-red-600 text-white shadow-lg shadow-brand-900/40">
            <ShieldCheck className="h-6 w-6" strokeWidth={2.25} />
          </div>
          <h1 className="text-xl font-bold text-slate-100">IntelliSOC</h1>
          <p className="text-xs uppercase tracking-widest text-slate-500">Agentic AI Security Operations Center</p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-6 shadow-lg">
          <div className="mb-5 flex rounded-md border border-slate-800 bg-slate-950 p-1 text-sm">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={`flex-1 rounded py-1.5 font-medium transition-colors ${
                mode === 'login' ? 'bg-brand-500/20 text-brand-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={`flex-1 rounded py-1.5 font-medium transition-colors ${
                mode === 'register' ? 'bg-brand-500/20 text-brand-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Register
            </button>
          </div>

          {error && (
            <div className="mb-4">
              <ErrorBanner message={error} />
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">Username</label>
              <input
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-500"
                autoComplete="username"
              />
            </div>

            {mode === 'register' && (
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Email</label>
                <input
                  required
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-500"
                  autoComplete="email"
                />
              </div>
            )}

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">Password</label>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand-500"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 flex items-center justify-center gap-2 rounded-md bg-brand-600 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting && <InlineSpinner />}
              {mode === 'login' ? 'Log in' : 'Create account'}
            </button>
          </form>

          {mode === 'register' && (
            <p className="mt-4 text-center text-xs text-slate-500">
              The first registered account becomes ADMIN automatically.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
