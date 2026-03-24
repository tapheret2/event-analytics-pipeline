$ErrorActionPreference = 'SilentlyContinue'
$name = 'openclaw-zalo-personal-qr.png'
$searchRoots = @(
  'C:\\tmp',
  $env:TEMP,
  'C:\\Windows\\Temp'
) | Where-Object { $_ -and (Test-Path $_) }

$hit = $null
foreach ($root in $searchRoots) {
  $hit = Get-ChildItem -Path $root -Recurse -Filter $name -File | Select-Object -First 1
  if ($hit) { break }
}

if (-not $hit) {
  # Also try WSL-style /tmp path if it is mapped
  $wslTmp = 'C:\\tmp\\openclaw-zalo-personal-qr.png'
  if (Test-Path $wslTmp) { $hit = Get-Item $wslTmp }
}

if (-not $hit) {
  Write-Output 'qr_found=false'
  exit 0
}

$desktop = [Environment]::GetFolderPath('Desktop')
$dst = Join-Path $desktop 'zalo-qr.png'
Copy-Item -Force -Path $hit.FullName -Destination $dst
Write-Output ('qr_found=true')
Write-Output ('src=' + $hit.FullName)
Write-Output ('dst=' + $dst)
