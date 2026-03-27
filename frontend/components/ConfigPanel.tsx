'use client'
import { useState } from 'react'
import { useParseStore } from '@/lib/store'
import ModelSelector from '@/components/ModelSelector'
import ApiKeySettings from '@/components/ApiKeySettings'
import clsx from 'clsx'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const FIELDS = [
  { key: 'extract_name',       label: 'Name',       heavy: false },
  { key: 'extract_position',   label: 'Position',   heavy: false },
  { key: 'extract_phone',      label: 'Phone',      heavy: false },
  { key: 'extract_email',      label: 'Email',      heavy: false },
  { key: 'extract_address',    label: 'Address',    heavy: false },
  { key: 'extract_education',  label: 'Education',  heavy: true  },
  { key: 'extract_experience', label: 'Experience', heavy: true  },
] as const

const LANGS = [
  { code: 'eng', label: 'English' },
  { code: 'tha', label: 'Thai' },
]

const EXTRACT_MODES = [
  {
    value: 'concise',
    label: 'Concise',
    desc: 'Contact section only — fewer tokens, lower cost, best for standard resumes', 
  },
  {
    value: 'general',
    label: 'General',
    desc: 'Full text (4000 chars) — higher token cost, best for non-standard formats',
  },
] as const

const TABS = ['Config', 'API Keys'] as const
type Tab = typeof TABS[number]

export default function ConfigPanel() {
  const { config, setConfig } = useParseStore()
  const [tab, setTab] = useState<Tab>('Config')

  const toggleField = (key: typeof FIELDS[number]['key']) => {
    setConfig({ [key]: !config[key] })
  }

  const toggleLang = (code: string) => {
    const has = config.languages.includes(code)
    if (has && config.languages.length === 1) return
    setConfig({
      languages: has
        ? config.languages.filter(l => l !== code)
        : [...config.languages, code],
    })
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      {/* Tab header */}
      <div className="flex border-b border-gray-100">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              'flex-1 text-xs py-2.5 font-medium transition-colors',
              tab === t
                ? 'text-[--teal-dark] border-b-2 border-[--teal] bg-[--teal-light]'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            )}
          >
            {t === 'API Keys' && '🔑 '}{t}
          </button>
        ))}
      </div>

      <div className="p-4 flex flex-col gap-4">

        {/* ── Config tab ── */}
        {tab === 'Config' && (
          <>
            {/* AI Model */}
            <div>
              <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">
                AI model
              </p>
              <ModelSelector />
            </div>

            {/* Extract mode */}
            <div>
              <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">
                Extract mode
              </p>
              <div className="grid grid-cols-2 gap-2">
                {EXTRACT_MODES.map(({ value, label, desc }) => {
                  const on = config.extract_mode === value
                  return (
                    <button
                      key={value}
                      onClick={() => setConfig({ extract_mode: value })}
                      className={clsx(
                        'text-left p-3 rounded-xl border transition-all',
                        on ? 'bg-[--teal-light] border-[--teal]' : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', on ? 'bg-[--teal]' : 'bg-gray-300')} />
                        <span className={clsx('text-xs font-medium', on ? 'text-[--teal-dark]' : 'text-gray-600')}>
                          {label}
                        </span>
                      </div>
                      <p className="text-[10px] text-gray-400 leading-relaxed pl-4">{desc}</p>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Bottom row */}
            <div className="grid grid-cols-3 gap-3">
              {/* Fields */}
              <div className="col-span-2 bg-gray-50 rounded-xl p-3">
                <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">
                  Extract fields
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {FIELDS.map(({ key, label, heavy }) => {
                    const on = config[key]
                    return (
                      <button
                        key={key}
                        onClick={() => toggleField(key)}
                        className={clsx(
                          'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all',
                          on
                            ? 'bg-[--teal-light] text-[--teal-dark] border-[--teal]'
                            : 'bg-white text-gray-400 border-gray-200 hover:border-gray-300'
                        )}
                      >
                        <span className={clsx('w-1.5 h-1.5 rounded-full', on ? 'bg-[--teal]' : 'bg-gray-300')} />
                        {label}
                        {heavy && <span className="text-[9px] text-amber-400">full</span>}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Right column */}
              <div className="flex flex-col gap-2">
                {/* Language */}
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">OCR lang</p>
                  <div className="flex gap-1.5 mb-1.5">
                    {LANGS.map(({ code, label }) => {
                      const on = config.languages.includes(code)
                      return (
                        <button
                          key={code}
                          onClick={() => toggleLang(code)}
                          className={clsx(
                            'px-2 py-0.5 rounded-full text-xs border transition-all',
                            on ? 'bg-[--blue-light] text-[--blue] border-blue-300' : 'bg-white text-gray-400 border-gray-200'
                          )}
                        >
                          {label}
                        </button>
                      )
                    })}
                  </div>
                  <p className="text-[9px] text-gray-400">EasyOCR</p>
                </div>

                {/* Empty value */}
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">Not found</p>
                  <div className="flex flex-col gap-1">
                    {(['null', ''] as const).map(val => (
                      <label key={val} className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="radio"
                          name="empty"
                          checked={config.empty_value === val}
                          onChange={() => setConfig({ empty_value: val })}
                          className="accent-[--teal]"
                        />
                        <span className="text-[10px] text-gray-600 mono">
                          {val === 'null' ? 'null' : '""'}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── API Keys tab ── */}
        {tab === 'API Keys' && <ApiKeySettings />}

      </div>
    </div>
  )
}
