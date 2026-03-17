import { create } from 'zustand'

export type JobStatus = 'queued' | 'processing' | 'done' | 'failed' | 'low_confidence'

export interface ExtractedFields {
  name: string | null
  position: string | null
  phone: string | null
  email: string | null
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
  languages: string[]
  empty_value: 'null' | ''
}

interface ParseStore {
  batchId: string | null
  jobs: ParseJob[]
  config: ParseConfig
  isUploading: boolean
  setBatchId: (id: string) => void
  setJobs: (jobs: ParseJob[]) => void
  updateJob: (update: Partial<ParseJob> & { job_id: string }) => void
  setConfig: (config: Partial<ParseConfig>) => void
  setUploading: (v: boolean) => void
  reset: () => void
}

const defaultConfig: ParseConfig = {
  extract_name: true,
  extract_position: true,
  extract_phone: true,
  extract_email: true,
  languages: ['eng', 'tha'],
  empty_value: 'null',
}

export const useParseStore = create<ParseStore>((set) => ({
  batchId: null,
  jobs: [],
  config: defaultConfig,
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
  setUploading: (v) => set({ isUploading: v }),
  reset: () => set({ batchId: null, jobs: [], isUploading: false }),
}))
