$ErrorActionPreference='Stop'
$owner='Peganyx'
$repo='test-agent'
$marker='🤖 Auto-fix: started'

# token
$envPath = 'D:\Multi Agents\option-b\.env'
$line = (Select-String -Path $envPath -Pattern '^[ ]*GITHUB_TOKEN=' | Select-Object -First 1).Line
if(-not $line){ throw "No GITHUB_TOKEN line in $envPath" }
$token = $line.Substring($line.IndexOf('=')+1).Trim()
if($token.StartsWith('"') -and $token.EndsWith('"')){ $token = $token.Trim('"') }

$headers=@{
  Authorization = "Bearer $token"
  'X-GitHub-Api-Version'='2022-11-28'
  Accept='application/vnd.github+json'
}

$statePath = "$env:USERPROFILE\.openclaw\workspace\autofix_state.json"
$state=@{}
if(Test-Path $statePath){
  $raw=Get-Content $statePath -Raw
  if($raw.Trim()){ $state = $raw | ConvertFrom-Json }
}
$processedNumbers = @($state.PSObject.Properties.Name | ForEach-Object {[int]$_})

$issuesUrl = "https://api.github.com/repos/$owner/$repo/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=30"
$issues = Invoke-RestMethod -Uri $issuesUrl -Headers $headers -Method Get

foreach($it in $issues){
  if($it.pull_request){ continue }
  $n=[int]$it.number
  if($processedNumbers -contains $n){ continue }

  $commentsUrl = "https://api.github.com/repos/$owner/$repo/issues/$n/comments?per_page=100"
  $comments = Invoke-RestMethod -Uri $commentsUrl -Headers $headers -Method Get
  $hasMarker = $false
  foreach($c in $comments){ if(($c.body -as [string]) -like "*$marker*"){ $hasMarker=$true; break } }
  if($hasMarker){ continue }

  # return selection as json
  $out=[ordered]@{ number=$n; title=$it.title; url=$it.html_url; created_at=$it.created_at }
  $out | ConvertTo-Json -Depth 5
  exit 0
}

exit 2
