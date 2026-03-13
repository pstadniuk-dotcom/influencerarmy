"""CLI entry point for the AI Influencer Agency."""

import asyncio
import json

import click

from influencerarmy.agency import Agency
from influencerarmy.models import ContentType, Platform, ProductPlacement, QCStatus
from influencerarmy.queue import ContentQueue


@click.group()
def main():
    """AI Influencer Agency - create and manage AI influencers with Higgsfield + Nano Banana 2."""
    pass


# ============================================================
# Influencer management
# ============================================================


@main.command()
@click.option("--name", required=True, help="Display name")
@click.option("--handle", required=True, help="Handle (without @)")
@click.option("--niche", required=True, help="Content niche (fitness, travel, fashion, etc.)")
@click.option("--bio", default="", help="Bio / tagline")
@click.option(
    "--dna",
    default="",
    help=(
        "Character DNA: detailed physical description for visual consistency. "
        "E.g. '25yo woman, olive skin, dark brown wavy hair, green eyes, athletic build'"
    ),
)
@click.option("--style", default="", help="Default photography style")
def add(name: str, handle: str, niche: str, bio: str, dna: str, style: str):
    """Add a new AI influencer to the agency."""
    agency = Agency()
    profile = agency.add_influencer(
        name=name, handle=handle, niche=niche, bio=bio,
        character_dna=dna, default_style=style,
    )
    click.echo(f"Created @{handle} ({name})")
    click.echo(f"  Niche: {niche}")
    if dna:
        click.echo(f"  DNA: {dna}")
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. Generate reference images: influencerarmy generate-refs {handle}")
    click.echo(f"  2. Set up social accounts: influencerarmy onboard {handle}")


@main.command(name="list")
def list_cmd():
    """List all AI influencers."""
    agency = Agency()
    influencers = agency.list_influencers()
    if not influencers:
        click.echo("No influencers yet. Use 'add' to create one.")
        return
    for inf in influencers:
        accts = []
        for key, acct in inf.accounts.items():
            symbol = {"not_created": "x", "created": "~", "connected": "v"}[acct.status.value]
            accts.append(f"{key}[{symbol}]")
        acct_str = " ".join(accts)
        refs = len(inf.identity.reference_images)
        click.echo(f"  @{inf.handle} | {inf.name} | {inf.niche} | refs:{refs} | {acct_str}")


@main.command()
@click.argument("handle")
def remove(handle: str):
    """Remove an influencer from the agency."""
    agency = Agency()
    agency.remove_influencer(handle)
    click.echo(f"Removed @{handle}")


@main.command()
@click.argument("handle")
def status(handle: str):
    """Show onboarding status for an influencer."""
    agency = Agency()
    s = agency.onboarding_status(handle)
    click.echo(f"@{handle} onboarding status:")
    click.echo(f"  Character DNA: {'set' if s['has_character_dna'] else 'MISSING'}")
    click.echo(f"  Reference images: {s['reference_image_count']}")
    click.echo(f"  Higgsfield character: {'linked' if s['has_higgsfield_character'] else 'not set'}")
    for platform, info in s["accounts"].items():
        symbol = "CONNECTED" if info["connected"] else info["status"].upper()
        username = f" (@{info['username']})" if info["username"] else ""
        click.echo(f"  {platform}: {symbol}{username}")
    click.echo()
    if s["ready"]:
        click.echo("  READY for content generation and posting.")
    else:
        click.echo("  NOT READY - complete the steps above first.")


# ============================================================
# Onboarding
# ============================================================


