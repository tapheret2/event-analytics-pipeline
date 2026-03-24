param(
  [string]$SessionId
)

# Minimal helper: tails the process log and prints only lines containing 'PLACE'
# This does not send Telegram messages; the operator can monitor and forward.

while ($true) {
  try {
    $out = openclaw process log --sessionId $SessionId --offset 0 --limit 2000
    $lines = $out -split "`n" | Where-Object { $_ -match 'PLACE ' }
    if ($lines.Count -gt 0) {
      $lines | Select-Object -Last 5
    }
  } catch {}
  Start-Sleep -Seconds 10
}
