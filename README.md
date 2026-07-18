# Brickwise AI — Validation Site v0.2

Responsive landing page plus a real waitlist and product-research backend.

## Included

- Email waitlist saved to SQLite
- Duplicate-email handling
- Product feedback form
- Optional feedback follow-up email
- Consent checkboxes and privacy notice
- Honeypot spam field and basic rate limiting
- Hashed network identifier for abuse prevention
- Admin summary endpoint
- Protected CSV exports
- No third-party npm dependencies

## Requirements

Use Node.js 24 or newer because the server uses the built-in `node:sqlite` module.

## Run locally

### Windows PowerShell

```powershell
cd path\to\brickwise-landing
$env:ADMIN_TOKEN="replace-with-a-long-random-secret"
npm start
```

### macOS/Linux

```bash
cd path/to/brickwise-landing
ADMIN_TOKEN="replace-with-a-long-random-secret" npm start
```

Open `http://localhost:8000`.

## Test the API

Health check:

```text
http://localhost:8000/api/health
```

The database is created automatically at:

```text
data/brickwise.sqlite
```

## Admin endpoints

Send the token as an Authorization header:

```text
Authorization: Bearer YOUR_ADMIN_TOKEN
```

Available endpoints:

- `GET /api/admin/summary`
- `GET /api/admin/waitlist.csv`
- `GET /api/admin/feedback.csv`

Example CSV download with curl:

```bash
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  http://localhost:8000/api/admin/waitlist.csv \
  -o brickwise-waitlist.csv
```

## Before public deployment

1. Set a strong `ADMIN_TOKEN`; never use the development fallback.
2. Replace the placeholder contact section in `privacy.html`.
3. Use HTTPS through the hosting provider.
4. Add database backups.
5. Review privacy, consent, age, email-marketing, and trademark requirements for the countries where the site is offered.
6. Do not advertise scanning accuracy until it is measured on a representative test set.

## Trademark positioning

Use Brickwise AI or another neutral name. Do not imply endorsement by a toy manufacturer, use official logos, or reproduce protected instructions or commercial model designs without permission.
