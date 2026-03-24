param(
  [string]$Repo = 'Peganyx/test-agent',
  [string]$EnvPath = 'D:\\Multi Agents\\option-b\\.env',
  [string]$StatePath = 'C:\\Users\\ADMIN\\.openclaw\\workspace\\autofix_state.json',
  [string]$WorkDir = 'C:\\Users\\ADMIN\\.openclaw\\workspace\\autofix\\Peganyx_test-agent'
)

$ErrorActionPreference = 'Stop'

function Read-GithubToken([string]$path){
  if(!(Test-Path $path)){ throw "Env file not found: $path" }
  $line = (Get-Content $path | Where-Object { $_ -match '^GITHUB_TOKEN=' } | Select-Object -First 1)
  if(!$line){ throw "GITHUB_TOKEN not found in $path" }
  $tok = $line.Substring('GITHUB_TOKEN='.Length)
  $tok = $tok.Trim()
  if($tok.StartsWith('"') -and $tok.EndsWith('"')){ $tok = $tok.Trim('"') }
  return $tok
}

function Invoke-GH([string]$method, [string]$url, $body = $null, [string]$token){
  $headers = @{ Authorization = "token $token"; 'User-Agent' = 'openclaw-autofix'; Accept='application/vnd.github+json' }
  if($body -ne $null){
    $json = ($body | ConvertTo-Json -Depth 20)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-RestMethod -Method $method -Uri $url -Headers $headers -Body $bytes -ContentType 'application/json; charset=utf-8'
  }
  return Invoke-RestMethod -Method $method -Uri $url -Headers $headers
}

function Load-State([string]$path){
  if(Test-Path $path){
    try { return (Get-Content $path -Raw | ConvertFrom-Json) } catch { }
  }
  return [pscustomobject]@{ processedIssues = @(); processedPrs=@(); lastRunUtc = $null }
}