@main.command()
@click.argument("handle")
def onboard(handle: str):
    """Interactive onboarding guide for an influencer's social accounts."""
    agency = Agency()
    profile = agency.get_influencer(handle)

    click.echo(f"\n=== Onboarding @{handle} ({profile.name}) ===\n")

    # Instagram
    ig_account = profile.accounts.get("instagram")
    if not ig_account or ig_account.status != "connected":
        click.echo("--- Instagram Setup ---")
        click.echo("1. Create an Instagram account manually for this influencer")
        click.echo("2. Convert it to a Business or Creator account")
        click.echo("3. Link it to a Facebook Page")
        click.echo("4. Create a Meta App at https://developers.facebook.com/")
        click.echo("5. Add instagram_business_content_publish permission")
        click.echo("6. Generate a long-lived access token")
        click.echo()

        if click.confirm("Have you completed these steps?"):
            username = click.prompt("Instagram username")
            ig_user_id = click.prompt("IG User ID (from Graph API)")
            access_token = click.prompt("Long-lived access token", hide_input=True)
            page_id = click.prompt("Facebook Page ID", default="")

            agency.mark_account_created(handle, Platform.INSTAGRAM, username)
            agency.connect_instagram(
                handle, ig_user_id=ig_user_id,
                access_token=access_token, page_id=page_id, username=username,
            )
            click.echo(f"Instagram @{username} connected!\n")
        else:
            click.echo("Skipping Instagram for now.\n")

    # TikTok
    tt_account = profile.accounts.get("tiktok")
    if not tt_account or tt_account.status != "connected":
        click.echo("--- TikTok Setup ---")
        click.echo("1. Create a TikTok account manually for this influencer")
        click.echo("2. Register a developer app at https://developers.tiktok.com/")
        click.echo("3. Request video.publish scope approval")
        click.echo("4. Complete OAuth flow to get open_id and access_token")
        click.echo()

        if click.confirm("Have you completed these steps?"):
            username = click.prompt("TikTok username")
            open_id = click.prompt("TikTok Open ID")
            access_token = click.prompt("TikTok access token", hide_input=True)

            agency.mark_account_created(handle, Platform.TIKTOK, username)
            agency.connect_tiktok(
                handle, open_id=open_id,
                access_token=access_token, username=username,
            )
            click.echo(f"TikTok @{username} connected!\n")
        else:
            click.echo("Skipping TikTok for now.\n")

    click.echo("Onboarding complete. Run 'influencerarmy status " + handle + "' to check status.")


@main.command(name="set-dna")
@click.argument("handle")
@click.option("--dna", required=True, help="Detailed physical description")
def set_dna(handle: str, dna: str):
    """Set the character DNA (physical description) for an influencer."""
    agency = Agency()
    agency.set_character_dna(handle, dna)
    click.echo(f"Character DNA set for @{handle}")


@main.command(name="add-ref")
@click.argument("handle")
@click.argument("image_path", type=click.Path(exists=True))
def add_ref(handle: str, image_path: str):
    """Add a reference image for character consistency."""
    from influencerarmy.identity import IdentityManager

    agency = Agency()
    id_mgr = IdentityManager()
    stored_path = id_mgr.add_reference_image(handle, image_path)
    agency.add_reference_image(handle, stored_path)
    profile = agency.get_influencer(handle)
    click.echo(f"Added reference image ({len(profile.identity.reference_images)} total)")


# ============================================================
# Content generation
# ============================================================


@main.command()
@click.argument("handle")
@click.option("--prompt", required=True, help="Scene description")
@click.option("--platform", type=click.Choice(["instagram", "tiktok"]), default="instagram")
@click.option("--caption", default="", help="Post caption")
@click.option("--hashtags", default="", help="Comma-separated hashtags")
@click.option("--auto-post", is_flag=True, help="Skip QC review and post immediately")
def photo(handle: str, prompt: str, platform: str, caption: str, hashtags: str, auto_post: bool):
    """Generate a photo and queue it for review."""
    from influencerarmy.models import ContentBrief
    from influencerarmy.pipeline import ContentPipeline

    brief = ContentBrief(
        influencer_handle=handle,
        content_type=ContentType.PHOTO,
        platform=Platform(platform),
        prompt=prompt,
        caption=caption,
        hashtags=[h.strip() for h in hashtags.split(",") if h.strip()],
        auto_post=auto_post,
    )

    pipeline = ContentPipeline()
    click.echo(f"Generating photo for @{handle}...")
    item = asyncio.run(_run_create(pipeline, brief))
    _print_item(item)


