$ErrorActionPreference='Stop'
$dstDir='C:\Users\ADMIN\.openclaw\workspace\assets'
New-Item -ItemType Directory -Force $dstDir | Out-Null
$ico=Join-Path $dstDir 'bybit.ico'

# Try common favicon locations
$urls=@(
  'https://www.bybit.com/favicon.ico',
  'https://www.bybit.com/en/favicon.ico',
  'https://www.bybit.com/favicon-32x32.png'
)

foreach($u in $urls){
  try {
    Invoke-WebRequest -Uri $u -OutFile $ico -UseBasicParsing
    if((Get-Item $ico).Length -gt 0){
      Write-Output "OK $u -> $ico"
      exit 0
    }
  } catch {}
}

Write-Error 'Could not download bybit icon'
