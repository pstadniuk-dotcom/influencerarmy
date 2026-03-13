from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


# --- Higgsfield models ---


class ImageQuality(str, Enum):
    HD = "1080p"
    SD = "720p"


class VideoQuality(str, Enum):
    LITE = "lite"
    STANDARD = "standard"
    TURBO = "turbo"


class GenerationStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NSFW = "nsfw"


class HiggsImageRequest(BaseModel):
    prompt: str
    quality: ImageQuality = ImageQuality.HD
    character_id: str | None = None
    style_id: str | None = None


class HiggsVideoRequest(BaseModel):
    image_url: str
    motion_id: str
    prompt: str = ""
    quality: VideoQuality = VideoQuality.STANDARD


class HiggsJobResult(BaseModel):
    job_set_id: str
    status: GenerationStatus = GenerationStatus.QUEUED
    download_urls: list[str] = Field(default_factory=list)


class HiggsCharacter(BaseModel):
    name: str
    character_id: str = ""
    image_urls: list[str] = Field(default_factory=list)


# --- Nano Banana 2 models ---


class NanoBananaRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"
    reference_images: list[str] = Field(default_factory=list, max_length=14)


class NanoBananaResult(BaseModel):
    image_path: Path
    text_response: str = ""


# --- Influencer models ---


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"


class ContentType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    STORY = "story"
    REEL = "reel"


class InfluencerProfile(BaseModel):
    name: str
    handle: str
    niche: str
    character_id: str = ""
    style_description: str = ""
    platforms: list[Platform] = Field(default_factory=lambda: [Platform.INSTAGRAM])
    reference_images: list[str] = Field(default_factory=list)


class ContentBrief(BaseModel):
    influencer: InfluencerProfile
    content_type: ContentType
    prompt: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    motion_id: str = ""
