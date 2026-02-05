import { useRef, useState, useCallback } from 'react'
import { Upload, Film, Loader2, Clock, HardDrive, Trash2 } from 'lucide-react'
import type { UploadedVideo } from '../types'
import { formatDuration, formatFileSize, cn } from '../utils/format'

interface VideoUploadProps {
  video: UploadedVideo | null
  isUploading: boolean
  onUpload: (file: File) => void
  onClear: () => void
}

export function VideoUpload({ video, isUploading, onUpload, onClear }: VideoUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) onUpload(file)
    },
    [onUpload]
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) onUpload(file)
    },
    [onUpload]
  )

  return (
    <div className="card animate-fade-in">
      <div className="card-header">
        <div className="card-header-icon">
          <Upload size={20} />
        </div>
        <h2 className="card-title">Video Source</h2>
      </div>

      <div className="card-body">
        {isUploading ? (
          <div className="upload-zone uploading">
            <Loader2 size={48} className="upload-icon animate-spin" />
            <h3 className="upload-title">Uploading video...</h3>
            <p className="upload-subtitle">Please wait while your video is being processed</p>
          </div>
        ) : !video ? (
          <div
            className={cn('upload-zone', isDragging && 'dragging')}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Film size={48} className="upload-icon" />
            <h3 className="upload-title">Drop your video here</h3>
            <p className="upload-subtitle">or click to browse files</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>
        ) : (
          <>
            <div className="video-preview">
              <video src={video.url} controls />
              <div className="video-info">
                <span className="video-filename">{video.filename}</span>
                <div className="video-meta">
                  <span>
                    <Clock size={14} />
                    {formatDuration(video.duration)}
                  </span>
                  <span>
                    <HardDrive size={14} />
                    {formatFileSize(video.file_size)}
                  </span>
                </div>
              </div>
            </div>

            <div className="btn-row">
              <button className="btn btn-secondary" onClick={onClear}>
                <Trash2 size={18} />
                Remove Video
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
