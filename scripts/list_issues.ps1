$envFile='D:\Multi Agents\option-b\.env'
$token=((Select-String -Path $envFile -Pattern '^GITHUB_TOKEN=').Line -split '=',2)[1].Trim()
$headers=@{ Authorization = ('token ' + $token); 'User-Agent' = 'openclaw-autofix' }
$url='https://api.github.com/repos/Peganyx/test-agent/issues?state=open&labels=auto-fix&sort=updated&direction=desc&per_page=10'
$issues=Invoke-RestMethod -Headers $headers -Uri $url
$out=@()
foreach($i in $issues){
  if(-not $i.pull_request){
    $out += [PSCustomObject]@{ number=$i.number; title=$i.title; updated_at=$i.updated_at; url=$i.html_url }
  }
}
$out | ConvertTo-Json -Depth 4
