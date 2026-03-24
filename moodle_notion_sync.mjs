import { execSync } from 'node:child_process';

function getNotionToken(){
  const env = process.env.NOTION_TOKEN;
  if(env && env.trim()) return env.trim();
  try{
    const out = execSync('reg query HKCU\\Environment /v NOTION_TOKEN', { stdio:['ignore','pipe','ignore'] }).toString('utf8');
    const m = out.match(/NOTION_TOKEN\s+REG_\w+\s+(.+)/i);
    if(m) return m[1].trim();
  } catch {}
  return '';
}

export function parseVietnameseDue(text, defaultYear=2026){
  if(!text || text.trim()==='-' ) return null;
  // Examples:
  // "Thứ Sáu, 3 tháng 4, 4:30 PM"
  // "Thứ Ba, 10 tháng 3, 12:00 PM"
  // "Today, 24 tháng 3, 12:00 PM"
  const t = text.replace(/^Cảnh báo\s*/i,'').trim();
  const m = t.match(/(?:Thứ\s+\S+|Today)\s*,\s*(\d{1,2})\s+tháng\s+(\d{1,2})\s*,\s*(\d{1,2}):(\d{2})\s*(AM|PM)/i);
  if(!m) return null;
  let [_, d, mo, hh, mm, ap] = m;
  let H = parseInt(hh,10);
  const M = parseInt(mm,10);
  ap = ap.toUpperCase();
  if(ap==='PM' && H!==12) H+=12;
  if(ap==='AM' && H===12) H=0;
  const day = parseInt(d,10);
  const month = parseInt(mo,10);
  // Asia/Bangkok is UTC+7. Notion accepts ISO string; include offset.
  const iso = `${defaultYear.toString().padStart(4,'0')}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}T${String(H).padStart(2,'0')}:${String(M).padStart(2,'0')}:00+07:00`;
  return iso;
}

export async function notionRequest(token, path, method='GET', body){
  const url = `https://api.notion.com/v1${path}`;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
  };
  const res = await fetch(url, { method, headers, body: body? JSON.stringify(body): undefined });
  const text = await res.text();
  let json;
  try{ json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
  if(!res.ok){
    const msg = `Notion API ${method} ${path} failed: ${res.status} ${res.statusText} :: ${text.slice(0,500)}`;
    const err = new Error(msg);
    err.status = res.status;
    err.payload = json;
    throw err;
  }
  return json;
}

export async function upsertTask({token, databaseId, title, description, deadlineIso, statusName, priorityName='Medium', categoryName='Class'}){
  // Query existing by title.
  const query = await notionRequest(token, `/databases/${databaseId}/query`, 'POST', {
    filter: {
      property: 'Task',
      title: { equals: title }
    },
    page_size: 1
  });
  const props = {
    'Task': { title: [{ text: { content: title } }] },
    'Description': { rich_text: [{ text: { content: description } }] },
    'Deadline': deadlineIso ? { date: { start: deadlineIso } } : { date: null },
    'Status': { status: { name: statusName } },
    'Priority': { select: { name: priorityName } },
    ' Category': { select: { name: categoryName } },
  };

  if(query.results?.length){
    const pageId = query.results[0].id;
    const updated = await notionRequest(token, `/pages/${pageId}`, 'PATCH', { properties: props });
    return { action: 'updated', pageId: updated.id };
  } else {
    const created = await notionRequest(token, `/pages`, 'POST', {
      parent: { database_id: databaseId },
      properties: props
    });
    return { action: 'created', pageId: created.id };
  }
}

export async function queryDigest({token, databaseId}){
  // Pull non-done tasks with deadlines (and category)
  const all = [];
  let cursor = undefined;
  while(true){
    const q = await notionRequest(token, `/databases/${databaseId}/query`, 'POST', {
      start_cursor: cursor,
      page_size: 100,
      filter: {
        and: [
          { property: 'Status', status: { does_not_equal: 'Done' } },
          { property: 'Deadline', date: { is_not_empty: true } }
        ]
      },
      sorts: [{ property: 'Deadline', direction: 'ascending' }]
    });
    all.push(...q.results);
    if(!q.has_more) break;
    cursor = q.next_cursor;
  }
  return all;
}

async function main(){
  const token = getNotionToken();
  const databaseId = '31e4c265832d8011bc64e832d0cff957';
  if(!token){
    console.log('ERROR: NOTION_TOKEN missing (env + HKCU\\Environment).');
    process.exit(2);
  }

  const moodleItems = JSON.parse(process.argv[2]||'[]');
  const results = [];

  for(const it of moodleItems){
    const submission = (it.submissionStatus||'').toLowerCase();
    const done = submission.includes('đã nộp') || submission.includes('submitted') || submission.includes('done');
    const statusName = done ? 'Done' : 'Not started';

    const deadlineIso = it.dueIso || null;
    const description = [
      `Course: ${it.courseName}`,
      `Moodle URL: ${it.url}`,
      `Due (original): ${it.dueText}`,
      `Submission status (original): ${it.submissionStatus}`,
    ].join('\n');

    const r = await upsertTask({
      token,
      databaseId,
      title: it.title,
      description,
      deadlineIso,
      statusName,
      priorityName: 'Medium',
      categoryName: 'Class'
    });
    results.push({ ...it, ...r });
  }

  console.log(JSON.stringify({ ok:true, upserts: results }, null, 2));
}

if(import.meta.url === `file://${process.argv[1].replace(/\\/g,'/')}`){
  main().catch(e=>{
    console.error('ERROR:', e.message);
    process.exit(1);
  });
}
