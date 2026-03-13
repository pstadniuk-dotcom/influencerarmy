"""Identity management - ensures each AI influencer looks like the same person across all content."""

from pathlib import Path

from influencerarmy.config import settings
from influencerarmy.models import IdentityConfig, InfluencerProfile, ProductPlacement


class IdentityManager:
    """Manages the visual identity of AI influencers.

    Handles reference image storage, prompt engineering for character consistency,
    and Higgsfield character registration.
    """

    def __init__(self):
        self.identity_dir = settings.ensure_data_dir() / "identities"
        self.identity_dir.mkdir(parents=True, exist_ok=True)

    def get_identity_dir(self, handle: str) -> Path:
        """Get the directory where an influencer's reference images are stored."""
        d = self.identity_dir / handle
        d.mkdir(parents=True, exist_ok=True)
        return d

    def add_reference_image(self, handle: str, image_path: str | Path) -> str:
        """Copy a reference image into the influencer's identity folder.

        Returns the stored path.
        """
        src = Path(image_path)
        if not src.exists():
            raise FileNotFoundError(f"Reference image not found: {src}")

        dest_dir = self.get_identity_dir(handle)
        dest = dest_dir / f"ref_{len(list(dest_dir.glob('ref_*')))}{src.suffix}"
        dest.write_bytes(src.read_bytes())
        return str(dest)

    def get_reference_images(self, profile: InfluencerProfile) -> list[str]:
        """Get all reference image paths for an influencer.

        Combines images from the identity config and the identity directory.
        """
        paths = list(profile.identity.reference_images)

        # Also check the identity directory for any stored references
        identity_dir = self.get_identity_dir(profile.handle)
        for img in sorted(identity_dir.glob("ref_*")):
            img_str = str(img)
            if img_str not in paths:
                paths.append(img_str)

        return paths[:6]  # Cap at 6 for optimal NB2 consistency

    def build_character_prompt(
        self,
        profile: InfluencerProfile,
        scene_prompt: str,
        product: ProductPlacement | None = None,
    ) -> str:
        """Build a detailed prompt that maintains character consistency.

        Combines the character DNA, scene description, style, and optional
        product placement into a single optimized prompt.
        """
        parts = []

        # Character identity anchor
        identity = profile.identity
        if identity.character_dna:
            parts.append(
                f"Photorealistic image of {profile.name}: {identity.character_dna}."
            )
        else:
            parts.append(f"Photorealistic image of {profile.name}.")

        # Scene description
        parts.append(f"Scene: {scene_prompt}.")

        # Product placement
        if product:
            placement = product.placement_instructions or f"featuring {product.product_name}"
            parts.append(
                f"Product: {product.product_name} by {product.brand_name}. "
                f"{placement}. {product.product_description}."
            )
            if product.brand_guidelines:
                parts.append(f"Brand notes: {product.brand_guidelines}.")

        # Style
        style = identity.default_style
        parts.append(f"Style: {style}.")

        # Quality anchors
        parts.append(
            "The person should look exactly like the reference images. "
            "Maintain exact facial features, skin tone, hair, and body proportions. "
            "Natural, authentic social media photo. High resolution, sharp focus."
        )

        return " ".join(parts)

    def build_product_prompt(
        self,
        profile: InfluencerProfile,
        product: ProductPlacement,
        scene_prompt: str = "",
    ) -> str:
        """Build a prompt specifically for product modeling/showcase."""
        return self.build_character_prompt(profile, scene_prompt, product)

    def get_aspect_ratio(self, profile: InfluencerProfile, platform: str, content_type: str) -> str:
        """Get the right aspect ratio for a platform/content type combo."""
        ratios = profile.identity.platform_aspect_ratios

        # Check for specific content type first (e.g. instagram_reel)
        key = f"{platform}_{content_type}"
        if key in ratios:
            return ratios[key]

        # Fall back to platform default
        if platform in ratios:
            return ratios[platform]

        return "1:1"
