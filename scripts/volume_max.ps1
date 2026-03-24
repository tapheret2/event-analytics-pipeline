$ErrorActionPreference = 'Stop'
$ws = New-Object -ComObject WScript.Shell
1..60 | ForEach-Object {
  $ws.SendKeys([char]175) # VK_VOLUME_UP
  Start-Sleep -Milliseconds 25
}
Write-Output 'volume_up_done'
