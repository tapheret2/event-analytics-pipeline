param([int]$Issue,[string]$Commit,[string]$Branch,[string]$PrUrl,[string]$Decision)
$ErrorActionPreference='Stop'
$path = "$env:USERPROFILE\.openclaw\workspace\autofix_state.json"
$state = @{}
if(Test-Path $path){
  $raw = Get-Content $path -Raw -Encoding UTF8
  if($raw.Trim()){ $state = $raw | ConvertFrom-Json }
}

$entry = [ordered]@{
  commit = $Commit
  branch = $Branch
  pr = $PrUrl
  decision = $Decision
  issue = "https://github.com/Peganyx/test-agent/issues/$Issue"
  updatedAt = (Get-Date).ToUniversalTime().ToString('o')
}

$state | Add-Member -NotePropertyName ([string]$Issue) -NotePropertyValue $entry -Force
$state | ConvertTo-Json -Depth 10 | Set-Content -Path $path -Encoding UTF8
