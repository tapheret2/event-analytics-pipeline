param([int]$IssueNumber,[string]$Body)
$ErrorActionPreference='Stop'
$owner='Peganyx'; $repo='test-agent'
$envPath = 'D:\Multi Agents\option-b\.env'
$line = (Select-String -Path $envPath -Pattern '^[ ]*GITHUB_TOKEN=' | Select-Object -First 1).Line
if(-not $line){ throw "No GITHUB_TOKEN line in $envPath" }
$token = $line.Substring($line.IndexOf('=')+1).Trim()
if($token.StartsWith('"') -and $token.EndsWith('"')){ $token = $token.Trim('"') }
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }
$url = "https://api.github.com/repos/$owner/$repo/issues/$IssueNumber/comments"
$payload = @{ body = $Body } | ConvertTo-Json
Invoke-RestMethod -Uri $url -Headers $headers -Method Post -Body $payload -ContentType 'application/json' | Out-Null
