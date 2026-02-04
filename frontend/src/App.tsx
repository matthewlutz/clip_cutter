import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Menu,
  X,
  Home,
  History,
  Settings,
  Upload,
  Scissors,
  Play,
  Download,
  Trash2,
  Loader2,
  CheckCircle,
  AlertCircle,
  Film,
} from 'lucide-react'

// Types
interface Timestamp {
  start_time: number
  end_time: number
  description: string
}

interface JobStatus {
  job_id: string
  status: string
  progress: number
  message: string
  result_url: string | null
  timestamps: Timestamp[] | null
  error: string | null
}

interface UploadedVideo {
  job_id: string
  filename: string
  duration: number
  file_size: number
  url: string
}

// API functions
const API_BASE = ''

async function uploadVideo(file: File): Promise<UploadedVideo> {
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

async function startAnalysis(jobId: string, query: string, padding: number): Promise<void> {
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

async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/api/status/${jobId}`)
  if (!res.ok) throw new Error('Failed to get status')
  return res.json()
}

async function deleteJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/api/job/${jobId}`, { method: 'DELETE' })
}

// Format helpers
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Main App
export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('home')

  // Video state
  const [video, setVideo] = useState<UploadedVideo | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Analysis state
  const [query, setQuery] = useState('')
  const [padding, setPadding] = useState(2)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Results
  const [timestamps, setTimestamps] = useState<Timestamp[] | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)

  // Handle file selection
  const handleFileSelect = useCallback(async (file: File) => {
    if (!file.type.startsWith('video/')) {
      setError('Please select a video file')
      return
    }

    setError(null)
    setTimestamps(null)
    setResultUrl(null)
    setStatusMessage('Uploading video...')

    try {
      const uploaded = await uploadVideo(file)
      setVideo(uploaded)
      setStatusMessage('Video uploaded successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setStatusMessage('')
    }
  }, [])

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }

  // Poll for status updates
  useEffect(() => {
    if (!isProcessing || !video) return

    const pollStatus = async () => {
      try {
        const status = await getJobStatus(video.job_id)
        setProgress(status.progress)
        setStatusMessage(status.message)

        if (status.timestamps) {
          setTimestamps(status.timestamps)
        }

        if (status.status === 'complete') {
          setIsProcessing(false)
          if (status.result_url) {
            setResultUrl(`${API_BASE}${status.result_url}`)
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

  // Start analysis
  const handleAnalyze = async () => {
    if (!video || !query.trim()) return

    setError(null)
    setIsProcessing(true)
    setProgress(0)
    setTimestamps(null)
    setResultUrl(null)
    setStatusMessage('Starting analysis...')

    try {
      await startAnalysis(video.job_id, query, padding)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis')
      setIsProcessing(false)
    }
  }

  // Clear video
  const handleClear = async () => {
    if (video) {
      try {
        await deleteJob(video.job_id)
      } catch {
        // Ignore delete errors
      }
    }
    setVideo(null)
    setQuery('')
    setTimestamps(null)
    setResultUrl(null)
    setError(null)
    setStatusMessage('')
    setProgress(0)
  }

  return (
    <div className="app-container">
      {/* Sidebar Trigger */}
      <div
        className="sidebar-trigger"
        onMouseEnter={() => setSidebarOpen(true)}
      >
        <div className="hamburger">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>

      {/* Sidebar */}
      <div
        className={`sidebar ${sidebarOpen ? 'open' : ''}`}
        onMouseLeave={() => setSidebarOpen(false)}
      >
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Scissors size={28} />
            Clip Cutter
          </div>
        </div>

        <nav className="sidebar-nav">
          <div
            className={`nav-item ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => setActiveTab('home')}
          >
            <Home size={20} />
            Home
          </div>
          <div
            className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <History size={20} />
            History
          </div>
          <div
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <Settings size={20} />
            Settings
          </div>
        </nav>

        <div className="sidebar-footer">
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Powered by Gemini AI
          </p>
        </div>
      </div>

      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <h1>Clip Cutter</h1>
          <p>Upload a video and describe what you want to find. AI will analyze and extract matching clips.</p>
        </header>

        {activeTab === 'home' && (
          <div>
            {/* Upload Section */}
            <div className="card">
              <div className="card-header">
                <Upload className="icon" size={24} />
                <h2>Video</h2>
              </div>

              {!video ? (
                <div
                  className={`upload-area ${isDragging ? 'dragging' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Film className="icon" />
                  <h3>Drop your video here</h3>
                  <p>or click to browse</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                    style={{ display: 'none' }}
                  />
                </div>
              ) : (
                <div className="video-preview">
                  <video src={video.url} controls />
                  <div className="video-info">
                    <span className="filename">{video.filename}</span>
                    <span className="meta">
                      {formatDuration(video.duration)} &bull; {formatFileSize(video.file_size)}
                    </span>
                  </div>
                </div>
              )}

              {video && (
                <div className="button-row">
                  <button className="btn btn-secondary" onClick={handleClear}>
                    <Trash2 size={18} />
                    Clear Video
                  </button>
                </div>
              )}
            </div>

            {/* Analysis Section */}
            {video && (
              <div className="card">
                <div className="card-header">
                  <Scissors className="icon" size={24} />
                  <h2>Analysis</h2>
                </div>

                <div className="form-group">
                  <label>What do you want to find?</label>
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="e.g., every time #3 ran a route, all completed passes, every touchdown"
                    disabled={isProcessing}
                  />
                </div>

                <div className="form-group">
                  <label>Clip Padding</label>
                  <div className="slider-container">
                    <div className="slider-header">
                      <span>Extra time before/after each clip</span>
                      <span className="slider-value">{padding}s</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.5"
                      value={padding}
                      onChange={(e) => setPadding(parseFloat(e.target.value))}
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                <div className="button-row">
                  <button
                    className="btn btn-primary btn-large"
                    onClick={handleAnalyze}
                    disabled={isProcessing || !query.trim()}
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 size={20} className="animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Play size={20} />
                        Analyze Video
                      </>
                    )}
                  </button>
                </div>

                {/* Progress */}
                {isProcessing && (
                  <div className="progress-container">
                    <div className="progress-header">
                      <span className="progress-message">{statusMessage}</span>
                      <span className="progress-percent">{Math.round(progress)}%</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div className="status-badge error" style={{ marginTop: 16 }}>
                    <AlertCircle size={16} />
                    {error}
                  </div>
                )}
              </div>
            )}

            {/* Results Section */}
            {timestamps && timestamps.length > 0 && (
              <div className="card">
                <div className="card-header">
                  <CheckCircle className="icon" size={24} />
                  <h2>Found {timestamps.length} Clips</h2>
                </div>

                <div className="timestamps-list">
                  {timestamps.map((ts, i) => (
                    <div key={i} className="timestamp-item">
                      <div className="timestamp-number">{i + 1}</div>
                      <div className="timestamp-content">
                        <div className="timestamp-time">
                          {formatDuration(ts.start_time)} - {formatDuration(ts.end_time)}
                        </div>
                        <div className="timestamp-desc">{ts.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Result Video */}
            {resultUrl && (
              <div className="card">
                <div className="card-header">
                  <Film className="icon" size={24} />
                  <h2>Extracted Clips</h2>
                </div>

                <video
                  className="result-video"
                  src={resultUrl}
                  controls
                />

                <div className="download-section">
                  <a
                    href={resultUrl}
                    download
                    className="btn btn-primary"
                  >
                    <Download size={18} />
                    Download Video
                  </a>
                </div>
              </div>
            )}

            {/* Empty result state */}
            {timestamps && timestamps.length === 0 && !isProcessing && (
              <div className="card">
                <div className="empty-state">
                  <AlertCircle className="icon" />
                  <h3>No clips found</h3>
                  <p>Try adjusting your search query</p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="card">
            <div className="card-header">
              <History className="icon" size={24} />
              <h2>Analysis History</h2>
            </div>
            <div className="empty-state">
              <History className="icon" />
              <h3>Coming Soon</h3>
              <p>Your analysis history will appear here</p>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="card">
            <div className="card-header">
              <Settings className="icon" size={24} />
              <h2>Settings</h2>
            </div>
            <div className="empty-state">
              <Settings className="icon" />
              <h3>Coming Soon</h3>
              <p>Settings will be available here</p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
