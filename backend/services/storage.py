"""Cloudflare R2 storage operations."""

import os
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from core.config import settings


def get_r2_client():
    """Get boto3 client configured for Cloudflare R2."""
    if not settings.r2_configured:
        return None

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def generate_video_key(user_id: UUID, filename: str) -> str:
    """Generate a unique R2 key for a video file."""
    unique_id = uuid4().hex[:8]
    safe_filename = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
    return f"videos/{user_id}/{unique_id}_{safe_filename}"


def generate_output_key(user_id: UUID, video_id: UUID, query: str) -> str:
    """Generate a unique R2 key for analysis output."""
    unique_id = uuid4().hex[:8]
    safe_query = "".join(c if c.isalnum() else "_" for c in query[:30])
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    return f"outputs/{user_id}/{video_id}/{timestamp}_{safe_query}_{unique_id}.mp4"


def upload_video(file_path: str, r2_key: str, content_type: str = "video/mp4") -> bool:
    """Upload a video file to R2."""
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        with open(file_path, "rb") as f:
            client.upload_fileobj(
                f,
                settings.r2_bucket_name,
                r2_key,
                ExtraArgs={"ContentType": content_type},
            )
        return True
    except ClientError as e:
        print(f"Error uploading to R2: {e}")
        return False


def download_video(r2_key: str, destination_path: str) -> bool:
    """Download a video from R2 to a local file."""
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        client.download_file(settings.r2_bucket_name, r2_key, destination_path)
        return True
    except ClientError as e:
        print(f"Error downloading from R2: {e}")
        return False


def delete_video(r2_key: str) -> bool:
    """Delete a video from R2."""
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        client.delete_object(Bucket=settings.r2_bucket_name, Key=r2_key)
        return True
    except ClientError as e:
        print(f"Error deleting from R2: {e}")
        return False


def generate_presigned_url(r2_key: str, expires_in: int = 3600, for_upload: bool = False) -> Optional[str]:
    """Generate a presigned URL for accessing or uploading a video."""
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        method = "put_object" if for_upload else "get_object"
        url = client.generate_presigned_url(
            ClientMethod=method,
            Params={"Bucket": settings.r2_bucket_name, "Key": r2_key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None


def get_video_url(r2_key: str, expires_in: int = 3600) -> Optional[str]:
    """Get a temporary URL for accessing a video."""
    return generate_presigned_url(r2_key, expires_in, for_upload=False)
