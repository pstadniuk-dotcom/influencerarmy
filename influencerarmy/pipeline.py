"""Content pipeline - orchestrates generation, QC, and posting for influencer content."""

import asyncio
from pathlib import Path

from influencerarmy.agency import Agency
from influencerarmy.config import settings
from influencerarmy.higgsfield import HiggsFieldClient
from influencerarmy.identity import IdentityManager
from influencerarmy.instagram import InstagramClient
from influencerarmy.models import (
    AccountStatus,
    ContentBrief,
    ContentItem,
    ContentType,
    GenerationStatus,
    NanoBananaResult,
    Platform,
    QCStatus,
)
from influencerarmy.nano_banana import NanoBananaClient
from influencerarmy.queue import ContentQueue
from influencerarmy.tiktok import TikTokClient


class ContentPipeline:
    """Full content creation and publishing pipeline.

    Flow:
      1. Create content brief
      2. Generate base image with Nano Banana 2 (character-consistent)
      3. Optionally generate video with Higgsfield
      4. Queue for quality control review
      5. On approval, post to connected social accounts
    """

    def __init__(
        self,
        agency: Agency | None = None,
        queue: ContentQueue | None = None,
        nano_banana: NanoBananaClient | None = None,
        higgsfield: HiggsFieldClient | None = None,
        identity_mgr: IdentityManager | None = None,
    ):
        self.agency = agency or Agency()
        self.queue = queue or ContentQueue()
        self.nb = nano_banana or NanoBananaClient()
        self.hf = higgsfield or HiggsFieldClient()
        self.identity = identity_mgr or IdentityManager()

    # --- Main entry point ---

    async def create_content(self, brief: ContentBrief) -> ContentItem:
        """Execute a content brief: generate assets and queue for review.

        Returns the ContentItem (in PENDING_REVIEW status).
        """
        profile = self.agency.get_influencer(brief.influencer_handle)

        # Create queue item
        item = ContentItem(
            influencer_handle=brief.influencer_handle,
            content_type=brief.content_type,
            platform=brief.platform,
            prompt=brief.prompt,
            caption=brief.caption,
            hashtags=brief.hashtags,
            motion_id=brief.motion_id,
            qc_status=QCStatus.GENERATING,
        )
        item = self.queue.add(item)

        try:
            # Step 1: Generate base image with Nano Banana 2
            out_dir = settings.ensure_output_dir() / brief.influencer_handle
            out_dir.mkdir(parents=True, exist_ok=True)

            prompt = self.identity.build_character_prompt(
                profile, brief.prompt, brief.product
            )
            aspect_ratio = self.identity.get_aspect_ratio(
                profile, brief.platform.value, brief.content_type.value
            )
            reference_images = self.identity.get_reference_images(profile)

            import uuid
            image_path = out_dir / f"{brief.content_type.value}_{uuid.uuid4().hex[:8]}.png"

            image_result = self.nb.generate_image(
                prompt=prompt,
                output_path=image_path,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
            )
            item.image_path = str(image_result.image_path)

            # Step 2: If video/reel, animate with Higgsfield
            if brief.content_type in (ContentType.VIDEO, ContentType.REEL) and brief.motion_id:
                video_path = await self._generate_video(
                    profile, brief, image_result, out_dir
                )
                if video_path:
                    item.video_path = video_path

            # Mark ready for review
            self.queue.mark_pending_review(
                item.id,
                image_path=item.image_path,
                video_path=item.video_path,
            )

            # If auto-approve is on, skip review
            if settings.auto_approve or brief.auto_post:
                self.queue.approve(item.id, notes="Auto-approved")
                await self.post_item(item.id)

        except Exception as e:
            self.queue.mark_failed(item.id, notes=str(e))
            raise

        return self.queue.get(item.id)

    # --- Posting ---

    async def post_item(self, item_id: str) -> ContentItem:
        """Post an approved content item to its target platform.

        The item must be in APPROVED status. Media files must be publicly
        accessible URLs for the platform APIs. In production, you'd upload
        to cloud storage (S3, GCS) first.
        """
        item = self.queue.get(item_id)
        if item.qc_status != QCStatus.APPROVED:
            raise ValueError(f"Item must be APPROVED to post, got {item.qc_status}")

        profile = self.agency.get_influencer(item.influencer_handle)
        account = profile.accounts.get(item.platform.value)

        if not account or account.status != AccountStatus.CONNECTED:
            raise ValueError(
                f"No connected {item.platform.value} account for @{item.influencer_handle}. "
                "Run 'influencerarmy onboard' first."
            )

        # Determine which media URL to use
        # NOTE: In production, upload local files to cloud storage and use the URL.
        # For now, this expects the paths to be publicly accessible URLs or
        # that you've set up a file serving mechanism.
        media_path = item.video_path or item.image_path
        if not media_path:
            raise ValueError("No media asset to post")

        try:
            if item.platform == Platform.INSTAGRAM:
                ig_client = InstagramClient(account)
                post_id = await ig_client.post_content(item, media_path)
                await ig_client.close()
                self.queue.mark_posted(item.id, post_id=post_id)

            elif item.platform == Platform.TIKTOK:
                tt_client = TikTokClient(account)
                publish_id = await tt_client.post_content(item, media_path)
                await tt_client.close()
                self.queue.mark_posted(item.id, post_id=publish_id)

        except Exception as e:
            self.queue.mark_failed(item.id, notes=str(e))
            raise

        return self.queue.get(item.id)

    async def post_all_approved(self) -> list[ContentItem]:
        """Post all approved items in the queue."""
        results = []
        for item in self.queue.approved():
            try:
                posted = await self.post_item(item.id)
                results.append(posted)
            except Exception as e:
                print(f"Failed to post {item.id}: {e}")
                results.append(self.queue.get(item.id))
        return results

    # --- Batch generation ---

    async def generate_photo_set(
        self,
        handle: str,
        prompts: list[str],
        platform: Platform = Platform.INSTAGRAM,
    ) -> list[ContentItem]:
        """Generate a batch of photos for an influencer."""
        items = []
        for prompt in prompts:
            brief = ContentBrief(
                influencer_handle=handle,
                content_type=ContentType.PHOTO,
                platform=platform,
                prompt=prompt,
            )
            item = await self.create_content(brief)
            items.append(item)
        return items

    # --- Character setup ---

    async def setup_higgsfield_character(
        self, handle: str, reference_image_urls: list[str]
    ) -> str:
        """Create a Higgsfield character for video consistency and link it."""
        profile = self.agency.get_influencer(handle)
        character = await self.hf.create_character(profile.name, reference_image_urls)
        self.agency.set_higgsfield_character(handle, character.character_id)
        return character.character_id

    # --- Internal ---

    async def _generate_video(
        self, profile, brief, image_result, out_dir
    ) -> str | None:
        """Animate an image into a video via Higgsfield."""
        try:
            # Generate through Higgsfield to get a hosted URL
            char_id = profile.identity.higgsfield_character_id or None
            hf_job = await self.hf.generate_image(
                prompt=brief.prompt,
                character_id=char_id,
            )
            hf_result = await self.hf.wait_for_completion(hf_job.job_set_id)

            if hf_result.status != GenerationStatus.COMPLETED or not hf_result.download_urls:
                return None

            # Create video from the hosted image
            video_job = await self.hf.generate_video(
                image_url=hf_result.download_urls[0],
                motion_id=brief.motion_id,
                prompt=brief.prompt,
            )
            video_result = await self.hf.wait_for_completion(video_job.job_set_id)

            if video_result.status != GenerationStatus.COMPLETED or not video_result.download_urls:
                return None

            import uuid
            video_path = out_dir / f"video_{uuid.uuid4().hex[:8]}.mp4"
            await self.hf.download_file(video_result.download_urls[0], str(video_path))
            return str(video_path)

        except Exception as e:
            print(f"Video generation failed: {e}")
            return None

    async def close(self) -> None:
        await self.hf.close()
