'use strict';

const TOKEN_KEY = 'brickwiseAdminToken';
const loginView = document.querySelector('#login-view');
const dashboardView = document.querySelector('#dashboard-view');
const loginForm = document.querySelector('#login-form');
const tokenInput = document.querySelector('#token');
const loginStatus = document.querySelector('#login-status');
const dashboardStatus = document.querySelector('#dashboard-status');
const loginButton = document.querySelector('#login-button');

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || '';
}

function setStatus(element, message, isError = false) {
  element.textContent = message;
  element.style.color = isError ? '#b3261e' : '#417252';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

async function adminFetch(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  let response;
  try {
    response = await fetch(path, {
      headers: { Authorization: `Bearer ${getToken()}` },
      cache: 'no-store',
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
  if (response.status === 401) throw new Error('UNAUTHORIZED');
  if (!response.ok) throw new Error('REQUEST_FAILED');
  return response;
}

function renderBars(container, items, labelKey, emptyMessage = 'No data yet.') {
  if (!items.length) {
    container.className = 'bar-list empty-state';
    container.textContent = emptyMessage;
    return;
  }
  const maximum = Math.max(...items.map((item) => Number(item.count) || 0), 1);
  container.className = 'bar-list';
  container.innerHTML = items.map((item) => {
    const label = escapeHtml(item[labelKey]);
    const count = Number(item.count) || 0;
    const width = Math.max((count / maximum) * 100, 4);
    return `
      <div class="bar-item">
        <div class="bar-meta"><span title="${label}">${label}</span><strong>${count}</strong></div>
        <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
      </div>`;
  }).join('');
}

function renderWaitlist(rows) {
  const body = document.querySelector('#waitlist-table');
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="3" class="table-empty">No signups yet.</td></tr>';
    return;
  }
  body.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.email)}</td>
      <td>${escapeHtml(row.source)}</td>
      <td>${escapeHtml(formatDate(row.createdAt))}</td>
    </tr>`).join('');
}

function renderFeedback(rows) {
  const container = document.querySelector('#feedback-list');
  if (!rows.length) {
    container.className = 'feedback-list empty-state';
    container.textContent = 'No feedback submitted yet.';
    return;
  }
  container.className = 'feedback-list';
  container.innerHTML = rows.map((row) => `
    <article class="feedback-card">
      <div class="feedback-card-head">
        <h3>${escapeHtml(row.problem)}</h3>
        <time datetime="${escapeHtml(row.createdAt)}">${escapeHtml(formatDate(row.createdAt))}</time>
      </div>
      <p>${escapeHtml(row.feedback)}</p>
      <div class="feedback-meta">
        <span>Collection: ${escapeHtml(row.collectionSize)}</span>
        <span>Source: ${escapeHtml(row.source || 'unknown')}</span>
        <span>Contact: ${escapeHtml(row.email || 'Not provided')}</span>
      </div>
    </article>`).join('');
}

function renderTrafficTrend(rows) {
  const body = document.querySelector('#traffic-table');
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="3" class="table-empty">Traffic will appear after the next public visit.</td></tr>';
    return;
  }
  body.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.day)}</td>
      <td>${escapeHtml(row.visitors)}</td>
      <td>${escapeHtml(row.pageViews)}</td>
    </tr>`).join('');
}

function renderDashboard(data) {
  document.querySelector('#visitor-count').textContent = data.uniqueVisitorCount;
  document.querySelector('#pageview-count').textContent = data.pageViewCount;
  document.querySelector('#waitlist-count').textContent = data.waitlistCount;
  document.querySelector('#feedback-count').textContent = data.feedbackCount;
  document.querySelector('#conversion-rate').textContent = `${data.conversionRate}%`;
  document.querySelector('#visitor-week').textContent = data.uniqueVisitorsLast7Days;
  document.querySelector('#pageview-week').textContent = data.pageViewsLast7Days;
  document.querySelector('#waitlist-week').textContent = data.waitlistLast7Days;
  document.querySelector('#feedback-week').textContent = data.feedbackLast7Days;
  document.querySelector('#updated-at').textContent = `Updated ${formatDate(data.generatedAt)}`;

  const topProblem = data.problems[0];
  document.querySelector('#top-problem').textContent = topProblem?.problem || 'No data yet';
  document.querySelector('#top-problem-count').textContent = topProblem ? `${topProblem.count} response${topProblem.count === 1 ? '' : 's'}` : 'Waiting for responses';

  renderBars(document.querySelector('#traffic-source-bars'), data.trafficSources, 'source', 'No tracked visits yet.');
  renderBars(document.querySelector('#signup-source-bars'), data.signupSources, 'source', 'No signups yet.');
  renderBars(document.querySelector('#problem-bars'), data.problems, 'problem', 'No feedback submitted yet.');
  renderBars(document.querySelector('#collection-bars'), data.collectionSizes, 'collectionSize', 'No feedback submitted yet.');
  renderTrafficTrend(data.dailyTraffic);
  renderWaitlist(data.recentWaitlist);
  renderFeedback(data.recentFeedback);
}

async function loadDashboard() {
  setStatus(dashboardStatus, 'Loading…');
  try {
    const response = await adminFetch('/api/admin/dashboard');
    const data = await response.json();
    renderDashboard(data);
    loginView.hidden = true;
    dashboardView.hidden = false;
    setStatus(dashboardStatus, '');
  } catch (error) {
    if (error.message === 'UNAUTHORIZED') {
      sessionStorage.removeItem(TOKEN_KEY);
      dashboardView.hidden = true;
      loginView.hidden = false;
      setStatus(loginStatus, 'That token was rejected. Copy the current ADMIN_TOKEN from Railway.', true);
      tokenInput.focus();
    } else {
      console.error('Dashboard load failed:', error);
      dashboardView.hidden = true;
      loginView.hidden = false;
      const message = error.name === 'AbortError'
        ? 'The server took too long to respond. Refresh the page and try again.'
        : 'The dashboard could not load. The page files may be out of sync; deploy v0.4.1.';
      setStatus(loginStatus, message, true);
    }
  }
}

async function downloadCsv(path, filename) {
  setStatus(dashboardStatus, 'Preparing download…');
  try {
    const response = await adminFetch(path);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setStatus(dashboardStatus, `${filename} downloaded.`);
  } catch (error) {
    if (error.message === 'UNAUTHORIZED') {
      sessionStorage.removeItem(TOKEN_KEY);
      location.reload();
      return;
    }
    setStatus(dashboardStatus, 'Download failed. Try again.', true);
  }
}

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const token = tokenInput.value.trim();
  if (!token) return;
  sessionStorage.setItem(TOKEN_KEY, token);
  setStatus(loginStatus, 'Checking token…');
  loginButton.disabled = true;
  try {
    await loadDashboard();
    tokenInput.value = '';
  } finally {
    loginButton.disabled = false;
  }
});

document.querySelector('#refresh-button').addEventListener('click', loadDashboard);
document.querySelector('#logout-button').addEventListener('click', () => {
  sessionStorage.removeItem(TOKEN_KEY);
  location.reload();
});
document.querySelector('#download-waitlist').addEventListener('click', () => downloadCsv('/api/admin/waitlist.csv', 'brickwise-waitlist.csv'));
document.querySelector('#download-feedback').addEventListener('click', () => downloadCsv('/api/admin/feedback.csv', 'brickwise-feedback.csv'));
document.querySelector('#download-traffic').addEventListener('click', () => downloadCsv('/api/admin/traffic.csv', 'brickwise-traffic.csv'));

if (getToken()) loadDashboard();
