$statePath='C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'
$state=@{}
if(Test-Path $statePath){ $state=Get-Content $statePath -Raw | ConvertFrom-Json }
$processedNums=@($state.PSObject.Properties.Name | ForEach-Object {[int]$_})

$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$headers=@{ Authorization = ('token ' + $token); 'User-Agent' = 'openclaw-autofix' }

$issuesUrl='https://api.github.com/repos/Peganyx/test-agent/issues?state=open&labels=auto-fix&sort=updated&direction=desc&per_page=20'
$issues=Invoke-RestMethod -Headers $headers -Uri $issuesUrl

foreach($i in $issues){
  if($i.pull_request){ continue }
  $num=[int]$i.number
  if($processedNums -contains $num){ continue }
  $commentsUrl="https://api.github.com/repos/Peganyx/test-agent/issues/$num/comments?per_page=100"
  $comments=Invoke-RestMethod -Headers $headers -Uri $commentsUrl
  $started=$false
  foreach($c in $comments){ if($c.body -match '🤖 Auto-fix: started'){ $started=$true; break } }
  if($started){ continue }
  [PSCustomObject]@{ number=$num; title=$i.title; url=$i.html_url; updated_at=$i.updated_at } | ConvertTo-Json -Depth 4
  exit 0
}
Write-Output ''
exit 0
