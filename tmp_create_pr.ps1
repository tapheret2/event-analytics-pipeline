$ErrorActionPreference='Stop'
$envFile='D:\\Multi Agents\\option-b\\.env'
$token=(Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line.Split('=',2)[1].Trim()
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }
$payload=@{
  title='fix: prevent promo code validation bypass (Fixes #32)'
  head='fix/issue-32'
  base='main'
  body="Fixes #32\n\n- Require promo codes to match an explicit allow-list (no pattern/regex-based discounts).\n- Add regression tests for invalid codes like 'FAKE1'."
} | ConvertTo-Json
$bytes=[System.Text.Encoding]::UTF8.GetBytes($payload)
try {
  $pr=Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Body $bytes -Uri 'https://api.github.com/repos/Peganyx/test-agent/pulls'
  $pr.html_url
} catch {
  # If PR already exists for this branch, fetch it.
  $prs=Invoke-RestMethod -Headers $headers -Uri 'https://api.github.com/repos/Peganyx/test-agent/pulls?state=open&per_page=50'
  $existing=$prs | Where-Object { $_.head.ref -eq 'fix/issue-32' } | Select-Object -First 1
  if($existing){ $existing.html_url } else { throw }
}
