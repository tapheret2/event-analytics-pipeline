$ErrorActionPreference='Stop'

$envPath = 'D:\\Multi Agents\\option-b\\.env'
$repo = 'Peganyx/test-agent'
$statePath = 'C:\\Users\\ADMIN\\.openclaw\\workspace\\autofix_state.json'
$startedMarker = '🤖 Auto-fix: started'

if (!(Test-Path $envPath)) { throw "Missing .env at $envPath" }

$tokenLine = Get-Content $envPath | Where-Object { $_ -match '^\s*GITHUB_TOKEN\s*=' } | Select-Object -First 1
if (-not $tokenLine) { throw 'GITHUB_TOKEN not found in .env' }
$token = ($tokenLine -replace '^\s*GITHUB_TOKEN\s*=\s*','').Trim().Trim('"').Trim("'")

$processed = @{}
if (Test-Path $statePath) {
  $state = Get-Content $statePath -Raw | ConvertFrom-Json
  foreach ($p in $state.PSObject.Properties) {
    $n = 0
    if ([int]::TryParse($p.Name, [ref]$n)) { $processed[$n] = $true }
  }
}

$headers = @{
  Authorization = "Bearer $token"
  Accept        = 'application/vnd.github+json'
  'User-Agent'  = 'openclaw-autofix'
  'X-GitHub-Api-Version' = '2022-11-28'
}

$issuesUrl = "https://api.github.com/repos/$repo/issues?state=open&labels=auto-fix&per_page=30&sort=created&direction=desc"
$issues = Invoke-RestMethod -Method Get -Headers $headers -Uri $issuesUrl

$selected = $null
foreach ($iss in $issues) {
  if ($iss.pull_request) { continue }
  $n = [int]$iss.number
  if ($processed.ContainsKey($n)) { continue }

  $commentsUrl = "https://api.github.com/repos/$repo/issues/$n/comments?per_page=100"
  $comments = Invoke-RestMethod -Method Get -Headers $headers -Uri $commentsUrl
  $hasStarted = $false
  foreach ($c in $comments) {
    if ($c.body -and $c.body -like "*$startedMarker*") { $hasStarted = $true; break }
  }
  if ($hasStarted) { continue }

  $selected = [pscustomobject]@{ number=$n; title=$iss.title; url=$iss.html_url; body=$iss.body }
  break
}

if (-not $selected) {
  Write-Host 'No eligible issues found.'
  exit 0
}

$selected | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path .\autofix_selected_issue.json
Write-Host ("Selected issue #$($selected.number): $($selected.title)")
