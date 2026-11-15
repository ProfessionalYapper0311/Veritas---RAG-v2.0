from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS S3 Storage
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""  # optional temp aws cred
    s3_bucket: str = Field(
        default="",
        validation_alias=AliasChoices(
            "s3_bucket", "your_s3_bucket_name", "S3_BUCKET", "YOUR_S3_BUCKET_NAME"
        ),
    )

    # Database
    database_url: str = ""

    # Google Gemini Models
    gemini_api_key: str = ""
    gemini_embed_model: str = "models/gemini-embedding-001"
    gemini_chat_model: str = "gemini-3.8-flash"
    embed_dimension: int = 1024

    # Alias for app/vector.py compatibility
    @property
    def embed_dim(self) -> int:
        return self.embed_dimension

    # Uploads & Pinecone Vector Store
    max_upload_bytes: int = 10485760  # 10MB
    pinecone_api_key: str = ""
    pinecone_index_name: str = "veritas--rag-gemini-index"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_ready_timeout: int = 180
    min_relevance: float = 0.25

    # Human-in-the-Loop & Memory
    hitl_enabled: bool = True
    memory_turns: int = 6

    # RIUS Observability
    rius_api_key: str = ""
    rius_service_name: str = "veritas--rag"
    rius_disabled: bool = False
    rius_capture_content: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()