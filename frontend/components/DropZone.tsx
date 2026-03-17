'use client'
import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import clsx from 'clsx'

interface Props {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
}

export default function DropZone({ onFiles, disabled }: Props) {
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length) onFiles(accepted)
  }, [onFiles])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    disabled,
    multiple: true,
  })

  return (
    <div
      {...getRootProps()}
      className={clsx(
        'relative flex flex-col items-center justify-center gap-3',
        'border-2 border-dashed rounded-xl p-10 cursor-pointer transition-all duration-200',
        isDragActive && !isDragReject && 'border-[--teal] bg-[--teal-light] scale-[1.01]',
        isDragReject && 'border-red-400 bg-[--red-light]',
        !isDragActive && !disabled && 'border-gray-200 bg-white hover:border-[--teal] hover:bg-[--teal-light]',
        disabled && 'opacity-50 cursor-not-allowed border-gray-200 bg-gray-50',
      )}
    >
      <input {...getInputProps()} />

      {/* Icon */}
      <div className={clsx(
        'w-12 h-12 rounded-xl flex items-center justify-center transition-colors',
        isDragActive ? 'bg-[--teal]' : 'bg-gray-100'
      )}>
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <path
            d="M11 3v11M7 7l4-4 4 4"
            stroke={isDragActive ? '#fff' : '#1D9E75'}
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M3 15v1.5A2.5 2.5 0 005.5 19h11a2.5 2.5 0 002.5-2.5V15"
            stroke={isDragActive ? '#fff' : '#1D9E75'}
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </div>

      <div className="text-center">
        <p className="text-sm font-medium text-gray-800">
          {isDragActive ? 'Drop files here' : 'Drop resumes here or click to browse'}
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Batch upload supported — PDF (text & scanned), JPG, PNG
        </p>
      </div>

      <div className="flex gap-2 flex-wrap justify-center">
        {['PDF (text)', 'PDF (scanned)', 'JPG', 'PNG'].map((t) => (
          <span key={t} className="text-[10px] px-2 py-0.5 rounded-full border border-gray-200 text-gray-500 bg-gray-50">
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
