"""
Advanced Football Video Analysis using Gemini 2.0 Flash.

This module implements a sophisticated multi-stage analysis pipeline for detecting
specific plays in football film. Key features:

1. EXPERT SYSTEM INSTRUCTIONS: Establishes Gemini as a football film analyst with
   deep knowledge of camera angles, play structure, and player identification.

2. CAMERA ANGLE FILTERING: Only accepts sideline "All-22" footage, rejecting
   scoreboard views, endzone angles, and other non-standard angles.

3. COMPLETE PLAY CAPTURE: Ensures clips include pre-snap motion through post-whistle,
   typically 8-15 seconds per play.

4. MULTI-STAGE ANALYSIS: Uses chain-of-thought prompting with four stages:
   - Stage 1: Camera angle identification
   - Stage 2: Target event detection (sideline only)
   - Stage 3: Timestamp expansion for complete plays
   - Stage 4: Confidence scoring and verification

5. TWO-STAGE VERIFICATION: Each detected clip is verified with a second Gemini call
   to confirm camera angle, play completeness, and target criteria.

6. CONSERVATIVE DETECTION: Only reports high-confidence detections to minimize
   false positives.
"""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Callable

import ffmpeg
from google import genai
from google.genai import types
from dotenv import load_dotenv

from .clipper import FFMPEG_PATH, FFPROBE_PATH
from knowledge import get_full_knowledge_prompt

load_dotenv()

# Load comprehensive football knowledge base
# See backend/knowledge/football.py for full definitions
FOOTBALL_KNOWLEDGE_BASE = get_full_knowledge_prompt()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Maximum file size for Gemini (1.8GB to be safe)
MAX_FILE_SIZE_BYTES = 1.8 * 1024 * 1024 * 1024

# Target segment size (1.5GB to have margin)
TARGET_SEGMENT_SIZE_BYTES = 1.5 * 1024 * 1024 * 1024

# Minimum confidence score to accept a detection (0-100)
MIN_CONFIDENCE_SCORE = 70

# Enable/disable verification stage (set False to speed up testing)
ENABLE_VERIFICATION = True

# =============================================================================
# SYSTEM INSTRUCTIONS FOR EXPERT FOOTBALL FILM ANALYSIS
# =============================================================================

SYSTEM_INSTRUCTIONS = f"""You are an expert football film analyst with comprehensive knowledge
of positions, plays, routes, blocking, tackles, and field position.

## CAMERA ANGLES (CRITICAL - Filter First)
- **Sideline/All-22**: Wide shot from the sideline showing all 22 players. ONLY ANALYZE THESE.
- **Endzone**: Shot from behind the endzone looking down the field. EXCLUDE these.
- **Scoreboard/Graphics**: Static overlay showing score, stats, or broadcast graphics. EXCLUDE these.
- **Tight/Isolated**: Close-up on specific players. EXCLUDE these.
- **Aerial/Skycam**: Overhead moving camera. EXCLUDE these.
- **Replay**: Slow-motion replay of a play. EXCLUDE these unless specifically requested.

## PLAY STRUCTURE
- A complete play starts BEFORE the snap (include pre-snap motion, shifts, audibles)
- The snap is when the center hikes the ball to the quarterback
- A play ends AFTER the whistle (include tackle completion, out of bounds, celebration)
- Typical play duration: 8-15 seconds from pre-snap to post-whistle
- NEVER cut off a play mid-action

## CONSERVATIVE DETECTION PHILOSOPHY
- Only report plays where you have HIGH CONFIDENCE in your detection
- When in doubt, DO NOT include the play
- False negatives (missing a play) are better than false positives (wrong plays)
- Confidence score must reflect actual certainty, not optimism

{FOOTBALL_KNOWLEDGE_BASE}"""

# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

