"""Database operations using Supabase."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import create_client, Client

from core.config import settings
from models.schemas import (
    Analysis,
    AnalysisCreate,
    AnalysisStatus,
    AnalysisUpdate,
    HistoryItem,
    Timestamp,
    User,
    UserSettings,
    UserSettingsUpdate,
    Video,
    VideoCreate,
    VideoStatus,
    VideoUpdate,
)


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client if configured."""
    if not settings.supabase_configured:
        return None
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_service_client() -> Optional[Client]:
    """Get Supabase client with service role (admin) permissions."""
    if not settings.supabase_configured or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# =============================================================================
# User Settings Operations
# =============================================================================

def get_user_settings(user_id: UUID) -> Optional[UserSettings]:
    """Get settings for a user."""
    client = get_supabase_client()
    if not client:
        return None

    result = client.table("user_settings").select("*").eq("user_id", str(user_id)).execute()

    if result.data:
        row = result.data[0]
        return UserSettings(
            user_id=UUID(row["user_id"]),
            default_padding=row.get("default_padding", 2.0),
            theme=row.get("theme", "dark"),
            gemini_api_key=row.get("gemini_api_key"),
        )
    return None


def get_or_create_user_settings(user_id: UUID) -> UserSettings:
    """Get user settings, creating defaults if they don't exist."""
    existing = get_user_settings(user_id)
    if existing:
        return existing

    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase not configured")

    default_settings = UserSettings(user_id=user_id)
    client.table("user_settings").insert({
        "user_id": str(user_id),
        "default_padding": default_settings.default_padding,
        "theme": default_settings.theme.value,
    }).execute()

    return default_settings


# =============================================================================
# Video Operations
# =============================================================================

def create_video(video_data: VideoCreate) -> Video:
    """Create a new video record."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase not configured")

    result = client.table("videos").insert({
        "user_id": str(video_data.user_id),
        "filename": video_data.filename,
        "r2_key": video_data.r2_key,
        "file_size": video_data.file_size,
        "duration": video_data.duration,
        "status": VideoStatus.UPLOADING.value,
    }).execute()

    row = result.data[0]
    return Video(
        id=UUID(row["id"]),
        user_id=UUID(row["user_id"]),
        filename=row["filename"],
        r2_key=row["r2_key"],
        file_size=row["file_size"],
        duration=row.get("duration"),
        created_at=datetime.fromisoformat(row["created_at"]),
        status=VideoStatus(row["status"]),
    )


def get_video(video_id: UUID) -> Optional[Video]:
    """Get a video by ID."""
    client = get_supabase_client()
    if not client:
        return None

    result = client.table("videos").select("*").eq("id", str(video_id)).execute()

    if result.data:
        row = result.data[0]
        return Video(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            filename=row["filename"],
            r2_key=row["r2_key"],
            file_size=row["file_size"],
            duration=row.get("duration"),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=VideoStatus(row["status"]),
        )
    return None


def get_user_videos(user_id: UUID, limit: int = 50) -> list[Video]:
    """Get all videos for a user."""
    client = get_supabase_client()
    if not client:
        return []

    result = (
        client.table("videos")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [
        Video(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            filename=row["filename"],
            r2_key=row["r2_key"],
            file_size=row["file_size"],
            duration=row.get("duration"),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=VideoStatus(row["status"]),
        )
        for row in result.data
    ]


# =============================================================================
# Analysis Operations
# =============================================================================

def create_analysis(analysis_data: AnalysisCreate) -> Analysis:
    """Create a new analysis record."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase not configured")

    result = client.table("analyses").insert({
        "video_id": str(analysis_data.video_id),
        "user_id": str(analysis_data.user_id),
        "query": analysis_data.query,
        "timestamps": [],
        "status": AnalysisStatus.PENDING.value,
    }).execute()

    row = result.data[0]
    return Analysis(
        id=UUID(row["id"]),
        video_id=UUID(row["video_id"]),
        user_id=UUID(row["user_id"]),
        query=row["query"],
        timestamps=[],
        output_r2_key=row.get("output_r2_key"),
        created_at=datetime.fromisoformat(row["created_at"]),
        status=AnalysisStatus(row["status"]),
    )


def get_analysis(analysis_id: UUID) -> Optional[Analysis]:
    """Get an analysis by ID."""
    client = get_supabase_client()
    if not client:
        return None

    result = client.table("analyses").select("*").eq("id", str(analysis_id)).execute()

    if result.data:
        row = result.data[0]
        timestamps = [Timestamp(**ts) for ts in (row.get("timestamps") or [])]
        return Analysis(
            id=UUID(row["id"]),
            video_id=UUID(row["video_id"]),
            user_id=UUID(row["user_id"]),
            query=row["query"],
            timestamps=timestamps,
            output_r2_key=row.get("output_r2_key"),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=AnalysisStatus(row["status"]),
        )
    return None


def get_user_history(user_id: UUID, limit: int = 50) -> list[HistoryItem]:
    """Get analysis history for a user with video info."""
    client = get_supabase_client()
    if not client:
        return []

    result = (
        client.table("analyses")
        .select("id, query, timestamps, status, created_at, videos(filename)")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    history = []
    for row in result.data:
        video_info = row.get("videos", {})
        timestamps = row.get("timestamps") or []
        history.append(HistoryItem(
            id=UUID(row["id"]),
            video_filename=video_info.get("filename", "Unknown"),
            query=row["query"],
            clips_found=len(timestamps),
            status=AnalysisStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        ))

    return history
