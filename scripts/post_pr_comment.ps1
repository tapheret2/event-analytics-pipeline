param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][int]$Number,
  [Parameter(Mandatory=$true)][string]$Body
)

$envPath='D:\Multi Agents\option-b\.env'
$tokenLine = Get-Content $envPath | Where-Object { $_ -match '^GITHUB_TOKEN=' } | Select-Object -First 1
$token = $tokenLine -replace '^GITHUB_TOKEN=',''
$headers=@{ Authorization = "Bearer $token"; 'User-Agent'='openclaw-autofix'; Accept='application/vnd.github+json' }

$payload = @{ body = $Body } | ConvertTo-Json
$url = "https://api.github.com/repos/$Repo/issues/$Number/comments"
$res = Invoke-RestMethod -Method Post -Headers $headers -Uri $url -Body $payload
$res.html_url