def get_detection_prompt(query: str) -> str:
    """
    Multi-stage analysis prompt using chain-of-thought reasoning.

    This prompt forces Gemini to:
    1. First identify camera angles throughout the video
    2. Only analyze sideline footage
    3. Detect the target event with strict criteria
    4. Expand timestamps to capture complete plays
    5. Assign confidence scores
    """
    return f"""Analyze this football video using the following multi-stage process.

## YOUR TASK
Find every instance where: {query}

## STAGE 1: CAMERA ANGLE IDENTIFICATION
First, mentally note the camera angles used throughout this video:
- Sideline/All-22 (wide shot showing all players) - ANALYZE THESE
- Endzone view - SKIP THESE
- Scoreboard/graphics overlay - SKIP THESE
- Tight/isolated shots - SKIP THESE
- Replay footage - SKIP THESE

ONLY analyze footage from SIDELINE/ALL-22 camera angles.

## STAGE 2: EVENT DETECTION (Sideline footage only)
For each potential match, verify:
- Is this definitely the correct player (jersey number clearly visible)?
- Is this definitely the correct action (catch vs run vs block)?
- Is the camera angle sideline/All-22?

## STAGE 3: TIMESTAMP EXPANSION
For each confirmed detection:
- start_time: Set to 3-5 seconds BEFORE the snap to capture pre-snap motion
- end_time: Set to 2-3 seconds AFTER the play ends (tackle, out of bounds, whistle)
- Total clip duration should be 8-15 seconds for a typical play

## STAGE 4: CONFIDENCE SCORING
Rate your confidence (0-100) based on:
- 90-100: Jersey number clearly visible, action unambiguous, sideline angle confirmed
- 70-89: High confidence but minor uncertainty (number slightly obscured, etc.)
- Below 70: DO NOT INCLUDE - too uncertain

## OUTPUT FORMAT
Return ONLY a valid JSON array. Each object must have:
- "start_time": number (seconds, BEFORE the snap)
- "end_time": number (seconds, AFTER the whistle/play end)
- "confidence_score": number (0-100, must be >= 70 to include)
- "camera_angle": string (must be "sideline" to include)
- "play_description": string (detailed description of the play)
- "player_jersey": string (jersey number identified, e.g., "#17")
- "action_type": string (e.g., "catch", "run", "block", etc.)
- "reasoning": string (brief explanation of why this detection is confident)

If no high-confidence instances are found, return an empty array: []

## EXAMPLE OUTPUT
[
  {{
    "start_time": 45.0,
    "end_time": 56.5,
    "confidence_score": 92,
    "camera_angle": "sideline",
    "play_description": "#17 in yellow runs a deep post route, catches pass at the 30-yard line, tackled after 8-yard gain",
    "player_jersey": "#17",
    "action_type": "catch",
    "reasoning": "Jersey number clearly visible on sideline All-22 shot, catch is unambiguous, included full play from pre-snap through tackle"
  }}
]

CRITICAL RULES:
1. ONLY include clips from SIDELINE camera angle
2. ONLY include clips with confidence >= 70
3. ALWAYS capture the COMPLETE play (pre-snap to post-whistle)
4. When uncertain, DO NOT include the play

Return ONLY the JSON array, no other text."""


def get_verification_prompt(query: str, clip_info: dict) -> str:
    """
    Verification prompt for second-stage confirmation.

    This runs on each detected clip to verify it meets all criteria.
    Uses direct yes/no questions to force explicit verification.
    """
    return f"""You are verifying a detected football play clip. Answer each question carefully.

ORIGINAL SEARCH QUERY: {query}

DETECTED CLIP INFO:
- Timestamps: {clip_info.get('start_time', 'N/A')}s to {clip_info.get('end_time', 'N/A')}s
- Claimed action: {clip_info.get('play_description', 'N/A')}
- Claimed player: {clip_info.get('player_jersey', 'N/A')}

## VERIFICATION QUESTIONS

Answer each question with YES or NO, followed by brief reasoning:

1. CAMERA ANGLE: Is this clip filmed from a SIDELINE/ALL-22 camera angle (wide shot showing most/all players)?
   - Answer NO if: endzone view, scoreboard graphics, tight shot, replay, or aerial view

2. COMPLETE PLAY: Does this clip show a COMPLETE play from pre-snap through post-whistle?
   - Answer NO if: play is cut off mid-action, missing the snap, or missing the play conclusion

3. CORRECT PLAYER: Is the identified player ({clip_info.get('player_jersey', 'the target player')}) clearly visible and correctly identified?
   - Answer NO if: jersey number not visible, wrong player, or uncertain identification

4. CORRECT ACTION: Does the play match the search criteria "{query}"?
   - Answer NO if: different action type (e.g., run instead of catch), different player, or ambiguous

## OUTPUT FORMAT
Return ONLY a valid JSON object:
{{
  "camera_angle_verified": boolean,
  "camera_angle_reasoning": "string",
  "complete_play_verified": boolean,
  "complete_play_reasoning": "string",
  "player_verified": boolean,
  "player_reasoning": "string",
  "action_verified": boolean,
  "action_reasoning": "string",
  "all_criteria_met": boolean,
  "overall_confidence": number (0-100),
  "recommendation": "KEEP" or "REJECT",
  "rejection_reason": "string or null"
}}

Be STRICT in verification. When in doubt, recommend REJECT."""


