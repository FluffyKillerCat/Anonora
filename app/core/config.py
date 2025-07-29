from pydantic_settings import BaseSettings
from pydantic import Field, validator, field_validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    app_name: str = Field(default="Document Intelligence Platform", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    secret_key: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440, description="Token expiration in minutes")

    supabase_url: str = Field(default="", description="Supabase URL")
    supabase_key: str = Field(default="", description="Supabase API key")
    database_url: str = Field(default="", description="Database connection URL")

    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")

    celery_broker_url: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", description="Celery result backend URL")

    upload_dir: str = Field(default="uploads", description="File upload directory")
    max_file_size: int = Field(default=50 * 1024 * 1024, ge=1024, description="Maximum file size in bytes")
    allowed_extensions: List[str]

    @field_validator("allowed_extensions", mode="before")
    def split_extensions(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    sentence_transformer_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    zero_shot_model: str = Field(default="facebook/bart-large-mnli", description="Zero-shot classification model")

    presidio_language: str = Field(default="en", description="Presidio language")

    vector_dimension: int = Field(default=384, ge=128, le=1536, description="Vector embedding dimension")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold for search")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()