# Settings and Environment configuration
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()
\n