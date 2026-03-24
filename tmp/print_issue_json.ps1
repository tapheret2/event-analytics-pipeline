param([string]$Path)
$j = Get-Content -Path $Path -Raw -Encoding Unicode | ConvertFrom-Json
$j.title
'---'
$j.body
