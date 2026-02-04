"""Authentication using Supabase Auth with Google OAuth."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import create_client, Client

from config import settings
from models import AuthState, User


def get_auth_client() -> Optional[Client]:
    """Get Supabase client for authentication."""
    if not settings.supabase_configured:
        return None
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_google_oauth_url(redirect_url: str) -> Optional[str]:
    """
    Get the Google OAuth URL for sign-in.

    Args:
        redirect_url: URL to redirect to after authentication

    Returns:
        OAuth URL to redirect user to, or None if not configured
    """
    client = get_auth_client()
    if not client:
        return None

    try:
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url,
            },
        })
        return response.url if response else None
    except Exception as e:
        print(f"Error getting OAuth URL: {e}")
        return None


def exchange_code_for_session(code: str) -> Optional[AuthState]:
    """
    Exchange an OAuth code for a session.

    Args:
        code: OAuth authorization code from callback

    Returns:
        AuthState with user info and tokens, or None if failed
    """
    client = get_auth_client()
    if not client:
        return None

    try:
        response = client.auth.exchange_code_for_session({"auth_code": code})

        if response and response.user:
            user = User(
                id=UUID(response.user.id),
                email=response.user.email,
                created_at=response.user.created_at or datetime.utcnow(),
                last_sign_in_at=response.user.last_sign_in_at,
            )
            return AuthState(
                is_authenticated=True,
                user=user,
                access_token=response.session.access_token if response.session else None,
            )
        return None
    except Exception as e:
        print(f"Error exchanging code for session: {e}")
        return None


def sign_in_with_token(access_token: str, refresh_token: str) -> Optional[AuthState]:
    """
    Sign in with existing tokens (for session restoration).

    Args:
        access_token: JWT access token
        refresh_token: Refresh token

    Returns:
        AuthState with user info, or None if tokens are invalid
    """
    client = get_auth_client()
    if not client:
        return None

    try:
        response = client.auth.set_session(access_token, refresh_token)

        if response and response.user:
            user = User(
                id=UUID(response.user.id),
                email=response.user.email,
                created_at=response.user.created_at or datetime.utcnow(),
                last_sign_in_at=response.user.last_sign_in_at,
            )
            return AuthState(
                is_authenticated=True,
                user=user,
                access_token=response.session.access_token if response.session else access_token,
            )
        return None
    except Exception as e:
        print(f"Error signing in with token: {e}")
        return None


def get_current_user(access_token: str) -> Optional[User]:
    """
    Get the current user from an access token.

    Args:
        access_token: JWT access token

    Returns:
        User object or None if token is invalid
    """
    client = get_auth_client()
    if not client:
        return None

    try:
        response = client.auth.get_user(access_token)

        if response and response.user:
            return User(
                id=UUID(response.user.id),
                email=response.user.email,
                created_at=response.user.created_at or datetime.utcnow(),
                last_sign_in_at=response.user.last_sign_in_at,
            )
        return None
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None


def refresh_session(refresh_token: str) -> Optional[AuthState]:
    """
    Refresh an expired session.

    Args:
        refresh_token: Refresh token

    Returns:
        New AuthState with updated tokens, or None if refresh failed
    """
    client = get_auth_client()
    if not client:
        return None

    try:
        response = client.auth.refresh_session(refresh_token)

        if response and response.user:
            user = User(
                id=UUID(response.user.id),
                email=response.user.email,
                created_at=response.user.created_at or datetime.utcnow(),
                last_sign_in_at=response.user.last_sign_in_at,
            )
            return AuthState(
                is_authenticated=True,
                user=user,
                access_token=response.session.access_token if response.session else None,
            )
        return None
    except Exception as e:
        print(f"Error refreshing session: {e}")
        return None


def sign_out(access_token: str) -> bool:
    """
    Sign out the current user.

    Args:
        access_token: JWT access token

    Returns:
        True if sign out succeeded, False otherwise
    """
    client = get_auth_client()
    if not client:
        return False

    try:
        # Set the session first so we can sign out
        client.auth.sign_out()
        return True
    except Exception as e:
        print(f"Error signing out: {e}")
        return False


def is_authenticated(access_token: Optional[str]) -> bool:
    """
    Check if an access token is valid.

    Args:
        access_token: JWT access token to validate

    Returns:
        True if token is valid, False otherwise
    """
    if not access_token:
        return False

    user = get_current_user(access_token)
    return user is not None


# =============================================================================
# Session Management for Gradio
# =============================================================================

class SessionManager:
    """
    Manages user sessions for the Gradio app.

    This is a simple in-memory session store. For production,
    consider using Redis or another distributed cache.
    """

    def __init__(self):
        self._sessions: dict[str, AuthState] = {}

    def create_session(self, session_id: str, auth_state: AuthState) -> None:
        """Store a session."""
        self._sessions[session_id] = auth_state

    def get_session(self, session_id: str) -> Optional[AuthState]:
        """Retrieve a session."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, auth_state: AuthState) -> None:
        """Update a session."""
        if session_id in self._sessions:
            self._sessions[session_id] = auth_state

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self._sessions.pop(session_id, None)

    def is_authenticated(self, session_id: str) -> bool:
        """Check if a session is authenticated."""
        session = self.get_session(session_id)
        return session is not None and session.is_authenticated

    def get_user(self, session_id: str) -> Optional[User]:
        """Get the user from a session."""
        session = self.get_session(session_id)
        return session.user if session else None


# Global session manager instance
session_manager = SessionManager()


# =============================================================================
# Gradio Auth Helpers
# =============================================================================

def get_login_url(request_url: str) -> Optional[str]:
    """
    Get the Google login URL for the Gradio app.

    Args:
        request_url: Base URL of the request (for redirect)

    Returns:
        URL to redirect user to for Google OAuth
    """
    # Construct callback URL
    callback_url = f"{request_url.rstrip('/')}/auth/callback"
    return get_google_oauth_url(callback_url)


def handle_oauth_callback(code: str, session_id: str) -> AuthState:
    """
    Handle the OAuth callback and create a session.

    Args:
        code: OAuth authorization code
        session_id: Session ID to store auth state

    Returns:
        AuthState (authenticated or not)
    """
    auth_state = exchange_code_for_session(code)

    if auth_state and auth_state.is_authenticated:
        session_manager.create_session(session_id, auth_state)
        return auth_state

    return AuthState(is_authenticated=False)


def handle_logout(session_id: str) -> bool:
    """
    Handle logout for a session.

    Args:
        session_id: Session ID to log out

    Returns:
        True if logout succeeded
    """
    session = session_manager.get_session(session_id)

    if session and session.access_token:
        sign_out(session.access_token)

    session_manager.delete_session(session_id)
    return True


def get_auth_state(session_id: str) -> AuthState:
    """
    Get the current auth state for a session.

    Args:
        session_id: Session ID

    Returns:
        Current AuthState
    """
    session = session_manager.get_session(session_id)
    return session or AuthState(is_authenticated=False)


def require_auth(session_id: str) -> Optional[User]:
    """
    Decorator helper to require authentication.

    Args:
        session_id: Session ID

    Returns:
        User if authenticated, None otherwise
    """
    auth_state = get_auth_state(session_id)
    if auth_state.is_authenticated:
        return auth_state.user
    return None
