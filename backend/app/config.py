from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://chiefos:chiefos_dev_password@localhost:5432/chiefos"

    # Auth
    secret_key: str = "change-this-to-a-random-secret-key"
    google_client_id: str = ""
    google_client_secret: str = ""

    # External
    openai_api_key: str = ""
    ai_base_url: str | None = None  # None=OpenAI, or "https://api.groq.com/openai/v1" for Groq
    ai_model: str = "llama-3.1-70b-versatile"  # Default to free Groq model
    resend_api_key: str = ""
    from_email: str = "briefs@yourdomain.com"

    # URLs
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
