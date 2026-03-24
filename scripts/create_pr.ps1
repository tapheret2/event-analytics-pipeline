param([string]$Head,[string]$Base,[string]$Title,[string]$Body)
$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$headers=@{ Authorization=('token '+$token); 'User-Agent'='openclaw-autofix'; Accept='application/vnd.github+json' }
$url='https://api.github.com/repos/Peganyx/test-agent/pulls'
$payload=@{ title=$Title; head=$Head; base=$Base; body=$Body; draft=$false } | ConvertTo-Json -Depth 6
$pr=Invoke-RestMethod -Method Post -Headers $headers -Uri $url -Body $payload
[PSCustomObject]@{ number=$pr.number; url=$pr.html_url } | ConvertTo-Json
