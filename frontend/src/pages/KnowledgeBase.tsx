import { ChangeEvent, FormEvent, useRef, useState } from 'react'
import { BookMarked, FolderOpen, Search, Trash2, UploadCloud } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { InlineSpinner } from '../components/LoadingSpinner'
import { ErrorBanner, EmptyState } from '../components/ErrorBanner'
import { getApiErrorMessage } from '../services/client'
import { useToast } from '../hooks/useToast'
import { useConfirm } from '../hooks/useConfirm'
import type { KnowledgeDocument } from '../services/knowledge'
import {
  useDeleteKnowledgeDocument,
  useKnowledgeDocuments,
  useKnowledgeSearch,
  useUploadKnowledgeDocument,
} from '../hooks/queries/useKnowledgeBase'

export default function KnowledgeBase() {
  const [query, setQuery] = useState('')
  const search = useKnowledgeSearch()
  const documents = useKnowledgeDocuments()
  const upload = useUploadKnowledgeDocument()
  const remove = useDeleteKnowledgeDocument()
  const toast = useToast()
  const confirm = useConfirm()
  const fileInputRef = useRef<HTMLInputElement>(null)

  function onFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    upload.mutate(file, {
      onSuccess: (result) => {
        if (result.indexed) toast.success(`${result.title}: ${result.message}`)
        else toast.error(result.message)
      },
      onError: (err) => toast.error(getApiErrorMessage(err, 'Failed to upload document.')),
    })
  }

  async function handleDelete(doc: KnowledgeDocument) {
    const ok = await confirm({
      title: `Delete "${doc.title}"?`,
      message: 'The file is removed from custom/ and its chunks from the search index. Investigations will no longer cite it.',
      confirmLabel: 'Delete document',
      tone: 'danger',
    })
    if (!ok) return
    remove.mutate(doc.id, {
      onSuccess: () => toast.success(`Deleted ${doc.title}`),
      onError: (err) => toast.error(getApiErrorMessage(err, 'Failed to delete document.')),
    })
  }

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
              <EmptyState message={response.message || 'The knowledge base is currently unavailable.'} />
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
                        {src.match === 'keyword' && <span className="ml-1 text-brand-400">&middot; exact ID match</span>}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      source: {src.source}
                      {src.page ? `, page ${src.page}` : ''}
                    </p>
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
        actions={
          <div className="flex items-center gap-3">
            <input ref={fileInputRef} type="file" accept=".md,.txt,.pdf" className="hidden" onChange={onFileInputChange} />
            <button
              type="button"
              disabled={upload.isPending}
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {upload.isPending ? <InlineSpinner /> : <UploadCloud className="h-3.5 w-3.5" />}
              {upload.isPending ? 'Indexing...' : 'Add document (.md / .txt / .pdf)'}
            </button>
            <BookMarked className="h-4 w-4 text-slate-600" />
          </div>
        }
      >
        <p className="mb-3 text-xs text-slate-500">
          Uploaded documents are saved to{' '}
          <code className="font-mono-ids text-slate-400">data/knowledge_base/custom/</code> and embedded immediately.
          PDFs are indexed page by page, so answers cite the page number (scanned PDFs need OCR first). Markdown files can
          start with a <code className="font-mono-ids text-slate-400">title / source</code> frontmatter block; the category
          is the folder. Public sources (MITRE ATT&amp;CK, NIST PDFs, OWASP, CWE, CVEs) are fetched with{' '}
          <code className="font-mono-ids text-slate-400">scripts/download_knowledge_base.ps1</code>.
        </p>
        {documents.isError && (
          <ErrorBanner message={getApiErrorMessage(documents.error, 'Failed to load knowledge base documents.')} />
        )}
        {documents.isSuccess && documents.data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Chunks</th>
                  <th className="px-3 py-2">File</th>
                  <th className="px-3 py-2">Origin</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {documents.data.map((doc) => (
                  <tr key={doc.id} className="border-b border-slate-900">
                    <td className="px-3 py-2 text-slate-200">{doc.title}</td>
                    <td className="px-3 py-2 text-slate-400">{doc.category}</td>
                    <td className="px-3 py-2 text-slate-400">
                      {doc.indexed ? doc.chunk_count : <span className="text-amber-400">not indexed</span>}
                    </td>
                    <td className="px-3 py-2 font-mono-ids text-slate-500">
                      {doc.id}
                      {doc.file_type === 'pdf' && (
                        <span className="ml-2 rounded border border-slate-700 px-1 text-[10px] uppercase text-slate-400">pdf</span>
                      )}
                    </td>
                    <td className="max-w-[260px] truncate px-3 py-2 font-mono-ids text-slate-600" title={doc.source}>
                      {doc.source}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {doc.deletable && (
                        <button
                          type="button"
                          onClick={() => handleDelete(doc)}
                          disabled={remove.isPending}
                          title="Delete this uploaded document"
                          className="rounded p-1 text-slate-500 hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          documents.isSuccess && (
            <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-700 px-4 py-10 text-center">
              <FolderOpen className="h-6 w-6 text-slate-600" />
              <p className="text-sm text-slate-400">No documents in the knowledge base yet.</p>
              <p className="max-w-md text-xs text-slate-600">
                Add a document above, or run{' '}
                <code className="font-mono-ids text-slate-500">scripts/ingest_knowledge_base.ps1</code> to index{' '}
                <code className="font-mono-ids text-slate-500">data/knowledge_base/</code>.
              </p>
            </div>
          )
        )}
      </Card>
    </div>
  )
}
