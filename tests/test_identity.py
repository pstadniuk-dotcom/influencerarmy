"""Tests for identity management and prompt building."""

from pathlib import Path

from influencerarmy.identity import IdentityManager
from influencerarmy.models import (
    IdentityConfig,
    InfluencerProfile,
    ProductPlacement,
)


def _make_profile(**kwargs) -> InfluencerProfile:
    defaults = dict(
        name="Luna Rivera",
        handle="luna_rivera",
        niche="fitness",
        identity=IdentityConfig(
            character_dna="25yo latina woman, olive skin, dark brown wavy hair, green eyes, athletic build",
            default_style="golden hour photography, warm tones",
        ),
    )
    defaults.update(kwargs)
    return InfluencerProfile(**defaults)


def test_build_character_prompt():
    mgr = IdentityManager()
    profile = _make_profile()
    prompt = mgr.build_character_prompt(profile, "doing yoga on a beach at sunset")
    assert "Luna Rivera" in prompt
    assert "25yo latina woman" in prompt
    assert "yoga" in prompt
    assert "golden hour" in prompt
    assert "reference images" in prompt.lower()


def test_build_product_prompt():
    mgr = IdentityManager()
    profile = _make_profile()
    product = ProductPlacement(
        product_name="HydroFlask Bottle",
        product_description="32oz insulated water bottle in coral",
        placement_instructions="holding the bottle after a workout",
        brand_name="HydroFlask",
    )
    prompt = mgr.build_product_prompt(profile, product, "in a gym setting")
    assert "HydroFlask" in prompt
    assert "holding the bottle" in prompt
    assert "Luna Rivera" in prompt


def test_get_aspect_ratio():
    mgr = IdentityManager()
    profile = _make_profile()

    assert mgr.get_aspect_ratio(profile, "instagram", "photo") == "1:1"
    assert mgr.get_aspect_ratio(profile, "instagram", "reel") == "9:16"
    assert mgr.get_aspect_ratio(profile, "tiktok", "video") == "9:16"


def test_add_reference_image(tmp_path):
    mgr = IdentityManager()

    # Create a fake image file
    fake_img = tmp_path / "face.png"
    fake_img.write_bytes(b"fake image data")

    stored = mgr.add_reference_image("test_handle", fake_img)
    assert Path(stored).exists()
    assert "ref_" in stored


def test_get_reference_images_capped():
    mgr = IdentityManager()
    profile = _make_profile()
    # Add more than 6 reference images
    profile.identity.reference_images = [f"/img{i}.png" for i in range(10)]
    refs = mgr.get_reference_images(profile)
    assert len(refs) == 6  # Capped at 6 for optimal NB2 consistency
