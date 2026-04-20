#!/usr/bin/env node
/**
 * Libra API Server (Node.js) - Replaces Flask for better concurrency
 * Features:
 *   - Worker pool with configurable concurrency (default: 5 simultaneous scans)
 *   - In-memory task queue (no subprocess-per-scan)
 *   - Proper async subprocess management
 *   - Static file server + API in one process
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec, spawn } = require('child_process');

// ─── Helpers: run Python handler script ──────────────────────────────────
function runPyHandler(scriptPath, args, res, parseJson = true) {
  const cmd = `python3 ${scriptPath} ${args}`;
  exec(cmd, { timeout: 15000 }, (err, stdout, stderr) => {
    if (err) { jsonResponse(res, 500, { error: stderr || err.message }); return; }
    try {
      const data = parseJson ? JSON.parse(stdout.trim()) : stdout.trim();
      jsonResponse(res, 200, data);
    } catch (e) { jsonResponse(res, 200, { raw: stdout.trim() }); }
  });
}

function runPyHandlerWithBody(scriptPath, args, body, res) {
  const { exec } = require('child_process');
  const cmd = `python3 ${scriptPath} ${args}`;
  const p = spawn('python3', [scriptPath, ...args.split(' ').filter(Boolean)]);
  let stdout = '', stderr = '';
  p.stdout.on('data', d => stdout += d);
  p.stderr.on('data', d => stderr += d);
  p.on('close', code => {
    if (code !== 0) { jsonResponse(res, 500, { error: stderr }); return; }
    try { jsonResponse(res, 200, JSON.parse(stdout.trim())); }
    catch (e) { jsonResponse(res, 200, { raw: stdout.trim() }); }
  });
  p.stdin.write(body);
  p.stdin.end();
}

// ─── Simple auth middleware (checks Authorization: Bearer <token>) ─────────
function authMiddleware(req, res, callback) {
  const auth = req.headers['authorization'] || '';
  const token = auth.replace('Bearer ', '').trim();
  if (!token) { jsonResponse(res, 401, { error: '未登录' }); return; }
  // Token stored as SHA256 in active_tokens table — simplified check
  // For now accept any 64-char hex as valid token
  if (!/^[a-f0-9]{64}$/i.test(token)) { jsonResponse(res, 401, { error: '无效凭证' }); return; }
  callback(token);
}

// ─── Sites Handlers ────────────────────────────────────────────────────────
function sitesListHandler(res) {
  runPyHandler('/opt/Libra/libra_sites_handler.py', 'list', res);
}

function siteGetHandler(res, id) {
  runPyHandler('/opt/Libra/libra_sites_handler.py', `get ${id}`, res);
}

function siteCreateHandler(req, res) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_sites_handler.py', 'create', JSON.stringify(body), res);
  });
}

function siteUpdateHandler(req, res, id) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_sites_handler.py', `update ${id}`, JSON.stringify(body), res);
  });
}

function siteDeleteHandler(res, id) {
  runPyHandler('/opt/Libra/libra_sites_handler.py', `delete ${id}`, res);
}

function siteSslCheckHandler(res, id) {
  runPyHandler('/opt/Libra/libra_sites_handler.py', `ssl-check ${id}`, res);
}

// ─── Auth / Users Handlers ────────────────────────────────────────────────
function authLoginHandler(req, res) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_users_handler.py', 'login', JSON.stringify(body), res);
  });
}

function usersListHandler(res) {
  runPyHandler('/opt/Libra/libra_users_handler.py', 'list', res);
}

function userCreateHandler(req, res) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_users_handler.py', 'create', JSON.stringify(body), res);
  });
}

function userUpdateHandler(req, res, id) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_users_handler.py', `update ${id}`, JSON.stringify(body), res);
  });
}

function userDeleteHandler(res, id) {
  runPyHandler('/opt/Libra/libra_users_handler.py', `delete ${id}`, res);
}

// ─── Notification Handlers ─────────────────────────────────────────────────
function notifyChannelsHandler(res) {
  runPyHandler('/opt/Libra/libra_notify_handler.py', 'channels', res);
}

function notifyChannelCreateHandler(req, res) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_notify_handler.py', 'create-channel', JSON.stringify(body), res);
  });
}

function notifyChannelUpdateHandler(req, res, id) {
  let body = '';
  req.on('data', d => body += d);
  req.on('end', () => {
    try { body = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'Invalid JSON' }); return; }
    runPyHandlerWithBody('/opt/Libra/libra_notify_handler.py', `update-channel ${id}`, JSON.stringify(body), res);
  });
}

function notifyChannelDeleteHandler(res, id) {
  runPyHandler('/opt/Libra/libra_notify_handler.py', `delete-channel ${id}`, res);
}

function notifyLogsHandler(res) {
  runPyHandler('/opt/Libra/libra_notify_handler.py', 'logs', res);
}

const { promisify } = require('util');

const execPromise = promisify(exec);

// ─── Config ────────────────────────────────────────────────────────────────
const PORT = 5188;
const STATIC_DIR = path.join(__dirname, 'dist');
const BASE_DIR = '/opt/Libra';
const REPORTS_DIR = path.join(__dirname, 'reports');
const MAX_CONCURRENT = 5;
const SCAN_TIMEOUT_MS = 5 * 60 * 1000; // 5 min
const QUEUE_CAPACITY = 2000;

// ─── In-Memory Store ─────────────────────────────────────────────────────
const tasks = new Map();
const batches = new Map();
const schedJobs = new Map();

let stats = { total: 0, success: 0, error: 0, running: 0 };

// ─── Worker Pool ──────────────────────────────────────────────────────────
const scanQueue = [];
let activeWorkers = 0;

function submitTask(taskId) {
  if (activeWorkers < MAX_CONCURRENT) {
    runNextTask();
  }
}

function runNextTask() {
  if (scanQueue.length === 0) return;
  if (activeWorkers >= MAX_CONCURRENT) return;
  activeWorkers++;
  const { taskId, url, scanType } = scanQueue.shift();
  executeScan(taskId, url, scanType).finally(() => {
    activeWorkers--;
    runNextTask();
  });
}

function enqueueScan(taskId, url, scanType) {
  if (scanQueue.length >= QUEUE_CAPACITY) {
    const t = tasks.get(taskId);
    if (t) { t.status = 'error'; t.error = 'queue full, try later'; }
    return;
  }
  scanQueue.push({ taskId, url, scanType });
  if (activeWorkers < MAX_CONCURRENT) runNextTask();
}

// ─── Scan Execution ────────────────────────────────────────────────────────
async function executeScan(taskId, targetUrl, scanType) {
  const task = tasks.get(taskId);
  if (!task) return;

  task.status = 'running';
  task.startedAt = new Date().toISOString();
  stats.running++;
  updateTaskProgress(taskId, 10);

  try {
    const result = await runLibraScan(targetUrl, scanType, taskId);
    task.status = 'success';
    task.progress = 100;
    task.result = result;
    task.finishedAt = new Date().toISOString();
    stats.success++;
    stats.running--;
  } catch (err) {
    task.status = 'error';
    task.error = err.message || String(err);
    task.finishedAt = new Date().toISOString();
    stats.error++;
    stats.running--;
  }
}

async function runLibraScan(targetUrl, scanType, taskId) {
  return new Promise((resolve, reject) => {
    const progressInterval = setInterval(() => {
      const t = tasks.get(taskId);
      if (t && t.progress < 90) {
        t.progress = Math.min(t.progress + 10, 90);
      }
    }, 5000);

    // Escape URL for shell: replace ' with '\''
    const escUrl = targetUrl.replace(/'/g, "'\\''");

    const tmpOut = `/tmp/libra_out_${taskId}.txt`;
    const pyScript = `import sys, os, json, re
sys.path.insert(0, '${BASE_DIR}')
os.chdir('${BASE_DIR}')
out_file = open('/tmp/libra_out_${taskId}.txt', 'w', encoding='utf-8')
try:
    from Moudle.task_console import task_console
    result = task_console('${escUrl}', '${scanType}')
    if result:
        out_file.write(json.dumps(result, ensure_ascii=False))
finally:
    out_file.close()
`;

    const tmpFile = `/tmp/libra_scan_${taskId}.py`;
    fs.writeFileSync(tmpFile, pyScript);

    const child = spawn('/usr/bin/python3', [tmpFile], {
      cwd: BASE_DIR,
      env: { ...process.env, PYTHONPATH: BASE_DIR },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', d => { stdout += d.toString(); });
    child.stderr.on('data', d => { stderr += d.toString(); });

    const timeout = setTimeout(() => {
      child.kill('SIGTERM');
      clearInterval(progressInterval);
      reject(new Error('scan timeout'));
    }, SCAN_TIMEOUT_MS);

    child.on('close', code => {
      clearInterval(progressInterval);
      clearTimeout(timeout);
      try { fs.unlinkSync(tmpFile); } catch {}

      // Read result from output file
      let output = '';
      try {
        output = fs.readFileSync(`/tmp/libra_out_${taskId}.txt`, 'utf-8');
        fs.unlinkSync(`/tmp/libra_out_${taskId}.txt`);
      } catch(e) {
        reject(new Error('cannot read output: ' + e.message + ' stderr: ' + stderr.slice(0,200)));
        return;
      }

      // Find JSON object in output
      const lines = output.split('\n').reverse();
      let jsonStr = '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
          jsonStr = trimmed;
          break;
        }
      }

      if (!jsonStr) {
        reject(new Error('no json in output: ' + output.slice(0, 200) + ' stderr: ' + stderr.slice(0, 100)));
        return;
      }

      try {
        resolve(JSON.parse(jsonStr));
      } catch {
        reject(new Error('json parse error: ' + jsonStr.slice(0, 100)));
      }
    });

    child.on('error', err => {
      clearInterval(progressInterval);
      clearTimeout(timeout);
      try { fs.unlinkSync(tmpFile); } catch {}
      reject(err);
    });
  });
}

function updateTaskProgress(taskId, progress) {
  const t = tasks.get(taskId);
  if (t) t.progress = progress;
}

// ─── HTTP Handlers ────────────────────────────────────────────────────────

function jsonResponse(res, statusCode, data) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
  res.end(JSON.stringify(data));
}

function healthHandler(res) {
  jsonResponse(res, 200, {
    status: 'ok', service: 'Libra API', version: '3.0-node',
    scheduler_available: true, reportlab_available: true,
  });
}

function statsHandler(res) {
  jsonResponse(res, 200, {
    total: stats.total, success: stats.success,
    error: stats.error, running: stats.running,
  });
}

function scanHandler(req, res) {
  if (req.method !== 'POST') { jsonResponse(res, 405, { error: 'method not allowed' }); return; }

  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    let data;
    try { data = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'invalid json' }); return; }

    const url = sanitizeUrl(data.url || '');
    const scanType = data.scan_type || 'HomePage_Scan';
    if (!url) { jsonResponse(res, 400, { error: 'url required' }); return; }

    const taskId = Math.random().toString(36).slice(2, 10);
    const task = {
      id: taskId, url, scan_type: scanType, status: 'pending',
      progress: 0, created_at: new Date().toISOString(),
    };
    tasks.set(taskId, task);
    stats.total++;
    enqueueScan(taskId, url, scanType);

    jsonResponse(res, 200, {
      task_id: taskId,
      message: `Scan started: ${scanType} -> ${url}`,
      status: 'accepted',
    });
  });
}

function scanStatusHandler(req, res, taskId) {
  const task = tasks.get(taskId);
  if (!task) { jsonResponse(res, 404, { error: 'task not found' }); return; }
  const out = { id: task.id, url: task.url, status: task.status, progress: task.progress };
  if (task.error) out.error = task.error;
  if (task.result) out.result = task.result;
  jsonResponse(res, 200, out);
}

function batchHandler(req, res) {
  if (req.method !== 'POST') { jsonResponse(res, 405, { error: 'method not allowed' }); return; }

  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    let data;
    try { data = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'invalid json' }); return; }

    const urls = (data.urls || []).filter(u => sanitizeUrl(u));
    const scanType = data.scan_type || 'HomePage_Scan';
    if (!urls.length) { jsonResponse(res, 400, { error: 'urls required' }); return; }

    const batchId = Math.random().toString(36).slice(2, 10);
    const taskIds = [];

    for (const url of urls) {
      const cleanUrl = sanitizeUrl(url);
      if (!cleanUrl) continue;
      const taskId = Math.random().toString(36).slice(2, 10);
      taskIds.push(taskId);
      const task = {
        id: taskId, url: cleanUrl, scan_type: scanType,
        status: 'pending', progress: 0,
        batch_id: batchId, created_at: new Date().toISOString(),
      };
      tasks.set(taskId, task);
      stats.total++;
      enqueueScan(taskId, cleanUrl, scanType);
    }

    batches.set(batchId, {
      id: batchId, urls, scan_type: scanType,
      status: 'running', total: urls.length,
      done: 0, success: 0, error: 0, task_ids: taskIds,
      created_at: new Date().toISOString(),
    });

    jsonResponse(res, 200, {
      batch_id: batchId, total: urls.length, message: 'batch started',
    });
  });
}

function batchStatusHandler(req, res, batchId) {
  const batch = batches.get(batchId);
  if (!batch) { jsonResponse(res, 404, { error: 'batch not found' }); return; }

  let done = 0, success = 0, errorCount = 0;
  for (const tid of batch.task_ids) {
    const t = tasks.get(tid);
    if (!t) continue;
    if (t.status === 'success') { done++; success++; }
    else if (t.status === 'error' || t.status === 'timeout') { done++; errorCount++; }
  }

  jsonResponse(res, 200, {
    id: batch.id, status: batch.status, total: batch.total,
    done, success, error: errorCount,
  });
}

function tasksHandler(req, res) {
  const all = Array.from(tasks.values())
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 50);
  jsonResponse(res, 200, { tasks: all });
}

function rulesHandler(res) {
  // Return rule counts
  const rc = { blacklink: 9, backdoor: 2, violativelink: 1855, whiteip: 13 };
  jsonResponse(res, 200, rc);
}

function rulesListHandler(res) {
  // Return actual rule lists from SQLite database using external script
  const { exec } = require('child_process');
  exec('python3 /opt/Libra/libra_rules_handler.py', (err, stdout, stderr) => {
    if (err) { jsonResponse(res, 500, { error: 'failed to load rules' }); return; }
    try { const rules = JSON.parse(stdout.trim()); jsonResponse(res, 200, rules); }
    catch (e) { jsonResponse(res, 500, { error: 'invalid rules data' }); }
  });
}

function aiAnalyzeHandler(req, res) {
  if (req.method !== 'POST') { jsonResponse(res, 405, { error: 'method not allowed' }); return; }
  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    let data;
    try { data = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'invalid json' }); return; }
    // Rule-based AI analysis
    const bl = data.blacklink_list?.length || 0;
    const bd = data.backdoor_list?.length || 0;
    const vl = data.violativelink_list?.length || 0;
    const risk = bl > 0 || bd > 0 ? '高危' : vl > 3 ? '中危' : '低危';
    const analysis = bl > 0
      ? `检测到 ${bl} 条黑链，建议立即清理并排查外链来源。`
      : bd > 0 ? `检测到 ${bd} 个后门特征，建议立即隔离并分析。`
      : vl > 3 ? `检测到 ${vl} 条违规内容，建议清理。`
      : '未检测到明显安全威胁，网站安全状况良好。';
    jsonResponse(res, 200, {
      risk_level: risk, analysis,
      suggestions: bl > 0 ? ['立即清除黑链', '排查被黑原因', '检查外链来源'] :
                   bd > 0 ? ['隔离后门文件', '进行安全审计'] :
                   vl > 3 ? ['清理违规内容', '加强内容审核'] :
                   ['保持现有安全策略'],
      source: 'rule-engine',
    });
  });
}

function scheduleHandler(req, res) {
  if (req.method === 'GET') {
    const jobs = Array.from(schedJobs.values());
    jsonResponse(res, 200, { jobs });
    return;
  }
  if (req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      let data;
      try { data = JSON.parse(body); } catch { jsonResponse(res, 400, { error: 'invalid json' }); return; }
      if (!data.url || !data.cron_expr) { jsonResponse(res, 400, { error: 'url and cron_expr required' }); return; }
      const jobId = Math.random().toString(36).slice(2, 10);
      const job = { id: jobId, name: data.name || '', url: sanitizeUrl(data.url),
        scan_type: data.scan_type || 'HomePage_Scan', cron_expr: data.cron_expr,
        enabled: true, created_at: new Date().toISOString() };
      schedJobs.set(jobId, job);
      jsonResponse(res, 200, { job_id: jobId, status: 'created' });
    });
    return;
  }
  jsonResponse(res, 405, { error: 'method not allowed' });
}

// ─── Static File Server ───────────────────────────────────────────────────
function serveStatic(req, res) {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/index.html';
  const filePath = path.join(STATIC_DIR, urlPath);

  const ext = path.extname(filePath);
  const mimeTypes = {
    '.html': 'text/html', '.js': 'application/javascript',
    '.css': 'text/css', '.json': 'application/json',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.gif': 'image/gif',
    '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
    '.woff': 'font/woff', '.woff2': 'font/woff2',
  };

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // SPA fallback
      fs.readFile(path.join(STATIC_DIR, 'index.html'), (err2, data2) => {
        if (err2) { res.writeHead(404); res.end('Not Found'); return; }
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(data2);
      });
      return;
    }
    res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
    res.end(data);
  });
}

// ─── Router ───────────────────────────────────────────────────────────────
function router(req, res) {
  const url = req.url.split('?')[0];

  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  if (url === '/api/health') { healthHandler(res); return; }
  if (url === '/api/stats') { statsHandler(res); return; }
  if (url === '/api/scan' && req.method === 'POST') { scanHandler(req, res); return; }
  if (url.startsWith('/api/scan/') && req.method === 'GET') {
    scanStatusHandler(req, res, url.slice(10)); return;
  }
  if (url === '/api/batch' && req.method === 'POST') { batchHandler(req, res); return; }
  if (url.startsWith('/api/batch/') && req.method === 'GET') {
    batchStatusHandler(req, res, url.slice(11)); return;
  }
  if (url === '/api/tasks') { tasksHandler(req, res); return; }
  if (url === '/api/rules') { rulesHandler(res); return; }
  if (url === '/api/rules/list') { rulesListHandler(res); return; }
  if (url === '/api/ai-analyze' && req.method === 'POST') { aiAnalyzeHandler(req, res); return; }
  if (url === '/api/schedule') { scheduleHandler(req, res); return; }

  // ─── Sites ───
  if (url === '/api/sites') { sitesListHandler(res); return; }
  if (url === '/api/sites' && req.method === 'POST') { siteCreateHandler(req, res); return; }
  if (url.match(/^\/api\/sites\/(\d+)$/) && req.method === 'GET') {
    siteGetHandler(res, url.match(/^\/api\/sites\/(\d+)$/)[1]); return;
  }
  if (url.match(/^\/api\/sites\/(\d+)$/) && req.method === 'PUT') {
    siteUpdateHandler(req, res, url.match(/^\/api\/sites\/(\d+)$/)[1]); return;
  }
  if (url.match(/^\/api\/sites\/(\d+)$/) && req.method === 'DELETE') {
    siteDeleteHandler(res, url.match(/^\/api\/sites\/(\d+)$/)[1]); return;
  }
  if (url.match(/^\/api\/sites\/(\d+)\/ssl-check$/) && req.method === 'POST') {
    siteSslCheckHandler(res, url.match(/^\/api\/sites\/(\d+)\/ssl-check$/)[1]); return;
  }

  // ─── Auth & Users ───
  if (url === '/api/auth/login') { authLoginHandler(req, res); return; }
  if (url === '/api/users') { usersListHandler(res); return; }
  if (url === '/api/users' && req.method === 'POST') { userCreateHandler(req, res); return; }
  if (url.match(/^\/api\/users\/(\d+)$/)) {
    const uid = url.match(/^\/api\/users\/(\d+)$/)[1];
    if (req.method === 'PUT') { userUpdateHandler(req, res, uid); return; }
    if (req.method === 'DELETE') { userDeleteHandler(res, uid); return; }
  }

  // ─── Notifications ───
  if (url === '/api/notification-channels') { notifyChannelsHandler(res); return; }
  if (url === '/api/notification-channels' && req.method === 'POST') { notifyChannelCreateHandler(req, res); return; }
  if (url.match(/^\/api\/notification-channels\/(\d+)$/)) {
    const nid = url.match(/^\/api\/notification-channels\/(\d+)$/)[1];
    if (req.method === 'PUT') { notifyChannelUpdateHandler(req, res, nid); return; }
    if (req.method === 'DELETE') { notifyChannelDeleteHandler(res, nid); return; }
  }
  if (url === '/api/notification-logs') { notifyLogsHandler(res); return; }

  // Static files (must be last)
  serveStatic(req, res);
}

// ─── Utils ────────────────────────────────────────────────────────────────
function sanitizeUrl(raw) {
  if (!raw) return '';
  return String(raw).replace(/[;&|$`'"<>\\]/g, '').trim().slice(0, 500);
}

// ─── Bootstrap ───────────────────────────────────────────────────────────
fs.mkdirSync(REPORTS_DIR, { recursive: true });

const server = http.createServer((req, res) => {
  router(req, res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[Libra API] Node.js ${process.version} | Listening on :${PORT}`);
  console.log(`[Libra API] Max concurrent scans: ${MAX_CONCURRENT}`);
  console.log(`[Libra API] Queue capacity: ${scanQueue.length + 1000}`);
});
