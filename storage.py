"""Cloudflare R2 storage operations."""

import os
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from config import settings


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
    # Create a path structure: videos/{user_id}/{uuid}_{filename}
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
    """
    Upload a video file to R2.

    Args:
        file_path: Local path to the video file
        r2_key: Key (path) in R2 bucket
        content_type: MIME type of the file

    Returns:
        True if upload succeeded, False otherwise
    """
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


def upload_video_bytes(data: bytes, r2_key: str, content_type: str = "video/mp4") -> bool:
    """
    Upload video data directly from bytes.

    Args:
        data: Video data as bytes
        r2_key: Key (path) in R2 bucket
        content_type: MIME type of the file

    Returns:
        True if upload succeeded, False otherwise
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        client.put_object(
            Bucket=settings.r2_bucket_name,
            Key=r2_key,
            Body=data,
            ContentType=content_type,
        )
        return True
    except ClientError as e:
        print(f"Error uploading to R2: {e}")
        return False


def download_video(r2_key: str, destination_path: str) -> bool:
    """
    Download a video from R2 to a local file.

    Args:
        r2_key: Key (path) in R2 bucket
        destination_path: Local path to save the file

    Returns:
        True if download succeeded, False otherwise
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        client.download_file(
            settings.r2_bucket_name,
            r2_key,
            destination_path,
        )
        return True
    except ClientError as e:
        print(f"Error downloading from R2: {e}")
        return False


def download_video_bytes(r2_key: str) -> Optional[bytes]:
    """
    Download a video from R2 as bytes.

    Args:
        r2_key: Key (path) in R2 bucket

    Returns:
        Video data as bytes, or None if download failed
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        response = client.get_object(
            Bucket=settings.r2_bucket_name,
            Key=r2_key,
        )
        return response["Body"].read()
    except ClientError as e:
        print(f"Error downloading from R2: {e}")
        return None


def delete_video(r2_key: str) -> bool:
    """
    Delete a video from R2.

    Args:
        r2_key: Key (path) in R2 bucket

    Returns:
        True if deletion succeeded, False otherwise
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        client.delete_object(
            Bucket=settings.r2_bucket_name,
            Key=r2_key,
        )
        return True
    except ClientError as e:
        print(f"Error deleting from R2: {e}")
        return False


def delete_videos(r2_keys: list[str]) -> int:
    """
    Delete multiple videos from R2.

    Args:
        r2_keys: List of keys (paths) in R2 bucket

    Returns:
        Number of successfully deleted files
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    if not r2_keys:
        return 0

    try:
        response = client.delete_objects(
            Bucket=settings.r2_bucket_name,
            Delete={
                "Objects": [{"Key": key} for key in r2_keys],
                "Quiet": False,
            },
        )
        deleted = response.get("Deleted", [])
        return len(deleted)
    except ClientError as e:
        print(f"Error deleting from R2: {e}")
        return 0


def generate_presigned_url(r2_key: str, expires_in: int = 3600, for_upload: bool = False) -> Optional[str]:
    """
    Generate a presigned URL for accessing or uploading a video.

    Args:
        r2_key: Key (path) in R2 bucket
        expires_in: URL expiration time in seconds (default 1 hour)
        for_upload: If True, generate URL for upload (PUT), otherwise for download (GET)

    Returns:
        Presigned URL string, or None if generation failed
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        method = "put_object" if for_upload else "get_object"
        url = client.generate_presigned_url(
            ClientMethod=method,
            Params={
                "Bucket": settings.r2_bucket_name,
                "Key": r2_key,
            },
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None


def generate_upload_url(user_id: UUID, filename: str, expires_in: int = 3600) -> tuple[str, str]:
    """
    Generate a presigned URL for direct video upload.

    Args:
        user_id: User ID for organizing storage
        filename: Original filename
        expires_in: URL expiration time in seconds

    Returns:
        Tuple of (presigned_url, r2_key)
    """
    r2_key = generate_video_key(user_id, filename)
    url = generate_presigned_url(r2_key, expires_in, for_upload=True)

    if not url:
        raise RuntimeError("Failed to generate upload URL")

    return url, r2_key


def get_video_url(r2_key: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get a temporary URL for accessing a video.

    Args:
        r2_key: Key (path) in R2 bucket
        expires_in: URL expiration time in seconds

    Returns:
        Presigned URL for downloading the video
    """
    return generate_presigned_url(r2_key, expires_in, for_upload=False)


def video_exists(r2_key: str) -> bool:
    """
    Check if a video exists in R2.

    Args:
        r2_key: Key (path) in R2 bucket

    Returns:
        True if the video exists, False otherwise
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        client.head_object(
            Bucket=settings.r2_bucket_name,
            Key=r2_key,
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        print(f"Error checking video existence: {e}")
        return False


def get_video_metadata(r2_key: str) -> Optional[dict]:
    """
    Get metadata for a video in R2.

    Args:
        r2_key: Key (path) in R2 bucket

    Returns:
        Dictionary with content_length, content_type, last_modified, or None if not found
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    try:
        response = client.head_object(
            Bucket=settings.r2_bucket_name,
            Key=r2_key,
        )
        return {
            "content_length": response.get("ContentLength"),
            "content_type": response.get("ContentType"),
            "last_modified": response.get("LastModified"),
        }
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None
        print(f"Error getting video metadata: {e}")
        return None


def list_user_videos(user_id: UUID, max_keys: int = 1000) -> list[dict]:
    """
    List all videos for a user in R2.

    Args:
        user_id: User ID
        max_keys: Maximum number of keys to return

    Returns:
        List of dictionaries with key, size, and last_modified
    """
    client = get_r2_client()
    if not client:
        raise RuntimeError("R2 storage not configured")

    prefix = f"videos/{user_id}/"

    try:
        response = client.list_objects_v2(
            Bucket=settings.r2_bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys,
        )

        videos = []
        for obj in response.get("Contents", []):
            videos.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"],
            })

        return videos
    except ClientError as e:
        print(f"Error listing videos: {e}")
        return []
