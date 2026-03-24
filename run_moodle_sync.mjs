import { execSync } from 'node:child_process';
import { parseVietnameseDue, upsertTask, queryDigest, notionRequest } from './moodle_notion_sync.mjs';

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

const databaseId = '31e4c265832d8011bc64e832d0cff957';
const token = getNotionToken();
if(!token){
  console.log(JSON.stringify({ ok:false, error:'NOTION_TOKEN missing (env + HKCU\\Environment).'}));
  process.exit(2);
}

const items = [
  {
    courseCode:'MTH10109',
    courseName:'Thực hành thống kê - 24KDL1 - MTH10109',
    type:'Quiz',
    num:1,
    origName:'Tính toán cơ bản trong R',
    url:'https://courses.hcmus.edu.vn/mod/quiz/view.php?id=53963',
    dueText:'Thứ Sáu, 3 tháng 4, 4:30 PM',
    submissionStatus:'-'
  },
  {
    courseCode:'MTH10109',
    courseName:'Thực hành thống kê - 24KDL1 - MTH10109',
    type:'Quiz',
    num:2,
    origName:'Tính toán các biểu thức khoa học',
    url:'https://courses.hcmus.edu.vn/mod/quiz/view.php?id=53967',
    dueText:'Thứ Sáu, 3 tháng 4, 4:30 PM',
    submissionStatus:'-'
  },
  {
    courseCode:'MTH10131',
    courseName:'Lý thuyết thống kê - 24KDL - MTH10131',
    type:'Homework',
    num:1,
    origName:'BTVN#1',
    url:'https://courses.hcmus.edu.vn/mod/assign/view.php?id=51798',
    dueText:'Thứ Ba, 10 tháng 3, 12:00 PM',
    submissionStatus:'Đã nộp để chấm điểm'
  },
  {
    courseCode:'MTH10131',
    courseName:'Lý thuyết thống kê - 24KDL - MTH10131',
    type:'Homework',
    num:2,
    origName:'BTVN#2',
    url:'https://courses.hcmus.edu.vn/mod/assign/view.php?id=53048',
    dueText:'Thứ Ba, 17 tháng 3, 12:00 PM',
    submissionStatus:'Đã nộp để chấm điểm'
  },
  {
    courseCode:'MTH10131',
    courseName:'Lý thuyết thống kê - 24KDL - MTH10131',
    type:'Homework',
    num:3,
    origName:'BTVN#3',
    url:'https://courses.hcmus.edu.vn/mod/assign/view.php?id=53559',
    dueText:'Today, 24 tháng 3, 12:00 PM',
    submissionStatus:'Đã nộp để chấm điểm'
  },
];

const upserts = [];
for(const it of items){
  it.title = `${it.courseCode} - ${it.type} ${it.num}`;
  it.dueIso = parseVietnameseDue(it.dueText, 2026);
}

for(const it of items){
  const submission = (it.submissionStatus||'').toLowerCase();
  const done = submission.includes('đã nộp') || submission.includes('submitted') || submission.includes('done');
  const statusName = done ? 'Done' : 'Not started';

  const description = [
    `Course: ${it.courseName}`,
    `Original name: ${it.origName}`,
    `Moodle URL: ${it.url}`,
    `Due (original): ${it.dueText}`,
    `Submission status (original): ${it.submissionStatus}`,
  ].join('\n');

  const r = await upsertTask({
    token,
    databaseId,
    title: it.title,
    description,
    deadlineIso: it.dueIso,
    statusName,
    priorityName: 'Medium',
    categoryName: 'Class'
  });
  upserts.push({ title: it.title, action: r.action, pageId: r.pageId });
}

const digestPages = await queryDigest({ token, databaseId });

function getProp(page, name){
  return page.properties?.[name];
}
function getTitle(page){
  const t = getProp(page,'Task')?.title?.map(x=>x.plain_text).join('') || '';
  return t;
}
function getCategory(page){
  return getProp(page,' Category')?.select?.name || 'Uncategorized';
}
function getDeadline(page){
  return getProp(page,'Deadline')?.date?.start || null;
}

console.log(JSON.stringify({ ok:true, upserts, digestCount:digestPages.length, digestPages: digestPages.map(p=>({ id:p.id, title:getTitle(p), category:getCategory(p), deadline:getDeadline(p) })) }, null, 2));
