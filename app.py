"""Gradio web UI for Clip Cutter video analysis."""

import os
import tempfile
import threading
from pathlib import Path
from typing import Optional
from uuid import UUID

import gradio as gr
from dotenv import load_dotenv

from analyzer import analyze_video
from clipper import extract_clips, get_video_info
from config import settings

load_dotenv()

# Global cancellation flag
cancel_event = threading.Event()

# Custom CSS - Dark theme with orange accents, collapsible sidebar
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Roboto:wght@400;500&display=swap');

/* Color variables */
:root {
    --bg-dark: #1e1e2e;
    --bg-darker: #181825;
    --bg-card: #2a2a3e;
    --orange-primary: #f97316;
    --orange-light: #fb923c;
    --orange-dark: #ea580c;
    --text-primary: #e4e4e7;
    --text-secondary: #a1a1aa;
    --text-muted: #71717a;
    --border-color: #3f3f5a;
}

/* Global dark theme */
.gradio-container {
    background: var(--bg-dark) !important;
    max-width: 100% !important;
}

.dark, body, .gr-app {
    background: var(--bg-dark) !important;
}

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
    color: var(--text-primary) !important;
}

h2, h3 {
    color: var(--text-primary) !important;
}

label, .gr-input-label {
    color: var(--text-secondary) !important;
}

/* Hamburger menu trigger */
.menu-trigger {
    position: fixed;
    left: 0;
    top: 0;
    width: 60px;
    height: 100vh;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 20px;
    background: var(--bg-darker);
    border-right: 1px solid var(--border-color);
    transition: all 0.3s ease;
}

.hamburger-icon {
    width: 28px;
    height: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    cursor: pointer;
    padding: 8px;
}

.hamburger-icon span {
    display: block;
    height: 3px;
    width: 100%;
    background: var(--orange-primary);
    border-radius: 2px;
    transition: all 0.3s ease;
}

.menu-trigger:hover .hamburger-icon span {
    background: var(--orange-light);
}

/* Sidebar - hidden by default, shows on hover */
.sidebar-container {
    position: fixed;
    left: -240px;
    top: 0;
    width: 240px;
    height: 100vh;
    background: var(--bg-darker);
    border-right: 1px solid var(--border-color);
    z-index: 999;
    transition: left 0.3s ease;
    padding: 20px 16px;
    overflow-y: auto;
}

.sidebar-container:hover,
.menu-trigger:hover + .sidebar-container,
.sidebar-container.show {
    left: 0;
}

/* When hovering the menu area, show sidebar */
.menu-area:hover .sidebar-container {
    left: 0;
}

.sidebar-title {
    color: var(--orange-primary) !important;
    font-family: 'Oswald', sans-serif !important;
    font-size: 1.5rem !important;
    font-weight: 700;
    margin-bottom: 32px;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.nav-button {
    width: 100%;
    margin-bottom: 8px;
    background: transparent !important;
    border: none !important;
    color: var(--text-secondary) !important;
    text-align: left !important;
    padding: 14px 18px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    font-size: 1rem !important;
}

.nav-button:hover {
    background: rgba(249, 115, 22, 0.15) !important;
    color: var(--orange-light) !important;
}

.nav-button.active {
    background: rgba(249, 115, 22, 0.2) !important;
    color: var(--orange-primary) !important;
    border-left: 3px solid var(--orange-primary) !important;
}

.nav-divider {
    height: 1px;
    background: var(--border-color);
    margin: 20px 0;
}

.user-section {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border-color);
}

.login-btn {
    width: 100%;
    background: linear-gradient(135deg, var(--orange-primary) 0%, var(--orange-dark) 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
}

.login-btn:hover {
    background: linear-gradient(135deg, var(--orange-light) 0%, var(--orange-primary) 100%) !important;
}

.logout-btn {
    width: 100%;
    background: transparent !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-secondary) !important;
    font-weight: 400 !important;
}

.logout-btn:hover {
    border-color: var(--orange-primary) !important;
    color: var(--orange-primary) !important;
}

.user-email {
    color: var(--orange-light) !important;
    font-size: 0.9rem;
    margin-bottom: 12px;
    word-break: break-all;
}

/* Main content - full width with padding for menu */
.main-content {
    margin-left: 60px;
    padding: 32px 48px;
    min-height: 100vh;
    background: var(--bg-dark);
}

