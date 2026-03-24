$ErrorActionPreference = 'Stop'

$repo = 'Peganyx/test-agent'
$statePath = 'C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'
$envFile = 'D:\Multi Agents\option-b\.env'
$startedMarker = '🤖 Auto-fix: started'

function Get-GitHubToken {
  param([string]$Path)
  if (!(Test-Path $Path)) { throw "env file not found: $Path" }
  $line = Get-Content $Path | Where-Object { $_ -match '^\s*GITHUB_TOKEN\s*=' } | Select-Object -First 1
  if (-not $line) { throw 'GITHUB_TOKEN not found in .env' }
  $token = ($line -replace '^\s*GITHUB_TOKEN\s*=\s*','').Trim()
  $token = $token.Trim('"').Trim([char]39)
  if (-not $token) { throw 'GITHUB_TOKEN empty' }
  return $token
}

function Invoke-GHApi {
  param(
    [Parameter(Mandatory=$true)][string]$Method,
    [Parameter(Mandatory=$true)][string]$Path,
    [object]$Body = $null,
    [Parameter(Mandatory=$true)][string]$Token
  )

  $uri = "https://api.github.com$Path"
  $headers = @{
    'Authorization' = "Bearer $Token"
    'Accept'        = 'application/vnd.github+json'
    'User-Agent'    = 'openclaw-autofix'
    'X-GitHub-Api-Version' = '2022-11-28'
  }

  if ($null -eq $Body) {
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
  }

  $json = $Body | ConvertTo-Json -Depth 20
  return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType 'application/json' -Body $json
}

function Load-State {
  if (!(Test-Path $statePath)) {
    return [ordered]@{ processed = @(); history = @() }
  }
  try {
    $raw = Get-Content $statePath -Raw
    if (-not $raw.Trim()) { return [ordered]@{ processed = @(); history = @() } }
    $obj = $raw | ConvertFrom-Json
    if (-not $obj.processed) { $obj | Add-Member -NotePropertyName processed -NotePropertyValue @() }
    if (-not $obj.history) { $obj | Add-Member -NotePropertyName history -NotePropertyValue @() }
    return $obj
  } catch {
    # If corrupted, keep a backup and start fresh
    Copy-Item $statePath "$statePath.bak" -Force
    return [ordered]@{ processed = @(); history = @() }
  }
}

function Save-State($state) {
  $state | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $statePath
}

function Git-AuthHeaderBase64([string]$Token) {
  $bytes = [Text.Encoding]::ASCII.GetBytes("x-access-token:$Token")
  return [Convert]::ToBase64String($bytes)
}

function Run($cmd, $cwd = $null) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'cmd.exe'
  $psi.Arguments = "/c $cmd"
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  if ($cwd) { $psi.WorkingDirectory = $cwd }

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  $null = $p.Start()
  $out = $p.StandardOutput.ReadToEnd()
  $err = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  if ($p.ExitCode -ne 0) {
    throw "Command failed ($($p.ExitCode)): $cmd`nSTDOUT:`n$out`nSTDERR:`n$err"
  }
  return ($out + $err)
}

$token = Get-GitHubToken -Path $envFile
$state = Load-State

# List newest open issues with label auto-fix (exclude PRs)
$issues = Invoke-GHApi -Method GET -Path "/repos/$repo/issues?state=open&labels=auto-fix&per_page=30&sort=created&direction=desc" -Token $token |
  Where-Object { -not $_.pull_request }

if (-not $issues -or $issues.Count -eq 0) {
  Write-Output "No open issues with label auto-fix in $repo."
  exit 0
}

$candidate = $null
foreach ($issue in $issues) {
  $n = [int]$issue.number
  if ($state.processed -contains $n) { continue }

  $comments = Invoke-GHApi -Method GET -Path "/repos/$repo/issues/$n/comments?per_page=100" -Token $token
  $alreadyStarted = $false
  foreach ($c in $comments) {
    if ($c.body -and $c.body -like "*$startedMarker*") { $alreadyStarted = $true; break }
  }
  if ($alreadyStarted) { continue }

  $candidate = $issue
  break
}

if (-not $candidate) {
  Write-Output "No eligible issues found (all already processed or already started)."
  exit 0
}

$issueNumber = [int]$candidate.number
$issueTitle = [string]$candidate.title
$issueBody  = [string]$candidate.body

# Comment started
$startBody = "$startedMarker\n\nI’m starting an automated fix pass now. I’ll open a PR if I can reproduce and fix it." 
$null = Invoke-GHApi -Method POST -Path "/repos/$repo/issues/$issueNumber/comments" -Body @{ body = $startBody } -Token $token

# Prepare working dir
$workRoot = Join-Path $env:TEMP ("openclaw-autofix-" + $repo.Replace('/','-') + "-issue-$issueNumber")
if (Test-Path $workRoot) { Remove-Item $workRoot -Recurse -Force }
New-Item -ItemType Directory -Path $workRoot | Out-Null

