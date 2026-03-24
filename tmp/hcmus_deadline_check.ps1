$ErrorActionPreference='Stop'

function Get-NotionToken {
  $t=[Environment]::GetEnvironmentVariable('NOTION_TOKEN','User')
  if([string]::IsNullOrEmpty($t)){ $t=[Environment]::GetEnvironmentVariable('NOTION_TOKEN','Process') }
  return $t
}

$token = Get-NotionToken
if([string]::IsNullOrEmpty($token)){
  throw 'NOTION_TOKEN missing'
}

$headers=@{
  'Authorization' = "Bearer $token"
  'Notion-Version' = '2022-06-28'
  'Content-Type'='application/json'
}

$dbId='31e4c265832d8011bc64e832d0cff957'

function Invoke-Notion($method,$url,$bodyObj){
  if($null -ne $bodyObj){
    $json = ($bodyObj | ConvertTo-Json -Depth 20)
    return Invoke-RestMethod -Method $method -Uri $url -Headers $headers -Body $json
  } else {
    return Invoke-RestMethod -Method $method -Uri $url -Headers $headers
  }
}

function Find-PageByTitle($title){
  $url="https://api.notion.com/v1/databases/$dbId/query"
  $body=@{
    filter=@{
      property='Task'
      title=@{ equals=$title }
    }
    page_size=5
  }
  $res=Invoke-Notion 'Post' $url $body
  if($res.results.Count -gt 0){ return $res.results[0] }
  return $null
}

function Upsert-Task($title,$desc,$deadlineIso,$statusName){
  $existing = Find-PageByTitle $title

  $props=@{
    'Task' = @{ title = @(@{ type='text'; text=@{ content=$title } }) }
    'Description' = @{ rich_text = @(@{ type='text'; text=@{ content=$desc } }) }
    'Priority' = @{ select = @{ name = 'Medium' } }
    ' Category' = @{ select = @{ name = 'Class' } }
    'Status' = @{ status = @{ name = $statusName } }
    'Deadline' = @{ date = $null }
  }
  if(-not [string]::IsNullOrEmpty($deadlineIso)){
    $props['Deadline'] = @{ date = @{ start = $deadlineIso } }
  }

  if($null -ne $existing){
    $pageId=$existing.id
    $url="https://api.notion.com/v1/pages/$pageId"
    $body=@{ properties=$props }
    Invoke-Notion 'Patch' $url $body | Out-Null
    return @{ action='updated'; id=$pageId }
  } else {
    $url='https://api.notion.com/v1/pages'
    $body=@{
      parent=@{ database_id=$dbId }
      properties=$props
    }
    $res=Invoke-Notion 'Post' $url $body
    return @{ action='created'; id=$res.id }
  }
}