# =============================================================================
# GENERATION CONFIG
# =============================================================================

def get_generation_config() -> types.GenerateContentConfig:
    """
    Optimized generation config for consistent, deterministic outputs.

    - temperature=0.2: Low temperature for more deterministic responses
    - top_p=0.8: Nucleus sampling for quality while maintaining consistency
    - top_k=40: Limits token selection for more focused outputs
    """
    return types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.8,
        top_k=40,
    )


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def log_detection(clip: dict, status: str, reason: str = None):
    """Log detection results with clear formatting."""
    timestamp = f"{clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s"
    confidence = clip.get('confidence_score', 0)

    if status == "ACCEPTED":
        print(f"  ✓ ACCEPTED: {timestamp} (confidence: {confidence})")
        print(f"    → {clip.get('play_description', 'No description')}")
    elif status == "REJECTED":
        print(f"  ✗ REJECTED: {timestamp} (confidence: {confidence})")
        print(f"    → Reason: {reason}")
    elif status == "FILTERED":
        print(f"  ⊘ FILTERED: {timestamp}")
        print(f"    → Reason: {reason}")


def log_verification_result(clip: dict, verification: dict):
    """Log detailed verification results."""
    timestamp = f"{clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s"

    print(f"\n  Verification for {timestamp}:")
    print(f"    Camera angle: {'✓' if verification.get('camera_angle_verified') else '✗'} - {verification.get('camera_angle_reasoning', 'N/A')}")
    print(f"    Complete play: {'✓' if verification.get('complete_play_verified') else '✗'} - {verification.get('complete_play_reasoning', 'N/A')}")
    print(f"    Player ID: {'✓' if verification.get('player_verified') else '✗'} - {verification.get('player_reasoning', 'N/A')}")
    print(f"    Action match: {'✓' if verification.get('action_verified') else '✗'} - {verification.get('action_reasoning', 'N/A')}")
    print(f"    → Recommendation: {verification.get('recommendation', 'UNKNOWN')}")


# =============================================================================
# CORE ANALYSIS FUNCTIONS
# =============================================================================

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


def call_gemini_with_retry(client: genai.Client, video_file: types.File, prompt: str,
                           cancel_event=None, max_retries: int = 5) -> str:
    """
    Call Gemini API with retry logic for rate limits.

    Returns the response text or raises an exception.
    """
    retry_delay = 30  # Start with 30 seconds

    for attempt in range(max_retries):
        try:
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Cancelled by user")

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
                config=get_generation_config(),
            )
            return response.text.strip()

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    print(f"Rate limited, waiting {retry_delay}s before retry {attempt + 2}/{max_retries}...")
                    # Wait with cancellation check
                    for _ in range(retry_delay):
                        if cancel_event and cancel_event.is_set():
                            raise InterruptedError("Cancelled by user")
                        time.sleep(1)
                    retry_delay = min(retry_delay * 2, 120)  # Exponential backoff, max 2 min
                else:
                    raise ValueError(f"Rate limit exceeded after {max_retries} retries. Please wait or upgrade your Gemini API plan.")
            else:
                raise

    return ""


def parse_json_response(response_text: str) -> list | dict | None:
    """
    Parse JSON from Gemini response, handling markdown code blocks.
    """
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        return json.loads(response_text)

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response was: {response_text[:500]}...")
        return None


