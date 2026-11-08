# Brickwise

An ongoing project exploring photo-based brick recognition and build recommendations.

## Project Status

Work in progress. This repository currently contains a product validation website and Python data-preparation tools. The vision model is not yet implemented; model training, recognition accuracy, and end-to-end scanning have not been validated.

The committed catalog examples are empty fixtures. They do not represent a verified real-world parts dataset.

## Current Implementation

- Website: collect waitlist registrations and product feedback, with a SQLite backend and a token-protected administration dashboard.
- Data preparation: import parts metadata from CSV, validate catalog records, check LDraw file dependencies and license policies, and select eligible parts.
- Supporting tools: file hashing, provenance records, environment checks, and foundation tests.

See [the ML documentation](ml/README.md) for the data workflow and its current limitations.

## Technology

- Website: HTML, CSS, JavaScript, Node.js, and SQLite.
- Data foundation: Python, Pydantic, JSON Schema, and pytest.

The recognition and build-recommendation features described by the product concept remain development goals.

## Website Features

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
- The website backend uses Node.js built-in modules, without third-party npm dependencies.

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


## v0.4.1 fix

Fixes the admin page remaining on “Checking token…” because the v0.4 HTML omitted the traffic dashboard elements required by `admin.js`.
