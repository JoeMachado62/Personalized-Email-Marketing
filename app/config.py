"""
Application configuration using Pydantic settings.
Loads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Sales Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"
    
    # API Keys - Primary LLM Provider
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Additional LLM Provider Keys (for multi-provider support)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # LLM Service Configuration
    LLM_CACHE_SIZE: int = 1000
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_RATE_LIMIT_PER_MINUTE: int = 50
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT_SECONDS: int = 30
    
    # Content Generation Settings
    DEFAULT_MAX_TOKENS: int = 400
    DEFAULT_TEMPERATURE: float = 0.7
    MAX_COST_PER_RECORD: float = 0.02
    QUALITY_THRESHOLD: float = 70.0
    
    # Limits
    MAX_CONCURRENT_ENRICHMENTS: int = 3
    MAX_FILE_SIZE_MB: int = 10
    MAX_RECORDS_PER_JOB: int = 100000  # Increased to handle larger datasets
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3001,http://localhost:8001"
    
    # Paths
    UPLOAD_DIR: Path = Path("./uploads")
    OUTPUT_DIR: Path = Path("./outputs")
    DATA_DIR: Path = Path("./data")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env

settings = Settings()

# Create directories
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.OUTPUT_DIR.mkdir(exist_ok=True)
settings.DATA_DIR.mkdir(exist_ok=True)