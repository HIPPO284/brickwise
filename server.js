'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, 'data');
const PORT = Number(process.env.PORT || 8000);
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'change-this-before-public-launch';
const MAX_BODY_BYTES = 32 * 1024;

fs.mkdirSync(DATA_DIR, { recursive: true });
const db = new DatabaseSync(path.join(DATA_DIR, 'brickwise.sqlite'));
db.exec(`
  PRAGMA journal_mode = WAL;
  CREATE TABLE IF NOT EXISTS waitlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL DEFAULT 'unknown',
    consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    ip_hash TEXT
  );
  CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem TEXT NOT NULL,
    collection_size TEXT NOT NULL,
    feedback TEXT NOT NULL,
    email TEXT,
    consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    ip_hash TEXT
  );
`);

const insertWaitlist = db.prepare(`
  INSERT INTO waitlist (email, source, consent, created_at, ip_hash)
  VALUES (?, ?, ?, ?, ?)
`);
const insertFeedback = db.prepare(`
  INSERT INTO feedback (problem, collection_size, feedback, email, consent, created_at, ip_hash)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);

const rateBuckets = new Map();
function rateLimit(ip) {
  const now = Date.now();
  const windowMs = 60_000;
  const limit = 20;
  const recent = (rateBuckets.get(ip) || []).filter((time) => now - time < windowMs);
  if (recent.length >= limit) return false;
  recent.push(now);
  rateBuckets.set(ip, recent);
  return true;
}

function getIp(req) {
  return String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown').split(',')[0].trim();
}

function hashIp(ip) {
  return crypto.createHash('sha256').update(`${ip}|brickwise-v1`).digest('hex').slice(0, 24);
}

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
  });
  res.end(body);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (Buffer.byteLength(raw) > MAX_BODY_BYTES) {
        reject(new Error('PAYLOAD_TOO_LARGE'));
        req.destroy();
      }
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(raw || '{}'));
      } catch {
        reject(new Error('INVALID_JSON'));
      }
    });
    req.on('error', reject);
  });
}

function isEmail(value) {
  return typeof value === 'string' && value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function cleanText(value, maxLength) {
  return typeof value === 'string' ? value.trim().slice(0, maxLength) : '';
}

function authorized(req) {
  const token = req.headers.authorization?.replace(/^Bearer\s+/i, '') || '';
  return token.length > 0 && crypto.timingSafeEqual(Buffer.from(token), Buffer.from(ADMIN_TOKEN));
}

function csvEscape(value) {
  const stringValue = value == null ? '' : String(value);
  return `"${stringValue.replaceAll('"', '""')}"`;
}

