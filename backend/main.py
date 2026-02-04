"""FastAPI backend for Clip Cutter."""

import os
import shutil
import tempfile
import asyncio
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from analyzer import analyze_video
from clipper import extract_clips, get_video_info

load_dotenv()

app = FastAPI(title="Clip Cutter API", version="1.0.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active jobs and their progress
jobs: dict[str, dict] = {}

# Temp directory for processing
TEMP_DIR = Path(tempfile.gettempdir()) / "clip_cutter"
TEMP_DIR.mkdir(exist_ok=True)


class AnalyzeRequest(BaseModel):
    query: str
    padding: float = 2.0


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, uploading, analyzing, extracting, complete, error
    progress: float  # 0-100
    message: str
    result_url: Optional[str] = None
    timestamps: Optional[list] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Clip Cutter API", "version": "1.0.0"}


@app.get("/health")
async def health():
    api_key = os.getenv("GOOGLE_API_KEY")
    return {
        "status": "healthy",
        "gemini_configured": bool(api_key),
    }


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file and return a job ID."""
    job_id = str(uuid4())
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    # Save uploaded file
    file_path = job_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Get video info
    try:
        info = get_video_info(str(file_path))
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")

    # Initialize job
    jobs[job_id] = {
        "status": "uploaded",
        "progress": 0,
        "message": "Video uploaded successfully",
        "file_path": str(file_path),
        "filename": file.filename,
        "duration": info.get("duration", 0),
        "file_size": info.get("size", 0),
        "result_path": None,
        "timestamps": None,
        "error": None,
    }

    return {
        "job_id": job_id,
        "filename": file.filename,
        "duration": info.get("duration", 0),
        "file_size": info.get("size", 0),
    }


@app.post("/api/analyze/{job_id}")
async def analyze(job_id: str, request: AnalyzeRequest):
    """Start analyzing a video."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] not in ["uploaded", "complete", "error"]:
        raise HTTPException(status_code=400, detail="Job is already processing")

    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    # Reset job state for re-analysis
    job["status"] = "analyzing"
    job["progress"] = 0
    job["message"] = "Starting analysis..."
    job["error"] = None
    job["timestamps"] = None
    job["result_path"] = None
    job["query"] = request.query
    job["padding"] = request.padding

    # Start processing in background
    asyncio.create_task(process_video(job_id))

    return {"job_id": job_id, "status": "analyzing"}


async def process_video(job_id: str):
    """Process video in background."""
    job = jobs[job_id]
    video_path = job["file_path"]
    query = job["query"]
    padding = job["padding"]

    try:
        # Progress callback for analysis
        def analysis_progress(pct: float, msg: str):
            job["progress"] = pct * 60  # Analysis is 0-60%
            job["message"] = msg

        # Run analysis in thread pool to not block
        loop = asyncio.get_event_loop()
        timestamps = await loop.run_in_executor(
            None,
            lambda: analyze_video(video_path, query, progress_callback=analysis_progress)
        )

        if not timestamps:
            job["status"] = "complete"
            job["progress"] = 100
            job["message"] = "No matching clips found"
            job["timestamps"] = []
            return

        job["timestamps"] = timestamps
        job["status"] = "extracting"
        job["message"] = f"Found {len(timestamps)} clips. Extracting..."

        # Progress callback for extraction
        def clip_progress(pct: float, msg: str):
            job["progress"] = 60 + pct * 40  # Extraction is 60-100%
            job["message"] = msg

        # Create output path
        job_dir = Path(video_path).parent
        output_path = job_dir / f"highlights_{job_id}.mp4"

        # Extract clips
        await loop.run_in_executor(
            None,
            lambda: extract_clips(
                video_path,
                timestamps,
                output_path=str(output_path),
                padding=padding,
                progress_callback=clip_progress,
            )
        )

        job["status"] = "complete"
        job["progress"] = 100
        job["message"] = f"Successfully extracted {len(timestamps)} clips"
        job["result_path"] = str(output_path)

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        job["message"] = f"Error: {str(e)}"
        print(f"Error processing job {job_id}: {e}")
        import traceback
        traceback.print_exc()


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        result_url=f"/api/download/{job_id}" if job.get("result_path") else None,
        timestamps=job.get("timestamps"),
        error=job.get("error"),
    )


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the processed video."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if not job.get("result_path") or not os.path.exists(job["result_path"]):
        raise HTTPException(status_code=404, detail="Result not available")

    return FileResponse(
        job["result_path"],
        media_type="video/mp4",
        filename=f"clips_{job['filename']}",
    )


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Delete job directory
    job_dir = Path(job["file_path"]).parent
    shutil.rmtree(job_dir, ignore_errors=True)

    # Remove from jobs dict
    del jobs[job_id]

    return {"success": True}


@app.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket for real-time progress updates."""
    await websocket.accept()

    if job_id not in jobs:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    try:
        last_progress = -1
        while True:
            job = jobs.get(job_id)
            if not job:
                await websocket.send_json({"error": "Job deleted"})
                break

            # Send update if progress changed
            if job["progress"] != last_progress:
                last_progress = job["progress"]
                await websocket.send_json({
                    "status": job["status"],
                    "progress": job["progress"],
                    "message": job["message"],
                    "timestamps": job.get("timestamps"),
                    "result_url": f"/api/download/{job_id}" if job.get("result_path") else None,
                    "error": job.get("error"),
                })

            # Check if complete
            if job["status"] in ["complete", "error"]:
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
