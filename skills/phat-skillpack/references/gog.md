# gog (Google Workspace CLI) — notes

Use for Gmail/Calendar/Drive/Contacts/Sheets/Docs. Requires OAuth setup.

## Setup (once)
- `gog auth credentials /path/to/client_secret.json`
- `gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs`
- `gog auth list`

Tip: set `GOG_ACCOUNT=you@gmail.com` to avoid repeating `--account`.

## Common commands
- Gmail search: `gog gmail search 'newer_than:7d' --max 10`
- Gmail send: `gog gmail send --to a@b.com --subject "Hi" --body "Hello"`
- Calendar events: `gog calendar events --from <iso/date> --to <iso/date>`
- Drive search: `gog drive search "query" --max 10`
- Contacts: `gog contacts list --max 20`

### Sheets
- Get: `gog sheets get "Tab!A1:D10" --json`
- Update: `gog sheets update "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]' --input USER_ENTERED`
- Append: `gog sheets append "Tab!A:C" --values-json '[["x","y","z"]]' --insert INSERT_ROWS`
- Clear: `gog sheets clear "Tab!A2:Z"`
- Metadata: `gog sheets metadata --json`

### Docs
- Export: `gog docs export --format txt --out /tmp/doc.txt`
- Cat: `gog docs cat`

Safety note: confirm before **sending mail** or **creating events**.

Source: https://clawhub.ai/steipete/gog
