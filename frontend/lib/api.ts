import { ParseConfig, ParseJob } from './store'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function uploadBatch(
  files: File[],
  config: ParseConfig
): Promise<{ batch_id: string; jobs: ParseJob[] }> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('extract_name', String(config.extract_name))
  form.append('extract_position', String(config.extract_position))
  form.append('extract_phone', String(config.extract_phone))
  form.append('extract_email', String(config.extract_email))
  form.append('languages', config.languages.join(','))
  form.append('empty_value', config.empty_value === 'null' ? 'null' : '')

  const res = await fetch(`${API}/api/parse`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
  return res.json()
}

export function subscribeToStatus(
  batchId: string,
  onUpdate: (job: Partial<ParseJob> & { job_id?: string; event?: string }) => void,
  onComplete: () => void
): () => void {
  const es = new EventSource(`${API}/api/status/${batchId}`)

  es.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.event === 'batch_complete') {
      onComplete()
      es.close()
    } else if (data.job_id) {
      onUpdate(data)
    }
  }

  es.onerror = () => {
    es.close()
  }

  return () => es.close()
}

export function getExportUrl(batchId: string): string {
  return `${API}/api/export/${batchId}`
}
