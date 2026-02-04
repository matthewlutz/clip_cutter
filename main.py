"""FastAPI entry point for Clip Cutter."""

import os
import tempfile
from typing import Optional
from uuid import UUID, uuid4

import gradio as gr
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app import create_ui
from auth import (
    get_auth_state,
    get_login_url,
    handle_logout,
    handle_oauth_callback,
    session_manager,
)
from config import settings
from database import (
    create_analysis,
    create_video,
    delete_analysis,
    delete_video as db_delete_video,
    get_analysis,
    get_user_history,
    get_user_videos,
    get_video,
    update_video,
)
from models import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisStatus,
    AuthState,
    HistoryItem,
    Video,
    VideoCreate,
    VideoStatus,
    VideoUpdate,
    VideoUploadResponse,
)
from storage import (
    delete_video as storage_delete_video,
    generate_upload_url,
    get_video_url,
    upload_video,
)


# Create FastAPI app
app = FastAPI(
    title="Clip Cutter API",
    description="API for video clip extraction using AI",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Session Helpers
# =============================================================================

def get_session_id(request: Request) -> str:
    """Get or create a session ID from cookies."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid4())
    return session_id


def get_current_auth(request: Request) -> AuthState:
    """Get current authentication state."""
    session_id = get_session_id(request)
    return get_auth_state(session_id)


def require_auth(request: Request) -> AuthState:
    """Require authentication, raise 401 if not authenticated."""
    auth = get_current_auth(request)
    if not auth.is_authenticated or not auth.user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth


# =============================================================================
# Auth Endpoints
# =============================================================================

@app.get("/auth/login")
async def login(request: Request):
    """Initiate Google OAuth login."""
    # Get the base URL from the request
    base_url = str(request.base_url).rstrip("/")
    login_url = get_login_url(base_url)

    if not login_url:
        raise HTTPException(
            status_code=503,
            detail="Authentication not configured. Please set up Supabase.",
        )

    return RedirectResponse(url=login_url)


@app.get("/auth/callback")
async def auth_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handle OAuth callback."""
    if error:
        return RedirectResponse(url=f"/?error={error}")

    if not code:
        return RedirectResponse(url="/?error=no_code")

    session_id = get_session_id(request)
    auth_state = handle_oauth_callback(code, session_id)

    response = RedirectResponse(url="/")

    if auth_state.is_authenticated:
        # Set session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
        )

    return response


@app.get("/auth/logout")
async def logout(request: Request):
    """Log out the current user."""
    session_id = get_session_id(request)
    handle_logout(session_id)

    response = RedirectResponse(url="/")
    response.delete_cookie("session_id")
    return response


@app.get("/auth/me")
async def get_me(auth: AuthState = Depends(require_auth)):
    """Get the current user."""
    return {"user": auth.user}


@app.get("/auth/status")
async def auth_status(request: Request):
    """Get current authentication status."""
    auth = get_current_auth(request)
    return {
        "is_authenticated": auth.is_authenticated,
        "user": auth.user.model_dump() if auth.user else None,
    }


# =============================================================================
# Video Endpoints
# =============================================================================

