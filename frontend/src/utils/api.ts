import type { UploadedVideo, JobStatus } from '../types'

const API_BASE = ''

export async function uploadVideo(file: File): Promise<UploadedVideo> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.detail || 'Upload failed')
  }

  const data = await res.json()
  return {
    ...data,
    url: URL.createObjectURL(file),
  }
}

export async function startAnalysis(
  jobId: string,
  query: string,
  padding: number
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/analyze/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, padding }),
  })

  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.detail || 'Analysis failed to start')
  }
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/status/${jobId}`)
  if (!res.ok) throw new Error('Failed to get status')
  return res.json()
}

export async function deleteJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/api/job/${jobId}`, { method: 'DELETE' })
}

export function getDownloadUrl(path: string): string {
  return `${API_BASE}${path}`
}
