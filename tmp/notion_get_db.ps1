$ErrorActionPreference='Stop'
$token=[Environment]::GetEnvironmentVariable('NOTION_TOKEN','User')
if([string]::IsNullOrEmpty($token)){ $token=[Environment]::GetEnvironmentVariable('NOTION_TOKEN','Process') }
if([string]::IsNullOrEmpty($token)){ throw 'NOTION_TOKEN missing' }
$headers=@{
  'Authorization' = "Bearer $token"
  'Notion-Version' = '2022-06-28'
  'Content-Type'='application/json'
}
$dbId='31e4c265832d8011bc64e832d0cff957'
$url="https://api.notion.com/v1/databases/$dbId"
$res=Invoke-RestMethod -Method Get -Uri $url -Headers $headers
$res | ConvertTo-Json -Depth 20
