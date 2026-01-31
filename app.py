"""Gradio web UI for football video analysis."""

import os
import tempfile
import threading
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from analyzer import analyze_video
from clipper import extract_clips, get_video_info

load_dotenv()

# Global cancellation flag
cancel_event = threading.Event()

# Custom CSS for sporty PFF-style font
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Roboto:wght@400;500&display=swap');

* {
    font-family: 'Roboto', sans-serif !important;
}

h1, h2, h3, .gr-button, label {
    font-family: 'Oswald', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

h1 {
    font-weight: 700 !important;
    font-size: 2.5rem !important;
}

.gr-button-primary {
    font-weight: 600 !important;
    font-size: 1.1rem !important;
}

.gr-button-stop {
    background: #dc3545 !important;
    border-color: #dc3545 !important;
}
"""


def process_video(video_path: str, query: str, padding: float, progress=gr.Progress()):
    """
    Process a video: analyze with Gemini and extract clips.

    Args:
        video_path: Path to uploaded video
        query: Natural language query for what to find
        padding: Seconds to add before/after each clip
        progress: Gradio progress tracker

    Returns:
        Tuple of (output_video_path, status_message, timestamps_text)
    """
    # Reset cancellation flag
    cancel_event.clear()

    if not video_path:
        return None, "Please upload a video first.", ""

    if not query.strip():
        return None, "Please enter a search query.", ""

    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        return None, "Error: GOOGLE_API_KEY not set. Please set it in your environment or .env file.", ""

    try:
        # Get video info
        progress(0.02, desc="Reading video info...")
        info = get_video_info(video_path)
        duration_str = f"{info['duration']:.1f}s"
        file_size_mb = info['size'] / (1024 * 1024)

        # Info about large files (will be auto-segmented)
        if file_size_mb > 1800:
            progress(0.03, desc=f"Large video ({file_size_mb:.0f}MB) - will be split into segments...")

        # Check for cancellation
        if cancel_event.is_set():
            return None, "Cancelled by user.", ""

        # Analyze video with Gemini
        def analysis_progress(pct, msg):
            if cancel_event.is_set():
                raise InterruptedError("Cancelled by user")
            # Scale analysis to 0.05-0.6 range
            progress(0.05 + pct * 0.55, desc=msg)

        timestamps = analyze_video(video_path, query, progress_callback=analysis_progress, cancel_event=cancel_event)

        if cancel_event.is_set():
            return None, "Cancelled by user.", ""

        if not timestamps:
            return None, f"No instances found matching: '{query}'", "No matches found."

        # Format timestamps for display
        timestamps_text = f"Found {len(timestamps)} instances:\n\n"
        for i, ts in enumerate(timestamps, 1):
            timestamps_text += f"{i}. [{ts['start_time']:.1f}s - {ts['end_time']:.1f}s] {ts['description']}\n"

        # Extract clips
        def clip_progress(pct, msg):
            if cancel_event.is_set():
                raise InterruptedError("Cancelled by user")
            # Scale clipping to 0.6-1.0 range
            progress(0.6 + pct * 0.4, desc=msg)

        # Create output in temp directory
        video_name = Path(video_path).stem
        output_dir = tempfile.mkdtemp(prefix="football_clips_")
        output_path = Path(output_dir) / f"{video_name}_highlights.mp4"

        output_video = extract_clips(
            video_path,
            timestamps,
            output_path=str(output_path),
            padding=padding,
            progress_callback=clip_progress,
        )

        status = f"Successfully extracted {len(timestamps)} clips from {duration_str} video."
        return output_video, status, timestamps_text

    except InterruptedError:
        return None, "Cancelled by user.", ""
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return None, error_msg, ""


def cancel_processing():
    """Signal cancellation of the current processing."""
    cancel_event.set()
    return "Cancelling..."


def clear_video():
    """Clear the uploaded video."""
    return None


def create_ui():
    """Create the Gradio interface."""

    with gr.Blocks(title="Football Video Analyzer", css=CUSTOM_CSS) as app:
        gr.Markdown("""
        # Football Video Analyzer

        Upload a football video and describe what you want to find.
        The AI will analyze the footage and extract matching clips.

        **Examples:**
        - "every time #3 ran a route"
        - "all completed passes"
        - "every touchdown"
        - "when the quarterback gets sacked"
        """)

        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(
                    label="Upload Football Video",
                    sources=["upload"],
                )

                with gr.Row():
                    clear_btn = gr.Button("Clear Video", variant="secondary", size="sm")

                query_input = gr.Textbox(
                    label="What do you want to find?",
                    placeholder="e.g., every time #3 ran a route",
                    lines=2,
                )

                padding_slider = gr.Slider(
                    minimum=0,
                    maximum=10,
                    value=2,
                    step=0.5,
                    label="Clip Padding (seconds)",
                    info="Extra time before/after each clip for context",
                )

                with gr.Row():
                    analyze_btn = gr.Button("Analyze Video", variant="primary", size="lg")
                    cancel_btn = gr.Button("Cancel", variant="stop", size="lg")

            with gr.Column(scale=1):
                status_output = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=2,
                )

                timestamps_output = gr.Textbox(
                    label="Found Timestamps",
                    interactive=False,
                    lines=10,
                )

        gr.Markdown("### Results")

        video_output = gr.Video(
            label="Extracted Clips",
        )

        # Connect the buttons
        analyze_btn.click(
            fn=process_video,
            inputs=[video_input, query_input, padding_slider],
            outputs=[video_output, status_output, timestamps_output],
        )

        cancel_btn.click(
            fn=cancel_processing,
            inputs=[],
            outputs=[status_output],
        )

        clear_btn.click(
            fn=clear_video,
            inputs=[],
            outputs=[video_input],
        )

        gr.Markdown("""
        ---
        **Note:** This tool uses Google's Gemini 2.0 Flash for video analysis.
        Make sure your `GOOGLE_API_KEY` environment variable is set.

        Large videos are automatically split into segments for processing.
        """)

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch()
