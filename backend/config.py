"""
Configuration for Trading Journal backend.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).with_name(".env")


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
    
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
