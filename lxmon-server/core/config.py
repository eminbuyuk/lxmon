"""
Core configuration for lxmon-server using Pydantic settings.
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://lxmon:lxmon@localhost:5432/lxmon")

    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # CORS settings
    ALLOWED_ORIGINS_STR: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS from comma-separated string."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

    # API Keys for agents
    AGENT_API_KEYS_STR: str = os.getenv("AGENT_API_KEYS", "agent-key-1,agent-key-2")
    
    @property
    def AGENT_API_KEYS(self) -> List[str]:
        """Parse AGENT_API_KEYS from comma-separated string."""
        return [key.strip() for key in self.AGENT_API_KEYS_STR.split(",") if key.strip()]

    # Multi-tenant settings
    DEFAULT_TENANT_ID: str = "default"

    # Command execution settings
    MAX_COMMAND_TIMEOUT: int = 300  # 5 minutes
    ALLOWED_COMMANDS_STR: str = os.getenv("ALLOWED_COMMANDS", "systemctl,service,docker,nginx,apache2,ps,top,df,free,uptime,whoami,hostname,date,echo")
    
    @property
    def ALLOWED_COMMANDS(self) -> List[str]:
        """Parse ALLOWED_COMMANDS from comma-separated string."""
        return [cmd.strip() for cmd in self.ALLOWED_COMMANDS_STR.split(",") if cmd.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
