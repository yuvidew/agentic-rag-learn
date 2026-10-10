import os
from dotenv import load_dotenv
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "Enterprise IT Support Agentic RAG Copilot"
    app_env: str = "development"
    groq_api_key: str = ""
    tavily_api_key: str = ""
    pinecone_api_key: str = os.getenv("PINECODE_API_KEY")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_KEY")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE")
    embedding_model: str = os.getenv("EMBEDDING_MODEL")
    groq_model: str = os.getenv("TEXT_MODEL")
    top_k: int = 4
    max_retries: int = 1
    admin_api_key: str = os.getenv("ADMIN_API_KEY")
    db_name: str = os.getenv("DB_NAME")
    upload_dir: str = str(BASE_DIR / "uploads")
    sample_kb_dir: str = str(BASE_DIR / "data" / "sample_kb")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    @property
    def audit_db_path(self) -> str:
        path = Path(self.db_name)
        if not path.is_absolute():
            path = BASE_DIR / "data" / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

@lru_cache
def get_settings() -> Settings:
    return Settings()
