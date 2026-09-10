from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    playwright_headless: bool = True
    scraper_timeout: int = 30
    cache_ttl: int = 60
    demo_mode: bool = False
    log_level: str = "INFO"
    ignav_api_key: str = "ignav_JaygezSb88PrlIBq2sAU9ftpL1YzyqE5"
    database_url: str = ""
    supabase_url: str = ""
    supabase_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
