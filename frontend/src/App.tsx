import { Header, VideoUpload, AnalysisForm, ResultsList, ResultVideo } from './components'
import { useVideoAnalysis } from './hooks/useVideoAnalysis'
import './styles/globals.css'

export default function App() {
  const {
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
  } = useVideoAnalysis()

  return (
    <div className="app">
      <Header />

      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">AI Video Clip Extraction</h1>
          <p className="page-subtitle">
            Upload football game footage, describe what you're looking for, and let AI find and extract the matching plays.
          </p>
        </div>

        <VideoUpload
          video={video}
          isUploading={isUploading}
          onUpload={uploadVideo}
          onClear={clearVideo}
        />

        {video && (
          <AnalysisForm
            isProcessing={isProcessing}
            progress={progress}
            statusMessage={statusMessage}
            error={error}
            onAnalyze={startAnalysis}
          />
        )}

        {timestamps && <ResultsList timestamps={timestamps} />}

        {resultUrl && <ResultVideo url={resultUrl} />}
      </main>
    </div>
  )
}
