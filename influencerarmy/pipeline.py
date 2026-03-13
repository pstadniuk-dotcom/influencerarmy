"""Content pipeline - orchestrates image generation and video creation for influencer content."""

import asyncio
from pathlib import Path

from influencerarmy.config import settings
from influencerarmy.higgsfield import HiggsFieldClient
from influencerarmy.models import (
    ContentBrief,
    ContentType,
    GenerationStatus,
    HiggsJobResult,
    NanoBananaResult,
)
from influencerarmy.nano_banana import NanoBananaClient


class ContentPipeline:
    """Orchestrates the full content creation workflow.

    1. Generate base images with Nano Banana 2 (character-consistent photos)
    2. Optionally animate images into video with Higgsfield
    3. Save outputs organized by influencer
    """

    def __init__(
        self,
        nano_banana: NanoBananaClient | None = None,
        higgsfield: HiggsFieldClient | None = None,
    ):
        self.nb = nano_banana or NanoBananaClient()
        self.hf = higgsfield or HiggsFieldClient()

    async def execute_brief(self, brief: ContentBrief) -> dict:
        """Execute a content brief end-to-end.

        Returns a dict with paths to generated assets and metadata.
        """
        influencer = brief.influencer
        out_dir = settings.ensure_output_dir() / influencer.handle
        out_dir.mkdir(parents=True, exist_ok=True)

        result: dict = {
            "influencer": influencer.handle,
            "content_type": brief.content_type.value,
            "caption": brief.caption,
            "hashtags": brief.hashtags,
            "assets": [],
        }

        # Step 1: Generate the base image with Nano Banana 2
        image_result = self._generate_image(brief, out_dir)
        result["assets"].append({"type": "image", "path": str(image_result.image_path)})

        # Step 2: If video content, animate with Higgsfield
        if brief.content_type in (ContentType.VIDEO, ContentType.REEL):
            video_result = await self._generate_video(brief, image_result, out_dir)
            if video_result:
                result["assets"].extend(video_result)

        return result

    def _generate_image(self, brief: ContentBrief, out_dir: Path) -> NanoBananaResult:
        """Generate the base image using Nano Banana 2."""
        reference_images = brief.influencer.reference_images or []
        style_hint = brief.influencer.style_description or "professional social media photography"

        full_prompt = (
            f"{brief.prompt}. "
            f"Style: {style_hint}. "
            "Photorealistic, high quality, Instagram-worthy photo."
        )

        import uuid
        output_path = out_dir / f"photo_{uuid.uuid4().hex[:8]}.png"

        return self.nb.generate_image(
            prompt=full_prompt,
            output_path=output_path,
            reference_images=reference_images,
        )

    async def _generate_video(
        self,
        brief: ContentBrief,
        image_result: NanoBananaResult,
        out_dir: Path,
    ) -> list[dict]:
        """Animate the generated image into a video via Higgsfield."""
        if not brief.motion_id:
            return []

        # The image needs to be publicly accessible for Higgsfield.
        # In production, you'd upload to cloud storage first.
        # For now, we use the Higgsfield image generation + video pipeline.
        try:
            # First, generate an image through Higgsfield to get a hosted URL
            hf_image_job = await self.hf.generate_image(
                prompt=brief.prompt,
                character_id=brief.influencer.character_id or None,
            )
            hf_image_result = await self.hf.wait_for_completion(hf_image_job.job_set_id)

            if (
                hf_image_result.status != GenerationStatus.COMPLETED
                or not hf_image_result.download_urls
            ):
                return []

            image_url = hf_image_result.download_urls[0]

            # Now create the video from the hosted image
            video_job = await self.hf.generate_video(
                image_url=image_url,
                motion_id=brief.motion_id,
                prompt=brief.prompt,
            )
            video_result = await self.hf.wait_for_completion(video_job.job_set_id)

            if (
                video_result.status != GenerationStatus.COMPLETED
                or not video_result.download_urls
            ):
                return []

            assets = []
            for i, url in enumerate(video_result.download_urls):
                import uuid
                video_path = out_dir / f"video_{uuid.uuid4().hex[:8]}.mp4"
                await self.hf.download_file(url, str(video_path))
                assets.append({"type": "video", "path": str(video_path)})

            return assets

        except Exception as e:
            print(f"Video generation failed: {e}")
            return []

    async def create_photo_set(
        self,
        handle: str,
        prompts: list[str],
        style: str = "professional Instagram photography",
        reference_images: list[str] | None = None,
    ) -> list[NanoBananaResult]:
        """Generate a batch of photos for an influencer.

        Useful for creating a consistent set of images for a content calendar.
        """
        out_dir = settings.ensure_output_dir() / handle
        out_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for prompt in prompts:
            full_prompt = f"{prompt}. Style: {style}."
            import uuid
            output_path = out_dir / f"photo_{uuid.uuid4().hex[:8]}.png"
            result = self.nb.generate_image(
                prompt=full_prompt,
                output_path=output_path,
                reference_images=reference_images or [],
            )
            results.append(result)

        return results

    async def setup_character(
        self, name: str, reference_image_urls: list[str]
    ) -> str:
        """Create a Higgsfield character for consistent video generation.

        Returns the character_id.
        """
        character = await self.hf.create_character(name, reference_image_urls)
        return character.character_id

    async def close(self) -> None:
        await self.hf.close()
