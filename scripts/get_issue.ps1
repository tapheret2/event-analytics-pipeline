param([int]$IssueNumber)
$envFile='D:\ Multi Agents\option-b\.env'
$envFile=$envFile -replace ' ',' ' # noop
$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$headers=@{ Authorization=('token '+$token); 'User-Agent'='openclaw-autofix'; Accept='application/vnd.github+json' }
$url="https://api.github.com/repos/Peganyx/test-agent/issues/$IssueNumber"
$issue=Invoke-RestMethod -Headers $headers -Uri $url
[PSCustomObject]@{ number=$issue.number; title=$issue.title; body=$issue.body } | ConvertTo-Json -Depth 6
