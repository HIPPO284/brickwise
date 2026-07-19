'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const ROOT = __dirname;
const DATA_DIR = process.env.DATA_DIR || path.join(ROOT, 'data');
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
  CREATE TABLE IF NOT EXISTS page_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visitor_hash TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'direct',
    campaign TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '/',
    referrer_host TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    ip_hash TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_page_views_created_at ON page_views(created_at);
  CREATE INDEX IF NOT EXISTS idx_page_views_source ON page_views(source);
  CREATE INDEX IF NOT EXISTS idx_page_views_visitor_hash ON page_views(visitor_hash);
`);

function ensureColumn(table, column, definition) {
  const columns = db.prepare(`PRAGMA table_info(${table})`).all().map((row) => row.name);
  if (!columns.includes(column)) db.exec(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`);
}
ensureColumn('feedback', 'source', "TEXT NOT NULL DEFAULT 'unknown'");

const insertWaitlist = db.prepare(`
  INSERT INTO waitlist (email, source, consent, created_at, ip_hash)
  VALUES (?, ?, ?, ?, ?)
`);
const insertFeedback = db.prepare(`
  INSERT INTO feedback (problem, collection_size, feedback, email, consent, created_at, ip_hash, source)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`);
const insertPageView = db.prepare(`
  INSERT INTO page_views (visitor_hash, source, campaign, path, referrer_host, created_at, ip_hash)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);

const rateBuckets = new Map();
function rateLimit(ip) {
  const now = Date.now();
  const windowMs = 60_000;
  const limit = 45;
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

function dailyVisitorHash(ip, userAgent, dateKey) {
  return crypto.createHash('sha256').update(`${ip}|${userAgent}|${dateKey}|brickwise-analytics-v1`).digest('hex').slice(0, 24);
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

function cleanSource(value) {
  const cleaned = cleanText(value, 80).toLowerCase();
  return cleaned.replace(/[^a-z0-9._:\/-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || 'direct';
}

function authorized(req) {
  const token = req.headers.authorization?.replace(/^Bearer\s+/i, '') || '';
  const expected = Buffer.from(ADMIN_TOKEN);
  const supplied = Buffer.from(token);
  if (supplied.length === 0 || supplied.length !== expected.length) return false;
  return crypto.timingSafeEqual(supplied, expected);
}

function csvEscape(value) {
  const stringValue = value == null ? '' : String(value);
  return `"${stringValue.replaceAll('"', '""')}"`;
}

