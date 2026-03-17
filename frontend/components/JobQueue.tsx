'use client'
import { ParseJob } from '@/lib/store'
import clsx from 'clsx'

interface Props {
  jobs: ParseJob[]
}

const STATUS_CONFIG = {
  queued:         { label: 'queued',      cls: 'bg-gray-100 text-gray-500' },
  processing:     { label: 'parsing…',   cls: 'bg-[--blue-light] text-[--blue]' },
  done:           { label: 'done',        cls: 'bg-[--teal-light] text-[--teal-dark]' },
  low_confidence: { label: 'low conf.',   cls: 'bg-[--amber-light] text-[--amber]' },
  failed:         { label: 'failed',      cls: 'bg-[--red-light] text-[--red]' },
}

function FileIcon({ name }: { name: string }) {
  const ext = name.split('.').pop()?.toLowerCase()
  const isImg = ext === 'jpg' || ext === 'jpeg' || ext === 'png'
  return (
    <div className={clsx(
      'w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-medium flex-shrink-0',
      isImg ? 'bg-purple-50 text-purple-600' : 'bg-gray-100 text-gray-500'
    )}>
      {isImg ? 'IMG' : 'PDF'}
    </div>
  )
}

function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? '#1D9E75' : pct >= 60 ? '#BA7517' : '#A32D2D'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-[10px] mono" style={{ color }}>{pct}%</span>
    </div>
  )
}

export default function JobQueue({ jobs }: Props) {
  const counts = {
    total: jobs.length,
    done: jobs.filter(j => j.status === 'done').length,
    processing: jobs.filter(j => j.status === 'processing').length,
    flagged: jobs.filter(j => j.status === 'low_confidence').length,
    failed: jobs.filter(j => j.status === 'failed').length,
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span className="text-sm font-medium text-gray-800">Processing queue</span>
        <div className="flex gap-3 text-xs text-gray-400">
          <span>{counts.done}/{counts.total} done</span>
          {counts.flagged > 0 && (
            <span className="text-[--amber]">{counts.flagged} flagged</span>
          )}
          {counts.failed > 0 && (
            <span className="text-[--red]">{counts.failed} failed</span>
          )}
        </div>
      </div>

      {/* File rows */}
      <div className="divide-y divide-gray-50">
        {jobs.map((job) => {
          const cfg = STATUS_CONFIG[job.status]
          const isProcessing = job.status === 'processing'

          return (
            <div
              key={job.job_id}
              className={clsx(
                'flex items-center gap-3 px-4 py-3 transition-colors',
                job.status === 'low_confidence' && 'bg-amber-50/40',
                job.status === 'failed' && 'bg-red-50/30',
              )}
            >
              <FileIcon name={job.filename} />

              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-800 truncate">{job.filename}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-gray-400">
                    {job.file_size_kb > 0 ? `${job.file_size_kb} KB` : '—'}
                  </span>
                  {job.parse_method && (
                    <span className="text-[10px] text-gray-400 mono">{job.parse_method}</span>
                  )}
                </div>
                {/* Progress shimmer for processing */}
                {isProcessing && (
                  <div className="mt-1.5 h-0.5 w-full bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[--teal] rounded-full animate-[shimmer_1.5s_ease-in-out_infinite]"
                      style={{ width: '60%', animation: 'pulse 1.5s ease-in-out infinite' }} />
                  </div>
                )}
              </div>

              {/* Confidence bar (only when done) */}
              {job.result && (
                <ConfBar value={job.result.confidence} />
              )}

              {/* Status pill */}
              <span className={clsx('text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0', cfg.cls)}>
                {cfg.label}
              </span>
            </div>
          )
        })}

        {jobs.length === 0 && (
          <div className="px-4 py-8 text-center text-xs text-gray-400">
            No files uploaded yet
          </div>
        )}
      </div>
    </div>
  )
}
