param([int]$IssueNumber,[string]$Head,[string]$Base='main')
$ErrorActionPreference='Stop'
$owner='Peganyx'; $repo='test-agent'
$envPath = 'D:\Multi Agents\option-b\.env'
$line = (Select-String -Path $envPath -Pattern '^[ ]*GITHUB_TOKEN=' | Select-Object -First 1).Line
if(-not $line){ throw "No GITHUB_TOKEN line in $envPath" }
$token = $line.Substring($line.IndexOf('=')+1).Trim()
if($token.StartsWith('"') -and $token.EndsWith('"')){ $token = $token.Trim('"') }
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }

$title = "Fix ShopEngine payment/admin security issues (Fixes #$IssueNumber)"
$body = @"
Fixes #$IssueNumber

Changes:
- Use placeholder Stripe key by default; allow overriding via STRIPE_API_KEY
- Replace weak webhook verification with HMAC-SHA256 + constant-time compare
- Require X-Admin-Token for admin endpoints; allow override via SHOP_ADMIN_TOKEN

Test plan:
- pytest
"@

$url = "https://api.github.com/repos/$owner/$repo/pulls"
$payload = @{ title=$title; head=$Head; base=$Base; body=$body; draft=$false } | ConvertTo-Json
$pr = Invoke-RestMethod -Uri $url -Headers $headers -Method Post -Body $payload -ContentType 'application/json'
$pr.html_url
