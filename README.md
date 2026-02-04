# Clip Cutter

AI-powered video clip extraction tool. Upload a video, describe what you want to find, and get a highlight reel.

## Quick Start

### 1. Start the Backend (Terminal 1)
```bash
cd backend
python main.py
```
Backend runs at http://localhost:8000

### 2. Start the Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```
Frontend runs at http://localhost:5173

### 3. Open the App
Go to http://localhost:5173 in your browser

## Requirements

- Python 3.11+
- Node.js 18+
- FFmpeg (must be in PATH or at C:\ffmpeg\bin\)
- Google Gemini API key (set in `backend/.env`)

## Environment Variables

Create `backend/.env`:
```
GOOGLE_API_KEY=your_gemini_api_key
```

## Tech Stack

- **Frontend**: React + Vite + TypeScript
- **Backend**: FastAPI + Python
- **AI**: Google Gemini 2.0 Flash
- **Video Processing**: FFmpeg
