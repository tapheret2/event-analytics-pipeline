$ErrorActionPreference = 'Stop'
$dst = Join-Path $env:USERPROFILE '.openclaw\extensions\codex-list'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Force 'C:\Users\ADMIN\.openclaw\workspace\tmp\codex_list\openclaw.plugin.json' -Destination $dst
Copy-Item -Force 'C:\Users\ADMIN\.openclaw\workspace\tmp\codex_list\index.js' -Destination $dst
Get-ChildItem -Path $dst | Select-Object Name,Length | Format-Table -AutoSize
