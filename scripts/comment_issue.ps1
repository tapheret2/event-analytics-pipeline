param([int]$IssueNumber,[string]$Body)
$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$headers=@{ Authorization = ('token ' + $token); 'User-Agent'='openclaw-autofix'; Accept='application/vnd.github+json' }
$url="https://api.github.com/repos/Peganyx/test-agent/issues/$IssueNumber/comments"
$payload=@{ body=$Body } | ConvertTo-Json
Invoke-RestMethod -Method Post -Headers $headers -Uri $url -Body $payload | Out-Null
