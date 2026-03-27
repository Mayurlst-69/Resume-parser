import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type JobStatus = 'queued' | 'processing' | 'done' | 'failed' | 'low_confidence'
export type Certainty = 'confident' | 'unsure' | 'absent'

export interface ExtractedFields {
  name: string | null
  name_cert: Certainty
  position: string | null
  position_cert: Certainty
  phone: string | null
  email: string | null
  address: string | null
  education: string | null
  experience: string | null
  confidence: number
}

export interface ParseJob {
  job_id: string
  filename: string
  status: JobStatus
  file_size_kb: number
  parse_method: string
  result: ExtractedFields | null
  error: string | null
}

export interface ParseConfig {
  extract_name: boolean
  extract_position: boolean
  extract_phone: boolean
  extract_email: boolean
  extract_address: boolean
  extract_education: boolean
  extract_experience: boolean
  languages: string[]
  empty_value: 'null' | ''
  extract_mode: 'concise' | 'general'
  model: string
}

export interface ApiKeys {
  groq: string
  openai: string
  anthropic: string
  google: string
}

interface ParseStore {
  batchId: string | null
  jobs: ParseJob[]
  config: ParseConfig
  apiKeys: ApiKeys
  isUploading: boolean
  setBatchId: (id: string) => void
  setJobs: (jobs: ParseJob[]) => void
  updateJob: (update: Partial<ParseJob> & { job_id: string }) => void
  setConfig: (config: Partial<ParseConfig>) => void
  setApiKey: (provider: keyof ApiKeys, key: string) => void
  setUploading: (v: boolean) => void
  reset: () => void
}

const defaultConfig: ParseConfig = {
  extract_name: true,
  extract_position: true,
  extract_phone: true,
  extract_email: true,
  extract_address: false,
  extract_education: false,
  extract_experience: false,
  languages: ['eng', 'tha'],
  empty_value: 'null',
  extract_mode: 'concise',
  model: 'llama-3.3-70b-versatile',
}

const defaultApiKeys: ApiKeys = {
  groq: '',
  openai: '',
  anthropic: '',
  google: '',
}

export const useParseStore = create<ParseStore>()(
  persist(
    (set) => ({
      batchId: null,
      jobs: [],
      config: defaultConfig,
      apiKeys: defaultApiKeys,
      isUploading: false,

      setBatchId: (id) => set({ batchId: id }),
      setJobs: (jobs) => set({ jobs }),
      updateJob: (update) =>
        set((state) => ({
          jobs: state.jobs.map((j) =>
            j.job_id === update.job_id ? { ...j, ...update } : j
          ),
        })),
      setConfig: (partial) =>
        set((state) => ({ config: { ...state.config, ...partial } })),
      setApiKey: (provider, key) =>
        set((state) => ({ apiKeys: { ...state.apiKeys, [provider]: key } })),
      setUploading: (v) => set({ isUploading: v }),
      reset: () => set({ batchId: null, jobs: [], isUploading: false }),
    }),
    {
      name: 'resume-parser-store',
      // persist config + apiKeys across sessions, not jobs
      partialize: (state) => ({
        config: state.config,
        apiKeys: state.apiKeys,
      }),
    }
  )
)