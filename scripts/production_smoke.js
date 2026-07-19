'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');

function request(port, pathname) {
  return new Promise((resolve, reject) => {
    const req = http.get({ hostname: '127.0.0.1', port, path: pathname }, (res) => {
      res.resume();
      res.on('end', () => resolve(res.statusCode));
    });
    req.on('error', reject);
  });
}

async function main() {
  const port = 18000 + Math.floor(Math.random() * 1000);
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'brickwise-smoke-'));
  const child = spawn(process.execPath, ['server.js'], {
    env: { ...process.env, PORT: String(port), DATA_DIR: dataDir, ADMIN_TOKEN: 'smoke-test-only' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  try {
    let health = 0;
    for (let attempt = 0; attempt < 30; attempt += 1) {
      try { health = await request(port, '/api/health'); if (health === 200) break; } catch {}
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
    const results = {
      '/api/health': health,
      '/': await request(port, '/'),
      '/admin': await request(port, '/admin'),
      '/privacy': await request(port, '/privacy'),
    };
    console.log(JSON.stringify(results));
    if (Object.values(results).some((status) => status !== 200)) process.exitCode = 1;
  } finally {
    child.kill('SIGTERM');
    fs.rmSync(dataDir, { recursive: true, force: true });
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
