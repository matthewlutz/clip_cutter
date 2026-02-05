"""Authentication using Supabase Auth with Google OAuth."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import create_client, Client

from core.config import settings
from models.schemas import AuthState, User


def get_auth_client() -> Optional[Client]:
    """Get Supabase client for authentication."""
    if not settings.supabase_configured:
        return None
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_google_oauth_url(redirect_url: str) -> Optional[str]:
    """Get the Google OAuth URL for sign-in."""
    client = get_auth_client()
    if not client:
        return None

    try:
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url},
        })
        return response.url if response else None
    except Exception as e:
        print(f"Error getting OAuth URL: {e}")
        return None


def exchange_code_for_session(code: str) -> Optional[AuthState]:
    """Exchange an OAuth code for a session."""
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


def get_current_user(access_token: str) -> Optional[User]:
    """Get the current user from an access token."""
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
    """Refresh an expired session."""
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
    """Sign out the current user."""
    client = get_auth_client()
    if not client:
        return False

    try:
        client.auth.sign_out()
        return True
    except Exception as e:
        print(f"Error signing out: {e}")
        return False


def verify_access_token(access_token: Optional[str]) -> bool:
    """Check if an access token is valid."""
    if not access_token:
        return False
    user = get_current_user(access_token)
    return user is not None
