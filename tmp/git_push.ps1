param([string]$Branch)
$ErrorActionPreference='Stop'
$envPath = 'D:\Multi Agents\option-b\.env'
$line = (Select-String -Path $envPath -Pattern '^[ ]*GITHUB_TOKEN=' | Select-Object -First 1).Line
if(-not $line){ throw "No GITHUB_TOKEN line in $envPath" }
$token = $line.Substring($line.IndexOf('=')+1).Trim()
if($token.StartsWith('"') -and $token.EndsWith('"')){ $token = $token.Trim('"') }

cd "$env:USERPROFILE\.openclaw\workspace\test-agent"
# Use an auth header so we don't embed tokens in remotes/urls
& git -c "http.extraHeader=AUTHORIZATION: bearer $token" push -u origin $Branch
