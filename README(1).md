# News Studio — v1.0

Automated 3-minute vertical news briefing: multi-source RSS → Gemini editorial JSON → capped AI video clips → open-license media fallback → Gemini TTS → FFmpeg subtitles/render → Telegram.

## What is included
- 10-story daily briefing
- Shot-level visual plan (3 shots/story)
- Gemini TTS narration
- Optional Veo 3.1 video provider, capped by `MAX_AI_VIDEO_CLIPS`
- Optional HTTP provider for Runway/other hosted endpoints
- Optional local command provider for Wan/LTX/VACE/Hunyuan workflows
- Openverse image fallback
- Branded fallback cards so the render does not stop when media generation fails
- 1080x1920 H.264 + AAC output
- Burned-in subtitles
- GitHub Actions daily schedule + manual run
- Telegram delivery

## Important: free vs paid compute
Open-source Wan/LTX/VACE/Hunyuan models are included as **adapters**, not as GPU compute. GitHub-hosted CPU runners cannot realistically run these large video models. Use a GPU machine/provider and set `VIDEO_PROVIDER=local` with `LOCAL_VIDEO_COMMAND`, or use an HTTP endpoint.

Veo/Runway are optional paid/API providers. Your consumer app quota is not automatically the same as an API quota. If an AI-video provider is unavailable, the pipeline falls back to Openverse or generated news cards and still renders the 3-minute package.

## Secrets
Required for a real run:
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN` (optional if Telegram delivery is not needed)
- `TELEGRAM_CHAT_ID` (optional if Telegram delivery is not needed)

## Optional variables
- `GEMINI_MODEL` (default `gemini-3.8-flash`)
- `GEMINI_TTS_MODEL` (default `gemini-3.8-flash-tts`)
- `VEO_MODEL` (default `veo-3.1-generate-preview`)
- `MAX_AI_VIDEO_CLIPS` (default `4`)
- `VIDEO_PROVIDER=veo|http|local|off`
- `VIDEO_PROVIDER_URL` for HTTP provider
- `LOCAL_VIDEO_COMMAND` for a local GPU command. It receives `{prompt}`, `{output}`, `{index}`.

## Local open-source engines to wire to the local adapter
- Wan 2.2
- LTX-2
- VACE (Wan/LTX workflows)
- HunyuanVideo

Do not commit model weights or API keys to GitHub.
