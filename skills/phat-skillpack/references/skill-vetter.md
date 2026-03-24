# skill-vetter — security checklist (notes)

Never install a skill you haven’t vetted.

## Protocol

### 1) Source check
- Author reputation, stars/downloads, last updated, reviews.

### 2) Code review (mandatory)
Read **all files**. Reject if you see red flags like:
- hidden network exfil (curl/wget to unknown URLs)
- credential harvesting, reading ~/.ssh ~/.aws ~/.config
- touching MEMORY.md/USER.md/SOUL.md/IDENTITY.md without clear need
- eval/exec with external input, obfuscation/base64 tricks
- installs packages silently, asks for sudo/elevation
- accesses browser cookies/sessions

### 3) Permission scope
What files, commands, network destinations are required? Is it minimal?

### 4) Risk classify
- Low: notes/weather/formatting
- Medium: file ops/browser/APIs
- High: credentials/trading/system
- Extreme: root/security configs

## Report format
Produce a “SKILL VETTING REPORT” with metrics, red flags, permissions, risk level, verdict.

Source: https://clawhub.ai/spclaudehome/skill-vetter