@main.command()
@click.argument("handle")
@click.option("--prompt", required=True, help="Scene description")
@click.option("--motion", required=True, help="Higgsfield motion preset ID")
@click.option("--platform", type=click.Choice(["instagram", "tiktok"]), default="instagram")
@click.option("--caption", default="", help="Post caption")
@click.option("--hashtags", default="", help="Comma-separated hashtags")
@click.option("--auto-post", is_flag=True, help="Skip QC review and post immediately")
def video(handle: str, prompt: str, motion: str, platform: str, caption: str, hashtags: str, auto_post: bool):
    """Generate a video/reel and queue it for review."""
    from influencerarmy.models import ContentBrief
    from influencerarmy.pipeline import ContentPipeline

    brief = ContentBrief(
        influencer_handle=handle,
        content_type=ContentType.REEL,
        platform=Platform(platform),
        prompt=prompt,
        caption=caption,
        hashtags=[h.strip() for h in hashtags.split(",") if h.strip()],
        motion_id=motion,
        auto_post=auto_post,
    )

    pipeline = ContentPipeline()
    click.echo(f"Generating video for @{handle}...")
    item = asyncio.run(_run_create(pipeline, brief))
    _print_item(item)


@main.command()
@click.argument("handle")
@click.option("--prompt", required=True, help="Scene description")
@click.option("--product-name", required=True, help="Product name")
@click.option("--product-desc", default="", help="Product description")
@click.option("--product-image", default="", type=click.Path(), help="Product image path")
@click.option("--placement", default="", help="How the product should appear")
@click.option("--brand", default="", help="Brand name")
@click.option("--platform", type=click.Choice(["instagram", "tiktok"]), default="instagram")
@click.option("--caption", default="", help="Post caption")
@click.option("--hashtags", default="", help="Comma-separated hashtags")
def product(
    handle: str, prompt: str, product_name: str, product_desc: str,
    product_image: str, placement: str, brand: str,
    platform: str, caption: str, hashtags: str,
):
    """Generate a product placement photo for an influencer."""
    from influencerarmy.models import ContentBrief
    from influencerarmy.pipeline import ContentPipeline

    prod = ProductPlacement(
        product_name=product_name,
        product_description=product_desc,
        product_image_path=product_image,
        placement_instructions=placement,
        brand_name=brand,
    )

    brief = ContentBrief(
        influencer_handle=handle,
        content_type=ContentType.PHOTO,
        platform=Platform(platform),
        prompt=prompt,
        caption=caption,
        hashtags=[h.strip() for h in hashtags.split(",") if h.strip()],
        product=prod,
    )

    pipeline = ContentPipeline()
    click.echo(f"Generating product photo for @{handle} with {product_name}...")
    item = asyncio.run(_run_create(pipeline, brief))
    _print_item(item)


# ============================================================
# Quality control
# ============================================================


@main.command()
@click.option("--status", "filter_status", type=click.Choice(
    ["all", "pending_review", "approved", "rejected", "posted", "failed"]
), default="all")
@click.option("--influencer", default="", help="Filter by influencer handle")
def queue(filter_status: str, influencer: str):
    """View the content queue."""
    q = ContentQueue()

    if influencer:
        items = q.list_by_influencer(influencer)
    elif filter_status == "all":
        items = q.list_all()
    else:
        items = q.list_by_status(QCStatus(filter_status))

    if not items:
        click.echo("Queue is empty.")
        return

    for item in items:
        _print_item_short(item)

    click.echo(f"\n  Total: {len(items)}")
    stats = q.stats()
    if stats:
        click.echo(f"  Stats: {json.dumps(stats)}")


