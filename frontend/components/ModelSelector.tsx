'use client'
import { useEffect, useRef, useState } from 'react'
import { useParseStore } from '@/lib/store'
import { fetchModels } from '@/lib/api'
import clsx from 'clsx'

interface Model {
  provider: string
  provider_label: string
  id: string
  label: string
  context: string
  speed: string
  desc: string
  free: boolean
}

const PROVIDER_COLORS: Record<string, string> = {
  groq:      'text-teal-600 bg-teal-50 border-teal-200',
  openai:    'text-green-600 bg-green-50 border-green-200',
  anthropic: 'text-orange-600 bg-orange-50 border-orange-200',
  google:    'text-blue-600 bg-blue-50 border-blue-200',
}

const SPEED_ICONS: Record<string, string> = {
  fastest: '⚡⚡',
  fast:    '⚡',
  medium:  '◎',
}

export default function ModelSelector() {
  const { config, apiKeys, setConfig } = useParseStore()
  const [models, setModels] = useState<Model[]>([])
  const [open, setOpen] = useState(false)
  const [hover, setHover] = useState<Model | null>(null)
  const [customMode, setCustomMode] = useState(false)
  const [customVal, setCustomVal] = useState('')
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchModels().then(d => setModels(d.models || []))
  }, [])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const currentModel = models.find(m => m.id === config.groq_model)

  // Group by provider
  const grouped = models.reduce((acc, m) => {
    if (!acc[m.provider]) acc[m.provider] = { label: m.provider_label, models: [] }
    acc[m.provider].models.push(m)
    return acc
  }, {} as Record<string, { label: string; models: Model[] }>)

  const hasKey = (provider: string) => {
    const key = apiKeys[provider as keyof typeof apiKeys]
    return key && key.length > 8
  }

  const selectModel = (m: Model) => {
    setConfig({ groq_model: m.id })
    setCustomMode(false)
    setOpen(false)
  }

  return (
    <div className="relative" ref={dropRef}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        className={clsx(
          'w-full flex items-center justify-between gap-2',
          'px-3 py-2.5 rounded-xl border text-left transition-all',
          open ? 'border-[--teal] bg-[--teal-light]' : 'border-gray-200 bg-white hover:border-gray-300'
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          {currentModel ? (
            <>
              <span className={clsx('text-[10px] px-1.5 py-0.5 rounded border font-medium flex-shrink-0',
                PROVIDER_COLORS[currentModel.provider])}>
                {currentModel.provider_label}
              </span>
              <span className="text-xs font-medium text-gray-800 truncate">{currentModel.label}</span>
              {currentModel.free && (
                <span className="text-[9px] text-teal-600 bg-teal-50 px-1.5 py-0.5 rounded-full border border-teal-200 flex-shrink-0">
                  free
                </span>
              )}
            </>
          ) : (
            <span className="text-xs text-gray-500 mono truncate">{config.groq_model}</span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className={clsx('flex-shrink-0 transition-transform', open && 'rotate-180')}>
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
          <div className="max-h-80 overflow-y-auto">
            {Object.entries(grouped).map(([provider, group]) => (
              <div key={provider}>
                {/* Provider header */}
                <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-b border-gray-100">
                  <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded border',
                    PROVIDER_COLORS[provider])}>
                    {group.label}
                  </span>
                  {hasKey(provider) ? (
                    <span className="text-[10px] text-teal-600 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-500 inline-block"/>
                      API key set
                    </span>
                  ) : provider !== 'groq' ? (
                    <span className="text-[10px] text-amber-500 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block"/>
                      No key
                    </span>
                  ) : null}
                </div>

                {/* Models */}
                {group.models.map(m => {
                  const selected = config.groq_model === m.id
                  const locked = !m.free && !hasKey(m.provider)
                  return (
                    <div
                      key={m.id}
                      onMouseEnter={() => setHover(m)}
                      onMouseLeave={() => setHover(null)}
                      onClick={() => !locked && selectModel(m)}
                      className={clsx(
                        'flex items-center justify-between px-3 py-2 cursor-pointer transition-colors',
                        selected && 'bg-[--teal-light]',
                        !selected && !locked && 'hover:bg-gray-50',
                        locked && 'opacity-50 cursor-not-allowed',
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        {selected && <span className="text-[--teal] text-xs">✓</span>}
                        {!selected && <span className="w-3"/>}
                        <span className={clsx('text-xs font-medium truncate',
                          selected ? 'text-[--teal-dark]' : 'text-gray-700')}>
                          {m.label}
                        </span>
                        {m.free && (
                          <span className="text-[9px] text-teal-600 bg-teal-50 px-1 rounded border border-teal-200 flex-shrink-0">
                            free
                          </span>
                        )}
                        {locked && (
                          <span className="text-[9px] text-amber-500 flex-shrink-0">🔒 need key</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-gray-400 flex-shrink-0">
                        <span>{m.context}</span>
                        <span title={m.speed}>{SPEED_ICONS[m.speed] || '◎'}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ))}

            {/* Custom */}
            <div className="border-t border-gray-100">
              {!customMode ? (
                <button
                  onClick={() => setCustomMode(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
                >
                  <span className="w-3 text-gray-300">+</span>
                  Custom model ID...
                </button>
              ) : (
                <div className="flex gap-2 px-3 py-2">
                  <input
                    autoFocus
                    type="text"
                    placeholder="e.g. llama-3.1-70b-versatile"
                    value={customVal}
                    onChange={e => setCustomVal(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && customVal.trim()) {
                        setConfig({ groq_model: customVal.trim() })
                        setCustomMode(false)
                        setOpen(false)
                      }
                      if (e.key === 'Escape') setCustomMode(false)
                    }}
                    className="flex-1 text-xs px-2 py-1 rounded-lg border border-gray-200 outline-none focus:border-[--teal]"
                  />
                  <button
                    onClick={() => {
                      if (customVal.trim()) {
                        setConfig({ groq_model: customVal.trim() })
                        setCustomMode(false)
                        setOpen(false)
                      }
                    }}
                    className="text-xs px-2 py-1 rounded-lg bg-[--teal] text-white"
                  >
                    Use
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Hover tooltip */}
          {hover && (
            <div className="border-t border-gray-100 px-3 py-2 bg-gray-50">
              <p className="text-xs font-medium text-gray-700 mb-0.5">{hover.label}</p>
              <p className="text-[10px] text-gray-500">{hover.desc}</p>
              <div className="flex gap-3 mt-1 text-[10px] text-gray-400">
                <span>Context: {hover.context}</span>
                <span>Speed: {hover.speed}</span>
                {hover.free && <span className="text-teal-600">Free tier ✓</span>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
