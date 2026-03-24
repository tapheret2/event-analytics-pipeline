$ErrorActionPreference='Stop'
$envFile='D:\\Multi Agents\\option-b\\.env'
$token=(Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line.Split('=',2)[1].Trim()
$headers=@{ Authorization = "Bearer $token"; 'X-GitHub-Api-Version'='2022-11-28'; Accept='application/vnd.github+json' }

$prNumber=33
$issueNumber=32
$prUrl='https://github.com/Peganyx/test-agent/pull/33'

$bodyPr=@{ body = "🤖 Auto-fix: completed\n\nChanges:\n- Promo codes are now strictly allow-listed (no pattern/regex-based bypass).\n- Input is normalized (case + whitespace).\n- Added unittest regression tests covering invalid codes like FAKE1.\n\nTest run:\n- python -m unittest -q (pass)\n\nFixes #$issueNumber" } | ConvertTo-Json
$bytesPr=[System.Text.Encoding]::UTF8.GetBytes($bodyPr)
Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Body $bytesPr -Uri "https://api.github.com/repos/Peganyx/test-agent/issues/$prNumber/comments" | Out-Null

$bodyIssue=@{ body = "🤖 Auto-fix: completed\n\nOpened PR: $prUrl\n\nThis removes the promo-code bypass where any code ending in a digit could yield a 100% discount." } | ConvertTo-Json
$bytesIssue=[System.Text.Encoding]::UTF8.GetBytes($bodyIssue)
Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -Body $bytesIssue -Uri "https://api.github.com/repos/Peganyx/test-agent/issues/$issueNumber/comments" | Out-Null

'OK'
