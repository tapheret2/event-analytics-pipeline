param([string]$Dir,[string]$Branch)
$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$pair='x-access-token:' + $token
$bytes=[System.Text.Encoding]::UTF8.GetBytes($pair)
$b64=[Convert]::ToBase64String($bytes)
$header='AUTHORIZATION: basic ' + $b64
if(Test-Path $Dir){ Remove-Item -Recurse -Force $Dir }
New-Item -ItemType Directory -Path $Dir | Out-Null
git -c http.extraheader="$header" clone --quiet https://github.com/Peganyx/test-agent.git $Dir
Set-Location $Dir
git checkout --quiet $Branch