function sendCsv(res, filename, headers, rows) {
  const body = `\uFEFF${[headers, ...rows].map((row) => row.map(csvEscape).join(',')).join('\n')}`;
  res.writeHead(200, {
    'Content-Type': 'text/csv; charset=utf-8',
    'Content-Disposition': `attachment; filename="${filename}"`,
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
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
  let requestPath = rawPath === '/' ? '/index.html' : rawPath;
  if (rawPath === '/admin' || rawPath === '/admin/') requestPath = '/admin.html';
  if (rawPath === '/privacy' || rawPath === '/privacy/') requestPath = '/privacy.html';

  const resolved = path.normalize(path.join(ROOT, requestPath));
  const relativePath = path.relative(ROOT, resolved);
  const escapesRoot = relativePath.startsWith('..') || path.isAbsolute(relativePath);
  const targetsDataDirectory = relativePath === 'data' || relativePath.startsWith(`data${path.sep}`);
  if (escapesRoot || targetsDataDirectory) {
    json(res, 403, { error: 'Forbidden' });
    return;
  }

  fs.readFile(resolved, (error, data) => {
    if (error) {
      json(res, 404, { error: 'Not found' });
      return;
    }
    const isAdminAsset = requestPath.startsWith('/admin');
    res.writeHead(200, {
      'Content-Type': mimeTypes[path.extname(resolved)] || 'application/octet-stream',
      'Content-Length': data.length,
      'Cache-Control': isAdminAsset ? 'no-store' : 'public, max-age=300',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=() ',
      'Content-Security-Policy': "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    });
    res.end(data);
  });
}

function getAdminDashboard() {
  const waitlistCount = db.prepare('SELECT COUNT(*) AS count FROM waitlist').get().count;
  const feedbackCount = db.prepare('SELECT COUNT(*) AS count FROM feedback').get().count;
  const pageViewCount = db.prepare('SELECT COUNT(*) AS count FROM page_views').get().count;
  const uniqueVisitorCount = db.prepare('SELECT COUNT(DISTINCT visitor_hash) AS count FROM page_views').get().count;
  const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const waitlistLast7Days = db.prepare('SELECT COUNT(*) AS count FROM waitlist WHERE created_at >= ?').get(since).count;
  const feedbackLast7Days = db.prepare('SELECT COUNT(*) AS count FROM feedback WHERE created_at >= ?').get(since).count;
  const pageViewsLast7Days = db.prepare('SELECT COUNT(*) AS count FROM page_views WHERE created_at >= ?').get(since).count;
  const uniqueVisitorsLast7Days = db.prepare('SELECT COUNT(DISTINCT visitor_hash) AS count FROM page_views WHERE created_at >= ?').get(since).count;
  const conversionRate = uniqueVisitorCount > 0 ? Number(((waitlistCount / uniqueVisitorCount) * 100).toFixed(1)) : 0;

  const problems = db.prepare(`
    SELECT problem, COUNT(*) AS count
    FROM feedback
    GROUP BY problem
    ORDER BY count DESC, problem ASC
  `).all();
  const collectionSizes = db.prepare(`
    SELECT collection_size AS collectionSize, COUNT(*) AS count
    FROM feedback
    GROUP BY collection_size
    ORDER BY count DESC, collection_size ASC
  `).all();
  const signupSources = db.prepare(`
    SELECT source, COUNT(*) AS count
    FROM waitlist
    GROUP BY source
    ORDER BY count DESC, source ASC
  `).all();
  const trafficSources = db.prepare(`
    SELECT source, COUNT(*) AS count
    FROM page_views
    GROUP BY source
    ORDER BY count DESC, source ASC
    LIMIT 20
  `).all();
  const recentWaitlist = db.prepare(`
    SELECT id, email, source, created_at AS createdAt
    FROM waitlist
    ORDER BY id DESC
    LIMIT 100
  `).all();
  const recentFeedback = db.prepare(`
    SELECT id, problem, collection_size AS collectionSize, feedback, email, source, created_at AS createdAt
    FROM feedback
    ORDER BY id DESC
    LIMIT 100
  `).all();
  const dailyTraffic = db.prepare(`
    SELECT substr(created_at, 1, 10) AS day,
           COUNT(*) AS pageViews,
           COUNT(DISTINCT visitor_hash) AS visitors
    FROM page_views
    WHERE created_at >= ?
    GROUP BY substr(created_at, 1, 10)
    ORDER BY day ASC
  `).all(since);

  return {
    generatedAt: new Date().toISOString(),
    waitlistCount,
    feedbackCount,
    pageViewCount,
    uniqueVisitorCount,
    conversionRate,
    waitlistLast7Days,
    feedbackLast7Days,
    pageViewsLast7Days,
    uniqueVisitorsLast7Days,
    problems,
    collectionSizes,
    signupSources,
    trafficSources,
    recentWaitlist,
    recentFeedback,
    dailyTraffic,
  };
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const ip = getIp(req);

    if (url.pathname.startsWith('/api/') && !rateLimit(ip)) {
      json(res, 429, { error: 'Too many requests. Please try again shortly.' });
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/health') {
      json(res, 200, { ok: true, service: 'brickwise-validation-api', version: '0.4.0' });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/visit') {
      try {
        const body = await readJson(req);
        if (body.website) return json(res, 200, { ok: true });
        const now = new Date();
        const dateKey = now.toISOString().slice(0, 10);
        const userAgent = cleanText(req.headers['user-agent'], 300);
        const source = cleanSource(body.source || 'direct');
        const campaign = cleanSource(body.campaign || '').replace(/^direct$/, '');
        const requestPath = cleanText(body.path, 180) || '/';
        const referrerHost = cleanSource(body.referrerHost || '').replace(/^direct$/, '');
        insertPageView.run(
          dailyVisitorHash(ip, userAgent, dateKey),
          source,
          campaign,
          requestPath,
          referrerHost,
          now.toISOString(),
          hashIp(ip),
        );
        json(res, 201, { ok: true });
      } catch (error) {
        json(res, error.message === 'PAYLOAD_TOO_LARGE' ? 413 : 400, { error: 'Unable to record visit.' });
      }
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/waitlist') {
      try {
        const body = await readJson(req);
        if (body.website) return json(res, 200, { ok: true });
        const email = cleanText(body.email, 254).toLowerCase();
        const source = cleanSource(body.source || 'unknown');
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
        const source = cleanSource(body.source || 'unknown');
        if (!problem || !collectionSize || feedback.length < 3) {
          return json(res, 400, { error: 'Complete all required feedback fields.' });
        }
        if (email && !isEmail(email)) return json(res, 400, { error: 'Enter a valid optional email.' });
        if (body.consent !== true) return json(res, 400, { error: 'Consent is required.' });

        insertFeedback.run(problem, collectionSize, feedback, email || null, 1, new Date().toISOString(), hashIp(ip), source);
        json(res, 201, { ok: true });
      } catch (error) {
        json(res, error.message === 'PAYLOAD_TOO_LARGE' ? 413 : 400, { error: 'Unable to save your feedback.' });
      }
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/admin/summary') {
      if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
      const dashboard = getAdminDashboard();
      json(res, 200, {
        waitlistCount: dashboard.waitlistCount,
        feedbackCount: dashboard.feedbackCount,
        pageViewCount: dashboard.pageViewCount,
        uniqueVisitorCount: dashboard.uniqueVisitorCount,
        conversionRate: dashboard.conversionRate,
        problems: dashboard.problems,
      });
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/admin/dashboard') {
      if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
      json(res, 200, getAdminDashboard());
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/admin/waitlist.csv') {
      if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
      const rows = db.prepare('SELECT id, email, source, created_at FROM waitlist ORDER BY id DESC').all();
      sendCsv(res, 'brickwise-waitlist.csv', ['id', 'email', 'source', 'created_at'], rows.map((row) => [row.id, row.email, row.source, row.created_at]));
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/admin/feedback.csv') {
      if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
      const rows = db.prepare('SELECT id, problem, collection_size, feedback, email, source, created_at FROM feedback ORDER BY id DESC').all();
      sendCsv(res, 'brickwise-feedback.csv', ['id', 'problem', 'collection_size', 'feedback', 'email', 'source', 'created_at'], rows.map((row) => [row.id, row.problem, row.collection_size, row.feedback, row.email, row.source, row.created_at]));
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/admin/traffic.csv') {
      if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' });
      const rows = db.prepare('SELECT id, visitor_hash, source, campaign, path, referrer_host, created_at FROM page_views ORDER BY id DESC').all();
      sendCsv(res, 'brickwise-traffic.csv', ['id', 'visitor_hash', 'source', 'campaign', 'path', 'referrer_host', 'created_at'], rows.map((row) => [row.id, row.visitor_hash, row.source, row.campaign, row.path, row.referrer_host, row.created_at]));
      return;
    }

    if (req.method === 'GET') {
      serveStatic(req, res);
      return;
    }

    json(res, 405, { error: 'Method not allowed' });
  } catch (error) {
    console.error('Unhandled request error:', error);
    if (!res.headersSent) json(res, 500, { error: 'Internal server error' });
    else res.end();
  }
});

server.listen(PORT, () => {
  console.log(`Brickwise running at http://localhost:${PORT}`);
  console.log(`Database directory: ${DATA_DIR}`);
  if (ADMIN_TOKEN === 'change-this-before-public-launch') {
    console.warn('WARNING: Set ADMIN_TOKEN before public deployment.');
  }
});
