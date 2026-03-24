$ErrorActionPreference='Stop'
$envPath='D:\\Multi Agents\\option-b\\.env'
$repo='Peganyx/test-agent'
$tokenLine=Get-Content $envPath | Where-Object {$_ -match '^\s*GITHUB_TOKEN\s*='} | Select-Object -First 1
$token=($tokenLine -replace '^\s*GITHUB_TOKEN\s*=\s*','').Trim().Trim('"').Trim("'")
$headers=@{Authorization="Bearer $token";Accept='application/vnd.github+json';'User-Agent'='openclaw-autofix';'X-GitHub-Api-Version'='2022-11-28'}
$url = 'https://api.github.com/repos/' + $repo + '/issues?state=open&labels=auto-fix&per_page=30&sort=created&direction=desc'
$issues = Invoke-RestMethod -Headers $headers -Uri $url
$issues | Where-Object { -not $_.pull_request } | Select-Object number,title,html_url | ConvertTo-Json -Depth 3
