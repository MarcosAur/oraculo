from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./oraculo.db"
    SECRET_KEY: str = "super_secret_key_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: str | None = None
    TOP_K: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
