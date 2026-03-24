$ErrorActionPreference = 'Stop'

if (-not $env:NOTION_TOKEN) {
  throw 'NOTION_TOKEN env var missing'
}

$Headers = @{
  Authorization   = 'Bearer ' + $env:NOTION_TOKEN
  'Notion-Version' = '2022-06-28'
  'Content-Type'  = 'application/json'
}

function Invoke-NotionGet([string]$Url) {
  return Invoke-RestMethod -Method Get -Uri $Url -Headers $Headers
}

function Invoke-NotionPost([string]$Url, $BodyObj) {
  $json = $BodyObj | ConvertTo-Json -Depth 20
  return Invoke-RestMethod -Method Post -Uri $Url -Headers $Headers -Body $json
}

function Get-BlockChildrenAll([string]$BlockId) {
  $results = @()
  $cursor = $null
  do {
    $url = "https://api.notion.com/v1/blocks/$BlockId/children?page_size=100"
    if ($cursor) { $url += "&start_cursor=$cursor" }
    $resp = Invoke-NotionGet $url
    if ($resp.results) { $results += $resp.results }
    $cursor = $resp.next_cursor
  } while ($resp.has_more)
  return $results
}

function Get-PlainText($rt) {
  if (-not $rt) { return '' }
  if ($rt -is [System.Array]) {
    return (($rt | ForEach-Object { $_.plain_text }) -join '')
  }
  return ''
}

$pageId = '1934c265832d80e1b249ff9d768f2479'

# Compute tomorrow date (Asia/Bangkok). For cron tick we trust local machine TZ or override.
$tz = [System.TimeZoneInfo]::FindSystemTimeZoneById('SE Asia Standard Time')
$nowLocal = [System.TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $tz)
$tomorrow = $nowLocal.Date.AddDays(1)
$tomorrowStr = $tomorrow.ToString('yyyy-MM-dd')

$blocks = Get-BlockChildrenAll $pageId

# Gather candidate databases from blocks
$candidateDbs = @()
foreach ($b in $blocks) {
  if ($b.type -eq 'child_database') {
    $candidateDbs += [pscustomobject]@{ id = $b.id; title = (Get-PlainText $b.child_database.title); source = 'child_database' }
  }
}

# If none found at top level, walk one level down for child_pages (common pattern)
if ($candidateDbs.Count -eq 0) {
  foreach ($b in $blocks) {
    if ($b.type -eq 'child_page') {
      $sub = Get-BlockChildrenAll $b.id
      foreach ($sb in $sub) {
        if ($sb.type -eq 'child_database') {
          $candidateDbs += [pscustomobject]@{ id = $sb.id; title = (Get-PlainText $sb.child_database.title); source = 'child_database (nested)' }
        }
      }
    }
  }
}

function Get-DatabaseItemsForDate([string]$DbId, [string]$DateStr) {
  $db = Invoke-NotionGet "https://api.notion.com/v1/databases/$DbId"
  $props = $db.properties.PSObject.Properties | ForEach-Object { $_.Name }

  # Find likely date property names
  $datePropCandidates = @('Date','Ngày','Day','When','Time','Thời gian','Datetime','Ngày học')
  $dateProp = $null
  foreach ($name in $props) {
    $ptype = $db.properties.$name.type
    if ($ptype -eq 'date') {
      if ($datePropCandidates -contains $name) { $dateProp = $name; break }
      if (-not $dateProp) { $dateProp = $name }
    }
  }
  if (-not $dateProp) { return @() }

  $body = @{ filter = @{ property = $dateProp; date = @{ equals = $DateStr } } }
  $resp = Invoke-NotionPost "https://api.notion.com/v1/databases/$DbId/query" $body
  return ,@($resp.results)
}

