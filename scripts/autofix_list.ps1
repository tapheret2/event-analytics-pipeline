param(
  [string]$EnvPath = 'D:\Multi Agents\option-b\.env',
  [string]$Owner = 'Peganyx',
  [string]$Repo = 'test-agent'
)

$envLines = Get-Content $EnvPath
$tokenLine = $envLines | Where-Object { $_ -match '^GITHUB_TOKEN=' } | Select-Object -First 1
if (-not $tokenLine) { throw "GITHUB_TOKEN not found in $EnvPath" }
$token = ($tokenLine -split '=', 2)[1].Trim()

$h = @{ 
  Authorization = ('token ' + $token)
  'User-Agent'  = 'openclaw-autofix'
  Accept        = 'application/vnd.github+json'
}

$uri = "https://api.github.com/repos/$Owner/$Repo/issues?state=open&labels=auto-fix&per_page=50"
$issues = Invoke-RestMethod -Headers $h -Uri $uri
$issues | Select-Object number, title, html_url, comments, created_at | ConvertTo-Json -Depth 4
