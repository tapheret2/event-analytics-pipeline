$ErrorActionPreference='Stop'

$envPath = 'D:\Multi Agents\option-b\.env'
if (!(Test-Path $envPath)) { throw "Missing .env at $envPath" }

$envText = Get-Content $envPath -Raw
$m = [regex]::Match($envText, '(?m)^\s*GITHUB_TOKEN\s*=\s*(.+)\s*$')
if (!$m.Success) { throw 'GITHUB_TOKEN not found in .env' }
$token = $m.Groups[1].Value.Trim().Trim('"').Trim("'")

$repo = 'Peganyx/test-agent'
$statePath = 'C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'

if (Test-Path $statePath) {
  $state = Get-Content $statePath -Raw | ConvertFrom-Json
} else {
  $state = [pscustomobject]@{ processedIssues=@(); processedIssueNumbers=@(); processed=@{} }
}

$headers = @{
  Authorization = "token $token"
  Accept        = 'application/vnd.github+json'
  'User-Agent'  = 'openclaw-autofix'
}

$issuesUrl = "https://api.github.com/repos/$repo/issues?state=open&labels=auto-fix&per_page=20&sort=created&direction=desc"
$issues = Invoke-RestMethod -Method Get -Headers $headers -Uri $issuesUrl
Write-Host "Found $($issues.Count) open issues w/ auto-fix"

$candidates = @()
foreach ($iss in $issues) {
  if ($iss.pull_request) { continue }
  $n = [int]$iss.number

  $already = $false
  if ($state.processedIssueNumbers -and ($state.processedIssueNumbers -contains $n)) { $already = $true }
  elseif ($state.processedIssues -and ($state.processedIssues -contains $n)) { $already = $true }
  elseif ($state.processed -and ($state.processed.PSObject.Properties.Name -contains "$n")) { $already = $true }

  if ($already) { continue }

  $commentsUrl = "https://api.github.com/repos/$repo/issues/$n/comments?per_page=100"
  $comments = Invoke-RestMethod -Method Get -Headers $headers -Uri $commentsUrl

  $hasStarted = $false
  foreach ($c in $comments) {
    if ($c.body -match [regex]::Escape('🤖 Auto-fix: started')) { $hasStarted = $true; break }
  }
  if ($hasStarted) { continue }

  $candidates += $iss
}

if ($candidates.Count -eq 0) {
  Write-Host 'No eligible issues.'
  exit 0
}

$target = $candidates[0]
$issueNum = [int]$target.number
Write-Host "Selected issue #${issueNum}: $($target.title)"

$out = [pscustomobject]@{
  number = $issueNum
  title  = $target.title
  url    = $target.html_url
  body   = $target.body
} | ConvertTo-Json -Depth 6

$out | Set-Content -Encoding UTF8 -Path '.\autofix_selected_issue.json'
