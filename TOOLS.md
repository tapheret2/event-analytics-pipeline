# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Local installs / paths

### gogcli (gog)
- Binary: `C:\Users\ADMIN\.openclaw\workspace\bin\gog.exe`
- Version observed: `v0.12.0`
- Credentials stored at: `C:\Users\ADMIN\AppData\Roaming\gogcli\credentials.json`
- Tip: set `GOG_ACCOUNT=<email>` to avoid repeating `--account`.

### Notion (API)
- Use Notion REST API with `Notion-Version: 2022-06-28`.
- Primary database (Phát):
  - Name: `To do`
  - database_id: `31e4c265832d8011bc64e832d0cff957`
  - Expected properties: `Task`, `Description`, `Deadline`, `Status`, `Priority`, `People`, `Category`.

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.