function Format-ClassRow($pageObj) {
  $p = $pageObj.properties
  $propList = $p.PSObject.Properties | ForEach-Object { $_.Name }

  function Get-PropText([string[]]$names) {
    foreach ($n in $names) {
      if ($propList -contains $n) {
        $prop = $p.$n
        switch ($prop.type) {
          'title' { return (Get-PlainText $prop.title) }
          'rich_text' { return (Get-PlainText $prop.rich_text) }
          'select' { return $prop.select.name }
          'multi_select' { return (($prop.multi_select | ForEach-Object { $_.name }) -join ', ') }
          'number' { return [string]$prop.number }
          'url' { return $prop.url }
          'email' { return $prop.email }
          'phone_number' { return $prop.phone_number }
        }
      }
    }
    return ''
  }

  function Get-PropDate([string[]]$names) {
    foreach ($n in $names) {
      if ($propList -contains $n -and $p.$n.type -eq 'date') {
        return $p.$n.date
      }
    }
    return $null
  }

  $title = Get-PropText @('Name','Tên','Môn','Course','Course name','Task','Class','Title')
  if (-not $title) { $title = Get-PropText @($propList) }

  $dateObj = Get-PropDate @('Date','Ngày','Time','Thời gian','When','Datetime','Ngày học')
  if (-not $dateObj) {
    foreach ($n in $propList) { if ($p.$n.type -eq 'date') { $dateObj = $p.$n.date; break } }
  }

  $start = $null
  $end = $null
  if ($dateObj) {
    $start = $dateObj.start
    $end = $dateObj.end
  }

  $room = Get-PropText @('Room','Phong','Location','Dia diem','Classroom')
  $code = Get-PropText @('Code','Ma','Course code','Ma mon')
  $note = Get-PropText @('Notes','Ghi chu','Note','Description')

  # Time formatting
  $timeRange = ''
  if ($start) {
    # parse as DateTimeOffset to local
    try {
      $startDto = [DateTimeOffset]::Parse($start)
      $startLocal = [System.TimeZoneInfo]::ConvertTime($startDto, $tz)
      if ($end) {
        $endDto = [DateTimeOffset]::Parse($end)
        $endLocal = [System.TimeZoneInfo]::ConvertTime($endDto, $tz)
        $timeRange = $startLocal.ToString('HH:mm') + '-' + $endLocal.ToString('HH:mm')
      } else {
        $timeRange = $startLocal.ToString('HH:mm')
      }
    } catch {
      $timeRange = $start + (if($end){"-$end"}else{''})
    }
  }

  $line = ''
  if ($timeRange) { $line += $timeRange + ' — ' }
  if ($code) { $line += $code + ' ' }
  $line += $title
  if ($room) { $line += ' | ' + $room }
  if ($note) { $line += ' | ' + $note }
  return $line.Trim()
}

$allItems = @()
foreach ($dbRow in $candidateDbs) {
  try {
    $items = Get-DatabaseItemsForDate $dbRow.id $tomorrowStr
    if ($items.Count -gt 0) {
      $allItems += $items
    }
  } catch {
    # ignore dbs we cannot query
  }
}

if ($allItems.Count -gt 0) {
  $lines = @()
  $lines += "Lịch học ngày mai ($($tomorrow.ToString('dd/MM/yyyy'))):"
  foreach ($it in $allItems) {
    $lines += '- ' + (Format-ClassRow $it)
  }
  $out = $lines -join "`n"
  Write-Output $out
  exit 0
}

# Fallback: summarize any text blocks mentioning tomorrow
$tomorrowKeywords = @('mai','tomorrow',$tomorrow.ToString('dd/MM'),$tomorrow.ToString('dd-MM'))
$textSnips = @()
foreach ($b in $blocks) {
  $t = $b.type
  if ($t -in @('paragraph','heading_1','heading_2','heading_3','bulleted_list_item','numbered_list_item','to_do','quote','callout')) {
    $rt = $b.$t.rich_text
    if (-not $rt -and $b.$t.text) { $rt = $b.$t.text }
    $plain = Get-PlainText $rt
    if ($plain) {
      foreach ($kw in $tomorrowKeywords) {
        if ($plain.ToLower().Contains($kw.ToLower())) {
          $textSnips += $plain
          break
        }
      }
    }
  }
}

if ($textSnips.Count -gt 0) {
  $out = "Lịch học ngày mai ($($tomorrow.ToString('dd/MM/yyyy'))) (tóm tắt từ ghi chú):`n" + (($textSnips | Select-Object -Unique) -join "`n")
  Write-Output $out
  exit 0
}

Write-Output 'Mai không có môn nào.'
