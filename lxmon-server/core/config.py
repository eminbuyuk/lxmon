"""
Core configuration for lxmon-server using Pydantic settings.
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://lxmon:lxmon@localhost:5432/lxmon")

    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # API Keys for agents
    AGENT_API_KEYS: List[str] = os.getenv("AGENT_API_KEYS", "agent-key-1,agent-key-2").split(",")

    # Multi-tenant settings
    DEFAULT_TENANT_ID: str = "default"

    # Command execution settings
    MAX_COMMAND_TIMEOUT: int = 300  # 5 minutes
    ALLOWED_COMMANDS: List[str] = [
        "systemctl",
        "service",
        "docker",
        "nginx",
        "apache2",
        "ps",
        "top",
        "df",
        "free",
        "uptime",
        "whoami",
        "hostname",
        "date",
        "echo"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
