#!/usr/bin/env node
/**
 * Libra All-in-One Server (Node.js)
 * Replaces serve.py (Python) + app_batch.py (Flask)
 *
 * Features:
 *   - Static file serving (Vue SPA) on port 5189
 *   - API proxy to Flask/Node.js backend on 5188
 *   - Starts its own Node.js API subprocess on 5188
 *   - Auto-restarts API subprocess if it crashes
 *
 * Usage: node serve.js
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { networkInterfaces } = require('os');

const PORT = 5189;
const API_PORT = 5188;
const BASE_DIR = '/opt/Libra';
const DIST_DIR = path.join(__dirname, 'dist');
const API_SCRIPT = path.join(__dirname, 'server.js');
const API_LOG = path.join(BASE_DIR, 'node_api.log');

let apiProcess = null;
let apiRunning = false;

// ─── MIME Types ───────────────────────────────────────────────────────────
const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript',
    '.mjs': 'application/javascript',
    '.ts': 'application/javascript',
    '.css': 'text/css',
    '.scss': 'text/css',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
    '.json': 'application/json',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
    '.eot': 'application/vnd.ms-fontobject',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.ogg': 'audio/ogg',
    '.mp3': 'audio/mpeg',
};

// ─── API Subprocess Management ─────────────────────────────────────────────

function startApiServer() {
    if (apiProcess) {
        apiProcess.kill('SIGTERM');
        apiProcess = null;
    }

    console.log(`[serve] Starting API server (Node.js) on :${API_PORT}...`);

    const logStream = fs.createWriteStream(API_LOG, { flags: 'a' });

    apiProcess = spawn('/usr/bin/node', [API_SCRIPT], {
        cwd: __dirname,
        env: {
            ...process.env,
            PYTHONPATH: BASE_DIR,
            NODE_ENV: 'production',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
    });

    apiProcess.stdout.on('data', d => {
        const line = d.toString().trim();
        if (line) console.log(`[api] ${line}`);
        logStream.write(`[api] ${line}\n`);
    });

    apiProcess.stderr.on('data', d => {
        const line = d.toString().trim();
        if (line) console.error(`[api:err] ${line}`);
        logStream.write(`[api:err] ${line}\n`);
    });

    apiProcess.on('exit', code => {
        apiRunning = false;
        console.log(`[serve] API server exited with code ${code}`);
        // Auto-restart after 3 seconds
        setTimeout(() => {
            if (!apiRunning) startApiServer();
        }, 3000);
    });

    apiProcess.on('error', err => {
        console.error(`[serve] API server error: ${err.message}`);
    });

    apiRunning = true;
    console.log(`[serve] API server started, pid=${apiProcess.pid}`);
}

function stopApiServer() {
    if (apiProcess) {
        apiProcess.kill('SIGTERM');
        apiProcess = null;
        apiRunning = false;
    }
}

// ─── HTTP Proxy ────────────────────────────────────────────────────────────

function proxyRequest(req, res, targetPort, timeout = 30000) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: '127.0.0.1',
            port: targetPort,
            path: req.url,
            method: req.method,
            headers: { ...req.headers },
            timeout,
        };

        // Remove hop-by-hop headers
        delete options.headers['transfer-encoding'];
        delete options.headers['connection'];

        const proxyReq = http.request(options, proxyRes => {
            // Follow redirects by handling location header
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res, { end: true });
            resolve();
        });

        proxyReq.on('error', err => {
            reject(err);
        });

        proxyReq.on('timeout', () => {
            proxyReq.destroy();
            reject(new Error('proxy timeout'));
        });

        req.pipe(proxyReq, { end: true });
    });
}

// ─── Static File Server ────────────────────────────────────────────────────

function serveStatic(req, res) {
    let urlPath = req.url.split('?')[0];
    if (urlPath === '/') urlPath = '/index.html';

    const filePath = path.join(DIST_DIR, urlPath);
    const ext = path.extname(filePath).toLowerCase();
    const mime = MIME[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, data) => {
        if (err) {
            if (err.code === 'ENOENT') {
                // SPA fallback - serve index.html
                fs.readFile(path.join(DIST_DIR, 'index.html'), (err2, data2) => {
                    if (err2) {
                        res.writeHead(404);
                        res.end('Not Found');
                    } else {
                        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
                        res.end(data2);
                    }
                });
            } else {
                res.writeHead(500);
                res.end('Server Error');
            }
            return;
        }

        // Cache control for static assets
        const isStatic = ['.js', '.css', '.svg', '.png', '.jpg', '.woff', '.woff2'].includes(ext);
        const headers = {
            'Content-Type': mime,
            'Content-Length': data.length,
        };
        if (isStatic) {
            headers['Cache-Control'] = 'public, max-age=3600';
        }

        res.writeHead(200, headers);
        res.end(data);
    });
}

// ─── Request Router ────────────────────────────────────────────────────────

const SKIP_PROXY = new Set(['/favicon.ico', '/robots.txt']);

async function handleRequest(req, res) {
    const url = req.url.split('?')[0];

    // CORS preflight
    if (req.method === 'OPTIONS') {
        res.writeHead(204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400',
        });
        res.end();
        return;
    }

    // API proxy to backend on 5188
    if (url.startsWith('/api/') && !SKIP_PROXY.has(url)) {
        try {
            await proxyRequest(req, res, API_PORT);
        } catch (err) {
            console.error(`[serve] Proxy error for ${req.url}: ${err.message}`);
            res.writeHead(502, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'API backend unavailable', message: err.message }));
        }
        return;
    }

    // Static files
    serveStatic(req, res);
}

// ─── Main ─────────────────────────────────────────────────────────────────

// Check if Node.js API is installed
if (!fs.existsSync(API_SCRIPT)) {
    console.error(`[serve] ERROR: server.js not found at ${API_SCRIPT}`);
    console.error(`[serve] Please upload server.js to ${__dirname}`);
    process.exit(1);
}

console.log('========================================');
console.log('  Libra All-in-One Server (Node.js)');
console.log(`  Web UI:  http://0.0.0.0:${PORT}`);
console.log(`  API:     http://0.0.0.0:${API_PORT} (managed)`);
console.log(`  Static:  ${DIST_DIR}`);
console.log('========================================');

// Start API subprocess
startApiServer();

// Start HTTP server
const server = http.createServer(handleRequest);

server.listen(PORT, '0.0.0.0', () => {
    console.log(`[serve] HTTP server listening on http://0.0.0.0:${PORT}`);
    console.log(`[serve] Web UI: http://210.44.49.21:${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('[serve] SIGTERM received, shutting down...');
    stopApiServer();
    server.close(() => {
        console.log('[serve] HTTP server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('[serve] SIGINT received, shutting down...');
    stopApiServer();
    server.close(() => process.exit(0));
});
