'use client'
import { useEffect, useState } from 'react'
import clsx from 'clsx'

interface BatchSummary {
    batch_id: string
    created_at: string
    total_files: number
    done_files: number
    flagged: number
    failed: number
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function HistoryPanel() {
    const [batches, setBatches] = useState<BatchSummary[]>([])
    const [loading, setLoading] = useState(true)
    const [deletingId, setDeletingId] = useState<string | null>(null)

    const fetchHistory = async () => {
    try {
        const res = await fetch(`${API}/api/history`)
        const data = await res.json()
        setBatches(data.batches || [])
    } catch {
        setBatches([])
    } finally {
        setLoading(false)
    }
    }

useEffect(() => { fetchHistory() }, [])

    const handleDownload = (batch_id: string) => {
    window.open(`${API}/api/history/${batch_id}/export`, '_blank')
    }

    const handleDelete = async (batch_id: string) => {
    setDeletingId(batch_id)
    await fetch(`${API}/api/history/${batch_id}`, { method: 'DELETE' })
    setBatches(prev => prev.filter(b => b.batch_id !== batch_id))
    setDeletingId(null)
    }

    if (loading) {
    return (
        <div className="bg-white border border-gray-100 rounded-xl p-8 text-center text-xs text-gray-400">
        Loading history…
        </div>
    )
    }

    return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span className="text-sm font-medium text-gray-800">Batch history</span>
        <span className="text-xs text-gray-400">{batches.length} batches</span>
        </div>

        {batches.length === 0 ? (
        <div className="px-4 py-10 text-center text-xs text-gray-400">
            No history yet — completed batches will appear here
        </div>
        ) : (
        <div className="divide-y divide-gray-50">
            {batches.map((b) => (
            <div key={b.batch_id} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50/50 transition-colors">

              {/* Date + batch id */}
                <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-800">{b.created_at}</p>
                <p className="text-[10px] text-gray-400 mono mt-0.5">{b.batch_id.slice(0, 16)}…</p>
                </div>

              {/* Stats */}
                <div className="flex items-center gap-3 text-[10px]">
                <span className="text-gray-500">{b.total_files} files</span>
                <span className="text-[--teal-dark]">{b.done_files} done</span>
                {b.flagged > 0 && (
                    <span className="text-[--amber]">{b.flagged} flagged</span>
                )}
                {b.failed > 0 && (
                    <span className="text-[--red]">{b.failed} failed</span>
                )}
                </div>

              {/* Actions */}
                <div className="flex items-center gap-2">
                <button
                    onClick={() => handleDownload(b.batch_id)}
                    className="flex items-center gap-1 text-[11px] px-2.5 py-1.5 rounded-lg bg-[--teal] text-white hover:bg-[--teal-dark] transition-colors"
                >
                    <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                    <path d="M6 1v7M3 5l3 3 3-3M1 9v1.5A.5.5 0 001.5 11h9a.5.5 0 00.5-.5V9"
                        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Excel
                </button>
                <button
                    onClick={() => handleDelete(b.batch_id)}
                    disabled={deletingId === b.batch_id}
                    className="text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 transition-colors"
                >
                    {deletingId === b.batch_id ? '…' : 'Delete'}
                </button>
                </div>

            </div>
            ))}
        </div>
        )}
    </div>
    )
}
