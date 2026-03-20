'use client'
import { ParseJob, ParseConfig, Certainty } from '@/lib/store'
import { getExportUrl } from '@/lib/api'
import clsx from 'clsx'

interface Props {
  jobs: ParseJob[]
  batchId: string | null
  config: ParseConfig
}

function Cell({ value, cert }: { value: string | null; cert?: Certainty }) {
  if (cert === 'unsure') {
    return (
      <span className="inline-flex items-center gap-1 text-amber-500 italic text-[11px]">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
        Unsure
      </span>
    )
  }
  if (!value || value === 'null') {
    return <span className="text-gray-300 italic mono text-[11px]">null</span>
  }
  return <span>{value}</span>
}

function ConfBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const cls =
    pct >= 80 ? 'bg-[--teal-light] text-[--teal-dark]' :
    pct >= 60 ? 'bg-[--amber-light] text-[--amber]' :
    'bg-[--red-light] text-[--red]'
  return (
    <span className={clsx('text-[10px] px-2 py-0.5 rounded-full font-medium mono whitespace-nowrap', cls)}>
      {pct}%
    </span>
  )
}

export default function ResultTable({ jobs, batchId, config }: Props) {
  const doneJobs = jobs.filter(
    (j) => j.status === 'done' || j.status === 'low_confidence'
  )

  const handleExport = () => {
    if (!batchId) return
    window.open(getExportUrl(batchId), '_blank')
  }

  // ── Build visible columns based on config toggles ──────────────────────────
  type ColDef = {
    label: string
    enabled: boolean
    render: (job: ParseJob) => React.ReactNode
  }

  const COLUMNS: ColDef[] = [
    {
      label: 'Name',
      enabled: config.extract_name,
      render: (job) => <Cell value={job.result?.name ?? null} cert={job.result?.name_cert as Certainty} />,
    },
    {
      label: 'Position',
      enabled: config.extract_position,
      render: (job) => <Cell value={job.result?.position ?? null} cert={job.result?.position_cert as Certainty} />,
    },
    {
      label: 'Phone',
      enabled: config.extract_phone,
      render: (job) => (
        <span className="mono whitespace-nowrap">
          <Cell value={job.result?.phone ?? null} />
        </span>
      ),
    },
    {
      label: 'Email',
      enabled: config.extract_email,
      render: (job) => (
        <span className="whitespace-nowrap">
          <Cell value={job.result?.email ?? null} />
        </span>
      ),
    },
    {
      label: 'Address',
      enabled: config.extract_address,
      render: (job) => (
        <span className="block truncate max-w-[160px] text-[11px]" title={job.result?.address ?? ''}>
          <Cell value={job.result?.address ?? null} />
        </span>
      ),
    },
    {
      label: 'Education',
      enabled: config.extract_education,
      render: (job) => (
        <span className="block truncate max-w-[180px] text-[11px]" title={job.result?.education ?? ''}>
          <Cell value={job.result?.education ?? null} />
        </span>
      ),
    },
    {
      label: 'Experience',
      enabled: config.extract_experience,
      render: (job) => (
        <span className="block truncate max-w-[180px] text-[11px]" title={job.result?.experience ?? ''}>
          <Cell value={job.result?.experience ?? null} />
        </span>
      ),
    },
    {
      label: 'Conf.',
      enabled: true, // always show
      render: (job) => job.result ? <ConfBadge value={job.result.confidence} /> : <span>—</span>,
    },
    {
      label: 'Source file',
      enabled: true,
      render: (job) => (
        <span className="text-blue-500 hover:text-blue-700 underline cursor-pointer block truncate max-w-[200px]" title={job.filename}>
          {job.filename}
        </span>
      ),
    },
    {
      label: 'Method',
      enabled: true,
      render: (job) => (
        <span className="text-gray-400 mono whitespace-nowrap">{job.parse_method || '—'}</span>
      ),
    },
  ]

  const visibleCols = COLUMNS.filter(c => c.enabled)

  return (
    <div className="card card-lift overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800">Extracted results</span>
          <span className="text-xs text-gray-400">{doneJobs.length} records</span>
          <span className="flex items-center gap-1 text-[10px] text-amber-500 ml-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
            If Unsure result pop up, Please double-check the result
          </span>
        </div>
        <button
          onClick={handleExport}
          disabled={!batchId || doneJobs.length === 0}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
            batchId && doneJobs.length > 0
              ? 'bg-[--teal-light] text-[--teal-dark] hover:bg-[--teal] hover:text-white'
              : 'bg-gray-100 text-gray-300 cursor-not-allowed'
          )}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 8v1.5A.5.5 0 002.5 10h7a.5.5 0 00.5-.5V8M6 2v6M3.5 5.5L6 8l2.5-2.5"
              stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Export Excel
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="data-table w-full text-xs">
          <thead>
            <tr className="bg-gray-50">
              {visibleCols.map(col => (
                <th key={col.label} className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {doneJobs.map((job) => {
              const hasUnsure = job.result?.name_cert === 'unsure' || job.result?.position_cert === 'unsure'
              return (
                <tr
                  key={job.job_id}
                  className={clsx(
                    'transition-colors hover:bg-gray-50/50',
                    job.status === 'low_confidence' && 'bg-amber-50/50',
                    hasUnsure && 'bg-amber-50/30',
                  )}
                >
                  {visibleCols.map(col => (
                    <td key={col.label} className="px-4 py-3 text-gray-700">
                      {col.render(job)}
                    </td>
                  ))}
                </tr>
              )
            })}
            {doneJobs.length === 0 && (
              <tr>
                <td colSpan={visibleCols.length} className="px-4 py-8 text-center text-gray-400">
                  Results will appear here as files are parsed
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
