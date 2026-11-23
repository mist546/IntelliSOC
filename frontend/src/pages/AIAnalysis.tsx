import { ChevronRight } from 'lucide-react'
import {
  BookOpen,
  BrainCircuit,
  Cpu,
  FileText,
  ListChecks,
  Radar,
  ShieldAlert,
  Sparkles,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorBanner } from '../components/ErrorBanner'
import { getApiErrorMessage } from '../services/client'
import { useAiStatusQuery } from '../hooks/queries/useAiStatus'

const PIPELINE = [
  { label: 'Alert', icon: ShieldAlert },
  { label: 'Evidence', icon: FileText },
  { label: 'Threat Intel', icon: Radar },
  { label: 'RAG', icon: BookOpen },
  { label: 'LLM', icon: BrainCircuit },
  { label: 'Analysis', icon: Sparkles },
  { label: 'Recommendation', icon: ListChecks },
]

export default function AIAnalysis() {
  const { data: aiStatus, isLoading, isError, error, refetch } = useAiStatusQuery()

  const ollamaOk = aiStatus?.reachable === true

  return (
    <div>
      <PageHeader title="AI Analysis" description="LLM status and the agentic investigation pipeline" />

      {isLoading ? (
        <LoadingSpinner label="Checking AI backend..." />
      ) : isError ? (
        <ErrorBanner message={getApiErrorMessage(error, 'Failed to check AI backend status.')} onRetry={() => refetch()} />
      ) : (
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card title="Ollama Status">
            <div className="flex items-center gap-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                  ollamaOk ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                }`}
              >
                {ollamaOk ? <Wifi className="h-5 w-5" /> : <WifiOff className="h-5 w-5" />}
              </div>
              <div>
                <p className={`text-sm font-semibold ${ollamaOk ? 'text-emerald-300' : 'text-red-300'}`}>
                  {ollamaOk ? 'Reachable' : 'Unreachable'}
                </p>
                <p className="text-xs text-slate-500 font-mono-ids">
                  {aiStatus?.provider === 'ollama_cloud' ? 'Cloud' : 'Local'} &middot; {aiStatus?.model}
                </p>
              </div>
            </div>
            {!ollamaOk && (
              <p className="mt-3 text-xs text-slate-500">
                Investigations will fall back to raw evidence and trace only until the configured Ollama service is
                reachable again.
              </p>
            )}
          </Card>

          <Card title="Model Information">
            <div className="flex items-start gap-3">
              <Cpu className="mt-0.5 h-5 w-5 shrink-0 text-slate-600" />
              <dl className="grid flex-1 grid-cols-2 gap-y-2 text-sm">
                <dt className="text-slate-500">Provider</dt>
                <dd className="text-slate-200">{aiStatus?.provider === 'ollama_cloud' ? 'Cloud (Ollama)' : 'Local (Ollama)'}</dd>
                <dt className="text-slate-500">Model</dt>
                <dd className="font-mono-ids text-slate-200">{aiStatus?.model}</dd>
                <dt className="text-slate-500">Embedding Model</dt>
                <dd className="font-mono-ids text-slate-200">{aiStatus?.embedding_model}</dd>
              </dl>
            </div>
          </Card>
        </div>
      )}

      <Card title="Agent Pipeline">
        <p className="mb-4 text-sm text-slate-400">
          Every AI investigation runs the same fixed pipeline. Only the final two stages are LLM-generated - evidence
          and threat intel are extracted directly from data, and RAG results are retrieved documentation, never
          model output.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {PIPELINE.map((step, i) => (
            <div key={step.label} className="flex items-center gap-2">
              <div className="flex flex-col items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2.5">
                <step.icon className="h-4 w-4 text-brand-400" />
                <span className="text-[11px] font-medium text-slate-300">{step.label}</span>
              </div>
              {i < PIPELINE.length - 1 && <ChevronRight className="h-4 w-4 shrink-0 text-slate-700" />}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
