import { useState } from 'react'
import type { MouseEvent } from 'react'
import { useToast } from '../hooks/useToast'

export function CopyButton({ value, label = 'Copy' }: { value: string; label?: string }) {
  const toast = useToast()
  const [copied, setCopied] = useState(false)

  async function handleCopy(e: MouseEvent) {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      toast.success('Copied to clipboard.')
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Could not access the clipboard.')
    }
  }

  return (
    <button
      onClick={handleCopy}
      title={`Copy "${value}"`}
      className="ml-1.5 inline-flex items-center rounded border border-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 transition-colors hover:border-slate-600 hover:bg-slate-800 hover:text-slate-200"
    >
      {copied ? '✓ Copied' : label}
    </button>
  )
}
