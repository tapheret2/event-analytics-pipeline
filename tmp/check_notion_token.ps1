$ErrorActionPreference='Stop'
$tok=[Environment]::GetEnvironmentVariable('NOTION_TOKEN','User')
if([string]::IsNullOrEmpty($tok)){
  $tok=[Environment]::GetEnvironmentVariable('NOTION_TOKEN','Process')
}
if([string]::IsNullOrEmpty($tok)){
  Write-Output 'NOTION_TOKEN_MISSING'
}else{
  Write-Output ("NOTION_TOKEN_PRESENT len={0}" -f $tok.Length)
}
