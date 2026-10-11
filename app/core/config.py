from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # OLLAMA_URL se acepta como alias para no romper despliegues existentes.
    ollama_host: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("ollama_host", "ollama_url"),
    )
    ollama_model: str = "gemma3:4b"
    ollama_timeout: float = 120.0

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
