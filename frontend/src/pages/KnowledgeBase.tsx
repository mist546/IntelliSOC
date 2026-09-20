import { FormEvent, useState } from 'react'
import { BookMarked, FolderOpen, Search } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { getApiErrorMessage } from '../services/client'
import { useKnowledgeDocuments, useKnowledgeSearch } from '../hooks/queries/useKnowledgeBase'

export default function KnowledgeBase() {
  const [query, setQuery] = useState('')
  const search = useKnowledgeSearch()
  const documents = useKnowledgeDocuments()

  function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    search.mutate({ query: query.trim(), top_k: 6 })
  }

  const response = search.data

  return (
    <div>
      <PageHeader title="Knowledge Base" description="Semantic search over ingested cybersecurity documentation (RAG)" />

      <div className="mb-6">
        <Card title="Semantic Search">
          <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[240px]">
              <label className="mb-1 block text-xs font-medium text-slate-400">Query</label>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. SSH brute force response playbook, OWASP injection mitigation"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600"
              />
            </div>
            <button
              type="submit"
              disabled={search.isPending}
              className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {search.isPending ? <InlineSpinner /> : <Search className="h-4 w-4" />}
              Search
            </button>
          </form>

          <div className="mt-4">
            {search.isError && (
              <ErrorBanner message={getApiErrorMessage(search.error, 'Failed to search the knowledge base.')} />
            )}
            {response && !response.available && (
              <EmptyState message={response.message ?? 'The knowledge base is currently unavailable.'} />
            )}
            {response?.available && response.results.length === 0 && (
              <EmptyState message="No matching knowledge base entries found." />
            )}
            {response?.available && response.results.length > 0 && (
              <div className="space-y-3">
                {response.results.map((src, i) => (
                  <div key={i} className="rounded-md border border-slate-800 bg-slate-950/60 p-3">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span className="font-semibold text-slate-300">{src.title}</span>
                      <span>
                        {src.category} &middot; score {src.score.toFixed(2)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">source: {src.source}</p>
                    <p className="mt-2 text-sm text-slate-300">{src.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>

      <Card
        title="Manage Documents"
        actions={<BookMarked className="h-4 w-4 text-slate-600" />}
      >
        {documents.isSuccess && documents.data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Chunks</th>
                  <th className="px-3 py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {documents.data.map((doc) => (
                  <tr key={doc.id} className="border-b border-slate-900">
                    <td className="px-3 py-2 text-slate-200">{doc.title}</td>
                    <td className="px-3 py-2 text-slate-400">{doc.category}</td>
                    <td className="px-3 py-2 text-slate-400">{doc.chunk_count}</td>
                    <td className="px-3 py-2 font-mono-ids text-slate-500">{doc.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-700 px-4 py-10 text-center">
            <FolderOpen className="h-6 w-6 text-slate-600" />
            <p className="text-sm text-slate-400">Document upload/management isn't exposed via the API yet.</p>
            <p className="max-w-md text-xs text-slate-600">
              The knowledge base is currently populated server-side from{' '}
              <code className="font-mono-ids text-slate-500">data/knowledge_base/</code> by running{' '}
              <code className="font-mono-ids text-slate-500">scripts/ingest_knowledge_base.py</code>. Once ingested,
              its contents are searchable above via RAG.
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}
