import { CheckCircle, AlertCircle } from 'lucide-react'
import type { Timestamp } from '../types'
import { formatDuration, cn } from '../utils/format'

interface ResultsListProps {
  timestamps: Timestamp[]
}

export function ResultsList({ timestamps }: ResultsListProps) {
  if (timestamps.length === 0) {
    return (
      <div className="card animate-fade-in">
        <div className="empty-state">
          <AlertCircle size={48} className="empty-icon" />
          <h3 className="empty-title">No clips found</h3>
          <p className="empty-text">Try adjusting your search query or using different keywords</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card animate-fade-in">
      <div className="card-header">
        <div className="card-header-icon">
          <CheckCircle size={20} />
        </div>
        <h2 className="card-title">Found {timestamps.length} Clips</h2>
      </div>

      <div className="card-body">
        <div className="results-list">
          {timestamps.map((ts, i) => (
            <div key={i} className="result-item">
              <div className="result-index">{i + 1}</div>
              <div className="result-content">
                <div className="result-header">
                  <span className="result-time">
                    {formatDuration(ts.start_time)} - {formatDuration(ts.end_time)}
                  </span>
                  {ts.confidence_score && (
                    <span className="result-confidence">
                      {ts.confidence_score}% confidence
                    </span>
                  )}
                </div>
                <p className="result-description">
                  {ts.play_description || ts.description || 'No description'}
                </p>
                {(ts.player_jersey || ts.action_type || ts.verification_status) && (
                  <div className="result-tags">
                    {ts.player_jersey && <span className="tag">{ts.player_jersey}</span>}
                    {ts.action_type && <span className="tag">{ts.action_type}</span>}
                    {ts.verification_status === 'verified' && (
                      <span className={cn('tag', 'tag-verified')}>verified</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
