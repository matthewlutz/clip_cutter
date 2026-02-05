"""Pydantic models for Clip Cutter."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Enums
class VideoStatus(str, Enum):
    """Status of a video file."""
    UPLOADING = "uploading"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"


class AnalysisStatus(str, Enum):
    """Status of an analysis job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class ThemeChoice(str, Enum):
    """Theme options."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# Timestamp models
class Timestamp(BaseModel):
    """A single timestamp from video analysis."""
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    description: str = Field(default="", description="Description of what happens")
    play_description: Optional[str] = Field(default=None, description="Detailed play description")
    confidence_score: Optional[int] = Field(default=None, ge=0, le=100, description="Detection confidence")
    camera_angle: Optional[str] = Field(default=None, description="Camera angle (sideline, endzone, etc.)")
    player_jersey: Optional[str] = Field(default=None, description="Player jersey number")
    action_type: Optional[str] = Field(default=None, description="Type of action (catch, run, etc.)")
    verification_status: Optional[str] = Field(default=None, description="Verification status")


class TimestampList(BaseModel):
    """List of timestamps from analysis."""
    timestamps: list[Timestamp] = Field(default_factory=list)


# User models
class UserBase(BaseModel):
    """Base user model."""
    email: str


class User(UserBase):
    """User model with ID."""
    id: UUID
    created_at: datetime
    last_sign_in_at: Optional[datetime] = None


class UserSettings(BaseModel):
    """User settings model."""
    user_id: UUID
    default_padding: float = Field(default=2.0, ge=0, le=10)
    theme: ThemeChoice = ThemeChoice.DARK
    gemini_api_key: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    """Model for updating user settings."""
    default_padding: Optional[float] = Field(default=None, ge=0, le=10)
    theme: Optional[ThemeChoice] = None
    gemini_api_key: Optional[str] = None


# Video models
class VideoBase(BaseModel):
    """Base video model."""
    filename: str
    file_size: int = Field(..., ge=0)
    duration: Optional[float] = Field(default=None, ge=0)


class VideoCreate(VideoBase):
    """Model for creating a video record."""
    user_id: UUID
    r2_key: str


class Video(VideoBase):
    """Video model with all fields."""
    id: UUID
    user_id: UUID
    r2_key: str
    created_at: datetime
    status: VideoStatus = VideoStatus.UPLOADING


class VideoUpdate(BaseModel):
    """Model for updating a video record."""
    status: Optional[VideoStatus] = None
    duration: Optional[float] = Field(default=None, ge=0)


# Analysis models
class AnalysisBase(BaseModel):
    """Base analysis model."""
    query: str = Field(..., min_length=1)


class AnalysisCreate(AnalysisBase):
    """Model for creating an analysis."""
    video_id: UUID
    user_id: UUID


class Analysis(AnalysisBase):
    """Analysis model with all fields."""
    id: UUID
    video_id: UUID
    user_id: UUID
    timestamps: list[Timestamp] = Field(default_factory=list)
    output_r2_key: Optional[str] = None
    created_at: datetime
    status: AnalysisStatus = AnalysisStatus.PENDING


class AnalysisUpdate(BaseModel):
    """Model for updating an analysis."""
    timestamps: Optional[list[Timestamp]] = None
    output_r2_key: Optional[str] = None
    status: Optional[AnalysisStatus] = None


# API response models
class AnalysisResponse(BaseModel):
    """Response model for analysis results."""
    analysis_id: UUID
    video_id: UUID
    query: str
    timestamps: list[Timestamp]
    output_url: Optional[str] = None
    status: AnalysisStatus


class VideoUploadResponse(BaseModel):
    """Response model for video upload."""
    video_id: UUID
    upload_url: str
    expires_in: int = Field(default=3600, description="URL expiration in seconds")


class HistoryItem(BaseModel):
    """Model for history list items."""
    id: UUID
    video_filename: str
    query: str
    clips_found: int
    status: AnalysisStatus
    created_at: datetime


# Auth models
class AuthState(BaseModel):
    """Authentication state."""
    is_authenticated: bool = False
    user: Optional[User] = None
    access_token: Optional[str] = None


class LoginResponse(BaseModel):
    """Response from login."""
    success: bool
    user: Optional[User] = None
    error: Optional[str] = None
