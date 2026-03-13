"""Higgsfield Cloud API client for video and image generation."""

import asyncio
import time

import httpx

from influencerarmy.config import settings
from influencerarmy.models import (
    GenerationStatus,
    HiggsCharacter,
    HiggsImageRequest,
    HiggsJobResult,
    HiggsVideoRequest,
    ImageQuality,
    VideoQuality,
)


class HiggsFieldClient:
    """Client for the Higgsfield Cloud API (cloud.higgsfield.ai)."""

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or settings.higgsfield_api_key
        self.secret = secret or settings.higgsfield_secret
        self.base_url = (base_url or settings.higgsfield_base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Secret": self.secret,
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- Image Generation (Soul model) ---

    async def generate_image(
        self,
        prompt: str,
        quality: ImageQuality = ImageQuality.HD,
        character_id: str | None = None,
        style_id: str | None = None,
    ) -> HiggsJobResult:
        """Generate an image using the Soul model. Returns a job to poll."""
        request = HiggsImageRequest(
            prompt=prompt,
            quality=quality,
            character_id=character_id,
            style_id=style_id,
        )
        client = await self._get_client()
        payload = request.model_dump(exclude_none=True)
        resp = await client.post("/api/v1/images/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return HiggsJobResult(job_set_id=data["job_set_id"])

    # --- Video Generation (DoP model) ---

    async def generate_video(
        self,
        image_url: str,
        motion_id: str,
        prompt: str = "",
        quality: VideoQuality = VideoQuality.STANDARD,
    ) -> HiggsJobResult:
        """Convert a static image to a cinematic 5-second video."""
        request = HiggsVideoRequest(
            image_url=image_url,
            motion_id=motion_id,
            prompt=prompt,
            quality=quality,
        )
        client = await self._get_client()
        payload = request.model_dump(exclude_none=True)
        resp = await client.post("/api/v1/videos/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return HiggsJobResult(job_set_id=data["job_set_id"])

    # --- Job Status ---

    async def get_status(self, job_set_id: str) -> HiggsJobResult:
        """Poll the status of a generation job."""
        client = await self._get_client()
        resp = await client.get(f"/api/v1/jobs/{job_set_id}")
        resp.raise_for_status()
        data = resp.json()
        return HiggsJobResult(
            job_set_id=job_set_id,
            status=GenerationStatus(data.get("status", "queued")),
            download_urls=data.get("download_urls", []),
        )

    async def wait_for_completion(
        self,
        job_set_id: str,
        poll_interval: float = 3.0,
        timeout: float = 120.0,
    ) -> HiggsJobResult:
        """Poll until a job completes or times out."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            result = await self.get_status(job_set_id)
            if result.status in (
                GenerationStatus.COMPLETED,
                GenerationStatus.FAILED,
                GenerationStatus.NSFW,
            ):
                return result
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Job {job_set_id} did not complete within {timeout}s")

    # --- Character Management ---

    async def create_character(
        self, name: str, image_urls: list[str]
    ) -> HiggsCharacter:
        """Create a reusable character reference for consistent appearance."""
        client = await self._get_client()
        resp = await client.post(
            "/api/v1/characters",
            json={"name": name, "image_urls": image_urls},
        )
        resp.raise_for_status()
        data = resp.json()
        return HiggsCharacter(
            name=name,
            character_id=data["character_id"],
            image_urls=image_urls,
        )

    async def list_characters(self) -> list[HiggsCharacter]:
        """List all created character references."""
        client = await self._get_client()
        resp = await client.get("/api/v1/characters")
        resp.raise_for_status()
        return [HiggsCharacter(**c) for c in resp.json().get("characters", [])]

    # --- Presets ---

    async def list_styles(self) -> list[dict]:
        """List available Soul image style presets."""
        client = await self._get_client()
        resp = await client.get("/api/v1/styles")
        resp.raise_for_status()
        return resp.json().get("styles", [])

    async def list_motions(self) -> list[dict]:
        """List available video motion presets."""
        client = await self._get_client()
        resp = await client.get("/api/v1/motions")
        resp.raise_for_status()
        return resp.json().get("motions", [])

    # --- Download ---

    async def download_file(self, url: str, output_path: str) -> str:
        """Download a generated file from a Higgsfield URL."""
        async with httpx.AsyncClient(timeout=120.0) as dl_client:
            resp = await dl_client.get(url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
        return output_path
