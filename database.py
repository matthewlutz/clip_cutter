"""Database operations using Supabase."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import create_client, Client

from config import settings
from models import (
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
# User Operations
# =============================================================================

def get_user_by_id(user_id: UUID) -> Optional[User]:
    """Get a user by their ID."""
    client = get_supabase_client()
    if not client:
        return None

    result = client.auth.admin.get_user_by_id(str(user_id))
    if result and result.user:
        return User(
            id=UUID(result.user.id),
            email=result.user.email,
            created_at=result.user.created_at,
            last_sign_in_at=result.user.last_sign_in_at,
        )
    return None


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
            theme=row.get("theme", "light"),
            gemini_api_key=row.get("gemini_api_key"),
        )
    return None


def create_user_settings(user_id: UUID) -> UserSettings:
    """Create default settings for a new user."""
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


def update_user_settings(user_id: UUID, updates: UserSettingsUpdate) -> Optional[UserSettings]:
    """Update user settings."""
    client = get_supabase_client()
    if not client:
        return None

    update_data = {}
    if updates.default_padding is not None:
        update_data["default_padding"] = updates.default_padding
    if updates.theme is not None:
        update_data["theme"] = updates.theme.value
    if updates.gemini_api_key is not None:
        update_data["gemini_api_key"] = updates.gemini_api_key

    if update_data:
        client.table("user_settings").update(update_data).eq("user_id", str(user_id)).execute()

    return get_user_settings(user_id)


def get_or_create_user_settings(user_id: UUID) -> UserSettings:
    """Get user settings, creating defaults if they don't exist."""
    existing = get_user_settings(user_id)
    if existing:
        return existing
    return create_user_settings(user_id)


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


def update_video(video_id: UUID, updates: VideoUpdate) -> Optional[Video]:
    """Update a video record."""
    client = get_supabase_client()
    if not client:
        return None

    update_data = {}
    if updates.status is not None:
        update_data["status"] = updates.status.value
    if updates.duration is not None:
        update_data["duration"] = updates.duration

    if update_data:
        client.table("videos").update(update_data).eq("id", str(video_id)).execute()

    return get_video(video_id)


def delete_video(video_id: UUID) -> bool:
    """Delete a video record."""
    client = get_supabase_client()
    if not client:
        return False

    client.table("videos").delete().eq("id", str(video_id)).execute()
    return True


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
        timestamps = [
            Timestamp(**ts) for ts in (row.get("timestamps") or [])
        ]
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


def get_user_analyses(user_id: UUID, limit: int = 50) -> list[Analysis]:
    """Get all analyses for a user."""
    client = get_supabase_client()
    if not client:
        return []

    result = (
        client.table("analyses")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [
        Analysis(
            id=UUID(row["id"]),
            video_id=UUID(row["video_id"]),
            user_id=UUID(row["user_id"]),
            query=row["query"],
            timestamps=[Timestamp(**ts) for ts in (row.get("timestamps") or [])],
            output_r2_key=row.get("output_r2_key"),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=AnalysisStatus(row["status"]),
        )
        for row in result.data
    ]


def update_analysis(analysis_id: UUID, updates: AnalysisUpdate) -> Optional[Analysis]:
    """Update an analysis record."""
    client = get_supabase_client()
    if not client:
        return None

    update_data = {}
    if updates.timestamps is not None:
        update_data["timestamps"] = [ts.model_dump() for ts in updates.timestamps]
    if updates.output_r2_key is not None:
        update_data["output_r2_key"] = updates.output_r2_key
    if updates.status is not None:
        update_data["status"] = updates.status.value

    if update_data:
        client.table("analyses").update(update_data).eq("id", str(analysis_id)).execute()

    return get_analysis(analysis_id)


def delete_analysis(analysis_id: UUID) -> bool:
    """Delete an analysis record."""
    client = get_supabase_client()
    if not client:
        return False

    client.table("analyses").delete().eq("id", str(analysis_id)).execute()
    return True


# =============================================================================
# History Operations
# =============================================================================

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


# =============================================================================
# SQL Schema (for reference - run in Supabase SQL Editor)
# =============================================================================

SCHEMA_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Videos table
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    r2_key TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    duration FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'uploading' CHECK (status IN ('uploading', 'ready', 'processing', 'error'))
);

-- Analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    timestamps JSONB DEFAULT '[]',
    output_r2_key TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'complete', 'failed'))
);

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    default_padding FLOAT DEFAULT 2.0,
    theme TEXT DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'system')),
    gemini_api_key TEXT
);

-- Row Level Security (RLS) policies
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Videos: users can only access their own videos
CREATE POLICY "Users can view own videos" ON videos
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own videos" ON videos
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own videos" ON videos
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own videos" ON videos
    FOR DELETE USING (auth.uid() = user_id);

-- Analyses: users can only access their own analyses
CREATE POLICY "Users can view own analyses" ON analyses
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analyses" ON analyses
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own analyses" ON analyses
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own analyses" ON analyses
    FOR DELETE USING (auth.uid() = user_id);

-- User settings: users can only access their own settings
CREATE POLICY "Users can view own settings" ON user_settings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own settings" ON user_settings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own settings" ON user_settings
    FOR UPDATE USING (auth.uid() = user_id);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_video_id ON analyses(video_id);
"""