$auth = Git-AuthHeaderBase64 -Token $token
$cloneCmd = 'git -c http.https://github.com/.extraheader="AUTHORIZATION: basic ' + $auth + '" clone https://github.com/' + $repo + '.git .'
Run $cloneCmd $workRoot | Out-Null

# Create branch
$branch = "fix/issue-$issueNumber"
Run "git checkout -b $branch" $workRoot | Out-Null

# Let Codex implement the fix (and commit)
$prompt = @"
You are fixing GitHub issue #$issueNumber in repo $repo.

Issue title: $issueTitle

Issue body:
$issueBody

Requirements:
- Implement a correct fix for the issue.
- Add/adjust tests if the repo has a test suite.
- Keep changes minimal and in-scope.
- Make sure the project builds/tests.
- Commit your changes with a clear message.

After changes:
- Print a short summary of what you changed.
"@

# Run codex (Codex CLI is non-interactive for exec; this script runs it via cmd.exe)
# NOTE: do not use --yolo. Use --full-auto for safety.
$escapedPrompt = $prompt -replace '"','\\"'
Run ('codex exec --full-auto "' + $escapedPrompt + '"') $workRoot | Out-Null

# Ensure we have a commit
$status = Run "git status --porcelain" $workRoot
if ($status.Trim()) {
  # If codex didn't commit, commit now
  Run "git add -A" $workRoot | Out-Null
  Run "git commit -m \"fix: issue #$issueNumber\"" $workRoot | Out-Null
}

# Push branch
Run ('git -c http.https://github.com/.extraheader="AUTHORIZATION: basic ' + $auth + '" push -u origin ' + $branch) $workRoot | Out-Null

# Create PR
$prTitle = "fix: $issueTitle (#$issueNumber)"
$prBody = "Fixes #$issueNumber\n\nAutomated fix created by OpenClaw autofix agent."
$pr = Invoke-GHApi -Method POST -Path "/repos/$repo/pulls" -Body @{ title=$prTitle; head=$branch; base='main'; body=$prBody; draft=$false } -Token $token
$prNumber = [int]$pr.number
$prUrl = [string]$pr.html_url

# AI review loop (up to 3 tries): run codex review on diff vs main, apply suggested fixes if any.
$maxTries = 3
$reviewNotes = @()
for ($i=1; $i -le $maxTries; $i++) {
  $diff = Run "git diff origin/main...HEAD" $workRoot
  if (-not $diff.Trim()) { break }

  $reviewPrompt = @"
You are reviewing a patch for repo $repo.

Context: This PR should fix issue #$issueNumber.

Review the following diff. If you find problems that should be addressed (bugs, tests, edge cases, style that would block merge), list them.
If everything looks good, respond with exactly: APPROVED

DIFF:
$diff
"@

  $escapedReview = $reviewPrompt -replace '"','\\"'
  $reviewOut = Run ('codex exec --full-auto "' + $escapedReview + '"') $workRoot
  $reviewNotes += "--- Review attempt $i ---`n$reviewOut"

  if ($reviewOut -match '\bAPPROVED\b') { break }

  # Apply fixes based on review
  $fixPrompt = @"
Based on this review feedback, update the code accordingly.

Feedback:
$reviewOut

Requirements:
- Make the minimum necessary changes.
- Update/add tests if needed.
- Commit the changes.
"@
  $escapedFix = $fixPrompt -replace '"','\\"'
  Run ('codex exec --full-auto "' + $escapedFix + '"') $workRoot | Out-Null

  $status2 = Run "git status --porcelain" $workRoot
  if ($status2.Trim()) {
    Run "git add -A" $workRoot | Out-Null
    Run "git commit -m \"chore: address review feedback\"" $workRoot | Out-Null
  }
  Run ('git -c http.https://github.com/.extraheader="AUTHORIZATION: basic ' + $auth + '" push') $workRoot | Out-Null
}

# Comment final to PR and issue
$finalMsg = "Opened PR #${prNumber}: $prUrl\n\nNotes:\n- Issue: #$issueNumber\n- Branch: $branch\n\nAI review log (best-effort):\n" + ($reviewNotes -join "\n")
$null = Invoke-GHApi -Method POST -Path "/repos/$repo/issues/${prNumber}/comments" -Body @{ body = $finalMsg } -Token $token
$null = Invoke-GHApi -Method POST -Path "/repos/$repo/issues/$issueNumber/comments" -Body @{ body = "✅ Opened PR #${prNumber}: $prUrl" } -Token $token

# Update state
$state.processed += $issueNumber
$state.history += [ordered]@{ issue=$issueNumber; pr=$prNumber; prUrl=$prUrl; at=(Get-Date).ToString('o') }
Save-State $state

Write-Output ("Processed issue #$issueNumber - PR: $prUrl")