import { useState } from 'react'
import { Sparkles, Play, Loader2, AlertCircle } from 'lucide-react'

interface AnalysisFormProps {
  isProcessing: boolean
  progress: number
  statusMessage: string
  error: string | null
  onAnalyze: (query: string, padding: number) => void
}

export function AnalysisForm({
  isProcessing,
  progress,
  statusMessage,
  error,
  onAnalyze,
}: AnalysisFormProps) {
  const [query, setQuery] = useState('')
  const [padding, setPadding] = useState(2)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onAnalyze(query, padding)
    }
  }

  return (
    <div className="card animate-fade-in">
      <div className="card-header">
        <div className="card-header-icon">
          <Sparkles size={20} />
        </div>
        <h2 className="card-title">AI Analysis</h2>
      </div>

      <div className="card-body">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">What do you want to find?</label>
            <textarea
              className="form-textarea"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., every time #17 catches a pass, all touchdown plays, completed passes over 20 yards"
              disabled={isProcessing}
              rows={3}
            />
          </div>

          <div className="slider-group">
            <div className="slider-header">
              <span className="slider-label">Clip padding (extra time before/after)</span>
              <span className="slider-value">{padding}s</span>
            </div>
            <input
              type="range"
              className="slider"
              min="0"
              max="10"
              step="0.5"
              value={padding}
              onChange={(e) => setPadding(parseFloat(e.target.value))}
              disabled={isProcessing}
            />
          </div>

          <div className="btn-row">
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={isProcessing || !query.trim()}
            >
              {isProcessing ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Play size={20} />
                  Analyze Video
                </>
              )}
            </button>
          </div>
        </form>

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

        {error && (
          <div className="alert alert-error" style={{ marginTop: 20 }}>
            <AlertCircle size={20} className="alert-icon" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  )
}
