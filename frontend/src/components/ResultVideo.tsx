import { Film, Download } from 'lucide-react'

interface ResultVideoProps {
  url: string
}

export function ResultVideo({ url }: ResultVideoProps) {
  return (
    <div className="card animate-fade-in">
      <div className="card-header">
        <div className="card-header-icon">
          <Film size={20} />
        </div>
        <h2 className="card-title">Extracted Highlights</h2>
      </div>

      <div className="card-body">
        <video className="result-video" src={url} controls />

        <div className="download-row">
          <a href={url} download className="btn btn-primary">
            <Download size={18} />
            Download Video
          </a>
        </div>
      </div>
    </div>
  )
}
