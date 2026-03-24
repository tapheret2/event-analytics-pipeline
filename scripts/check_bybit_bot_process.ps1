$ErrorActionPreference = 'SilentlyContinue'
$pattern = 'bot_btc15m_v3\.py'
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match $pattern }

if (-not $procs) {
  Write-Output 'NO_BOT_PROCESS'
  exit 0
}

$procs | Select-Object ProcessId, CommandLine | Format-List
