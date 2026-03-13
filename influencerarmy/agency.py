"""Influencer agency - manages AI influencer profiles and content pipelines."""

import json
from pathlib import Path

from influencerarmy.config import settings
from influencerarmy.models import (
    ContentBrief,
    ContentType,
    InfluencerProfile,
    Platform,
)


PROFILES_FILE = "influencers.json"


class Agency:
    """Manages a roster of AI influencer profiles."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.output_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, InfluencerProfile] = {}
        self._load()

    # --- Profile management ---

    def add_influencer(self, profile: InfluencerProfile) -> InfluencerProfile:
        """Register a new AI influencer."""
        self._profiles[profile.handle] = profile
        self._save()
        return profile

    def get_influencer(self, handle: str) -> InfluencerProfile:
        """Get an influencer by handle."""
        if handle not in self._profiles:
            raise KeyError(f"Influencer @{handle} not found")
        return self._profiles[handle]

    def list_influencers(self) -> list[InfluencerProfile]:
        """List all registered influencers."""
        return list(self._profiles.values())

    def remove_influencer(self, handle: str) -> None:
        """Remove an influencer from the roster."""
        if handle in self._profiles:
            del self._profiles[handle]
            self._save()

    # --- Content brief creation ---

    def create_brief(
        self,
        handle: str,
        content_type: ContentType,
        prompt: str,
        caption: str = "",
        hashtags: list[str] | None = None,
        motion_id: str = "",
    ) -> ContentBrief:
        """Create a content brief for an influencer."""
        influencer = self.get_influencer(handle)
        return ContentBrief(
            influencer=influencer,
            content_type=content_type,
            prompt=prompt,
            caption=caption,
            hashtags=hashtags or [],
            motion_id=motion_id,
        )

    # --- Persistence ---

    def _save(self) -> None:
        path = self.data_dir / PROFILES_FILE
        data = {
            handle: profile.model_dump(mode="json")
            for handle, profile in self._profiles.items()
        }
        path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self.data_dir / PROFILES_FILE
        if path.exists():
            data = json.loads(path.read_text())
            self._profiles = {
                handle: InfluencerProfile(**profile_data)
                for handle, profile_data in data.items()
            }
