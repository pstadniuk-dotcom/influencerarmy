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

    # Instagram Graph API (Meta)
    meta_app_id: str = ""
    meta_app_secret: str = ""

    # TikTok Content Posting API
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""

    # Output & data
    output_dir: Path = Path("./output")
    data_dir: Path = Path("./data")

    # Content queue
    auto_approve: bool = False

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


settings = Settings()
