from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    GROQ_API_KEY: str
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    CHROMA_DB_DIR: str = "./chroma_db"
    DATABASE_URL: str = ""
    JWT_SECRET: str = "dev-secret-change-this-in-production"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


if __name__ == "__main__":
    print("ENV file path used:", ENV_FILE)
    print("ENV file exists:", ENV_FILE.exists())
    print("GROQ_API_KEY loaded:", bool(settings.GROQ_API_KEY))
    print("LLM_MODEL:", settings.LLM_MODEL)
    print("VISION_MODEL:", settings.VISION_MODEL)
    print("CHROMA_DB_DIR:", settings.CHROMA_DB_DIR)
    print("config.py OK")