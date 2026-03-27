import { ParseConfig, ApiKeys, ParseJob } from './store'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function uploadBatch(
  files: File[],
  config: ParseConfig,
  apiKeys: ApiKeys
): Promise<{ batch_id: string; jobs: ParseJob[] }> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('extract_name',       String(config.extract_name))
  form.append('extract_position',   String(config.extract_position))
  form.append('extract_phone',      String(config.extract_phone))
  form.append('extract_email',      String(config.extract_email))
  form.append('extract_address',    String(config.extract_address))
  form.append('extract_education',  String(config.extract_education))
  form.append('extract_experience', String(config.extract_experience))
  form.append('languages',          config.languages.join(','))
  form.append('empty_value',        config.empty_value === 'null' ? 'null' : '')
  form.append('extract_mode',       config.extract_mode)
  form.append('model',         config.model)
  // Send api_keys as JSON — backend parses and uses per-provider
  form.append('api_keys', JSON.stringify(apiKeys))

  const res = await fetch(`${API}/api/parse`, { method: 'POST', body: form })
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
    if (data.event === 'batch_complete') { onComplete(); es.close() }
    else if (data.job_id) onUpdate(data)
  }
  es.onerror = () => es.close()
  return () => es.close()
}

export function getExportUrl(batchId: string): string {
  return `${API}/api/export/${batchId}`
}

export async function fetchModels() {
  const res = await fetch(`${API}/api/models`)
  return res.json()
}

export async function validateApiKey(provider: string, key: string): Promise<boolean> {
  try {
    const testModels: Record<string, string> = {
      groq:      'llama-3.1-8b-instant',
      openai:    'gpt-4o-mini',
      anthropic: 'claude-haiku-4-5',
      google:    'gemini-1.5-flash',
    } 
    const urls: Record<string, string> = {
      groq:      'https://api.groq.com/openai/v1/chat/completions',
      openai:    'https://api.openai.com/v1/chat/completions',
      anthropic: 'https://api.anthropic.com/v1/messages',
      google:    'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    }
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (provider === 'anthropic') {
      headers['x-api-key'] = key
      headers['anthropic-version'] = '2023-06-01'
    } else {
      headers['Authorization'] = `Bearer ${key}`
    }
    const res = await fetch(urls[provider], {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: testModels[provider],
        messages: [{ role: 'user', content: 'hi' }],
        max_tokens: 1,
      }),
    })
    return res.status !== 401 && res.status !== 403
  } catch {
    return false
  }
}