@main.command()
@click.argument("item_id")
def review(item_id: str):
    """Review a content item (view details, approve, or reject)."""
    q = ContentQueue()
    item = q.get(item_id)
    _print_item(item)

    if item.qc_status != QCStatus.PENDING_REVIEW:
        click.echo(f"\nItem is {item.qc_status.value}, not reviewable.")
        return

    click.echo("\nOpen the image/video file to review quality.")
    action = click.prompt("Action", type=click.Choice(["approve", "reject", "skip"]))

    if action == "approve":
        notes = click.prompt("Notes (optional)", default="")
        q.approve(item_id, notes=notes)
        click.echo("Approved!")
    elif action == "reject":
        reason = click.prompt("Rejection reason")
        q.reject(item_id, reason=reason)
        click.echo("Rejected. Regenerate with a new prompt.")


@main.command()
@click.argument("item_id")
def approve(item_id: str):
    """Quick-approve a content item."""
    q = ContentQueue()
    q.approve(item_id)
    click.echo(f"Approved {item_id}")


@main.command()
@click.argument("item_id")
@click.option("--reason", required=True)
def reject(item_id: str, reason: str):
    """Reject a content item."""
    q = ContentQueue()
    q.reject(item_id, reason=reason)
    click.echo(f"Rejected {item_id}: {reason}")


# ============================================================
# Posting
# ============================================================


@main.command()
@click.argument("item_id")
def post(item_id: str):
    """Post an approved content item to its target platform."""
    from influencerarmy.pipeline import ContentPipeline

    pipeline = ContentPipeline()
    click.echo("Posting...")
    item = asyncio.run(_run_post(pipeline, item_id))
    click.echo(f"Posted! ID: {item.post_id}")


@main.command(name="post-all")
def post_all():
    """Post all approved content items."""
    from influencerarmy.pipeline import ContentPipeline

    pipeline = ContentPipeline()
    results = asyncio.run(_run_post_all(pipeline))
    posted = [r for r in results if r.qc_status == QCStatus.POSTED]
    failed = [r for r in results if r.qc_status == QCStatus.FAILED]
    click.echo(f"Posted: {len(posted)}, Failed: {len(failed)}")


# ============================================================
# Higgsfield presets
# ============================================================


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


# ============================================================
# Helpers
# ============================================================


async def _run_create(pipeline, brief):
    try:
        return await pipeline.create_content(brief)
    finally:
        await pipeline.close()


async def _run_post(pipeline, item_id):
    try:
        return await pipeline.post_item(item_id)
    finally:
        await pipeline.close()


async def _run_post_all(pipeline):
    try:
        return await pipeline.post_all_approved()
    finally:
        await pipeline.close()


def _print_item(item):
    click.echo(f"\n  ID:       {item.id}")
    click.echo(f"  Handle:   @{item.influencer_handle}")
    click.echo(f"  Type:     {item.content_type.value}")
    click.echo(f"  Platform: {item.platform.value}")
    click.echo(f"  Status:   {item.qc_status.value}")
    click.echo(f"  Prompt:   {item.prompt}")
    if item.image_path:
        click.echo(f"  Image:    {item.image_path}")
    if item.video_path:
        click.echo(f"  Video:    {item.video_path}")
    if item.caption:
        click.echo(f"  Caption:  {item.caption}")
    if item.rejection_reason:
        click.echo(f"  Rejected: {item.rejection_reason}")
    if item.post_id:
        click.echo(f"  Post ID:  {item.post_id}")


def _print_item_short(item):
    status_icons = {
        "generating": "..",
        "pending_review": "??",
        "approved": "OK",
        "rejected": "XX",
        "posted": ">>",
        "failed": "!!",
    }
    icon = status_icons.get(item.qc_status.value, "  ")
    click.echo(
        f"  [{icon}] {item.id} | @{item.influencer_handle} | "
        f"{item.content_type.value} | {item.platform.value} | "
        f"{item.qc_status.value}"
    )


if __name__ == "__main__":
    main()
