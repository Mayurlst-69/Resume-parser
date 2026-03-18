'use client'
import { ParseJob } from '@/lib/store'
import { getExportUrl } from '@/lib/api'
import clsx from 'clsx'

interface Props {
  jobs: ParseJob[]
  batchId: string | null
}

function Cell({ value }: { value: string | null }) {
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

export default function ResultTable({ jobs, batchId }: Props) {
  const doneJobs = jobs.filter(
    (j) => j.status === 'done' || j.status === 'low_confidence'
  )

  const handleExport = () => {
    if (!batchId) return
    window.open(getExportUrl(batchId), '_blank')
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800">Extracted results</span>
          <span className="text-xs text-gray-400">{doneJobs.length} records</span>
        </div>
        <button
          onClick={handleExport}
          disabled={!batchId || doneJobs.length === 0}
          className={clsx(
            'flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium transition-all',
            batchId && doneJobs.length > 0
              ? 'bg-[--teal] text-white hover:bg-[--teal-dark]'
              : 'bg-gray-100 text-gray-300 cursor-not-allowed'
          )}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v7M3 5l3 3 3-3M1 9v1.5A.5.5 0 001.5 11h9a.5.5 0 00.5-.5V9"
              stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Export Excel
        </button>
      </div>

      {/* Table — horizontal scroll on overflow */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ minWidth: '900px' }}>
          <thead>
            <tr className="bg-gray-50">
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '160px' }}>Name</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '200px' }}>Position</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '140px' }}>Phone</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '200px' }}>Email</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '70px' }}>Conf.</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '180px' }}>Source file</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider" style={{ minWidth: '90px' }}>Method</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {doneJobs.map((job) => (
              <tr
                key={job.job_id}
                className={clsx(
                  'transition-colors hover:bg-gray-50/50',
                  job.status === 'low_confidence' && 'bg-amber-50/50',
                )}
              >
                {/* Name — never truncate */}
                <td className="px-4 py-3 text-gray-800 font-medium">
                  <Cell value={job.result?.name ?? null} />
                </td>
                {/* Position */}
                <td className="px-4 py-3 text-gray-700">
                  <Cell value={job.result?.position ?? null} />
                </td>
                {/* Phone */}
                <td className="px-4 py-3 text-gray-600 mono whitespace-nowrap">
                  <Cell value={job.result?.phone ?? null} />
                </td>
                {/* Email */}
                <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                  <Cell value={job.result?.email ?? null} />
                </td>
                {/* Confidence */}
                <td className="px-4 py-3">
                  {job.result ? <ConfBadge value={job.result.confidence} /> : '—'}
                </td>
                {/* Source file */}
                <td className="px-4 py-3 max-w-[200px]">
                  <span
                    className="text-blue-500 hover:text-blue-700 underline cursor-pointer block truncate"
                    title={job.filename}
                  >
                    {job.filename}
                  </span>
                </td>
                {/* Method */}
                <td className="px-4 py-3 text-gray-400 mono whitespace-nowrap">
                  {job.parse_method || '—'}
                </td>
              </tr>
            ))}
            {doneJobs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
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
