"""Data models for the AI Influencer Agency."""

from datetime import datetime
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


# --- Platform & Social models ---


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class ContentType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    STORY = "story"
    REEL = "reel"
    CAROUSEL = "carousel"


class AccountStatus(str, Enum):
    NOT_CREATED = "not_created"
    CREATED = "created"
    CONNECTED = "connected"


class SocialAccount(BaseModel):
    """A connected social media account for an influencer."""
    platform: Platform
    status: AccountStatus = AccountStatus.NOT_CREATED
    username: str = ""
    # Instagram Graph API
    ig_user_id: str = ""
    ig_access_token: str = ""
    ig_page_id: str = ""
    # TikTok Content Posting API
    tiktok_open_id: str = ""
    tiktok_access_token: str = ""


# --- Identity & Character Consistency ---


class IdentityConfig(BaseModel):
    """Defines the visual identity of an AI influencer for consistency."""
    # Core appearance anchors
    reference_images: list[str] = Field(
        default_factory=list,
        description="Paths to reference images that define this person's appearance (max 6 recommended)",
    )
    # Higgsfield character ID for video consistency
    higgsfield_character_id: str = ""
    # Detailed character description for prompt engineering
    character_dna: str = Field(
        default="",
        description=(
            "Detailed physical description: age range, ethnicity, hair color/style, "
            "eye color, build, distinguishing features. Used as prompt anchor."
        ),
    )
    # Default style
    default_style: str = "professional social media photography, natural lighting, high quality"
    # Aspect ratios per platform
    platform_aspect_ratios: dict[str, str] = Field(
        default_factory=lambda: {
            "instagram": "1:1",
            "instagram_story": "9:16",
            "instagram_reel": "9:16",
            "tiktok": "9:16",
        }
    )


class InfluencerProfile(BaseModel):
    """A complete AI influencer profile."""
    name: str
    handle: str
    niche: str
    bio: str = ""
    identity: IdentityConfig = Field(default_factory=IdentityConfig)
    accounts: dict[str, SocialAccount] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# --- Content Queue & Quality Control ---


class QCStatus(str, Enum):
    """Quality control status for content in the pipeline."""
    GENERATING = "generating"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    FAILED = "failed"


class ContentItem(BaseModel):
    """A piece of content in the pipeline queue."""
    id: str = ""
    influencer_handle: str
    content_type: ContentType
    platform: Platform
    prompt: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    motion_id: str = ""

    # Generated assets
    image_path: str = ""
    video_path: str = ""

    # Quality control
    qc_status: QCStatus = QCStatus.GENERATING
    qc_notes: str = ""
    rejection_reason: str = ""

    # Posting
    posted_at: str = ""
    post_id: str = ""
    post_url: str = ""

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProductPlacement(BaseModel):
    """Defines a product to be modeled by an influencer."""
    product_name: str
    product_description: str
    product_image_path: str = ""
    placement_instructions: str = Field(
        default="",
        description="How the product should appear (e.g. 'holding the product', 'wearing the outfit')",
    )
    brand_name: str = ""
    brand_guidelines: str = ""


class ContentBrief(BaseModel):
    """A content creation brief that feeds the pipeline."""
    influencer_handle: str
    content_type: ContentType
    platform: Platform = Platform.INSTAGRAM
    prompt: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    motion_id: str = ""
    product: ProductPlacement | None = None
    auto_post: bool = False
