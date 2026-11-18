# file config.py - Managing settings and keys.

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Default operating mode: "local" (Ollama) or "cloud" (OpenAI/Azure)
    DEFAULT_LLM_MODE: str = locals

    # Settings for the cloud (for Sela Software Laboratories & CSP Integrate Technology)
    OPENAI_API_KEY: str = "sk-placeholder" 
    CLOUD_MODEL_NAME: str = "gpt-4o-mini"

    # Settings for a closed countur
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_MODEL_NAME: str = "qwen2.5-coder:7b"

    # Infractructure
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    # Config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() 
