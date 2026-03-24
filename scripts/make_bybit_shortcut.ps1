param(
  [string]$TargetCmd,
  [string]$ShortcutPath,
  [string]$IconPath
)

$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut($ShortcutPath)
$sc.TargetPath = $TargetCmd
$sc.WorkingDirectory = Split-Path $TargetCmd
$sc.IconLocation = $IconPath
$sc.WindowStyle = 1
$sc.Save()
Write-Output "OK shortcut -> $ShortcutPath"