def filter_by_confidence_and_angle(detections: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filter detections by confidence score and camera angle.

    Returns:
        Tuple of (accepted_detections, rejected_detections)
    """
    accepted = []
    rejected = []

    for clip in detections:
        confidence = clip.get('confidence_score', 0)
        camera_angle = clip.get('camera_angle', '').lower()

        # Filter by camera angle
        if camera_angle != 'sideline':
            log_detection(clip, "FILTERED", f"Wrong camera angle: {camera_angle}")
            rejected.append({**clip, 'rejection_reason': f'Wrong camera angle: {camera_angle}'})
            continue

        # Filter by confidence score
        if confidence < MIN_CONFIDENCE_SCORE:
            log_detection(clip, "FILTERED", f"Low confidence: {confidence} < {MIN_CONFIDENCE_SCORE}")
            rejected.append({**clip, 'rejection_reason': f'Low confidence: {confidence}'})
            continue

        accepted.append(clip)

    return accepted, rejected


def verify_clip(client: genai.Client, video_file: types.File, query: str,
                clip: dict, cancel_event=None) -> dict:
    """
    Run second-stage verification on a detected clip.

    Returns verification result dict with recommendation.
    """
    prompt = get_verification_prompt(query, clip)

    try:
        response_text = call_gemini_with_retry(client, video_file, prompt, cancel_event)
        verification = parse_json_response(response_text)

        if verification is None:
            return {
                'all_criteria_met': False,
                'recommendation': 'REJECT',
                'rejection_reason': 'Failed to parse verification response'
            }

        return verification

    except Exception as e:
        print(f"Verification error: {e}")
        return {
            'all_criteria_met': False,
            'recommendation': 'REJECT',
            'rejection_reason': f'Verification error: {str(e)}'
        }


def analyze_single_segment(client: genai.Client, video_path: str, query: str,
                           time_offset: float = 0.0, cancel_event=None,
                           progress_callback=None) -> list[dict]:
    """
    Analyze a single video segment with multi-stage detection and verification.

    Pipeline:
    1. Upload video to Gemini
    2. Run detection prompt with chain-of-thought reasoning
    3. Filter by confidence score and camera angle
    4. (Optional) Verify each detection with second Gemini call
    5. Return verified detections adjusted by time offset
    """
    print(f"\n{'='*60}")
    print(f"ANALYZING SEGMENT (offset: {time_offset:.1f}s)")
    print(f"{'='*60}")

    if cancel_event and cancel_event.is_set():
        raise InterruptedError("Cancelled by user")

    # Stage 1: Upload video
    print("\n[Stage 1] Uploading video to Gemini...")
    video_file = upload_video(client, video_path, cancel_event=cancel_event)

    if cancel_event and cancel_event.is_set():
        try:
            client.files.delete(name=video_file.name)
        except:
            pass
        return []

    try:
        # Stage 2: Run detection with chain-of-thought prompt
        print("\n[Stage 2] Running multi-stage detection analysis...")
        detection_prompt = get_detection_prompt(query)
        response_text = call_gemini_with_retry(client, video_file, detection_prompt, cancel_event)

        detections = parse_json_response(response_text)

        if detections is None or not isinstance(detections, list):
            print("No valid detections returned")
            return []

        print(f"\nInitial detections: {len(detections)} clips found")

        # Stage 3: Filter by confidence and camera angle
        print("\n[Stage 3] Filtering by confidence and camera angle...")
        accepted, rejected = filter_by_confidence_and_angle(detections)

        print(f"After filtering: {len(accepted)} accepted, {len(rejected)} rejected")

        if not accepted:
            return []

        # Stage 4: Verification (optional)
        if ENABLE_VERIFICATION:
            print("\n[Stage 4] Running verification on accepted clips...")
            verified_clips = []

            for i, clip in enumerate(accepted):
                if cancel_event and cancel_event.is_set():
                    break

                print(f"\nVerifying clip {i+1}/{len(accepted)}...")
                verification = verify_clip(client, video_file, query, clip, cancel_event)

                log_verification_result(clip, verification)

                if verification.get('recommendation') == 'KEEP':
                    # Merge verification data into clip
                    clip['verification_status'] = 'verified'
                    clip['verification_confidence'] = verification.get('overall_confidence', clip.get('confidence_score', 0))
                    verified_clips.append(clip)
                    log_detection(clip, "ACCEPTED")
                else:
                    clip['verification_status'] = 'rejected'
                    clip['rejection_reason'] = verification.get('rejection_reason', 'Failed verification')
                    log_detection(clip, "REJECTED", verification.get('rejection_reason'))

            accepted = verified_clips
            print(f"\nAfter verification: {len(accepted)} clips confirmed")
        else:
            # Mark as unverified but accepted
            for clip in accepted:
                clip['verification_status'] = 'skipped'
                log_detection(clip, "ACCEPTED")

        # Adjust timestamps by offset
        for clip in accepted:
            clip['start_time'] = float(clip['start_time']) + time_offset
            clip['end_time'] = float(clip['end_time']) + time_offset

        return accepted

    finally:
        # Clean up the uploaded file
        try:
            client.files.delete(name=video_file.name)
            print("Cleaned up uploaded video file")
        except Exception as e:
            print(f"Warning: Could not delete uploaded file: {e}")


def analyze_video(video_path: str, query: str, progress_callback=None, cancel_event=None) -> list[dict]:
    """
    Analyze a video using Gemini 2.0 Flash with advanced detection pipeline.

    This is the main entry point for video analysis. It handles:
    - Automatic video segmentation for large files
    - Multi-stage detection with chain-of-thought reasoning
    - Two-stage verification for accuracy
    - Comprehensive logging of accepted/rejected clips

    Args:
        video_path: Path to the video file
        query: Natural language query describing what to find
        progress_callback: Optional callback for progress updates (pct, message)
        cancel_event: Optional threading.Event for cancellation

    Returns:
        List of verified clip dictionaries with:
        - start_time: Pre-snap timestamp in seconds
        - end_time: Post-whistle timestamp in seconds
        - confidence_score: Detection confidence (0-100)
        - camera_angle: Should always be "sideline"
        - play_description: Detailed play description
        - player_jersey: Identified player number
        - action_type: Type of action (catch, run, etc.)
        - verification_status: "verified", "skipped", or "rejected"
    """
    print(f"\n{'#'*60}")
    print(f"FOOTBALL VIDEO ANALYZER")
    print(f"{'#'*60}")
    print(f"Query: {query}")
    print(f"Video: {video_path}")
    print(f"Verification: {'ENABLED' if ENABLE_VERIFICATION else 'DISABLED'}")
    print(f"Min confidence: {MIN_CONFIDENCE_SCORE}")

    client = get_client()

    # Get video info
    duration, file_size = get_video_duration_and_size(video_path)
    print(f"Duration: {duration:.1f}s, Size: {file_size / (1024**2):.1f}MB")

    # Check if we need to segment
    if file_size <= MAX_FILE_SIZE_BYTES:
        # Small enough to process directly
        if progress_callback:
            progress_callback(0.1, "Uploading video to Gemini...")

        results = analyze_single_segment(
            client, video_path, query,
            time_offset=0.0,
            cancel_event=cancel_event,
            progress_callback=progress_callback
        )

        if progress_callback:
            progress_callback(1.0, f"Found {len(results)} verified clips")

        print_summary(results)
        return results

    # Need to segment the video
    print(f"\nVideo is {file_size / (1024**3):.2f}GB, segmenting for processing...")

    # Calculate segment duration based on file size and target
    segment_duration = (TARGET_SEGMENT_SIZE_BYTES / file_size) * duration
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
        all_clips = []
        total_segments = len(segments)

        for i, (segment_path, time_offset) in enumerate(segments):
            if cancel_event and cancel_event.is_set():
                return []

            if progress_callback:
                base_progress = 0.1 + (i / total_segments) * 0.8
                progress_callback(base_progress, f"Analyzing segment {i + 1}/{total_segments}...")

            segment_clips = analyze_single_segment(
                client, segment_path, query,
                time_offset=time_offset,
                cancel_event=cancel_event,
                progress_callback=progress_callback
            )

            all_clips.extend(segment_clips)
            print(f"\nSegment {i + 1} complete: {len(segment_clips)} verified clips")

        if progress_callback:
            progress_callback(1.0, f"Found {len(all_clips)} total verified clips")

        # Sort by start time
        all_clips.sort(key=lambda x: x["start_time"])

        print_summary(all_clips)
        return all_clips

    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {e}")


def print_summary(clips: list[dict]):
    """Print a summary of analysis results."""
    print(f"\n{'='*60}")
    print(f"ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"Total verified clips: {len(clips)}")

    if clips:
        print(f"\nVerified clips:")
        for i, clip in enumerate(clips, 1):
            print(f"\n  {i}. [{clip['start_time']:.1f}s - {clip['end_time']:.1f}s]")
            print(f"     Confidence: {clip.get('confidence_score', 'N/A')}")
            print(f"     Player: {clip.get('player_jersey', 'N/A')}")
            print(f"     Action: {clip.get('action_type', 'N/A')}")
            print(f"     Description: {clip.get('play_description', 'N/A')}")
    else:
        print("\nNo clips met all verification criteria.")

    print(f"\n{'='*60}\n")


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
