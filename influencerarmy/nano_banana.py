"""Nano Banana 2 (Gemini 3.1 Flash Image) client for AI image generation."""

import base64
from pathlib import Path

from google import genai
from google.genai import types

from influencerarmy.config import settings
from influencerarmy.models import NanoBananaRequest, NanoBananaResult


class NanoBananaClient:
    """Client for Google's Nano Banana 2 image generation model.

    Uses the Gemini API with model gemini-3.1-flash-image-preview.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.google_api_key
        self.model = model or settings.nano_banana_model
        self._client = genai.Client(api_key=self.api_key)

    def generate_image(
        self,
        prompt: str,
        output_path: str | Path | None = None,
        aspect_ratio: str = "1:1",
        reference_images: list[str | Path] | None = None,
    ) -> NanoBananaResult:
        """Generate an image from a text prompt using Nano Banana 2.

        Args:
            prompt: Text description of the image to generate.
            output_path: Where to save the generated image. Auto-generated if None.
            aspect_ratio: Aspect ratio (e.g. "1:1", "16:9", "9:16").
            reference_images: Optional list of reference image file paths for
                consistency or editing (up to 14 images).
        """
        contents = self._build_contents(prompt, reference_images)

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        return self._process_response(response, output_path)

    def generate_influencer_photo(
        self,
        influencer_name: str,
        scene_description: str,
        style: str = "professional photography, high quality, Instagram-worthy",
        output_path: str | Path | None = None,
        reference_images: list[str | Path] | None = None,
    ) -> NanoBananaResult:
        """Generate a photo for an AI influencer with consistency hints.

        Builds a detailed prompt optimized for influencer content.
        """
        prompt = (
            f"Create a photorealistic image of {influencer_name}. "
            f"Scene: {scene_description}. "
            f"Style: {style}. "
            "The person should look natural and authentic, as if this is a real "
            "social media photo. High resolution, sharp focus."
        )
        return self.generate_image(
            prompt=prompt,
            output_path=output_path,
            reference_images=reference_images,
        )

    def edit_image(
        self,
        image_path: str | Path,
        edit_instruction: str,
        output_path: str | Path | None = None,
    ) -> NanoBananaResult:
        """Edit an existing image using Nano Banana 2's editing capabilities."""
        return self.generate_image(
            prompt=edit_instruction,
            output_path=output_path,
            reference_images=[image_path],
        )

    def _build_contents(
        self, prompt: str, reference_images: list[str | Path] | None
    ) -> list:
        """Build the contents list with optional reference images."""
        parts: list = []

        if reference_images:
            for img_path in reference_images:
                img_path = Path(img_path)
                if img_path.exists():
                    img_data = img_path.read_bytes()
                    mime = self._guess_mime(img_path)
                    parts.append(
                        types.Part.from_bytes(data=img_data, mime_type=mime)
                    )

        parts.append(prompt)
        return parts

    @staticmethod
    def _guess_mime(path: Path) -> str:
        suffix = path.suffix.lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(suffix, "image/png")

    def _process_response(
        self, response, output_path: str | Path | None
    ) -> NanoBananaResult:
        """Extract image and text from the Gemini response."""
        text_parts: list[str] = []
        image_saved = False
        save_path = Path(output_path) if output_path else None

        if not response.candidates:
            raise RuntimeError("No response candidates returned from Nano Banana 2")

        for part in response.candidates[0].content.parts:
            if part.text:
                text_parts.append(part.text)
            elif part.inline_data:
                if save_path is None:
                    out_dir = settings.ensure_output_dir()
                    import uuid
                    save_path = out_dir / f"nb2_{uuid.uuid4().hex[:8]}.png"

                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(part.inline_data.data)
                image_saved = True

        if not image_saved:
            raise RuntimeError(
                "Nano Banana 2 did not return an image. "
                f"Text response: {' '.join(text_parts)}"
            )

        return NanoBananaResult(
            image_path=save_path,
            text_response=" ".join(text_parts),
        )
