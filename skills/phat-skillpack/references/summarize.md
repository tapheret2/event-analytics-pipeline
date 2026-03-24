# summarize (CLI) — notes

Summarize URLs, local files, and YouTube links.

## Quick start
- `summarize "https://example.com" --model google/gemini-3-flash-preview`
- `summarize "/path/to/file.pdf" --model google/gemini-3-flash-preview`
- `summarize "https://youtu.be/..." --youtube auto`

## Useful flags
- `--length short|medium|long|xl|xxl`
- `--max-output-tokens`
- `--extract-only` (URLs only)
- `--json`
- `--firecrawl auto|off|always` (fallback extraction)
- `--youtube auto` (Apify fallback if `APIFY_API_TOKEN` is set)

## Keys
Set provider API key env vars:
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- xAI: `XAI_API_KEY`
- Google: `GEMINI_API_KEY` (aliases: `GOOGLE_GENERATIVE_AI_API_KEY`, `GOOGLE_API_KEY`)

## Optional config
`~/.summarize/config.json` e.g. `{ "model": "openai/gpt-5.2" }`

Source: https://clawhub.ai/steipete/summarize
