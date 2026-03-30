"""
Database clients for Trading Journal.
Dual database setup: Personal (read/write) + Arete (read-only).
"""

from supabase import create_client, Client
from config import settings


def get_personal_client() -> Client:
    """Get client for personal trading database (read/write)."""
    return create_client(
        settings.personal_supabase_url,
        settings.personal_supabase_key
    )


def get_arete_client() -> Client:
    """Get client for Arete database (read-only)."""
    return create_client(
        settings.arete_supabase_url,
        settings.arete_supabase_key
    )


# Singleton instances
_personal_client: Client | None = None
_arete_client: Client | None = None


def personal_db() -> Client:
    """Get or create personal database client."""
    global _personal_client
    if _personal_client is None:
        _personal_client = get_personal_client()
    return _personal_client


def arete_db() -> Client:
    """Get or create Arete database client."""
    global _arete_client
    if _arete_client is None:
        _arete_client = get_arete_client()
    return _arete_client
