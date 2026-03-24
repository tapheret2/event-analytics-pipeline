# agent-browser (CLI) — notes

Browser automation using snapshots + element refs.

## Core workflow
1) Navigate: `agent-browser open <url>`
2) Snapshot interactive elements: `agent-browser snapshot -i`
3) Act using refs from snapshot (e.g. `@e1`):
- `agent-browser click @e1`
- `agent-browser fill @e2 "text"`
4) After navigation / DOM changes, **snapshot again**.

## Handy snapshot options
- `agent-browser snapshot -i` (recommended)
- `-c` compact, `-d <depth>`, `-s "<css>"` scope

## Wait patterns
- `agent-browser wait 2000`
- `agent-browser wait --text "Success"`
- `agent-browser wait --url "/dashboard"`
- `agent-browser wait --load networkidle`

## State
- `agent-browser state save auth.json`
- `agent-browser state load auth.json`

Source: https://clawhub.ai/TheSethRose/agent-browser
