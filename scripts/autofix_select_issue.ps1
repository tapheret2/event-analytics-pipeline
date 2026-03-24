$ErrorActionPreference='Stop'

$envPath='D:\Multi Agents\option-b\.env'
$vars=@{}
Get-Content $envPath | ForEach-Object {
  if($_ -match '^[A-Z0-9_]+=' ){
    $k,$v=$_.Split('=',2)
    $vars[$k]=$v
  }
}

$token=$vars['GITHUB_TOKEN']
$owner=$vars['REPO_OWNER']
$repo=$vars['REPO_NAME']
$statePath='C:\Users\ADMIN\.openclaw\workspace\autofix_state.json'

$processed=@{}
if(Test-Path $statePath){
  $processed=(Get-Content $statePath -Raw | ConvertFrom-Json)
}

$headers=@{
  Authorization=("token {0}" -f $token)
  'User-Agent'='openclaw-autofix'
  Accept='application/vnd.github+json'
}

$uri=('https://api.github.com/repos/{0}/{1}/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=30' -f $owner,$repo)
$issues=Invoke-RestMethod -Headers $headers -Uri $uri

$selected=$null
foreach($it in $issues){
  if($it.PSObject.Properties.Name -contains 'pull_request'){ continue }
  $num=[string]$it.number
  if($processed.PSObject.Properties.Name -contains $num){ continue }

  $cUri=('https://api.github.com/repos/{0}/{1}/issues/{2}/comments?per_page=100' -f $owner,$repo,$it.number)
  $comments=Invoke-RestMethod -Headers $headers -Uri $cUri
  $hasStarted=$false
  foreach($c in $comments){
    if($c.body -like '*🤖 Auto-fix: started*'){ $hasStarted=$true; break }
  }
  if(-not $hasStarted){ $selected=$it; break }
}

if(-not $selected){
  Write-Output 'NO_ISSUE'
  exit 0
}

Write-Output ("{0}|{1}" -f $selected.number,$selected.title)
