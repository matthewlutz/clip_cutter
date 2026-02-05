import { useState, useCallback, useEffect } from 'react'
import type { UploadedVideo, Timestamp } from '../types'
import * as api from '../utils/api'

interface UseVideoAnalysisReturn {
  // Video state
  video: UploadedVideo | null
  isUploading: boolean

  // Analysis state
  isProcessing: boolean
  progress: number
  statusMessage: string
  error: string | null

  // Results
  timestamps: Timestamp[] | null
  resultUrl: string | null

  // Actions
  uploadVideo: (file: File) => Promise<void>
  startAnalysis: (query: string, padding: number) => Promise<void>
  clearVideo: () => Promise<void>
  clearError: () => void
}

export function useVideoAnalysis(): UseVideoAnalysisReturn {
  const [video, setVideo] = useState<UploadedVideo | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [timestamps, setTimestamps] = useState<Timestamp[] | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)

  // Poll for status updates
  useEffect(() => {
    if (!isProcessing || !video) return

    const pollStatus = async () => {
      try {
        const status = await api.getJobStatus(video.job_id)
        setProgress(status.progress)
        setStatusMessage(status.message)

        if (status.timestamps) {
          setTimestamps(status.timestamps)
        }

        if (status.status === 'complete') {
          setIsProcessing(false)
          if (status.result_url) {
            setResultUrl(api.getDownloadUrl(status.result_url))
          }
        } else if (status.status === 'error') {
          setIsProcessing(false)
          setError(status.error || 'Processing failed')
        }
      } catch {
        // Ignore polling errors
      }
    }

    const interval = setInterval(pollStatus, 500)
    return () => clearInterval(interval)
  }, [isProcessing, video])

  const uploadVideo = useCallback(async (file: File) => {
    if (!file.type.startsWith('video/')) {
      setError('Please select a video file')
      return
    }

    setError(null)
    setTimestamps(null)
    setResultUrl(null)
    setIsUploading(true)
    setStatusMessage('Uploading video...')

    try {
      const uploaded = await api.uploadVideo(file)
      setVideo(uploaded)
      setStatusMessage('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setStatusMessage('')
    } finally {
      setIsUploading(false)
    }
  }, [])

  const startAnalysis = useCallback(
    async (query: string, padding: number) => {
      if (!video || !query.trim()) return

      setError(null)
      setIsProcessing(true)
      setProgress(0)
      setTimestamps(null)
      setResultUrl(null)
      setStatusMessage('Starting analysis...')

      try {
        await api.startAnalysis(video.job_id, query, padding)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start analysis')
        setIsProcessing(false)
      }
    },
    [video]
  )

  const clearVideo = useCallback(async () => {
    if (video) {
      try {
        await api.deleteJob(video.job_id)
      } catch {
        // Ignore delete errors
      }
    }
    setVideo(null)
    setTimestamps(null)
    setResultUrl(null)
    setError(null)
    setStatusMessage('')
    setProgress(0)
  }, [video])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    video,
    isUploading,
    isProcessing,
    progress,
    statusMessage,
    error,
    timestamps,
    resultUrl,
    uploadVideo,
    startAnalysis,
    clearVideo,
    clearError,
  }
}
