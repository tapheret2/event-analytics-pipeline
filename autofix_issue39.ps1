$ErrorActionPreference='Stop'

# Inputs
$repo = 'Peganyx/test-agent'
$issueNum = 39
$branch = "fix/issue-$issueNum"
$baseBranch = 'main'

# Token
$envPath = 'D:\Multi Agents\option-b\.env'
if (!(Test-Path $envPath)) { throw "Missing .env at $envPath" }
$envText = Get-Content $envPath -Raw
$m = [regex]::Match($envText, '(?m)^\s*GITHUB_TOKEN\s*=\s*(.+)\s*$')
if (!$m.Success) { throw 'GITHUB_TOKEN not found in .env' }
$token = $m.Groups[1].Value.Trim().Trim('"').Trim("'")

$headers = @{
  Authorization = "token $token"
  Accept        = 'application/vnd.github+json'
  'User-Agent'  = 'openclaw-autofix'
}

# Workdir (outside ~/.openclaw)
$root = Join-Path $env:TEMP "openclaw-autofix-$issueNum-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Force -Path $root | Out-Null
Write-Host "Workdir: $root"

# Fetch issue details
$issue = Invoke-RestMethod -Method Get -Headers $headers -Uri "https://api.github.com/repos/$repo/issues/$issueNum"

# Comment started
$startedBody = @{
  body = "🤖 Auto-fix: started`n`nI’m taking a look at adding rate limiting / spam protection for the /tasks endpoint and will follow up with a PR."
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Uri "https://api.github.com/repos/$repo/issues/$issueNum/comments" -Body $startedBody | Out-Null
Write-Host 'Posted started comment.'

# Clone
$cloneUrl = "https://x-access-token:$token@github.com/$repo.git"
Set-Location $root
git clone $cloneUrl repo | Out-Host
Set-Location (Join-Path $root 'repo')

# Determine default branch (fallback main)
try {
  $repoInfo = Invoke-RestMethod -Method Get -Headers $headers -Uri "https://api.github.com/repos/$repo"
  if ($repoInfo.default_branch) { $baseBranch = $repoInfo.default_branch }
} catch {}
Write-Host "Base branch: $baseBranch"

git checkout $baseBranch | Out-Host

git checkout -b $branch | Out-Host

# Run Codex to implement fix (Codex needs PTY; script is non-PTY, but codex exec works non-interactively)
# NOTE: If your Codex config requires PTY, run this script manually in a terminal.

$prompt = @"
Fix GitHub issue #$issueNum in $repo.

Issue title: $($issue.title)
Issue URL: $($issue.html_url)
Issue body:
$($issue.body)

Goal:
- Add rate limiting / anti-spam protection to the /tasks endpoint to mitigate DoS/spam.
- Prefer a simple, maintainable approach (e.g., per-IP limiter; if behind proxy, respect X-Forwarded-For safely).
- Add/adjust tests if the repo has them.
- Update any relevant docs/config.

Constraints:
- Keep changes minimal and focused.
- Run the project's tests/lint (or at least a basic sanity check) before finishing.
- Commit with a clear message.

When done:
- Print a short summary of what you changed.
"@

codex exec --full-auto $prompt | Out-Host

# Ensure we have a commit
$pending = git status --porcelain
if ($pending) {
  Write-Host 'Working tree not clean after Codex run; committing.'
  git add -A | Out-Host
  git commit -m "fix: add rate limiting to /tasks (Fixes #$issueNum)" | Out-Host
}

# Push branch
$remoteBranch = $branch

git push -u origin $remoteBranch | Out-Host

# Create PR
$prTitle = "fix: rate limit /tasks (Fixes #$issueNum)"
$prBody = "Fixes #$issueNum\n\nAutomated fix: adds rate limiting / spam protection to the /tasks endpoint." 
$prPayload = @{
  title = $prTitle
  head  = $remoteBranch
  base  = $baseBranch
  body  = $prBody
  maintainer_can_modify = $true
} | ConvertTo-Json

$pr = Invoke-RestMethod -Method Post -Headers $headers -Uri "https://api.github.com/repos/$repo/pulls" -Body $prPayload
Write-Host "Created PR: $($pr.html_url)"

# AI Review pass (best-effort): run codex review if available; otherwise skip.
try {
  $review = codex review --base origin/$baseBranch 2>$null
  if ($LASTEXITCODE -eq 0 -and $review) {
    $review | Out-Host
    $review | Set-Content -Encoding UTF8 -Path "$root\\codex_review.txt"
  }
} catch {}

# Comment final (PR + issue)
$finalMsg = "🤖 Auto-fix: PR opened: $($pr.html_url)\n\nIf you’d like, I can iterate based on review feedback or CI results."

$issueFinalBody = @{ body = $finalMsg } | ConvertTo-Json
Invoke-RestMethod -Method Post -Headers $headers -Uri "https://api.github.com/repos/$repo/issues/$issueNum/comments" -Body $issueFinalBody | Out-Null

$prCommentBody = @{ body = $finalMsg } | ConvertTo-Json
Invoke-RestMethod -Method Post -Headers $headers -Uri "https://api.github.com/repos/$repo/issues/$($pr.number)/comments" -Body $prCommentBody | Out-Null

# Persist state
$statePath = 'C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'
if (Test-Path $statePath) {
  $state = Get-Content $statePath -Raw | ConvertFrom-Json
} else {
  $state = [pscustomobject]@{ processedIssueNumbers=@(); processed=@{} }
}
if (-not $state.processedIssueNumbers) { $state | Add-Member -NotePropertyName processedIssueNumbers -NotePropertyValue @() -Force }
if (-not ($state.processedIssueNumbers -contains $issueNum)) { $state.processedIssueNumbers += $issueNum }
if (-not $state.processed) { $state | Add-Member -NotePropertyName processed -NotePropertyValue @{} -Force }
$state.processed."$issueNum" = [pscustomobject]@{ pr = $pr.html_url; branch = $branch; processedAt = (Get-Date).ToString('o') }

($state | ConvertTo-Json -Depth 10) | Set-Content -Encoding UTF8 -Path $statePath

# Write summary artifact
@{
  issue = $issue.html_url
  pr    = $pr.html_url
  branch = $branch
  workdir = $root
} | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path 'C:\Users\ADMIN\.openclaw\workspace\autofix_result.json'