# Items collected from Moodle (browser step)
$items=@(
  @{ title='MTH10109 - Quiz 1'; deadline='2026-04-03T16:30:00+07:00'; status='Not started'; desc=@'
Course: Thuc hanh thong ke - 24KDL1 - MTH10109
Moodle: https://courses.hcmus.edu.vn/mod/quiz/view.php?id=53963
Original due date text: Dong: Thu Sau, 3 thang 4 2026, 4:30 PM
Original submission status: Button shows "Lam bai kiem tra" (not attempted).
Original name: Tinh toan co ban trong R
'@.Trim() },
  @{ title='MTH10109 - Quiz 2'; deadline='2026-04-03T16:30:00+07:00'; status='Not started'; desc=@'
Course: Thuc hanh thong ke - 24KDL1 - MTH10109
Moodle: https://courses.hcmus.edu.vn/mod/quiz/view.php?id=53967
Original due date text: Dong: Thu Sau, 3 thang 4 2026, 4:30 PM
Original submission status: Button shows "Lam bai kiem tra" (not attempted).
Original name: Tinh toan cac bieu thuc khoa hoc
'@.Trim() },
  @{ title='MTH10131 - Homework 1'; deadline='2026-03-10T12:00:00+07:00'; status='Done'; desc=@'
Course: Ly thuyet thong ke - 24KDL - MTH10131
Moodle: https://courses.hcmus.edu.vn/mod/assign/view.php?id=51798
Original due date text: Thu Ba, 10 thang 3, 12:00 PM
Original submission status: Da nop de cham diem
Original name: BTVN#1
'@.Trim() },
  @{ title='MTH10131 - Homework 2'; deadline='2026-03-17T12:00:00+07:00'; status='Done'; desc=@'
Course: Ly thuyet thong ke - 24KDL - MTH10131
Moodle: https://courses.hcmus.edu.vn/mod/assign/view.php?id=53048
Original due date text: Thu Ba, 17 thang 3, 12:00 PM
Original submission status: Da nop de cham diem
Original name: BTVN#2
'@.Trim() },
  @{ title='MTH10131 - Homework 3'; deadline='2026-03-24T12:00:00+07:00'; status='Not started'; desc=@'
Course: Ly thuyet thong ke - 24KDL - MTH10131
Moodle: https://courses.hcmus.edu.vn/mod/assign/view.php?id=53559
Original due date text: Tomorrow, 24 thang 3, 12:00 PM
Original submission status: Khong co bai nop
Original name: BTVN#3
'@.Trim() }
)

$upserts=@()
foreach($it in $items){
  $r=Upsert-Task $it.title $it.desc $it.deadline $it.status
  $upserts += @{ title=$it.title; action=$r.action; pageId=$r.id }
}

# Digest query
$now=[DateTimeOffset]::Parse('2026-03-23T18:00:00+07:00')
$in7=$now.AddDays(7)

function Query-NotionTasks($filter){
  $url="https://api.notion.com/v1/databases/$dbId/query"
  $body=@{ filter=$filter; page_size=100 }
  return (Invoke-Notion 'Post' $url $body).results
}

$statusNotDone=@{ property='Status'; status=@{ does_not_equal='Done' } }

$overdueFilter=@{ and=@(
  $statusNotDone,
  @{ property='Deadline'; date=@{ before=$now.ToString('o') } }
) }

$dueSoonFilter=@{ and=@(
  $statusNotDone,
  @{ property='Deadline'; date=@{ on_or_after=$now.ToString('o') } },
  @{ property='Deadline'; date=@{ on_or_before=$in7.ToString('o') } }
) }

$overdue=Query-NotionTasks $overdueFilter
$dueSoon=Query-NotionTasks $dueSoonFilter

function Get-PropText($page,$propName){
  $p=$page.properties.$propName
  if($null -eq $p){ return '' }
  switch($p.type){
    'title' { return ($p.title | ForEach-Object {$_.plain_text}) -join '' }
    'rich_text' { return ($p.rich_text | ForEach-Object {$_.plain_text}) -join '' }
    default { return '' }
  }
}

function Get-SelectName($page,$propName){
  $p=$page.properties.$propName
  if($null -eq $p){ return '' }
  if($p.type -eq 'select'){ return $p.select.name }
  if($p.type -eq 'status'){ return $p.status.name }
  return ''
}

function Get-DateStart($page,$propName){
  $p=$page.properties.$propName
  if($null -eq $p){ return $null }
  if($p.type -eq 'date' -and $null -ne $p.date){ return $p.date.start }
  return $null
}

function Group-ByCategory($pages){
  $groups=@{}
  foreach($pg in $pages){
    $cat=Get-SelectName $pg ' Category'
    if([string]::IsNullOrEmpty($cat)){ $cat='(No category)' }
    if(-not $groups.ContainsKey($cat)){ $groups[$cat]=@() }
    $groups[$cat] += $pg
  }
  return $groups
}

$overdueGroups=Group-ByCategory $overdue
$dueSoonGroups=Group-ByCategory $dueSoon

$lines=@()
$lines += ('Notion digest (Moodle deadlines) - {0}' -f $now.ToString('yyyy-MM-dd HH:mm'))
$lines += ''

if(($overdue.Count -eq 0) -and ($dueSoon.Count -eq 0)){
  $lines += 'Khong co deadline o 2 mon nay. Notion: khong co viec sap toi.'
} else {
  if($overdue.Count -gt 0){
    $lines += 'OVERDUE (Status != Done)'
    foreach($cat in ($overdueGroups.Keys | Sort-Object)){
      $lines += ('- {0}' -f $cat)
      foreach($pg in $overdueGroups[$cat]){
        $t=Get-PropText $pg 'Task'
        $d=Get-DateStart $pg 'Deadline'
        $lines += ('  * {0} - {1}' -f $t, $d)
      }
    }
    $lines += ''
  }

  if($dueSoon.Count -gt 0){
    $lines += 'DUE IN NEXT 7 DAYS (Status != Done)'
    foreach($cat in ($dueSoonGroups.Keys | Sort-Object)){
      $lines += ('- {0}' -f $cat)
      foreach($pg in $dueSoonGroups[$cat]){
        $t=Get-PropText $pg 'Task'
        $d=Get-DateStart $pg 'Deadline'
        $lines += ('  * {0} - {1}' -f $t, $d)
      }
    }
  }
}

$lines += ''
$lines += 'Upsert summary:'
foreach($u in $upserts){
  $lines += ('- {0}: {1}' -f $u.action, $u.title)
}

$lines -join "`n"
