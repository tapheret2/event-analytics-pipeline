$ErrorActionPreference = 'Stop'

$base = 'C:\Users\ADMIN\.openclaw\workspace'
$tmp = Join-Path $base 'tmp'
$skillsDir = Join-Path $base 'skills'
New-Item -ItemType Directory -Force $tmp | Out-Null
New-Item -ItemType Directory -Force $skillsDir | Out-Null

$items = @(
  @{ slug = 'excel-xlsx';      url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=excel-xlsx' },
  @{ slug = 'spotify-player';  url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=spotify-player' },
  @{ slug = 'powerpoint-pptx'; url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=powerpoint-pptx' },
  @{ slug = 'data-analysis';   url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=data-analysis' },
  @{ slug = 'docker';          url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=docker' },
  @{ slug = 'weather';         url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=weather' },
  @{ slug = 'auto-updater';    url = 'https://wry-manatee-359.convex.site/api/v1/download?slug=auto-updater' }
)

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach($it in $items){
  $slug = $it.slug
  $url = $it.url
  $zip = Join-Path $tmp "$slug.zip"
  $dst = Join-Path $skillsDir $slug

  Write-Host "==> $slug"
  Invoke-WebRequest -Uri $url -OutFile $zip

  if(Test-Path $dst){
    $bak = "$dst.bak-$stamp"
    Rename-Item -Force $dst $bak
  }
  New-Item -ItemType Directory -Force $dst | Out-Null
  Expand-Archive -Path $zip -DestinationPath $dst -Force

  # Validate basic structure
  $skill = Join-Path $dst 'SKILL.md'
  if(!(Test-Path $skill)){
    Write-Warning "SKILL.md not found at $skill (zip layout may be nested)."
  }
}

Write-Host "DONE"
