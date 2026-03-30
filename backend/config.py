"""
Configuration for Trading Journal backend.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Personal DB (new Supabase project)
    personal_supabase_url: str = ""
    personal_supabase_key: str = ""
    
    # Arete DB (read-only access)
    arete_supabase_url: str = "https://goptgqfllyutklnyjvoj.supabase.co"
    arete_supabase_key: str = ""  # Load from keychain
    
    # AI
    ai_provider: str = "anthropic"  # or "venice"
    anthropic_api_key: str = ""
    
    # App
    debug: bool = False
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
