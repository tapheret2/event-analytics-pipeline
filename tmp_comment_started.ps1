$ErrorActionPreference='Stop'
$envFile='D:\\Multi Agents\\option-b\\.env'
$token=(Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line.Split('=',2)[1].Trim()
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }
$body='{"body":"🤖 Auto-fix: started (automated attempt)."}'
$bytes=[System.Text.Encoding]::UTF8.GetBytes($body)
Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Body $bytes -Uri 'https://api.github.com/repos/Peganyx/test-agent/issues/32/comments' | Out-Null
'OK'
