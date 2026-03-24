$ErrorActionPreference='Stop'
$owner='Peganyx'
$repo='test-agent'

# Load token from .env
$envText = Get-Content -Raw 'D:\Multi Agents\option-b\.env'
$tokenLine = ($envText -split "`n" | Where-Object { $_ -match '^GITHUB_TOKEN=' } | Select-Object -First 1)
if(-not $tokenLine){ throw 'GITHUB_TOKEN not found in .env' }
$token = $tokenLine.Split('=',2)[1].Trim()

$headers = @{ 
  Authorization = 'token ' + $token
  'User-Agent'  = 'openclaw-autofix'
  Accept        = 'application/vnd.github+json'
}

$statePath='C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'
if(Test-Path $statePath){
  $state = Get-Content -Raw $statePath | ConvertFrom-Json
} else {
  $state = [pscustomobject]@{ history=@(); processedIssues=@() }
}
$processed = @{}
foreach($n in @($state.processedIssues)) { $processed[[string]$n] = $true }

# Find eligible issue
$issuesUri = "https://api.github.com/repos/$owner/$repo/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=20"
$issues = Invoke-RestMethod -Headers $headers -Uri $issuesUri -Method Get

$target = $null
foreach($iss in $issues){
  if($iss.pull_request){ continue }
  if($processed.ContainsKey([string]$iss.number)){ continue }

  $commentsUri = "https://api.github.com/repos/$owner/$repo/issues/$($iss.number)/comments?per_page=100"
  $comments = Invoke-RestMethod -Headers $headers -Uri $commentsUri -Method Get
  $started = $false
  foreach($c in $comments){
    if($c.body -and ($c.body -match 'Auto-fix: started')){ $started=$true; break }
  }
  if($started){ continue }

  $target = $iss
  break
}

if(-not $target){
  Write-Output 'No eligible issues found.'
  exit 0
}

$issueNumber = [int]$target.number
$issueTitle  = [string]$target.title
$issueBody   = [string]$target.body
Write-Output "Selected issue #$issueNumber - $issueTitle"

# Comment started
$startBody = "🤖 Auto-fix: started`n`nI’m picking this up now. I’ll open a PR shortly."
$issueCommentsPostUri = "https://api.github.com/repos/$owner/$repo/issues/$issueNumber/comments"
Invoke-RestMethod -Headers $headers -Uri $issueCommentsPostUri -Method Post -Body (@{ body = $startBody } | ConvertTo-Json) | Out-Null

# Clone and prepare branch
$tmp = Join-Path $env:TEMP ("autofix-$owner-$repo-issue-$issueNumber-" + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $tmp | Out-Null

# Use token in URL for push/pull
$cloneUrl = "https://$token@github.com/$owner/$repo.git"
git clone $cloneUrl $tmp | Out-Null
Set-Location $tmp

git config user.email 'autofix-bot@users.noreply.github.com'
git config user.name  'autofix-bot'

$repoInfoUri = "https://api.github.com/repos/$owner/$repo"
$repoInfo = Invoke-RestMethod -Headers $headers -Uri $repoInfoUri -Method Get
$base = [string]$repoInfo.default_branch

git checkout $base | Out-Null
git pull | Out-Null

$branch = "fix/issue-$issueNumber"
git checkout -b $branch | Out-Null

$ctx = "Issue #$issueNumber - $issueTitle`n`n$issueBody"
Set-Content -Encoding UTF8 -Path 'ISSUE_CONTEXT.txt' -Value $ctx

$attempt = 0
$decision = 'failed'
$prUrl = ''
$prNumber = $null

while($attempt -lt 3){
  $attempt++
  Write-Output "Attempt $attempt - implementing fix via codex"

  $prompt = @"
You are fixing a GitHub issue in repo $owner/$repo.

Read ISSUE_CONTEXT.txt for the issue description.

Goals:
- Implement a minimal, correct fix for issue #$issueNumber.
- Add/adjust tests if the repo has them.
- Run the project's test/lint commands (try npm test / pnpm test / pytest / go test depending on repo; pick what's appropriate).
- Keep the change small and focused.
- Commit your changes with message: "fix: issue #$issueNumber".

Constraints:
- Do NOT modify unrelated files.
- If the issue is unclear, inspect the codebase and infer intent from existing patterns/tests.
"@

  & codex exec --full-auto $prompt 2>&1 | Out-Host

  $aheadCount = [int](git rev-list --count HEAD ("^origin/$base"))
  if($aheadCount -le 0){
    Write-Output 'No new commits detected; retrying.'
    continue
  }

  git push -u origin $branch | Out-Null

  if(-not $prNumber){
    $prTitle = "fix: $issueTitle"
    $prBody  = "Fixes #$issueNumber`n`nAuto-generated fix."
    $createPrUri = "https://api.github.com/repos/$owner/$repo/pulls"
    $pr = Invoke-RestMethod -Headers $headers -Uri $createPrUri -Method Post -Body (@{ title=$prTitle; head=$branch; base=$base; body=$prBody; draft=$false } | ConvertTo-Json)
    $prUrl = [string]$pr.html_url
    $prNumber = [int]$pr.number
    Write-Output "Opened PR #$prNumber - $prUrl"
  }

  # AI review the diff
  $diff = git diff ("origin/$base...HEAD") | Out-String
  Set-Content -Encoding UTF8 -Path 'REVIEW_DIFF.patch' -Value $diff

  $reviewPrompt = @"
Review the patch in REVIEW_DIFF.patch for correctness, style, and likely CI failures.

If changes are needed, respond with exactly:
REQUEST_CHANGES:
- <bullets>

Otherwise respond with exactly:
APPROVE:
- <bullets>
"@

  $review = (& codex exec --full-auto $reviewPrompt 2>&1 | Out-String)
  if($review -match '^(?m)REQUEST_CHANGES:'){
    Write-Output 'AI review requested changes; applying and retrying.'
    Set-Content -Encoding UTF8 -Path 'REVIEW_NOTES.txt' -Value $review

    $fixPrompt = @"
Apply the requested changes from REVIEW_NOTES.txt.
Then run tests/lint again.
Commit with message: "fix: address review for issue #$issueNumber".
"@

    & codex exec --full-auto $fixPrompt 2>&1 | Out-Host
    git push | Out-Null
    continue
  }

  $decision = 'opened_pr'
  break
}

if(-not $prNumber){ throw 'Failed to open PR after retries.' }

# Final comments
$final = "🤖 Auto-fix: finished`n`nOpened PR: $prUrl`nDecision: $decision"
Invoke-RestMethod -Headers $headers -Uri $issueCommentsPostUri -Method Post -Body (@{ body = $final } | ConvertTo-Json) | Out-Null

$prIssueCommentsUri = "https://api.github.com/repos/$owner/$repo/issues/$prNumber/comments"
Invoke-RestMethod -Headers $headers -Uri $prIssueCommentsUri -Method Post -Body (@{ body = $final } | ConvertTo-Json) | Out-Null

# Update state
$newEntry = [pscustomobject]@{ issue=$issueNumber; pr=$prNumber; prUrl=$prUrl; decision=$decision; at=(Get-Date).ToString('o') }
$state.history += $newEntry
$state.processedIssues += $issueNumber
$state | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $statePath

Write-Output "Done. Issue #$issueNumber -> PR #$prNumber"
Write-Output "ANNOUNCE_TO_PHAT: $prUrl ($decision)"