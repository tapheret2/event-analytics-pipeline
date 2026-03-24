$ErrorActionPreference = 'Stop'

$p = Join-Path $env:USERPROFILE '.openclaw\openclaw.json'
$c = Get-Content -Raw -Path $p | ConvertFrom-Json

if (-not $c.plugins) {
  $c | Add-Member -NotePropertyName plugins -NotePropertyValue ([pscustomobject]@{})
}
if (-not $c.plugins.allow) {
  $c.plugins | Add-Member -NotePropertyName allow -NotePropertyValue @()
}
if ($c.plugins.allow -notcontains 'zalo-personal') {
  $c.plugins.allow += 'zalo-personal'
}

if (-not $c.channels) {
  $c | Add-Member -NotePropertyName channels -NotePropertyValue ([pscustomobject]@{})
}
if (-not $c.channels.'zalo-personal') {
  $c.channels | Add-Member -NotePropertyName 'zalo-personal' -NotePropertyValue ([pscustomobject]@{})
}

$zp = $c.channels.'zalo-personal'

# Ensure properties exist (PSCustomObject may not allow setting new properties directly)
$zp | Add-Member -NotePropertyName dmPolicy -NotePropertyValue 'pairing' -Force
$zp | Add-Member -NotePropertyName groupPolicy -NotePropertyValue 'disabled' -Force

if ($zp.PSObject.Properties.Name -contains 'allowFrom') {
  $zp.PSObject.Properties.Remove('allowFrom')
}

$c | ConvertTo-Json -Depth 50 | Set-Content -Encoding UTF8 -Path $p

Write-Output 'configured_zalo_personal=ok'
