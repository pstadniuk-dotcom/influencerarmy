"""Influencer agency - manages AI influencer profiles, onboarding, and account connections."""

import json
from pathlib import Path

from influencerarmy.config import settings
from influencerarmy.models import (
    AccountStatus,
    IdentityConfig,
    InfluencerProfile,
    Platform,
    SocialAccount,
)


PROFILES_FILE = "influencers.json"


class Agency:
    """Manages a roster of AI influencer profiles with social accounts."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.ensure_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, InfluencerProfile] = {}
        self._load()

    # --- Profile management ---

    def add_influencer(
        self,
        name: str,
        handle: str,
        niche: str,
        bio: str = "",
        character_dna: str = "",
        default_style: str = "",
    ) -> InfluencerProfile:
        """Register a new AI influencer with identity config.

        Automatically creates placeholder social accounts for Instagram and TikTok.
        """
        identity = IdentityConfig(
            character_dna=character_dna,
        )
        if default_style:
            identity.default_style = default_style

        # Create accounts for both platforms (not_created until onboarded)
        accounts = {
            Platform.INSTAGRAM.value: SocialAccount(
                platform=Platform.INSTAGRAM,
                status=AccountStatus.NOT_CREATED,
            ),
            Platform.TIKTOK.value: SocialAccount(
                platform=Platform.TIKTOK,
                status=AccountStatus.NOT_CREATED,
            ),
        }

        profile = InfluencerProfile(
            name=name,
            handle=handle,
            niche=niche,
            bio=bio,
            identity=identity,
            accounts=accounts,
        )
        self._profiles[handle] = profile
        self._save()
        return profile

    def get_influencer(self, handle: str) -> InfluencerProfile:
        if handle not in self._profiles:
            raise KeyError(f"Influencer @{handle} not found")
        return self._profiles[handle]

    def update_influencer(self, profile: InfluencerProfile) -> InfluencerProfile:
        self._profiles[profile.handle] = profile
        self._save()
        return profile

    def list_influencers(self) -> list[InfluencerProfile]:
        return list(self._profiles.values())

    def remove_influencer(self, handle: str) -> None:
        if handle in self._profiles:
            del self._profiles[handle]
            self._save()

    # --- Account connection ---

    def mark_account_created(
        self, handle: str, platform: Platform, username: str
    ) -> SocialAccount:
        """Mark that a social media account has been manually created."""
        profile = self.get_influencer(handle)
        account = profile.accounts.get(platform.value)
        if not account:
            account = SocialAccount(platform=platform)
        account.status = AccountStatus.CREATED
        account.username = username
        profile.accounts[platform.value] = account
        self._save()
        return account

    def connect_instagram(
        self,
        handle: str,
        ig_user_id: str,
        access_token: str,
        page_id: str = "",
        username: str = "",
    ) -> SocialAccount:
        """Connect an Instagram Business account via Graph API credentials."""
        profile = self.get_influencer(handle)
        account = profile.accounts.get(Platform.INSTAGRAM.value, SocialAccount(platform=Platform.INSTAGRAM))
        account.status = AccountStatus.CONNECTED
        account.ig_user_id = ig_user_id
        account.ig_access_token = access_token
        account.ig_page_id = page_id
        if username:
            account.username = username
        profile.accounts[Platform.INSTAGRAM.value] = account
        self._save()
        return account

    def connect_tiktok(
        self,
        handle: str,
        open_id: str,
        access_token: str,
        username: str = "",
    ) -> SocialAccount:
        """Connect a TikTok account via Content Posting API credentials."""
        profile = self.get_influencer(handle)
        account = profile.accounts.get(Platform.TIKTOK.value, SocialAccount(platform=Platform.TIKTOK))
        account.status = AccountStatus.CONNECTED
        account.tiktok_open_id = open_id
        account.tiktok_access_token = access_token
        if username:
            account.username = username
        profile.accounts[Platform.TIKTOK.value] = account
        self._save()
        return account

    def get_account(self, handle: str, platform: Platform) -> SocialAccount:
        """Get the social account for an influencer on a platform."""
        profile = self.get_influencer(handle)
        account = profile.accounts.get(platform.value)
        if not account:
            raise KeyError(f"No {platform.value} account for @{handle}")
        return account

    # --- Identity ---

    def add_reference_image(self, handle: str, image_path: str) -> InfluencerProfile:
        """Add a reference image to an influencer's identity."""
        profile = self.get_influencer(handle)
        if image_path not in profile.identity.reference_images:
            profile.identity.reference_images.append(image_path)
            self._save()
        return profile

    def set_character_dna(self, handle: str, dna: str) -> InfluencerProfile:
        """Set the detailed character description for consistency."""
        profile = self.get_influencer(handle)
        profile.identity.character_dna = dna
        self._save()
        return profile

    def set_higgsfield_character(self, handle: str, character_id: str) -> InfluencerProfile:
        """Link a Higgsfield character ID for video consistency."""
        profile = self.get_influencer(handle)
        profile.identity.higgsfield_character_id = character_id
        self._save()
        return profile

    # --- Onboarding status ---

    def onboarding_status(self, handle: str) -> dict:
        """Check what steps remain for full onboarding."""
        profile = self.get_influencer(handle)
        identity = profile.identity

        status = {
            "handle": handle,
            "has_character_dna": bool(identity.character_dna),
            "has_reference_images": len(identity.reference_images) > 0,
            "reference_image_count": len(identity.reference_images),
            "has_higgsfield_character": bool(identity.higgsfield_character_id),
            "accounts": {},
        }

        for platform_key, account in profile.accounts.items():
            status["accounts"][platform_key] = {
                "status": account.status.value,
                "username": account.username,
                "connected": account.status == AccountStatus.CONNECTED,
            }

        status["ready"] = (
            status["has_character_dna"]
            and status["has_reference_images"]
            and all(
                a["connected"] for a in status["accounts"].values()
            )
        )

        return status

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
