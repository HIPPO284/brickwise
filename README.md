# Brickwise validation site v0.4

A lightweight Node.js landing page and validation dashboard for testing demand before building the full product.

## Included

- Public landing page and research survey
- SQLite waitlist and feedback storage
- Persistent Railway-compatible data directory
- Private `/admin` dashboard
- Server-side page-view tracking without third-party analytics
- Approximate daily unique visitors using one-way hashes
- UTM/source tracking for community campaigns
- Waitlist conversion rate
- CSV exports for traffic, waitlist, and feedback
- Basic rate limiting and honeypot protection

## Run locally

Requires Node.js 22.13 or newer.

### Windows CMD

```cmd
set ADMIN_TOKEN=replace-with-a-long-random-secret
npm start
```

Open:

```text
http://localhost:8000
http://localhost:8000/admin
```

## Railway

Set:

```text
ADMIN_TOKEN=<long random secret>
```

Attach a Railway Volume at:

```text
/app/data
```

## Campaign links

Use different links for each community so the dashboard can attribute traffic and signups:

```text
https://your-domain.example/?utm_source=reddit&utm_campaign=r-lego
https://your-domain.example/?utm_source=reddit&utm_campaign=r-legotechnic
https://your-domain.example/?utm_source=discord&utm_campaign=brick-community
https://your-domain.example/?utm_source=producthunt&utm_campaign=launch
```

The dashboard combines source and campaign for signups, for example `reddit:r-lego`.

## Privacy

The site does not use advertising cookies or third-party analytics. It stores page-view metadata and one-way shortened hashes to estimate daily unique visitors. Replace the placeholder operator email in `privacy.html` before a broad public launch.
