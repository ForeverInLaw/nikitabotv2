"""
Application configuration settings.
Loads configuration from environment variables with fallback defaults.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    # Bot Configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "7898779323:AAGODe-tArATVTcnJKiqkJsD6TrKo7kK9IY")
    ADMIN_CHAT_ID: Optional[str] = os.getenv("ADMIN_CHAT_ID", "-1002600422954")
    
    # Database Configuration  
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "telegram_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres") 
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    ORDER_TIMEOUT_HOURS: int = int(os.getenv("ORDER_TIMEOUT_HOURS", "24"))
    
    # Web Server (if needed for webhooks)
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8081"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "123123")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL."""
        password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else "postgres"
        return f"postgresql+asyncpg://{self.DB_USER}{password_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL for Alembic."""
        password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else "postgres"
        return f"postgresql://{self.DB_USER}{password_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property 
    def REDIS_URL(self) -> str:
        """Construct Redis URL."""
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    def validate(self) -> None:
        """Validate critical settings."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD environment variable is required")


# Create global settings instance
settings = Settings()

# Validate settings on import
try:
    settings.validate()
except ValueError as e:
    import logging
    logging.critical(f"Configuration error: {e}")
    # Don't raise here to allow importing in development

