'use client'
import { useState, useEffect, useRef } from 'react'
import DropZone from '@/components/DropZone'
import ConfigPanel from '@/components/ConfigPanel'
import JobQueue from '@/components/JobQueue'
import ResultTable from '@/components/ResultTable'
import { useParseStore } from '@/lib/store'
import { uploadBatch, subscribeToStatus } from '@/lib/api'
import clsx from 'clsx'

export default function Home() {
  const {
    batchId, jobs, config,
    isUploading, setBatchId, setJobs, updateJob, setUploading, reset
  } = useParseStore()

  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const unsubRef = useRef<(() => void) | null>(null)

  const handleFiles = (files: File[]) => {
    setPendingFiles((prev) => [...prev, ...files])
  }

  const handleStart = async () => {
    if (!pendingFiles.length) return
    setError(null)
    setIsDone(false)
    setUploading(true)
    reset()

    try {
      const res = await uploadBatch(pendingFiles, config)
      setBatchId(res.batch_id)
      setJobs(res.jobs)
      setPendingFiles([])

      // Subscribe to SSE
      const unsub = subscribeToStatus(
        res.batch_id,
        (update) => {
          if (update.job_id) updateJob(update as any)
        },
        () => setIsDone(true)
      )
      unsubRef.current = unsub
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleReset = () => {
    unsubRef.current?.()
    reset()
    setIsDone(false)
    setError(null)
    setPendingFiles([])
  }

  const totalDone = jobs.filter(j => ['done', 'low_confidence', 'failed'].includes(j.status)).length
  const progress = jobs.length > 0 ? Math.round((totalDone / jobs.length) * 100) : 0

  return (
    <div className="min-h-screen bg-[--gray-50]">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[--teal]" />
          <span className="text-sm font-medium tracking-tight">resumeparse</span>
          <span className="text-xs text-gray-400 ml-1">/ Batch resume extractor</span>
        </div>
        <div className="flex items-center gap-2">
          {batchId && (
            <span className="text-[10px] mono text-gray-400">
              batch: {batchId.slice(0, 8)}
            </span>
          )}
          {(batchId || pendingFiles.length > 0) && (
            <button
              onClick={handleReset}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
            >
              New batch
            </button>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6 flex flex-col gap-5">

        {/* Error */}
        {error && (
          <div className="bg-[--red-light] border border-red-200 text-[--red] text-xs px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        {/* Drop zone — hide after upload started */}
        {!batchId && (
          <>
            <DropZone onFiles={handleFiles} disabled={isUploading} />
            <ConfigPanel />

            {/* Pending files preview */}
            {pendingFiles.length > 0 && (
              <div className="bg-white border border-gray-100 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-gray-700">
                    {pendingFiles.length} file{pendingFiles.length > 1 ? 's' : ''} ready
                  </span>
                  <button
                    onClick={() => setPendingFiles([])}
                    className="text-[10px] text-gray-400 hover:text-gray-600"
                  >
                    clear
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {pendingFiles.map((f, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 mono">
                      {f.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={handleStart}
              disabled={pendingFiles.length === 0 || isUploading}
              className={clsx(
                'w-full py-3 rounded-xl text-sm font-medium transition-all',
                pendingFiles.length > 0
                  ? 'bg-[--teal] text-white hover:bg-[--teal-dark] shadow-sm'
                  : 'bg-gray-100 text-gray-300 cursor-not-allowed'
              )}
            >
              {isUploading ? 'Uploading…' : `Parse ${pendingFiles.length || ''} resume${pendingFiles.length !== 1 ? 's' : ''}`}
            </button>
          </>
        )}

        {/* Progress bar */}
        {batchId && jobs.length > 0 && !isDone && (
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-1.5">
              <span>Processing {jobs.length} files…</span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-[--teal] rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Done banner */}
        {isDone && (
          <div className="bg-[--teal-light] border border-[--teal] text-[--teal-dark] text-sm px-4 py-3 rounded-xl flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" stroke="#1D9E75" strokeWidth="1.2"/>
              <path d="M4 7l2 2 4-4" stroke="#1D9E75" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            All files processed — download your Excel below
          </div>
        )}

        {/* Queue + Results */}
        {batchId && (
          <>
            <JobQueue jobs={jobs} />
            <ResultTable jobs={jobs} batchId={batchId} />
          </>
        )}

      </main>
    </div>
  )
}