function sendCsv(res, filename, headers, rows) {
  const body = [headers, ...rows].map((row) => row.map(csvEscape).join(',')).join('\n');
  res.writeHead(200, {
    'Content-Type': 'text/csv; charset=utf-8',
    'Content-Disposition': `attachment; filename="${filename}"`,
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
};

function serveStatic(req, res) {
  const rawPath = new URL(req.url, `http://${req.headers.host || 'localhost'}`).pathname;
  const requestPath = rawPath === '/' ? '/index.html' : rawPath;
  const resolved = path.normalize(path.join(ROOT, requestPath));
  if (!resolved.startsWith(ROOT) || resolved.includes(`${path.sep}data${path.sep}`)) {
    json(res, 403, { error: 'Forbidden' });
    return;
  }
  fs.readFile(resolved, (error, data) => {
    if (error) {
      json(res, 404, { error: 'Not found' });
      return;
    }
    res.writeHead(200, {
      'Content-Type': mimeTypes[path.extname(resolved)] || 'application/octet-stream',
      'Content-Length': data.length,
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
      'Content-Security-Policy': "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const ip = getIp(req);

  if (url.pathname.startsWith('/api/') && !rateLimit(ip)) {
    json(res, 429, { error: 'Too many requests. Please try again shortly.' });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/api/health') {
    json(res, 200, { ok: true, service: 'brickwise-validation-api' });
    return;
  }

  if (req.method === 'POST' && url.pathname === '/api/waitlist') {
    try {
      const body = await readJson(req);
      if (body.website) return json(res, 200, { ok: true });
      const email = cleanText(body.email, 254).toLowerCase();
      const source = cleanText(body.source, 32) || 'unknown';
      if (!isEmail(email)) return json(res, 400, { error: 'Enter a valid email address.' });
      if (body.consent !== true) return json(res, 400, { error: 'Consent is required.' });

      try {
        insertWaitlist.run(email, source, 1, new Date().toISOString(), hashIp(ip));
        json(res, 201, { ok: true, status: 'created' });
      } catch (error) {
        if (String(error.message).includes('UNIQUE')) {
          json(res, 200, { ok: true, status: 'existing' });
        } else {
          throw error;
        }
      }
    } catch (error) {
      json(res, error.message === 'PAYLOAD_TOO_LARGE' ? 413 : 400, { error: 'Unable to save your request.' });
    }
    return;
  }

  if (req.method === 'POST' && url.pathname === '/api/feedback') {
    try {
      const body = await readJson(req);
      if (body.website) return json(res, 200, { ok: true });
      const problem = cleanText(body.problem, 100);
      const collectionSize = cleanText(body.collectionSize, 64);
      const feedback = cleanText(body.feedback, 2000);
      const email = cleanText(body.email, 254).toLowerCase();
      if (!problem || !collectionSize || feedback.length < 3) {
        return json(res, 400, { error: 'Complete all required feedback fields.' });
      }
      if (email && !isEmail(email)) return json(res, 400, { error: 'Enter a valid optional email.' });
      if (body.consent !== true) return json(res, 400, { error: 'Consent is required.' });

      insertFeedback.run(problem, collectionSize, feedback, email || null, 1, new Date().toISOString(), hashIp(ip));
      json(res, 201, { ok: true });
    } catch (error) {
      json(res, error.message === 'PAYLOAD_TOO_LARGE' ? 413 : 400, { error: 'Unable to save your feedback.' });
    }
    return;
  }

  if (req.method === 'GET' && url.pathname === '/api/admin/summary') {
    if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
    const waitlistCount = db.prepare('SELECT COUNT(*) AS count FROM waitlist').get().count;
    const feedbackCount = db.prepare('SELECT COUNT(*) AS count FROM feedback').get().count;
    const problems = db.prepare('SELECT problem, COUNT(*) AS count FROM feedback GROUP BY problem ORDER BY count DESC').all();
    json(res, 200, { waitlistCount, feedbackCount, problems });
    return;
  }

  if (req.method === 'GET' && url.pathname === '/api/admin/waitlist.csv') {
    if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
    const rows = db.prepare('SELECT id, email, source, created_at FROM waitlist ORDER BY id DESC').all();
    sendCsv(res, 'brickwise-waitlist.csv', ['id', 'email', 'source', 'created_at'], rows.map((r) => [r.id, r.email, r.source, r.created_at]));
    return;
  }

  if (req.method === 'GET' && url.pathname === '/api/admin/feedback.csv') {
    if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
    const rows = db.prepare('SELECT id, problem, collection_size, feedback, email, created_at FROM feedback ORDER BY id DESC').all();
    sendCsv(res, 'brickwise-feedback.csv', ['id', 'problem', 'collection_size', 'feedback', 'email', 'created_at'], rows.map((r) => [r.id, r.problem, r.collection_size, r.feedback, r.email, r.created_at]));
    return;
  }

  if (req.method === 'GET') {
    serveStatic(req, res);
    return;
  }

  json(res, 405, { error: 'Method not allowed' });
});

server.listen(PORT, () => {
  console.log(`Brickwise running at http://localhost:${PORT}`);
  if (ADMIN_TOKEN === 'change-this-before-public-launch') {
    console.warn('WARNING: Set ADMIN_TOKEN before public deployment.');
  }
});
