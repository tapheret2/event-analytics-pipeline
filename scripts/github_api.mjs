import fs from 'node:fs';

export function loadToken(){
  const envText = fs.readFileSync('D:/Multi Agents/option-b/.env','utf8');
  const tokenLine = envText.split(/\r?\n/).find(l=>l.startsWith('GITHUB_TOKEN='));
  if(!tokenLine) throw new Error('GITHUB_TOKEN not found');
  return tokenLine.split('=').slice(1).join('=').trim();
}

export async function ghRequest(method, path, body){
  const token = loadToken();
  const url = `https://api.github.com${path}`;
  const res = await fetch(url, {
    method,
    headers: {
      'Authorization': `token ${token}`,
      'Accept': 'application/vnd.github+json',
      'User-Agent': 'openclaw-autofix'
    },
    body: body ? JSON.stringify(body) : undefined
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : null; } catch { json = text; }
  if(!res.ok){
    const msg = typeof json === 'object' ? JSON.stringify(json) : String(json);
    throw new Error(`GitHub API ${method} ${path} failed: ${res.status} ${res.statusText} :: ${msg}`);
  }
  return json;
}
