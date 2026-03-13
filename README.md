# Influencer Army

AI Influencer Agency — create persistent AI influencers that model products and post to their own Instagram and TikTok accounts, fully automated with quality control.

## How it works

Each AI influencer is a **static, consistent person** that looks the same across all content. They can model clothes, products, whatever you want — and each one has their own connected Instagram and TikTok accounts for automated posting.

**Nano Banana 2** (Google Gemini 3.1 Flash Image) generates photorealistic photos with character consistency using reference image anchoring. **Higgsfield** converts those photos into cinematic videos with motion presets.

### Content pipeline

```
Create brief → Generate image (NB2) → Generate video (Higgsfield)
                                          ↓
                                   Queue for QC review
                                          ↓
                              Approve ← You review → Reject
                                 ↓                      ↓
                          Auto-post to             Regenerate
                        IG + TikTok
```

## Setup

```bash
pip install -e .
cp .env.example .env
# Fill in your API keys (see below)
```

### API keys needed

| Service | Get it from | What for |
|---------|-------------|----------|
| Google API Key | [AI Studio](https://aistudio.google.com/apikey) | Nano Banana 2 image generation |
| Higgsfield | [cloud.higgsfield.ai](https://cloud.higgsfield.ai/api-keys) | Video generation + character consistency |
| Meta App | [developers.facebook.com](https://developers.facebook.com/) | Instagram posting via Graph API |
| TikTok App | [developers.tiktok.com](https://developers.tiktok.com/) | TikTok posting via Content Posting API |

## Usage

### 1. Create an influencer

```bash
influencerarmy add \
  --name "Luna Rivera" \
  --handle luna_rivera \
  --niche fitness \
  --dna "25yo latina woman, olive skin, dark brown wavy hair to shoulders, green eyes, athletic build, warm smile" \
  --style "golden hour photography, warm tones, natural lighting"
```

### 2. Add reference images (for consistency)

Generate or provide initial reference photos, then anchor the identity:

```bash
influencerarmy add-ref luna_rivera ./refs/luna_front.png
influencerarmy add-ref luna_rivera ./refs/luna_side.png
influencerarmy add-ref luna_rivera ./refs/luna_casual.png
```

### 3. Connect social accounts

Instagram and TikTok accounts must be created manually (no API for account creation), but once created, you connect them via OAuth for automated posting:

```bash
influencerarmy onboard luna_rivera
```

This walks you through:
- Creating the Instagram Business account + linking to a Facebook Page
- Creating the TikTok account + OAuth authorization
- Connecting API credentials for automated posting

### 4. Generate content

```bash
# Photo for Instagram
influencerarmy photo luna_rivera \
  --prompt "doing yoga on a beach at sunset, wearing black athletic wear" \
  --caption "Morning flow hits different 🌅" \
  --hashtags "yoga,fitness,beachlife"

# Product placement
influencerarmy product luna_rivera \
  --prompt "in a bright kitchen, making a smoothie" \
  --product-name "BlendJet 2" \
  --product-desc "portable blender in lavender" \
  --placement "using the blender on the counter" \
  --brand "BlendJet" \
  --caption "My new travel essential 💜"

# Video/reel
influencerarmy video luna_rivera \
  --prompt "running through a park in autumn" \
  --motion slow_zoom_in \
  --platform tiktok \
  --caption "Fall runs hit different 🍂"
```

### 5. Review and approve (quality control)

```bash
# See what's in the queue
influencerarmy queue --status pending_review

# Review an item (opens details, approve/reject)
influencerarmy review abc123def456

# Quick approve/reject
influencerarmy approve abc123def456
influencerarmy reject abc123def456 --reason "face doesn't match reference"
```

### 6. Post

```bash
# Post a single approved item
influencerarmy post abc123def456

# Post everything that's approved
influencerarmy post-all
```

### Skip QC (auto-post)

If you trust the output, skip review:

```bash
influencerarmy photo luna_rivera --prompt "..." --auto-post
```

Or set `AUTO_APPROVE=true` in `.env` to skip review globally.

## Architecture

```
influencerarmy/
├── models.py        # All data models (identity, content, social accounts)
├── config.py        # Settings from .env
├── identity.py      # Character consistency, reference images, prompt engineering
├── nano_banana.py   # Nano Banana 2 (Gemini API) — image generation
├── higgsfield.py    # Higgsfield Cloud API — video generation
├── instagram.py     # Instagram Graph API — automated posting
├── tiktok.py        # TikTok Content Posting API — automated posting
├── agency.py        # Influencer roster, onboarding, account management
├── queue.py         # Content queue with QC approval workflow
├── pipeline.py      # Orchestrates generation → QC → posting
└── cli.py           # CLI commands
```

## Costs per content piece

| Operation | Service | Cost |
|-----------|---------|------|
| Photo (1K) | Nano Banana 2 | ~$0.10 |
| Photo (4K) | Nano Banana 2 | ~$0.15 |
| Photo (1080p) | Higgsfield | ~$0.19 |
| Video (5s) | Higgsfield | ~$0.38 |
| Character setup | Higgsfield | ~$2.50 (one-time) |
| Instagram posting | Meta Graph API | Free |
| TikTok posting | TikTok API | Free |
