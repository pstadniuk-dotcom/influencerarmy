"""TikTok Content Posting API client for automated video publishing."""

import asyncio
import time

import httpx

from influencerarmy.models import ContentItem, SocialAccount


TIKTOK_API_BASE = "https://open.tiktokapis.com"


class TikTokClient:
    """Posts videos to TikTok via the Content Posting API.

    Requires:
    - A TikTok developer app with video.publish scope approved
    - OAuth authorization from the account owner
    - The open_id and access_token from the OAuth flow

    Setup guide: https://developers.tiktok.com/doc/content-posting-api-get-started
    """

    def __init__(self, account: SocialAccount):
        if not account.tiktok_open_id or not account.tiktok_access_token:
            raise ValueError(
                "TikTok account not fully connected. "
                "Run 'influencerarmy onboard' to set up OAuth."
            )
        self.open_id = account.tiktok_open_id
        self.access_token = account.tiktok_access_token
        self._client: httpx.AsyncClient | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=TIKTOK_API_BASE,
                headers=self._headers,
                timeout=120.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- Direct Post (public) ---

    async def post_video_from_url(
        self,
        video_url: str,
        title: str = "",
        privacy_level: str = "SELF_ONLY",
        disable_duet: bool = False,
        disable_stitch: bool = False,
        disable_comment: bool = False,
    ) -> dict:
        """Post a video directly to TikTok by pulling from a URL.

        Args:
            video_url: Publicly accessible URL of the video file.
            title: Video title/caption (max 2200 chars).
            privacy_level: "SELF_ONLY", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR",
                          or "PUBLIC_TO_EVERYONE".
            disable_duet: Disable duets.
            disable_stitch: Disable stitches.
            disable_comment: Disable comments.

        Returns:
            Dict with publish_id for status tracking.
        """
        client = await self._get_client()

        payload = {
            "post_info": {
                "title": title[:2200] if title else "",
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "disable_comment": disable_comment,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        resp = await client.post(
            "/v2/post/publish/video/init/",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("error", {}).get("code") != "ok":
            raise RuntimeError(f"TikTok publish failed: {data.get('error', {})}")

        return {"publish_id": data["data"]["publish_id"]}

    async def upload_to_inbox(
        self,
        video_url: str,
    ) -> dict:
        """Upload a video to the creator's inbox as a draft (for review before posting).

        The creator can then edit and post from the TikTok app.
        """
        client = await self._get_client()

        payload = {
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        resp = await client.post(
            "/v2/post/publish/inbox/video/init/",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("error", {}).get("code") != "ok":
            raise RuntimeError(f"TikTok upload failed: {data.get('error', {})}")

        return {"publish_id": data["data"]["publish_id"]}

    async def post_photo(
        self,
        photo_urls: list[str],
        title: str = "",
        privacy_level: str = "SELF_ONLY",
    ) -> dict:
        """Post photo(s) to TikTok."""
        client = await self._get_client()

        payload = {
            "post_info": {
                "title": title[:2200] if title else "",
                "privacy_level": privacy_level,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_urls": photo_urls,
            },
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        }

        resp = await client.post(
            "/v2/post/publish/content/init/",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("error", {}).get("code") != "ok":
            raise RuntimeError(f"TikTok photo post failed: {data.get('error', {})}")

        return {"publish_id": data["data"]["publish_id"]}

    # --- Status Tracking ---

    async def get_publish_status(self, publish_id: str) -> dict:
        """Check the status of a publish request."""
        client = await self._get_client()
        resp = await client.post(
            "/v2/post/publish/status/fetch/",
            json={"publish_id": publish_id},
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    async def wait_for_publish(
        self,
        publish_id: str,
        poll_interval: float = 10.0,
        timeout: float = 600.0,
    ) -> dict:
        """Wait until a video is published or fails."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            status = await self.get_publish_status(publish_id)
            pub_status = status.get("status")
            if pub_status == "PUBLISH_COMPLETE":
                return status
            if pub_status in ("FAILED", "PUBLISH_CANCELED"):
                raise RuntimeError(f"TikTok publish failed: {status}")
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"TikTok publish {publish_id} timed out after {timeout}s")

    # --- Content item helper ---

    async def post_content(
        self,
        item: ContentItem,
        media_url: str,
        privacy_level: str = "SELF_ONLY",
    ) -> str:
        """Post a ContentItem to TikTok. Returns the publish_id."""
        title = item.caption
        if item.hashtags:
            title += " " + " ".join(f"#{h}" for h in item.hashtags)

        if item.video_path:
            result = await self.post_video_from_url(
                video_url=media_url,
                title=title,
                privacy_level=privacy_level,
            )
        else:
            result = await self.post_photo(
                photo_urls=[media_url],
                title=title,
                privacy_level=privacy_level,
            )

        return result["publish_id"]
