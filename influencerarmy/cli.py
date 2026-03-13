"""CLI entry point for the AI Influencer Agency."""

import asyncio
import json

import click

from influencerarmy.agency import Agency
from influencerarmy.models import ContentType, Platform


@click.group()
def main():
    """AI Influencer Agency - create and manage AI influencers with Higgsfield + Nano Banana 2."""
    pass


# --- Influencer management ---


@main.command()
@click.option("--name", required=True, help="Display name of the influencer")
@click.option("--handle", required=True, help="Social media handle (without @)")
@click.option("--niche", required=True, help="Content niche (e.g. fitness, travel, fashion)")
@click.option("--style", default="", help="Visual style description for image generation")
@click.option(
    "--platform",
    multiple=True,
    type=click.Choice(["instagram", "tiktok", "youtube", "twitter"]),
    default=["instagram"],
    help="Target platforms",
)
def add(name: str, handle: str, niche: str, style: str, platform: tuple[str, ...]):
    """Add a new AI influencer to the agency roster."""
    from influencerarmy.models import InfluencerProfile

    agency = Agency()
    profile = InfluencerProfile(
        name=name,
        handle=handle,
        niche=niche,
        style_description=style,
        platforms=[Platform(p) for p in platform],
    )
    agency.add_influencer(profile)
    click.echo(f"Added influencer @{handle} ({name}) - niche: {niche}")


@main.command(name="list")
def list_cmd():
    """List all AI influencers in the agency."""
    agency = Agency()
    influencers = agency.list_influencers()
    if not influencers:
        click.echo("No influencers registered yet. Use 'add' to create one.")
        return
    for inf in influencers:
        platforms = ", ".join(p.value for p in inf.platforms)
        click.echo(f"  @{inf.handle} | {inf.name} | {inf.niche} | {platforms}")


@main.command()
@click.argument("handle")
def remove(handle: str):
    """Remove an influencer from the agency."""
    agency = Agency()
    agency.remove_influencer(handle)
    click.echo(f"Removed @{handle}")


# --- Content generation ---


@main.command()
@click.argument("handle")
@click.option("--prompt", required=True, help="Description of the photo to generate")
@click.option("--style", default=None, help="Override style for this photo")
def photo(handle: str, prompt: str, style: str | None):
    """Generate a photo for an influencer using Nano Banana 2."""
    from influencerarmy.nano_banana import NanoBananaClient
    from influencerarmy.config import settings

    agency = Agency()
    influencer = agency.get_influencer(handle)

    nb = NanoBananaClient()
    style_desc = style or influencer.style_description or "professional Instagram photography"
    full_prompt = f"{prompt}. Style: {style_desc}. Photorealistic, high quality."

    out_dir = settings.ensure_output_dir() / handle
    out_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    output_path = out_dir / f"photo_{uuid.uuid4().hex[:8]}.png"

    click.echo(f"Generating photo for @{handle}...")
    result = nb.generate_image(
        prompt=full_prompt,
        output_path=output_path,
        reference_images=influencer.reference_images or [],
    )
    click.echo(f"Saved: {result.image_path}")
    if result.text_response:
        click.echo(f"Model notes: {result.text_response}")


@main.command()
@click.argument("handle")
@click.option("--prompt", required=True, help="Description of the content")
@click.option("--motion", required=True, help="Higgsfield motion preset ID")
@click.option("--caption", default="", help="Social media caption")
@click.option("--hashtags", default="", help="Comma-separated hashtags")
def video(handle: str, prompt: str, motion: str, caption: str, hashtags: str):
    """Generate a video for an influencer using Higgsfield + Nano Banana 2."""
    from influencerarmy.pipeline import ContentPipeline

    agency = Agency()
    brief = agency.create_brief(
        handle=handle,
        content_type=ContentType.VIDEO,
        prompt=prompt,
        caption=caption,
        hashtags=[h.strip() for h in hashtags.split(",") if h.strip()],
        motion_id=motion,
    )

    pipeline = ContentPipeline()
    click.echo(f"Creating video content for @{handle}...")

    result = asyncio.run(_run_brief(pipeline, brief))
    click.echo(f"Content created: {json.dumps(result, indent=2)}")


async def _run_brief(pipeline, brief):
    try:
        return await pipeline.execute_brief(brief)
    finally:
        await pipeline.close()


# --- Utility ---


@main.command()
def styles():
    """List available Higgsfield image styles."""
    from influencerarmy.higgsfield import HiggsFieldClient

    client = HiggsFieldClient()
    result = asyncio.run(client.list_styles())
    for s in result:
        click.echo(f"  {s.get('id', '?')} - {s.get('name', 'unnamed')}")


@main.command()
def motions():
    """List available Higgsfield video motion presets."""
    from influencerarmy.higgsfield import HiggsFieldClient

    client = HiggsFieldClient()
    result = asyncio.run(client.list_motions())
    for m in result:
        click.echo(f"  {m.get('id', '?')} - {m.get('name', 'unnamed')}")


if __name__ == "__main__":
    main()
