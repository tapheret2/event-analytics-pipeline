param(
  [string]$Repo = 'Peganyx/test-agent',
  [string]$EnvPath = 'D:\\Multi Agents\\option-b\\.env',
  [string]$StatePath = 'C:\\Users\\ADMIN\\.openclaw\\workspace\\autofix_state.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if(!(Test-Path $EnvPath)) { throw "env not found: $EnvPath" }
$line = Get-Content $EnvPath | Where-Object { $_ -match '^GITHUB_TOKEN=' } | Select-Object -First 1
if(!$line) { throw 'GITHUB_TOKEN missing in env file' }
$token = ($line -replace '^GITHUB_TOKEN=', '').Trim().Trim('"')
$env:GITHUB_TOKEN = $token

$state = @{}
if(Test-Path $StatePath) {
  $raw = Get-Content $StatePath -Raw
  if($raw.Trim()) { $state = $raw | ConvertFrom-Json -AsHashtable }
}

$issuesJson = gh api "repos/$Repo/issues" -f state=open -f labels=auto-fix --paginate
$issues = $issuesJson | ConvertFrom-Json

# newest first by updated_at
$issues = $issues | Sort-Object -Property updated_at -Descending

function IssueAlreadyHasStartedComment($IssueNumber) {
  $commentsJson = gh api "repos/$Repo/issues/$IssueNumber/comments" --paginate
  $comments = $commentsJson | ConvertFrom-Json
  foreach($c in $comments) {
    if($c.body -match '🤖 Auto-fix: started') { return $true }
  }
  return $false
}

$target = $null
foreach($i in $issues) {
  $n = [string]$i.number
  if($state.ContainsKey($n)) { continue }
  if(IssueAlreadyHasStartedComment -IssueNumber $i.number) { continue }
  $target = $i
  break
}

if(!$target) {
  Write-Output 'NO_ISSUE'
  exit 0
}

Write-Output ("ISSUE\t{0}\t{1}\t{2}" -f $target.number, $target.updated_at, $target.title)
