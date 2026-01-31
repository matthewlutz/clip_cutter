"""Video analysis using Gemini 2.0 Flash."""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import ffmpeg
from google import genai
from google.genai import types
from dotenv import load_dotenv

from clipper import FFMPEG_PATH, FFPROBE_PATH

load_dotenv()

# Maximum file size for Gemini (1.8GB to be safe)
MAX_FILE_SIZE_BYTES = 1.8 * 1024 * 1024 * 1024

# Target segment size (1.5GB to have margin)
TARGET_SEGMENT_SIZE_BYTES = 1.5 * 1024 * 1024 * 1024


def get_client() -> genai.Client:
    """Create and return a Gemini client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


def get_video_duration_and_size(video_path: str) -> tuple[float, int]:
    """Get video duration in seconds and file size in bytes."""
    probe = ffmpeg.probe(video_path, cmd=FFPROBE_PATH)
    duration = float(probe["format"]["duration"])
    size = int(probe["format"]["size"])
    return duration, size


def split_video_into_segments(video_path: str, segment_duration: float, temp_dir: str,
                               progress_callback=None, cancel_event=None) -> list[tuple[str, float]]:
    """
    Split a video into segments of specified duration.

    Returns:
        List of tuples (segment_path, start_offset_seconds)
    """
    probe = ffmpeg.probe(video_path, cmd=FFPROBE_PATH)
    total_duration = float(probe["format"]["duration"])

    segments = []
    current_start = 0.0
    segment_index = 0

    while current_start < total_duration:
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("Cancelled by user")

        segment_path = os.path.join(temp_dir, f"segment_{segment_index:03d}.mp4")
        segment_end = min(current_start + segment_duration, total_duration)
        actual_duration = segment_end - current_start

        if progress_callback:
            pct = current_start / total_duration
            progress_callback(0.02 + pct * 0.08, f"Splitting video: segment {segment_index + 1}...")

        print(f"Creating segment {segment_index}: {current_start:.1f}s - {segment_end:.1f}s")

        # Extract segment using ffmpeg
        (
            ffmpeg
            .input(video_path, ss=current_start, t=actual_duration)
            .output(
                segment_path,
                c="copy",
                avoid_negative_ts="make_zero",
            )
            .overwrite_output()
            .run(cmd=FFMPEG_PATH, quiet=True)
        )

        segments.append((segment_path, current_start))
        current_start = segment_end
        segment_index += 1

    return segments


def upload_video(client: genai.Client, video_path: str, progress_callback=None, cancel_event=None) -> types.File:
    """Upload a video file to Gemini and wait for processing."""
    print(f"Uploading video: {video_path}")

    # Check for cancellation before starting
    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Cancelled by user")

    video_file = client.files.upload(file=video_path)
    print(f"Upload started: {video_file.name}")

    # Wait for video processing to complete
    poll_count = 0
    while video_file.state == types.FileState.PROCESSING:
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            print("Upload cancelled, cleaning up...")
            try:
                client.files.delete(name=video_file.name)
            except:
                pass
            raise InterruptedError("Cancelled by user")

        poll_count += 1
        print(f"Processing video... (attempt {poll_count})")
        time.sleep(3)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == types.FileState.FAILED:
        raise ValueError(f"Video processing failed: {video_file.name}")

    print(f"Video ready: {video_file.name}")
    return video_file


def analyze_single_segment(client: genai.Client, video_path: str, query: str,
                           time_offset: float = 0.0, cancel_event=None) -> list[dict]:
    """Analyze a single video segment and return timestamps adjusted by offset."""

    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Cancelled by user")

    video_file = upload_video(client, video_path, cancel_event=cancel_event)

    if cancel_event and cancel_event.is_set():
        try:
            client.files.delete(name=video_file.name)
        except:
            pass
        return []

    prompt = f"""Analyze this football video carefully. Find every instance where: {query}

For each instance found, provide the timestamps in seconds.

IMPORTANT: Return ONLY a valid JSON array with no additional text. Each object must have:
- "start_time": number (timestamp in seconds when the action begins)
- "end_time": number (timestamp in seconds when the action ends)
- "description": string (brief description of what happens)

If no instances are found, return an empty array: []

Example format:
[
  {{"start_time": 12.5, "end_time": 15.0, "description": "Player #3 runs a slant route"}},
  {{"start_time": 45.2, "end_time": 48.7, "description": "Player #3 runs a go route"}}
]

