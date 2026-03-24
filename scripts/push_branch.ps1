param([string]$Dir,[string]$Branch)
$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$pair='x-access-token:' + $token
$b64=[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pair))
$header='AUTHORIZATION: basic ' + $b64
Set-Location $Dir
git -c http.extraheader="$header" push -u origin $Branch
