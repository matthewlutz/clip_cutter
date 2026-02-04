"""Video clip extraction using FFmpeg."""

import os
import shutil
import tempfile
import ffmpeg
from pathlib import Path

# FFmpeg executable paths - use explicit path on Windows if not in PATH
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe" if os.name == "nt" else "ffmpeg"
FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe" if os.name == "nt" else "ffprobe"

# Fall back to PATH if explicit path doesn't exist
if not os.path.exists(FFMPEG_PATH):
    FFMPEG_PATH = "ffmpeg"
if not os.path.exists(FFPROBE_PATH):
    FFPROBE_PATH = "ffprobe"


def extract_clips(
    video_path: str,
    timestamps: list[dict],
    output_path: str = None,
    padding: float = 2.0,
    progress_callback=None,
) -> str:
    """
    Extract clips from a video based on timestamps and concatenate them.

    Args:
        video_path: Path to the source video
        timestamps: List of dicts with start_time and end_time (in seconds)
        output_path: Path for the output video (auto-generated if None)
        padding: Seconds to add before/after each clip for context
        progress_callback: Optional callback for progress updates

    Returns:
        Path to the concatenated output video
    """
    if not timestamps:
        raise ValueError("No timestamps provided")

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Get video duration to clamp timestamps
    probe = ffmpeg.probe(str(video_path), cmd=FFPROBE_PATH)
    duration = float(probe["format"]["duration"])

    # Generate output path if not provided
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_clips{video_path.suffix}"
    output_path = Path(output_path)

    # Create temp directory for individual clips
    temp_dir = tempfile.mkdtemp(prefix="video_clips_")
    clip_paths = []

    try:
        total_clips = len(timestamps)

        for i, ts in enumerate(timestamps):
            if progress_callback:
                progress_callback(
                    (i / total_clips) * 0.8,
                    f"Extracting clip {i + 1}/{total_clips}..."
                )

            # Apply padding and clamp to video bounds
            start = max(0, ts["start_time"] - padding)
            end = min(duration, ts["end_time"] + padding)
            clip_duration = end - start

            if clip_duration <= 0:
                print(f"Skipping invalid clip: {ts}")
                continue

            clip_path = Path(temp_dir) / f"clip_{i:04d}.mp4"
            clip_paths.append(clip_path)

            # Extract clip using FFmpeg
            (
                ffmpeg
                .input(str(video_path), ss=start, t=clip_duration)
                .output(
                    str(clip_path),
                    c="copy",  # Copy codec for speed (no re-encoding)
                    avoid_negative_ts="make_zero",
                )
                .overwrite_output()
                .run(cmd=FFMPEG_PATH, quiet=True)
            )

        if not clip_paths:
            raise ValueError("No valid clips extracted")

        if progress_callback:
            progress_callback(0.85, "Concatenating clips...")

        # Concatenate all clips
        if len(clip_paths) == 1:
            # Just copy the single clip
            import shutil
            shutil.copy(clip_paths[0], output_path)
        else:
            # Create concat file list
            concat_file = Path(temp_dir) / "concat.txt"
            with open(concat_file, "w") as f:
                for clip_path in clip_paths:
                    # FFmpeg concat requires forward slashes and escaped quotes
                    safe_path = str(clip_path).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")

            # Concatenate using FFmpeg concat demuxer
            (
                ffmpeg
                .input(str(concat_file), format="concat", safe=0)
                .output(str(output_path), c="copy")
                .overwrite_output()
                .run(cmd=FFMPEG_PATH, quiet=True)
            )

        if progress_callback:
            progress_callback(1.0, "Done!")

        return str(output_path)

    finally:
        # Clean up temp files
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {e}")


def get_video_info(video_path: str) -> dict:
    """Get basic information about a video file."""
    probe = ffmpeg.probe(video_path, cmd=FFPROBE_PATH)

    video_stream = next(
        (s for s in probe["streams"] if s["codec_type"] == "video"),
        None
    )

    info = {
        "duration": float(probe["format"]["duration"]),
        "size": int(probe["format"]["size"]),
        "format": probe["format"]["format_name"],
    }

    if video_stream:
        info["width"] = video_stream.get("width")
        info["height"] = video_stream.get("height")
        info["codec"] = video_stream.get("codec_name")

        # Calculate fps from frame rate fraction
        fps_parts = video_stream.get("r_frame_rate", "0/1").split("/")
        if len(fps_parts) == 2 and int(fps_parts[1]) != 0:
            info["fps"] = int(fps_parts[0]) / int(fps_parts[1])

    return info


if __name__ == "__main__":
    # Test with sample timestamps
    import sys

    if len(sys.argv) < 2:
        print("Usage: python clipper.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]

    # Print video info
    info = get_video_info(video_path)
    print(f"Video info: {info}")

    # Test extraction with dummy timestamps
    test_timestamps = [
        {"start_time": 0, "end_time": 5, "description": "Test clip 1"},
        {"start_time": 10, "end_time": 15, "description": "Test clip 2"},
    ]

    output = extract_clips(video_path, test_timestamps)
    print(f"Output saved to: {output}")
