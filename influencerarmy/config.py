from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Higgsfield Cloud API
    higgsfield_api_key: str = ""
    higgsfield_secret: str = ""
    higgsfield_base_url: str = "https://cloud.higgsfield.ai"

    # Google Gemini API (Nano Banana 2)
    google_api_key: str = ""
    nano_banana_model: str = "gemini-3.1-flash-image-preview"

    # Output
    output_dir: Path = Path("./output")

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


settings = Settings()
