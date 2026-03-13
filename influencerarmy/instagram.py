"""Instagram Graph API client for automated posting."""

import asyncio
import time

import httpx

from influencerarmy.models import ContentItem, ContentType, SocialAccount


GRAPH_API_BASE = "https://graph.facebook.com/v22.0"
RUPLOAD_BASE = "https://rupload.facebook.com/v22.0"


class InstagramClient:
    """Posts content to Instagram via the Graph API.

    Requires a connected Instagram Business/Creator account with:
    - A Meta app with instagram_business_content_publish permission
    - A long-lived access token
    - The IG user ID

    Setup guide: https://developers.facebook.com/docs/instagram-platform/content-publishing/
    """

    def __init__(self, account: SocialAccount):
        if not account.ig_user_id or not account.ig_access_token:
            raise ValueError(
                "Instagram account not fully connected. "
                "Run 'influencerarmy onboard' to set up OAuth."
            )
        self.ig_user_id = account.ig_user_id
        self.access_token = account.ig_access_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- Publishing ---

    async def post_photo(
        self,
        image_url: str,
        caption: str = "",
    ) -> str:
        """Post a single photo to the Instagram feed.

        Args:
            image_url: Publicly accessible URL of the image.
            caption: Post caption with hashtags.

        Returns:
            The published media ID.
        """
        # Step 1: Create media container
        container_id = await self._create_container(
            image_url=image_url,
            caption=caption,
            media_type=None,  # default = IMAGE
        )

        # Step 2: Publish
        return await self._publish_container(container_id)

    async def post_reel(
        self,
        video_url: str,
        caption: str = "",
        cover_url: str | None = None,
    ) -> str:
        """Post a Reel to Instagram.

        Args:
            video_url: Publicly accessible URL of the video.
            caption: Post caption.
            cover_url: Optional cover image URL.

        Returns:
            The published media ID.
        """
        container_id = await self._create_container(
            video_url=video_url,
            caption=caption,
            media_type="REELS",
            cover_url=cover_url,
        )

        # Wait for video processing
        await self._wait_for_container(container_id)

        return await self._publish_container(container_id)

    async def post_story(
        self,
        image_url: str | None = None,
        video_url: str | None = None,
    ) -> str:
        """Post a Story (image or video)."""
        container_id = await self._create_container(
            image_url=image_url,
            video_url=video_url,
            media_type="STORIES",
        )

        if video_url:
            await self._wait_for_container(container_id)

        return await self._publish_container(container_id)

    async def post_carousel(
        self,
        media_urls: list[dict],
        caption: str = "",
    ) -> str:
        """Post a carousel of images/videos.

        Args:
            media_urls: List of dicts with 'image_url' or 'video_url' keys.
            caption: Caption for the carousel post.
        """
        # Create child containers
        child_ids = []
        for media in media_urls:
            child_id = await self._create_container(
                image_url=media.get("image_url"),
                video_url=media.get("video_url"),
                is_carousel_item=True,
            )
            if media.get("video_url"):
                await self._wait_for_container(child_id)
            child_ids.append(child_id)

        # Create carousel container
        client = await self._get_client()
        resp = await client.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": self.access_token,
            },
        )
        resp.raise_for_status()
        carousel_id = resp.json()["id"]

        return await self._publish_container(carousel_id)

    # --- Content item helper ---

    async def post_content(self, item: ContentItem, media_url: str) -> str:
        """Post a ContentItem to Instagram. Returns the post ID."""
        caption = item.caption
        if item.hashtags:
            caption += "\n\n" + " ".join(f"#{h}" for h in item.hashtags)

        if item.content_type == ContentType.PHOTO:
            return await self.post_photo(image_url=media_url, caption=caption)
        elif item.content_type in (ContentType.VIDEO, ContentType.REEL):
            return await self.post_reel(video_url=media_url, caption=caption)
        elif item.content_type == ContentType.STORY:
            if item.video_path:
                return await self.post_story(video_url=media_url)
            return await self.post_story(image_url=media_url)
        else:
            raise ValueError(f"Unsupported content type for Instagram: {item.content_type}")

    # --- Rate limits ---

    async def check_rate_limit(self) -> dict:
        """Check current publishing rate limit usage."""
        client = await self._get_client()
        resp = await client.get(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/content_publishing_limit",
            params={
                "fields": "config,quota_usage",
                "access_token": self.access_token,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # --- Internal helpers ---

    async def _create_container(
        self,
        image_url: str | None = None,
        video_url: str | None = None,
        caption: str = "",
        media_type: str | None = None,
        cover_url: str | None = None,
        is_carousel_item: bool = False,
    ) -> str:
        """Create an IG media container."""
        client = await self._get_client()
        params: dict = {"access_token": self.access_token}

        if image_url:
            params["image_url"] = image_url
        if video_url:
            params["video_url"] = video_url
        if caption:
            params["caption"] = caption
        if media_type:
            params["media_type"] = media_type
        if cover_url:
            params["cover_url"] = cover_url
        if is_carousel_item:
            params["is_carousel_item"] = "true"

        resp = await client.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def _publish_container(self, container_id: str) -> str:
        """Publish a media container."""
        client = await self._get_client()
        resp = await client.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self.access_token,
            },
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def _wait_for_container(
        self,
        container_id: str,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> None:
        """Wait for a video container to finish processing."""
        client = await self._get_client()
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            resp = await client.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": self.access_token,
                },
            )
            resp.raise_for_status()
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram container {container_id} failed processing")
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Container {container_id} processing timed out")
