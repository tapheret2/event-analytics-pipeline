$ErrorActionPreference='Stop'
$envFile='D:\\Multi Agents\\option-b\\.env'
$token=(Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line.Split('=',2)[1].Trim()
$owner='Peganyx'
$repo='test-agent'
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }
$statePath='C:\\Users\\ADMIN\\.openclaw\\workspace\\autofix_state.json'
$state=@{}
if (Test-Path $statePath) {
  $obj=(Get-Content $statePath -Raw | ConvertFrom-Json)
  if($obj){ $obj.PSObject.Properties | ForEach-Object { $state[$_.Name]=$_.Value } }
}
$issues=Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$owner/$repo/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=20"
foreach($i in $issues){
  if($i.pull_request){ continue }
  $n=[string]$i.number
  if($state.ContainsKey($n)){ continue }
  $comments=Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$owner/$repo/issues/$($i.number)/comments?per_page=100"
  $already=$false
  foreach($c in $comments){ if($c.body -match '🤖 Auto-fix: started'){ $already=$true; break } }
  if($already){ continue }
  $out=@{ number=$i.number; title=$i.title; html_url=$i.html_url; created_at=$i.created_at }
  $out | ConvertTo-Json -Compress
  exit 0
}
''
