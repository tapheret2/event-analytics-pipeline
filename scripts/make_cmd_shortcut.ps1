param(
  [Parameter(Mandatory=$true)][string]$CmdPath,
  [Parameter(Mandatory=$true)][string]$ShortcutPath,
  [string]$IconPath = $null
)

$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut($ShortcutPath)
$sc.TargetPath = "$env:ComSpec"  # cmd.exe
$sc.Arguments = "/k \"\"$CmdPath\"\""  # keep window open
$sc.WorkingDirectory = Split-Path $CmdPath
if ($IconPath -and (Test-Path $IconPath)) {
  $sc.IconLocation = $IconPath
}
$sc.WindowStyle = 1
$sc.Save()
"OK"
