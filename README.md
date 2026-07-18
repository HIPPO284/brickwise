# Brickwise AI — Validation Site v0.3

Responsive landing page, SQLite validation backend, and a private browser-based admin dashboard.

## Included

- Email waitlist saved to SQLite
- Duplicate-email handling
- Product feedback form
- Optional feedback follow-up email
- Consent checkboxes and privacy notice
- Honeypot spam field and basic rate limiting
- Hashed network identifier for abuse prevention
- Private `/admin` dashboard protected by `ADMIN_TOKEN`
- Summary metrics, recent submissions, demand breakdowns
- Protected CSV exports from the dashboard
- No third-party npm dependencies

## Requirements

Use Node.js 24 or newer because the server uses the built-in `node:sqlite` module.

## Run locally

### Windows CMD

```cmd
cd path\to\brickwise-landing
set ADMIN_TOKEN=replace-with-a-long-random-secret
npm start
```

Open:

```text
http://localhost:8000
```

Admin dashboard:

```text
http://localhost:8000/admin
```

Enter the same `ADMIN_TOKEN`. The dashboard stores it only in browser `sessionStorage`, not in the URL.

## Railway deployment

Required service variable:

```text
ADMIN_TOKEN=your-long-random-secret
```

Persistent Volume mount path:

```text
/app/data
```

The database is stored at:

```text
data/brickwise.sqlite
```

With Railway's application directory at `/app`, this maps to `/app/data/brickwise.sqlite` on the mounted Volume.

## Admin API

Send the token as an Authorization header:

```text
Authorization: Bearer YOUR_ADMIN_TOKEN
```

Available endpoints:

- `GET /api/admin/summary`
- `GET /api/admin/dashboard`
- `GET /api/admin/waitlist.csv`
- `GET /api/admin/feedback.csv`

## Security notes

1. Never share or screenshot `ADMIN_TOKEN`.
2. Replace a token immediately if it is exposed.
3. The `/admin` HTML is publicly reachable, but no data is returned without the token.
4. Keep the GitHub repository free of the `data/` directory and `.env` files.
5. Back up the Railway Volume periodically.

## Before broader public promotion

1. Replace the placeholder operator contact in `privacy.html`.
2. Review privacy, consent, age, email-marketing, and trademark requirements for target countries.
3. Do not advertise scanning accuracy until measured on a representative test set.
4. Avoid implying endorsement by any toy manufacturer or reproducing protected instructions or commercial model designs without permission.
