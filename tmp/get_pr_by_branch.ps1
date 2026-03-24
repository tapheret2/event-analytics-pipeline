param([string]$Head)
$ErrorActionPreference='Stop'
$owner='Peganyx'; $repo='test-agent'
$envPath = 'D:\Multi Agents\option-b\.env'
$line = (Select-String -Path $envPath -Pattern '^[ ]*GITHUB_TOKEN=' | Select-Object -First 1).Line
if(-not $line){ throw "No GITHUB_TOKEN line in $envPath" }
$token = $line.Substring($line.IndexOf('=')+1).Trim()
if($token.StartsWith('"') -and $token.EndsWith('"')){ $token = $token.Trim('"') }
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }

$url = "https://api.github.com/repos/$owner/$repo/pulls?state=open&head=${owner}:$Head"
$prs = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
if(-not $prs -or $prs.Count -eq 0){ exit 3 }
$prs[0] | ConvertTo-Json -Depth 20