/* Header styling */
.app-header {
    text-align: center;
    margin-bottom: 40px;
}

.app-header h1 {
    margin-bottom: 12px;
    background: linear-gradient(135deg, var(--orange-primary), var(--orange-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.app-subtitle {
    color: var(--text-secondary) !important;
    font-size: 1.15rem;
}

/* Primary buttons - Orange */
.gr-button-primary {
    background: linear-gradient(135deg, var(--orange-primary) 0%, var(--orange-dark) 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    padding: 12px 24px !important;
}

.gr-button-primary:hover {
    background: linear-gradient(135deg, var(--orange-light) 0%, var(--orange-primary) 100%) !important;
    transform: translateY(-1px);
}

/* Secondary buttons */
.gr-button-secondary {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-secondary) !important;
}

.gr-button-secondary:hover {
    border-color: var(--orange-primary) !important;
    color: var(--orange-primary) !important;
}

/* Stop/Cancel button */
.gr-button-stop {
    background: #dc2626 !important;
    border-color: #dc2626 !important;
}

/* Form elements */
.gr-input, .gr-textarea, .gr-dropdown {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
}

.gr-input:focus, .gr-textarea:focus {
    border-color: var(--orange-primary) !important;
    box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.2) !important;
}

/* Slider */
.gr-slider input[type="range"] {
    accent-color: var(--orange-primary);
}

/* Video components - larger */
.gr-video {
    min-height: 400px !important;
}

.gr-video video {
    max-height: 500px !important;
}

/* Tabs */
.gr-tab-item {
    color: var(--text-secondary) !important;
    border: none !important;
    background: transparent !important;
}

.gr-tab-item:hover {
    color: var(--orange-light) !important;
}

.gr-tab-item.selected {
    color: var(--orange-primary) !important;
    border-bottom: 2px solid var(--orange-primary) !important;
}

/* Cards/Panels */
.gr-panel, .gr-box, .gr-form {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
}

/* Textbox */
textarea, input[type="text"], input[type="password"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
}

textarea:focus, input:focus {
    border-color: var(--orange-primary) !important;
    outline: none !important;
}

/* Dataframe/Table */
.gr-dataframe {
    background: var(--bg-card) !important;
}

.gr-dataframe th {
    background: var(--bg-darker) !important;
    color: var(--orange-primary) !important;
}

.gr-dataframe td {
    color: var(--text-primary) !important;
    border-color: var(--border-color) !important;
}

/* History table */
.history-table {
    width: 100%;
}

/* Status colors */
.status-complete {
    color: #22c55e !important;
}

.status-processing {
    color: var(--orange-primary) !important;
}

.status-failed {
    color: #ef4444 !important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-darker);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--orange-primary);
}

/* Info/Warning messages */
.gr-info {
    background: rgba(249, 115, 22, 0.1) !important;
    border: 1px solid var(--orange-primary) !important;
    color: var(--orange-light) !important;
}

/* Sidebar panel - Gradio column styling */
.sidebar-panel {
    position: fixed !important;
    left: -250px !important;
    top: 0 !important;
    width: 250px !important;
    height: 100vh !important;
    background: var(--bg-darker) !important;
    border-right: 1px solid var(--border-color) !important;
    z-index: 999 !important;
    transition: left 0.3s ease !important;
    padding: 70px 20px 24px 20px !important;
    box-sizing: border-box !important;
    overflow-y: auto !important;
}

.sidebar-panel.show,
.sidebar-panel:hover {
    left: 0 !important;
}

/* Main content offset for menu */
.main-content {
    margin-left: 60px !important;
    padding: 32px 48px !important;
    min-height: 100vh !important;
    background: var(--bg-dark) !important;
    width: calc(100% - 60px) !important;
}

/* Make video components larger */
.gr-video {
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* Wider layout */
.gradio-container .contain {
    max-width: 100% !important;
}
"""


def get_db_functions():
    """Lazy import database functions to avoid import errors when not configured."""
    try:
        from database import (
            create_analysis,
            get_or_create_user_settings,
            get_user_history,
            update_analysis,
            update_user_settings,
        )
        from models import (
            AnalysisCreate,
            AnalysisStatus,
            AnalysisUpdate,
            Timestamp,
            UserSettingsUpdate,
        )
        return {
            "create_analysis": create_analysis,
            "get_or_create_user_settings": get_or_create_user_settings,
            "get_user_history": get_user_history,
            "update_analysis": update_analysis,
            "update_user_settings": update_user_settings,
            "AnalysisCreate": AnalysisCreate,
            "AnalysisStatus": AnalysisStatus,
            "AnalysisUpdate": AnalysisUpdate,
            "Timestamp": Timestamp,
            "UserSettingsUpdate": UserSettingsUpdate,
        }
    except Exception:
        return None


def get_auth_functions():
    """Lazy import auth functions to avoid import errors when not configured."""
    try:
        from auth import get_auth_state, session_manager
        return {
            "get_auth_state": get_auth_state,
            "session_manager": session_manager,
        }
    except Exception:
        return None


def process_video(
    video_path: str,
    query: str,
    padding: float,
    session_id: Optional[str] = None,
    progress=gr.Progress(),
):
    """
    Process a video: analyze with Gemini and extract clips.

    Args:
        video_path: Path to uploaded video
        query: Natural language query for what to find
        padding: Seconds to add before/after each clip
        session_id: Optional session ID for authenticated users
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
    if not settings.gemini_configured:
        return None, "Error: GOOGLE_API_KEY not set. Please set it in your environment or .env file.", ""

    # Get user info if authenticated
    user_id = None
    analysis_id = None
    db_funcs = get_db_functions()
    auth_funcs = get_auth_functions()

    if session_id and auth_funcs and db_funcs and settings.supabase_configured:
        auth_state = auth_funcs["get_auth_state"](session_id)
        if auth_state.is_authenticated and auth_state.user:
            user_id = auth_state.user.id
            # Create analysis record
            try:
                analysis = db_funcs["create_analysis"](db_funcs["AnalysisCreate"](
                    video_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                    user_id=user_id,
                    query=query,
                ))
                analysis_id = analysis.id
            except Exception as e:
                print(f"Failed to create analysis record: {e}")

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

        # Update analysis status to processing
        if analysis_id and db_funcs:
            try:
                db_funcs["update_analysis"](analysis_id, db_funcs["AnalysisUpdate"](
                    status=db_funcs["AnalysisStatus"].PROCESSING
                ))
            except Exception:
                pass

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
            # Update analysis as complete with no results
            if analysis_id and db_funcs:
                try:
                    db_funcs["update_analysis"](analysis_id, db_funcs["AnalysisUpdate"](
                        status=db_funcs["AnalysisStatus"].COMPLETE,
                        timestamps=[],
                    ))
                except Exception:
                    pass
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
        output_dir = tempfile.mkdtemp(prefix="clip_cutter_")
        output_path = Path(output_dir) / f"{video_name}_highlights.mp4"

        output_video = extract_clips(
            video_path,
            timestamps,
            output_path=str(output_path),
            padding=padding,
            progress_callback=clip_progress,
        )

        # Save analysis results to database
        if analysis_id and db_funcs:
            try:
                timestamp_models = [
                    db_funcs["Timestamp"](
                        start_time=ts["start_time"],
                        end_time=ts["end_time"],
                        description=ts.get("description", ""),
                    )
                    for ts in timestamps
                ]
                db_funcs["update_analysis"](analysis_id, db_funcs["AnalysisUpdate"](
                    status=db_funcs["AnalysisStatus"].COMPLETE,
                    timestamps=timestamp_models,
                ))
            except Exception as e:
                print(f"Failed to save analysis results: {e}")

        status = f"Successfully extracted {len(timestamps)} clips from {duration_str} video."
        return output_video, status, timestamps_text

    except InterruptedError:
        # Mark analysis as failed if it was created
        if analysis_id and db_funcs:
            try:
                db_funcs["update_analysis"](analysis_id, db_funcs["AnalysisUpdate"](
                    status=db_funcs["AnalysisStatus"].FAILED,
                ))
            except Exception:
                pass
        return None, "Cancelled by user.", ""
    except Exception as e:
        # Mark analysis as failed
        if analysis_id and db_funcs:
            try:
                db_funcs["update_analysis"](analysis_id, db_funcs["AnalysisUpdate"](
                    status=db_funcs["AnalysisStatus"].FAILED,
                ))
            except Exception:
                pass

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


def load_history(session_id: Optional[str] = None):
    """Load analysis history for the current user."""
    if not session_id:
        return [], "Sign in to view your analysis history."

    auth_funcs = get_auth_functions()
    db_funcs = get_db_functions()

    if not auth_funcs or not db_funcs or not settings.supabase_configured:
        return [], "Database not configured."

    auth_state = auth_funcs["get_auth_state"](session_id)
    if not auth_state.is_authenticated or not auth_state.user:
        return [], "Sign in to view your analysis history."

    try:
        history = db_funcs["get_user_history"](auth_state.user.id)
        if not history:
            return [], "No analysis history yet. Analyze a video to get started!"

        # Format for dataframe
        rows = []
        for item in history:
            date_str = item.created_at.strftime("%Y-%m-%d %H:%M")
            rows.append([
                date_str,
                item.video_filename,
                item.query[:50] + "..." if len(item.query) > 50 else item.query,
                item.clips_found,
                item.status.value.capitalize(),
            ])
        return rows, f"Showing {len(rows)} analyses"
    except Exception as e:
        print(f"Error loading history: {e}")
        return [], f"Error loading history: {str(e)}"


def load_settings(session_id: Optional[str] = None):
    """Load user settings."""
    default_padding = 2.0
    default_theme = "Light"
    default_api_key = ""

    if not session_id:
        return default_padding, default_theme, default_api_key

    auth_funcs = get_auth_functions()
    db_funcs = get_db_functions()

    if not auth_funcs or not db_funcs or not settings.supabase_configured:
        return default_padding, default_theme, default_api_key

    auth_state = auth_funcs["get_auth_state"](session_id)
    if not auth_state.is_authenticated or not auth_state.user:
        return default_padding, default_theme, default_api_key

    try:
        user_settings = db_funcs["get_or_create_user_settings"](auth_state.user.id)
        return (
            user_settings.default_padding,
            user_settings.theme.value.capitalize(),
            user_settings.gemini_api_key or "",
        )
    except Exception as e:
        print(f"Error loading settings: {e}")
        return default_padding, default_theme, default_api_key


def save_settings(padding, theme, api_key, session_id: Optional[str] = None):
    """Save user settings."""
    if not session_id:
        return "Sign in to save settings permanently."

    auth_funcs = get_auth_functions()
    db_funcs = get_db_functions()

    if not auth_funcs or not db_funcs or not settings.supabase_configured:
        return "Database not configured. Settings saved locally only."

    auth_state = auth_funcs["get_auth_state"](session_id)
    if not auth_state.is_authenticated or not auth_state.user:
        return "Sign in to save settings permanently."

    try:
        db_funcs["update_user_settings"](
            auth_state.user.id,
            db_funcs["UserSettingsUpdate"](
                default_padding=padding,
                theme=theme.lower(),
                gemini_api_key=api_key if api_key else None,
            ),
        )
        return "Settings saved successfully!"
    except Exception as e:
        print(f"Error saving settings: {e}")
        return f"Error saving settings: {str(e)}"


def get_user_display(session_id: Optional[str] = None):
    """Get user display info for sidebar."""
    if not session_id:
        return "**Guest User**", True, False  # user_label, show_login, show_logout

    auth_funcs = get_auth_functions()
    if not auth_funcs or not settings.supabase_configured:
        return "**Guest User**", True, False

    auth_state = auth_funcs["get_auth_state"](session_id)
    if auth_state.is_authenticated and auth_state.user:
        email = auth_state.user.email
        # Truncate long emails
        if len(email) > 25:
            email = email[:22] + "..."
        return f"**{email}**", False, True

    return "**Guest User**", True, False


def create_ui():
    """Create the Gradio interface."""

    with gr.Blocks(title="Clip Cutter", css=CUSTOM_CSS, theme=gr.themes.Soft()) as app:
        # Session state
        session_state = gr.State(value=None)

        # Hamburger menu and collapsible sidebar using HTML/JS
        gr.HTML("""
        <div class="menu-area" onmouseenter="document.querySelector('.sidebar-panel').classList.add('show')"
             onmouseleave="document.querySelector('.sidebar-panel').classList.remove('show')">
            <div class="menu-trigger">
                <div class="hamburger-icon">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
        <style>
            .menu-area {
                position: fixed;
                left: 0;
                top: 0;
                width: 60px;
                height: 100vh;
                z-index: 1001;
            }
            .menu-trigger {
                position: fixed;
                left: 0;
                top: 0;
                width: 60px;
                height: 100vh;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding-top: 24px;
                background: #181825;
                border-right: 1px solid #3f3f5a;
            }
            .hamburger-icon {
                width: 28px;
                height: 22px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                cursor: pointer;
            }
            .hamburger-icon span {
                display: block;
                height: 3px;
                width: 100%;
                background: #f97316;
                border-radius: 2px;
                transition: all 0.3s ease;
            }
            .menu-trigger:hover .hamburger-icon span {
                background: #fb923c;
            }
            .sidebar-panel {
                position: fixed;
                left: -250px;
                top: 0;
                width: 250px;
                height: 100vh;
                background: #181825;
                border-right: 1px solid #3f3f5a;
                z-index: 999;
                transition: left 0.3s ease;
                padding: 24px 20px;
                box-sizing: border-box;
            }
            .sidebar-panel.show,
            .menu-area:hover .sidebar-panel {
                left: 0;
            }
            .sidebar-panel h2 {
                color: #f97316;
                font-family: 'Oswald', sans-serif;
                font-size: 1.6rem;
                font-weight: 700;
                margin: 0 0 32px 0;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
        </style>
        """)

        # Sidebar content (positioned fixed via CSS)
        with gr.Column(elem_classes=["sidebar-panel"], visible=True) as sidebar:
            gr.HTML("<h2>Clip Cutter</h2>")

            # Navigation buttons
            home_btn = gr.Button("Home", elem_classes=["nav-button", "active"], size="sm")
            history_btn = gr.Button("History", elem_classes=["nav-button"], size="sm")
            settings_btn = gr.Button("Settings", elem_classes=["nav-button"], size="sm")

            gr.HTML('<div class="nav-divider"></div>')

            # User section
            with gr.Column(elem_classes=["user-section"]):
                user_label = gr.Markdown("**Guest User**", elem_classes=["user-email"])
                login_btn = gr.Button("Sign in with Google", elem_classes=["login-btn"], size="sm", visible=True)
                logout_btn = gr.Button("Sign Out", elem_classes=["logout-btn"], size="sm", visible=False)

        # Main content area - full width
        with gr.Column(elem_classes=["main-content"]):
            # Header
            with gr.Column(elem_classes=["app-header"]):
                gr.Markdown("# Clip Cutter")
                gr.Markdown("Upload a video and describe what you want to find. AI will analyze and extract matching clips.", elem_classes=["app-subtitle"])

            # Main interface in tabs
            with gr.Tabs() as tabs:
                with gr.TabItem("Analyze", id="home"):
                    # Video upload section - larger
                    video_input = gr.Video(
                        label="Upload Video",
                        sources=["upload"],
                        height=450,
                    )

                    with gr.Row():
                        clear_btn = gr.Button("Clear Video", variant="secondary", size="sm")

                    with gr.Row():
                        with gr.Column(scale=2):
                            query_input = gr.Textbox(
                                label="What do you want to find?",
                                placeholder="e.g., every time #3 ran a route, all completed passes, every touchdown",
                                lines=3,
                            )

                        with gr.Column(scale=1):
                            padding_slider = gr.Slider(
                                minimum=0,
                                maximum=10,
                                value=2,
                                step=0.5,
                                label="Clip Padding (seconds)",
                                info="Extra time before/after each clip",
                            )

                    with gr.Row():
                        analyze_btn = gr.Button("Analyze Video", variant="primary", size="lg", scale=2)
                        cancel_btn = gr.Button("Cancel", variant="stop", size="lg", scale=1)

                    with gr.Row():
                        with gr.Column(scale=1):
                            status_output = gr.Textbox(
                                label="Status",
                                interactive=False,
                                lines=2,
                            )

                        with gr.Column(scale=2):
                            timestamps_output = gr.Textbox(
                                label="Found Timestamps",
                                interactive=False,
                                lines=8,
                            )

                    gr.Markdown("### Results")

                    video_output = gr.Video(
                        label="Extracted Clips",
                        height=500,
                    )

                with gr.TabItem("History", id="history", visible=True):
                    gr.Markdown("### Analysis History")
                    history_status = gr.Markdown("*Sign in to view your analysis history.*")
                    history_table = gr.Dataframe(
                        headers=["Date", "Video", "Query", "Clips", "Status"],
                        datatype=["str", "str", "str", "number", "str"],
                        interactive=False,
                        elem_classes=["history-table"],
                    )
                    refresh_history_btn = gr.Button("Refresh History", variant="secondary", size="sm")

                with gr.TabItem("Settings", id="settings", visible=True):
                    gr.Markdown("### Settings")
                    with gr.Column():
                        gr.Markdown("#### Default Preferences")
                        default_padding = gr.Slider(
                            minimum=0,
                            maximum=10,
                            value=2,
                            step=0.5,
                            label="Default Clip Padding (seconds)",
                            info="Default extra time before/after each clip",
                        )

                        theme_dropdown = gr.Dropdown(
                            choices=["Light", "Dark", "System"],
                            value="Dark",
                            label="Theme",
                            info="Choose your preferred color scheme",
                        )

                        gr.Markdown("#### API Configuration")
                        user_api_key = gr.Textbox(
                            label="Gemini API Key (Optional)",
                            placeholder="Leave blank to use system default",
                            type="password",
                            info="Provide your own API key for higher rate limits",
                        )

                        save_settings_btn = gr.Button("Save Settings", variant="primary")
                        settings_status = gr.Markdown("")

        # Event handlers

        # Analyze video
        def analyze_with_session(video, query, padding, session):
            return process_video(video, query, padding, session)

        analyze_btn.click(
            fn=analyze_with_session,
            inputs=[video_input, query_input, padding_slider, session_state],
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

        # Navigation
        home_btn.click(fn=lambda: gr.Tabs(selected="home"), outputs=[tabs])
        history_btn.click(fn=lambda: gr.Tabs(selected="history"), outputs=[tabs])
        settings_btn.click(fn=lambda: gr.Tabs(selected="settings"), outputs=[tabs])

        # History
        def refresh_history(session):
            rows, status = load_history(session)
            return rows, status

        refresh_history_btn.click(
            fn=refresh_history,
            inputs=[session_state],
            outputs=[history_table, history_status],
        )

        # Auto-load history when switching to history tab
        history_btn.click(
            fn=refresh_history,
            inputs=[session_state],
            outputs=[history_table, history_status],
        )

        # Settings
        def save_settings_with_session(padding, theme, api_key, session):
            return save_settings(padding, theme, api_key, session)

        save_settings_btn.click(
            fn=save_settings_with_session,
            inputs=[default_padding, theme_dropdown, user_api_key, session_state],
            outputs=[settings_status],
        )

        # Load settings when switching to settings tab
        def load_settings_for_tab(session):
            return load_settings(session)

        settings_btn.click(
            fn=load_settings_for_tab,
            inputs=[session_state],
            outputs=[default_padding, theme_dropdown, user_api_key],
        )

        # Auth handlers
        def handle_login():
            if not settings.supabase_configured:
                gr.Info("Authentication not configured. Please set up Supabase to enable sign-in.")
                return
            # Redirect to login endpoint
            gr.Info("Redirecting to Google sign-in... (Navigate to /auth/login)")

        def handle_logout(session):
            if session:
                auth_funcs = get_auth_functions()
                if auth_funcs:
                    from auth import handle_logout as do_logout
                    do_logout(session)
            return None, "**Guest User**", gr.update(visible=True), gr.update(visible=False)

        login_btn.click(fn=handle_login)

        logout_btn.click(
            fn=handle_logout,
            inputs=[session_state],
            outputs=[session_state, user_label, login_btn, logout_btn],
        )

        # Update user display on load
        def on_load(request: gr.Request):
            # Try to get session from cookie
            session_id = None
            if request:
                cookies = request.cookies
                session_id = cookies.get("session_id")

            user_text, show_login, show_logout = get_user_display(session_id)
            return session_id, user_text, gr.update(visible=show_login), gr.update(visible=show_logout)

        app.load(
            fn=on_load,
            outputs=[session_state, user_label, login_btn, logout_btn],
        )

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch()
