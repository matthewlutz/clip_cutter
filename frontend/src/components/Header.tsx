import { Scissors } from 'lucide-react'

export function Header() {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="logo">
          <div className="logo-icon">
            <Scissors size={20} />
          </div>
          <span>Clip Cutter</span>
        </div>
        <div className="header-badge">Powered by Gemini AI</div>
      </div>
    </header>
  )
}
