$ErrorActionPreference = 'Stop'
$envPath = 'D:\Multi Agents\option-b\.env'
$statePath = 'C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'

$envText = Get-Content -Raw $envPath
$tokenLine = ($envText -split "`n" | Where-Object { $_ -match '^GITHUB_TOKEN=' } | Select-Object -First 1)
if (-not $tokenLine) { throw "GITHUB_TOKEN not found in $envPath" }
$token = $tokenLine -replace '^GITHUB_TOKEN=',''
$hdr = @{ Authorization = 'Bearer ' + $token; 'User-Agent'='openclaw-autofix'; 'Accept'='application/vnd.github+json' }

$state = @{}
if (Test-Path $statePath) {
  $raw = Get-Content -Raw $statePath
  if ($raw.Trim()) { $state = $raw | ConvertFrom-Json }
}

$issues = Invoke-RestMethod -SkipHeaderValidation -Headers $hdr -Uri 'https://api.github.com/repos/Peganyx/test-agent/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=20'
$phrase = "🤖 Auto-fix: started"

$pick = $null
foreach ($iss in $issues) {
  if ($iss.pull_request) { continue }
  $num = [string]$iss.number
  if ($state.PSObject.Properties.Name -contains $num) { continue }

  $comments = @()
  if ($iss.comments -gt 0) {
    $comments = Invoke-RestMethod -SkipHeaderValidation -Headers $hdr -Uri $iss.comments_url
  }
  $already = $false
  foreach ($c in $comments) {
    if ($c.body -and $c.body -like "*$phrase*") { $already = $true; break }
  }
  if ($already) { continue }
  $pick = $iss
  break
}

if (-not $pick) {
  Write-Output 'NO_ISSUE'
  exit 0
}

$pick | Select-Object number,title,html_url | ConvertTo-Json -Depth 5
