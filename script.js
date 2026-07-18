function showToast(message, isError = false) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.toggle('error', isError);
  toast.classList.add('visible');
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => toast.classList.remove('visible'), 3200);
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}

function getTracking() {
  const params = new URLSearchParams(location.search);
  const source = params.get('utm_source') || params.get('source') || 'direct';
  const campaign = params.get('utm_campaign') || '';
  let referrerHost = '';
  try {
    referrerHost = document.referrer ? new URL(document.referrer).hostname : '';
  } catch {
    referrerHost = '';
  }
  const combinedSource = campaign ? `${source}:${campaign}` : source;
  return { source, campaign, combinedSource, referrerHost };
}

const tracking = getTracking();
postJson('/api/visit', {
  source: tracking.source,
  campaign: tracking.campaign,
  path: location.pathname,
  referrerHost: tracking.referrerHost,
  website: '',
}).catch(() => {});

document.querySelectorAll('[data-waitlist-form]').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const button = form.querySelector('button[type="submit"]');
    const emailInput = form.querySelector('input[name="email"]');
    const consentInput = form.querySelector('input[name="consent"]');
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Joining…';

    try {
      const formLocation = form.dataset.source || 'unknown';
      const source = tracking.combinedSource === 'direct'
        ? `direct:${formLocation}`
        : tracking.combinedSource;
      const result = await postJson('/api/waitlist', {
        email: emailInput.value.trim(),
        source,
        consent: consentInput.checked,
        website: form.querySelector('input[name="website"]')?.value || '',
      });
      const message = result.status === 'existing'
        ? 'You are already on the beta list.'
        : "You're on the beta list — thank you.";
      form.reset();
      showToast(message);
      document.querySelectorAll('[data-global-status]').forEach((node) => { node.textContent = message; });
    } catch (error) {
      showToast(error.message, true);
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  });
});

const researchForm = document.getElementById('research-form');
researchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!researchForm.reportValidity()) return;

  const button = researchForm.querySelector('button[type="submit"]');
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = 'Submitting…';

  try {
    const formData = Object.fromEntries(new FormData(researchForm).entries());
    await postJson('/api/feedback', {
      ...formData,
      source: tracking.combinedSource,
      consent: formData.consent === 'on',
    });
    document.getElementById('research-status').textContent = 'Feedback received. Thank you for shaping the beta.';
    researchForm.reset();
    showToast('Feedback received — thank you.');
  } catch (error) {
    document.getElementById('research-status').textContent = error.message;
    showToast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
});