function Save-State([string]$path, $state){
  $dir = Split-Path -Parent $path
  if(!(Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  ($state | ConvertTo-Json -Depth 50) | Set-Content -Encoding UTF8 $path
}

$token = Read-GithubToken $EnvPath
$state = Load-State $StatePath
$processed = @{}
foreach($n in $state.processedIssues){ $processed["$n"] = $true }

# Find newest open issue with label auto-fix not started and not processed
$issuesUrl = "https://api.github.com/repos/$Repo/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=30"
$issues = Invoke-GH GET $issuesUrl $null $token

$target = $null
foreach($it in $issues){
  if($it.pull_request){ continue } # skip PRs
  $num = [int]$it.number
  if($processed.ContainsKey("$num")){ continue }
  # Check comments for started marker
  $commentsUrl = "https://api.github.com/repos/$Repo/issues/$num/comments?per_page=100"
  $comments = Invoke-GH GET $commentsUrl $null $token
  $started = $false
  foreach($c in $comments){ if($c.body -like '*🤖 Auto-fix: started*'){ $started = $true; break } }
  if($started){ continue }
  $target = $it
  break
}

if(-not $target){
  Write-Output "No eligible issues found."
  $state.lastRunUtc = (Get-Date).ToUniversalTime().ToString('o')
  Save-State $StatePath $state
  exit 0
}

$issueNumber = [int]$target.number
$issueTitle = [string]$target.title
$issueBody = [string]$target.body

# Comment started on issue
$startedBody = "🤖 Auto-fix: started\n\nI’m taking a look at this now. I’ll open a PR shortly."
Invoke-GH POST "https://api.github.com/repos/$Repo/issues/$issueNumber/comments" @{ body = $startedBody } $token | Out-Null

# Prepare git branch
Set-Location $WorkDir

git fetch --all --prune | Out-Null
# Determine default branch
$defaultBranch = 'main'
try {
  $repoInfo = Invoke-GH GET "https://api.github.com/repos/$Repo" $null $token
  if($repoInfo.default_branch){ $defaultBranch = [string]$repoInfo.default_branch }
} catch {}

git checkout $defaultBranch | Out-Null

git pull | Out-Null

$branch = "fix/issue-$issueNumber"
# Recreate branch fresh
if(git show-ref --verify --quiet "refs/heads/$branch"){
  git branch -D $branch | Out-Null
}

git checkout -b $branch | Out-Null

# Run Codex to implement fix
$prompt = @"
You are fixing GitHub issue #$issueNumber in repo $Repo.

Issue title: $issueTitle
Issue body:
$issueBody

Requirements:
- Make the minimal correct fix.
- Add/adjust tests if the repo has tests.
- Run the project’s tests / lint if available and ensure they pass.
- Commit changes with a clear message referencing issue #$issueNumber.

When done, print a short summary of what you changed and which commands you ran.
"@

$maxAttempts = 3
$reviewDecision = 'unknown'
$attempt = 0

while($attempt -lt $maxAttempts){
  $attempt++

  # Use Claude Code (non-interactive print mode)
  $agentCmd = "claude --permission-mode bypassPermissions --print " + ('"' + ($prompt -replace '"','\"') + '"')
  $agentOut = cmd /c $agentCmd
  if($LASTEXITCODE -ne 0){ throw "Claude Code failed on attempt $attempt" }

  # Quick AI review of the diff to decide whether to retry
  $diff = git diff --stat "$defaultBranch...$branch"
  $reviewPrompt = @"
Review the changes for issue #$issueNumber.

Diffstat:
$diff

Now run: git diff $defaultBranch...$branch

Decide strictly one word on the first line: APPROVE or REQUEST_CHANGES.
Then bullet points.
"@
  $reviewCmd = "claude --permission-mode bypassPermissions --print " + ('"' + ($reviewPrompt -replace '"','\"') + '"')
  $reviewOut = cmd /c $reviewCmd

  $firstLine = ($reviewOut | Select-Object -First 1)
  if($firstLine -match 'APPROVE'){ $reviewDecision = 'approve'; break }
  if($firstLine -match 'REQUEST_CHANGES'){ $reviewDecision = 'request_changes' }
  else { $reviewDecision = 'unknown' }

  if($reviewDecision -ne 'request_changes'){ break }

  # Feed review back into another codex attempt
  $prompt = @"
Follow-up for issue #$issueNumber.

The AI review requested changes:
$reviewOut

Please apply the requested changes if they are valid and in-scope.
Then run tests again and commit.
"@
}

# Ensure we have at least one commit ahead
$ahead = git rev-list --count "$defaultBranch..$branch"
if([int]$ahead -lt 1){ throw "No commits were created on branch $branch" }

# Push branch (use token in remote URL temporarily)
$remoteUrl = "https://x-access-token:$token@github.com/$Repo.git"
# Save original remote
$origRemote = (git remote get-url origin)

git remote set-url origin $remoteUrl | Out-Null
try {
  git push -u origin $branch | Out-Null
} finally {
  git remote set-url origin $origRemote | Out-Null
}

# Create PR
$prTitle = "fix: $issueTitle (#$issueNumber)"
$prBody = "Fixes #$issueNumber\n\nAutomated fix attempt."
$pr = Invoke-GH POST "https://api.github.com/repos/$Repo/pulls" @{ title=$prTitle; head=$branch; base=$defaultBranch; body=$prBody } $token
$prNumber = [int]$pr.number
$prUrl = [string]$pr.html_url

# Comment final to PR and issue
$finalText = "🤖 Auto-fix: finished\n\nOpened PR #${prNumber}: $prUrl\n\nDecision: $reviewDecision\nAttempts: $attempt"
Invoke-GH POST "https://api.github.com/repos/$Repo/issues/$prNumber/comments" @{ body = $finalText } $token | Out-Null
Invoke-GH POST "https://api.github.com/repos/$Repo/issues/$issueNumber/comments" @{ body = $finalText } $token | Out-Null

# Update state
$state.processedIssues = @($state.processedIssues + @($issueNumber) | Select-Object -Unique)
$state.processedPrs = @($state.processedPrs + @($prNumber) | Select-Object -Unique)
$state.lastRunUtc = (Get-Date).ToUniversalTime().ToString('o')
Save-State $StatePath $state

Write-Output "Processed issue #$issueNumber -> PR #$prNumber ($prUrl). Decision=$reviewDecision"
