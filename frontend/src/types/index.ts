export interface Timestamp {
  start_time: number
  end_time: number
  description?: string
  play_description?: string
  confidence_score?: number
  camera_angle?: string
  player_jersey?: string
  action_type?: string
  verification_status?: 'verified' | 'skipped' | 'rejected'
}

export interface JobStatus {
  job_id: string
  status: 'uploaded' | 'analyzing' | 'extracting' | 'complete' | 'error'
  progress: number
  message: string
  result_url: string | null
  timestamps: Timestamp[] | null
  error: string | null
}

export interface UploadedVideo {
  job_id: string
  filename: string
  duration: number
  file_size: number
  url: string
}
