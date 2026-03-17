'use client'
import { useParseStore } from '@/lib/store'
import clsx from 'clsx'

const FIELDS = [
  { key: 'extract_name', label: 'Name' },
  { key: 'extract_position', label: 'Position' },
  { key: 'extract_phone', label: 'Phone' },
  { key: 'extract_email', label: 'Email' },
] as const

const LANGS = [
  { code: 'eng', label: 'English' },
  { code: 'tha', label: 'Thai' },
]

export default function ConfigPanel() {
  const { config, setConfig } = useParseStore()

  const toggleField = (key: typeof FIELDS[number]['key']) => {
    setConfig({ [key]: !config[key] })
  }

  const toggleLang = (code: string) => {
    const has = config.languages.includes(code)
    if (has && config.languages.length === 1) return // keep at least 1
    setConfig({
      languages: has
        ? config.languages.filter((l) => l !== code)
        : [...config.languages, code],
    })
  }

  return (
    <div className="grid grid-cols-3 gap-3">
      {/* Fields */}
      <div className="col-span-2 bg-white border border-gray-100 rounded-xl p-4">
        <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-3">
          Extract fields
        </p>
        <div className="flex flex-wrap gap-2">
          {FIELDS.map(({ key, label }) => {
            const on = config[key]
            return (
              <button
                key={key}
                onClick={() => toggleField(key)}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all',
                  on
                    ? 'bg-[--teal-light] text-[--teal-dark] border-[--teal]'
                    : 'bg-gray-50 text-gray-400 border-gray-200 hover:border-gray-300'
                )}
              >
                <span className={clsx(
                  'w-2 h-2 rounded-full transition-colors',
                  on ? 'bg-[--teal]' : 'bg-gray-300'
                )} />
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Language */}
      <div className="bg-white border border-gray-100 rounded-xl p-4">
        <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-3">
          OCR language
        </p>
        <div className="flex gap-2 mb-3">
          {LANGS.map(({ code, label }) => {
            const on = config.languages.includes(code)
            return (
              <button
                key={code}
                onClick={() => toggleLang(code)}
                className={clsx(
                  'px-3 py-1 rounded-full text-xs border transition-all',
                  on
                    ? 'bg-[--blue-light] text-[--blue] border-blue-300'
                    : 'bg-gray-50 text-gray-400 border-gray-200'
                )}
              >
                {label}
              </button>
            )
          })}
        </div>
        <p className="text-[10px] text-gray-400">Engine: PaddleOCR</p>
      </div>

      {/* Empty value */}
      <div className="bg-white border border-gray-100 rounded-xl p-4">
        <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-3">
          When field not found
        </p>
        <div className="flex flex-col gap-2">
          {(['null', ''] as const).map((val) => (
            <label key={val} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="empty"
                checked={config.empty_value === val}
                onChange={() => setConfig({ empty_value: val })}
                className="accent-[--teal]"
              />
              <span className="text-xs text-gray-700 mono">
                {val === 'null' ? 'null' : '""  (empty string)'}
              </span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