@app.post("/api/videos/upload-url", response_model=VideoUploadResponse)
async def get_upload_url(filename: str, auth: AuthState = Depends(require_auth)):
    """Get a presigned URL for direct video upload to R2."""
    if not settings.r2_configured:
        raise HTTPException(status_code=503, detail="Storage not configured")

    if not auth.user:
        raise HTTPException(status_code=401, detail="User not found")

    try:
        upload_url, r2_key = generate_upload_url(auth.user.id, filename)

        # Create video record in database
        video = create_video(VideoCreate(
            user_id=auth.user.id,
            filename=filename,
            r2_key=r2_key,
            file_size=0,  # Will be updated after upload
        ))

        return VideoUploadResponse(
            video_id=video.id,
            upload_url=upload_url,
            expires_in=3600,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/videos/upload")
async def upload_video_file(
    file: UploadFile = File(...),
    auth: AuthState = Depends(require_auth),
):
    """Upload a video file directly (alternative to presigned URL)."""
    if not settings.r2_configured:
        raise HTTPException(status_code=503, detail="Storage not configured")

    if not auth.user:
        raise HTTPException(status_code=401, detail="User not found")

    # Save to temp file
    temp_dir = tempfile.mkdtemp(prefix="upload_")
    temp_path = os.path.join(temp_dir, file.filename or "video.mp4")

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_size = os.path.getsize(temp_path)

        # Generate R2 key and upload
        from storage import generate_video_key
        r2_key = generate_video_key(auth.user.id, file.filename or "video.mp4")

        if not upload_video(temp_path, r2_key):
            raise HTTPException(status_code=500, detail="Failed to upload to storage")

        # Create video record
        video = create_video(VideoCreate(
            user_id=auth.user.id,
            filename=file.filename or "video.mp4",
            r2_key=r2_key,
            file_size=file_size,
        ))

        # Mark as ready
        update_video(video.id, VideoUpdate(status=VideoStatus.READY))

        return {"video_id": str(video.id), "filename": video.filename}

    finally:
        # Cleanup temp file
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/videos")
async def list_videos(auth: AuthState = Depends(require_auth)):
    """List all videos for the current user."""
    if not auth.user:
        raise HTTPException(status_code=401, detail="User not found")

    videos = get_user_videos(auth.user.id)
    return {"videos": [v.model_dump() for v in videos]}


@app.get("/api/videos/{video_id}")
async def get_video_info(video_id: UUID, auth: AuthState = Depends(require_auth)):
    """Get information about a specific video."""
    video = get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not auth.user or video.user_id != auth.user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get download URL
    download_url = get_video_url(video.r2_key) if settings.r2_configured else None

    return {
        "video": video.model_dump(),
        "download_url": download_url,
    }


@app.delete("/api/videos/{video_id}")
async def delete_video_endpoint(video_id: UUID, auth: AuthState = Depends(require_auth)):
    """Delete a video."""
    video = get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not auth.user or video.user_id != auth.user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete from storage
    if settings.r2_configured:
        storage_delete_video(video.r2_key)

    # Delete from database
    db_delete_video(video_id)

    return {"success": True}


# =============================================================================
# Analysis Endpoints
# =============================================================================

@app.get("/api/history")
async def get_history(auth: AuthState = Depends(require_auth)):
    """Get analysis history for the current user."""
    if not auth.user:
        raise HTTPException(status_code=401, detail="User not found")

    history = get_user_history(auth.user.id)
    return {"history": [h.model_dump() for h in history]}


@app.get("/api/analyses/{analysis_id}")
async def get_analysis_info(analysis_id: UUID, auth: AuthState = Depends(require_auth)):
    """Get information about a specific analysis."""
    analysis = get_analysis(analysis_id)

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not auth.user or analysis.user_id != auth.user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get output URL if available
    output_url = None
    if analysis.output_r2_key and settings.r2_configured:
        output_url = get_video_url(analysis.output_r2_key)

    return AnalysisResponse(
        analysis_id=analysis.id,
        video_id=analysis.video_id,
        query=analysis.query,
        timestamps=analysis.timestamps,
        output_url=output_url,
        status=analysis.status,
    )


@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis_endpoint(analysis_id: UUID, auth: AuthState = Depends(require_auth)):
    """Delete an analysis."""
    analysis = get_analysis(analysis_id)

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not auth.user or analysis.user_id != auth.user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete output from storage
    if analysis.output_r2_key and settings.r2_configured:
        storage_delete_video(analysis.output_r2_key)

    # Delete from database
    delete_analysis(analysis_id)

    return {"success": True}


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "gemini_configured": settings.gemini_configured,
        "supabase_configured": settings.supabase_configured,
        "r2_configured": settings.r2_configured,
    }


# =============================================================================
# Mount Gradio App
# =============================================================================

# Create and mount Gradio app
gradio_app = create_ui()
app = gr.mount_gradio_app(app, gradio_app, path="/")


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