Return ONLY the JSON array, no other text."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=video_file.uri,
                        mime_type=video_file.mime_type,
                    ),
                    types.Part.from_text(text=prompt),
                ],
            ),
        ],
    )

    # Parse the response
    response_text = response.text.strip()

    # Clean up the uploaded file
    try:
        client.files.delete(name=video_file.name)
    except Exception as e:
        print(f"Warning: Could not delete uploaded file: {e}")

    # Try to extract JSON from the response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        timestamps = json.loads(response_text)

        if not isinstance(timestamps, list):
            print(f"Unexpected response format: {response_text}")
            return []

        # Validate, clean, and adjust timestamps by offset
        valid_timestamps = []
        for item in timestamps:
            if isinstance(item, dict) and "start_time" in item and "end_time" in item:
                valid_timestamps.append({
                    "start_time": float(item["start_time"]) + time_offset,
                    "end_time": float(item["end_time"]) + time_offset,
                    "description": item.get("description", ""),
                })

        return valid_timestamps

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response was: {response_text}")
        return []


def analyze_video(video_path: str, query: str, progress_callback=None, cancel_event=None) -> list[dict]:
    """
    Analyze a video using Gemini 2.0 Flash and extract timestamps.
    Automatically segments large videos.

    Args:
        video_path: Path to the video file
        query: Natural language query describing what to find
        progress_callback: Optional callback for progress updates
        cancel_event: Optional threading.Event for cancellation

    Returns:
        List of dictionaries with start_time, end_time, and description
    """
    client = get_client()

    # Get video info
    duration, file_size = get_video_duration_and_size(video_path)

    # Check if we need to segment
    if file_size <= MAX_FILE_SIZE_BYTES:
        # Small enough to process directly
        if progress_callback:
            progress_callback(0.1, "Uploading video to Gemini...")

        video_file = upload_video(client, video_path, progress_callback, cancel_event)

        if cancel_event and cancel_event.is_set():
            try:
                client.files.delete(name=video_file.name)
            except:
                pass
            return []

        if progress_callback:
            progress_callback(0.4, "Analyzing video...")

        return analyze_single_segment(client, video_path, query, time_offset=0.0, cancel_event=cancel_event)

    # Need to segment the video
    print(f"Video is {file_size / (1024**3):.2f}GB, segmenting for processing...")

    # Calculate segment duration based on file size and target
    # Estimate: segment_duration = (target_size / file_size) * total_duration
    segment_duration = (TARGET_SEGMENT_SIZE_BYTES / file_size) * duration
    # Ensure minimum 60 seconds, maximum 10 minutes per segment
    segment_duration = max(60, min(600, segment_duration))

    num_segments = int(duration / segment_duration) + 1
    print(f"Will create ~{num_segments} segments of ~{segment_duration:.0f}s each")

    if progress_callback:
        progress_callback(0.02, f"Splitting video into {num_segments} segments...")

    # Create temp directory for segments
    temp_dir = tempfile.mkdtemp(prefix="video_segments_")

    try:
        # Split video
        segments = split_video_into_segments(
            video_path, segment_duration, temp_dir,
            progress_callback=progress_callback, cancel_event=cancel_event
        )

        if cancel_event and cancel_event.is_set():
            return []

        # Analyze each segment
        all_timestamps = []
        total_segments = len(segments)

        for i, (segment_path, time_offset) in enumerate(segments):
            if cancel_event and cancel_event.is_set():
                return []

            if progress_callback:
                # Progress: 0.1 to 0.9 for segment analysis
                base_progress = 0.1 + (i / total_segments) * 0.8
                progress_callback(base_progress, f"Analyzing segment {i + 1}/{total_segments}...")

            print(f"\nAnalyzing segment {i + 1}/{total_segments} (offset: {time_offset:.1f}s)")

            segment_timestamps = analyze_single_segment(
                client, segment_path, query,
                time_offset=time_offset, cancel_event=cancel_event
            )

            all_timestamps.extend(segment_timestamps)
            print(f"Found {len(segment_timestamps)} instances in segment {i + 1}")

        if progress_callback:
            progress_callback(1.0, f"Found {len(all_timestamps)} total instances")

        # Sort by start time
        all_timestamps.sort(key=lambda x: x["start_time"])

        return all_timestamps

    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {e}")


if __name__ == "__main__":
    # Test with a sample video
    import sys

    if len(sys.argv) < 3:
        print("Usage: python analyzer.py <video_path> <query>")
        sys.exit(1)

    video_path = sys.argv[1]
    query = sys.argv[2]

    results = analyze_video(video_path, query)
    print(json.dumps(results, indent=2))
