# Influencer Army

AI Influencer Agency powered by **Higgsfield** (video generation) and **Nano Banana 2** (image generation).

## What it does

Create and manage AI-generated influencer personas with consistent visual identity across photos and videos:

- **Nano Banana 2** (Gemini 3.1 Flash Image) generates photorealistic influencer photos with character consistency, text rendering, and up to 4K resolution
- **Higgsfield** converts static images into cinematic 5-second videos with motion presets, and maintains character consistency across generations

## Setup

```bash
# Install dependencies
pip install -e .

# Copy and fill in your API keys
cp .env.example .env
```

You'll need:
- **Higgsfield API credentials** from [cloud.higgsfield.ai/api-keys](https://cloud.higgsfield.ai/api-keys)
- **Google API key** from [AI Studio](https://aistudio.google.com/apikey) (for Nano Banana 2)

## Usage

### Add an influencer

```bash
influencerarmy add \
  --name "Luna Rivera" \
  --handle luna_rivera \
  --niche fitness \
  --style "golden hour photography, athletic wear, outdoor settings" \
  --platform instagram --platform tiktok
```

### Generate a photo

```bash
influencerarmy photo luna_rivera \
  --prompt "doing yoga on a beach at sunset, wearing athletic wear"
```

### Generate a video (reel)

```bash
influencerarmy video luna_rivera \
  --prompt "running through a park in autumn" \
  --motion slow_zoom_in \
  --caption "Morning runs hit different 🍂" \
  --hashtags "fitness,morningrun,healthylifestyle"
```

### List influencers

```bash
influencerarmy list
```

### Browse Higgsfield presets

```bash
influencerarmy styles   # image style presets
influencerarmy motions  # video motion presets
```

## Python API

```python
from influencerarmy.agency import Agency
from influencerarmy.pipeline import ContentPipeline
from influencerarmy.models import ContentType

# Create an influencer
agency = Agency()
from influencerarmy.models import InfluencerProfile
profile = InfluencerProfile(
    name="Luna Rivera",
    handle="luna_rivera",
    niche="fitness",
    style_description="golden hour, athletic wear",
)
agency.add_influencer(profile)

# Generate content
brief = agency.create_brief(
    handle="luna_rivera",
    content_type=ContentType.PHOTO,
    prompt="doing yoga on a beach at sunset",
)

pipeline = ContentPipeline()
import asyncio
result = asyncio.run(pipeline.execute_brief(brief))
print(result)
```

## Architecture

```
influencerarmy/
├── config.py        # Settings from .env (API keys, output dir)
├── models.py        # Pydantic data models
├── nano_banana.py   # Nano Banana 2 (Gemini API) client
├── higgsfield.py    # Higgsfield Cloud API client
├── agency.py        # Influencer profile management
├── pipeline.py      # Content creation orchestrator
└── cli.py           # Click CLI entry point
```

## Costs

| Service | Operation | Cost |
|---------|-----------|------|
| Nano Banana 2 | Image (1K) | ~$0.10 |
| Nano Banana 2 | Image (4K) | ~$0.15 |
| Higgsfield | Image (1080p) | ~$0.19 |
| Higgsfield | Video (standard) | ~$0.38 |
| Higgsfield | Character creation | ~$2.50 |
