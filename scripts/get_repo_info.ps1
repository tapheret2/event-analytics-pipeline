$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$headers=@{ Authorization = ('token ' + $token); 'User-Agent'='openclaw-autofix'; Accept='application/vnd.github+json' }
$url='https://api.github.com/repos/Peganyx/test-agent'
$repo=Invoke-RestMethod -Headers $headers -Uri $url
[PSCustomObject]@{ default_branch=$repo.default_branch; clone_url=$repo.clone_url } | ConvertTo-Json
