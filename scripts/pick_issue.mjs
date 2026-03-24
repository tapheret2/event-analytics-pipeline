import fs from 'node:fs';
import { ghRequest } from './github_api.mjs';

const repoOwner='Peganyx';
const repoName='test-agent';

const statePath='C:/Users/ADMIN/.openclaw/workspace/autofix_state.json';
const stateRaw=fs.readFileSync(statePath,'utf8').replace(/^\uFEFF/, '');
const state=JSON.parse(stateRaw);

const issues = await ghRequest('GET', `/repos/${repoOwner}/${repoName}/issues?state=open&labels=auto-fix&per_page=20&sort=created&direction=desc`);

let pick=null;
for(const i of issues){
  if(i.pull_request) continue;
  const n=String(i.number);
  if(Object.prototype.hasOwnProperty.call(state,n)) continue;
  const comments = await ghRequest('GET', `/repos/${repoOwner}/${repoName}/issues/${n}/comments?per_page=100`);
  const started = comments.some(c=>typeof c.body==='string' && c.body.includes('🤖 Auto-fix: started'));
  if(!started){ pick={number:i.number, title:i.title, url:i.html_url}; break; }
}

if(pick) process.stdout.write(JSON.stringify(pick));
