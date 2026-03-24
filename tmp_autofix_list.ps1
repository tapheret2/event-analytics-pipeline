$ErrorActionPreference='Stop'
$env:GITHUB_TOKEN = (Select-String -Path 'D:\Multi Agents\option-b\.env' -Pattern '^GITHUB_TOKEN=').Line.Split('=',2)[1].Trim()
$json = gh issue list -R Peganyx/test-agent --label auto-fix --state open --limit 20 --json number,title,createdAt
$issues = $json | ConvertFrom-Json
$issues | Sort-Object createdAt -Descending | ForEach-Object { "#${($_.number)}	$($_.createdAt)	$($_.title)" }
