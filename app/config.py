"""
Configuration settings for the Face Recognition Microservice.

Reads settings from environment variables and a .env file.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""

    # API Key for securing the service
    API_KEY: str

    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI: str = Field(
        default="mysql+mysqlconnector://user:password@localhost/face_recognition",
        description="SQLAlchemy database URI"
    )

    # Face recognition parameters
    SIMILARITY_THRESHOLD: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Threshold for face verification similarity"
    )
    MAX_IMAGES_PER_REGISTRATION: int = Field(
        default=10,
        gt=0,
        description="Maximum number of images allowed per registration request"
    )

    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR)"
    )
    LOG_FILE: str = Field(
        default="logs/app.log",
        description="Path to the log file"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Create a single instance of the settings to be used throughout the application
settings = Settings()
