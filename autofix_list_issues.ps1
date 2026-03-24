$envFile='D:\Multi Agents\option-b\.env'
$vars=@{}
Get-Content -LiteralPath $envFile | ForEach-Object {
  if($_ -match '^(?<k>[A-Z0-9_]+)=(?<v>.*)$'){
    $vars[$matches.k]=$matches.v.Trim()
  }
}
$token=$vars['GITHUB_TOKEN']
$headers=@{
  Authorization = 'token ' + $token
  'User-Agent'='openclaw-autofix'
  Accept='application/vnd.github+json'
}
$uri='https://api.github.com/repos/Peganyx/test-agent/issues?state=open&labels=auto-fix&sort=created&direction=desc&per_page=20'
$issues=Invoke-RestMethod -Headers $headers -Uri $uri -Method Get
$issues = $issues | Where-Object { -not $_.pull_request }
$issues | Select-Object -First 10 number,title,html_url,created_at | ConvertTo-Json -Depth 3
