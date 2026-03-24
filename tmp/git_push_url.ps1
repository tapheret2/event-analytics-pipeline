param([string]$Branch)
$ErrorActionPreference='Stop'
$envPath = 'D:\Multi Agents\option-b\.env'
$line = (Select-String -Path $envPath -Pattern '^[ ]*GITHUB_TOKEN=' | Select-Object -First 1).Line
if(-not $line){ throw "No GITHUB_TOKEN line in $envPath" }
$token = $line.Substring($line.IndexOf('=')+1).Trim()
if($token.StartsWith('"') -and $token.EndsWith('"')){ $token = $token.Trim('"') }

cd "$env:USERPROFILE\.openclaw\workspace\test-agent"
$remote = "https://x-access-token:$token@github.com/Peganyx/test-agent.git"
& git push -u $remote $Branch
