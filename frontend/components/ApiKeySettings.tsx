'use client'
import { useState } from 'react'
import { useParseStore, ApiKeys } from '@/lib/store'
import { validateApiKey } from '@/lib/api'
import clsx from 'clsx'

const PROVIDERS: {
  id: keyof ApiKeys
  label: string
  url: string
  placeholder: string
  color: string
  free?: boolean
}[] = [
  {
    id: 'groq',
    label: 'Groq',
    url: 'https://console.groq.com',
    placeholder: 'gsk_...',
    color: 'teal',
    free: true,
  },
  {
    id: 'openai',
    label: 'OpenAI',
    url: 'https://platform.openai.com/api-keys',
    placeholder: 'sk-...',
    color: 'green',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    url: 'https://console.anthropic.com',
    placeholder: 'sk-ant-...',
    color: 'orange',
  },
  {
    id: 'google',
    label: 'Google AI',
    url: 'https://aistudio.google.com/app/apikey',
    placeholder: 'AIza...',
    color: 'blue',
  },
]

type Status = 'idle' | 'checking' | 'valid' | 'invalid'

export default function ApiKeySettings() {
  const { apiKeys, setApiKey } = useParseStore()
  const [show, setShow] = useState<Record<string, boolean>>({})
  const [status, setStatus] = useState<Record<string, Status>>({})

  const toggleShow = (id: string) => setShow(s => ({ ...s, [id]: !s[id] }))

  const handleValidate = async (provider: string) => {
    const key = apiKeys[provider as keyof ApiKeys]
    if (!key) return
    setStatus(s => ({ ...s, [provider]: 'checking' }))
    const valid = await validateApiKey(provider, key)
    setStatus(s => ({ ...s, [provider]: valid ? 'valid' : 'invalid' }))
  }

  const colorMap: Record<string, string> = {
    teal: 'bg-teal-50 border-teal-200 text-teal-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    orange: 'bg-orange-50 border-orange-200 text-orange-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
  }

  return (
    <div className="flex flex-col gap-3">
      {PROVIDERS.map(p => {
        const key = apiKeys[p.id] || ''
        const st = status[p.id] || 'idle'
        const hasKey = key.length > 8

        return (
          <div key={p.id} className="bg-white border border-gray-100 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className={clsx('text-[10px] px-2 py-0.5 rounded border font-medium', colorMap[p.color])}>
                  {p.label}
                </span>
                {p.free && (
                  <span className="text-[9px] text-teal-600 bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded-full">
                    Free tier available
                  </span>
                )}
                {/* Status indicator */}
                {st === 'valid' && <span className="text-[10px] text-teal-600">✓ Valid</span>}
                {st === 'invalid' && <span className="text-[10px] text-red-500">✗ Invalid</span>}
                {st === 'checking' && <span className="text-[10px] text-gray-400">Checking…</span>}
                {st === 'idle' && hasKey && (
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-400 inline-block" title="Key set"/>
                )}
              </div>
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] text-blue-500 hover:underline"
              >
                Get key ↗
              </a>
            </div>

            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type={show[p.id] ? 'text' : 'password'}
                  placeholder={p.placeholder}
                  value={key}
                  onChange={e => {
                    setApiKey(p.id, e.target.value)
                    setStatus(s => ({ ...s, [p.id]: 'idle' }))
                  }}
                  className={clsx(
                    'w-full text-xs px-3 py-2 pr-8 rounded-lg border outline-none mono transition-colors',
                    st === 'valid' && 'border-teal-400 bg-teal-50',
                    st === 'invalid' && 'border-red-400 bg-red-50',
                    st === 'idle' && 'border-gray-200 focus:border-[--teal]',
                    st === 'checking' && 'border-gray-300',
                  )}
                />
                <button
                  onClick={() => toggleShow(p.id)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  title={show[p.id] ? 'Hide' : 'Show'}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    {show[p.id] ? (
                      <path d="M1 7s2-4 6-4 6 4 6 4-2 4-6 4-6-4-6-4zm4 0a2 2 0 104 0 2 2 0 00-4 0z" stroke="currentColor" strokeWidth="1.2" fill="none"/>
                    ) : (
                      <path d="M2 2l10 10M5.5 4.5A6 6 0 0113 7s-1.5 3-4 4M3 9.5A6 6 0 011 7s2-4 6-4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
                    )}
                  </svg>
                </button>
              </div>
              <button
                onClick={() => handleValidate(p.id)}
                disabled={!hasKey || st === 'checking'}
                className={clsx(
                  'text-xs px-3 py-2 rounded-lg border transition-all flex-shrink-0',
                  hasKey && st !== 'checking'
                    ? 'border-gray-200 text-gray-600 hover:border-[--teal] hover:text-[--teal]'
                    : 'border-gray-100 text-gray-300 cursor-not-allowed'
                )}
              >
                {st === 'checking' ? '…' : 'Test'}
              </button>
            </div>
          </div>
        )
      })}

      <p className="text-[10px] text-gray-400 px-1">
        🔒 API keys are stored locally in your browser only — never sent to our server except for AI calls.
      </p>
    </div>
  )
}
