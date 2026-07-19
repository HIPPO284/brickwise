# LDraw licensing workflow

The validator parses the asset header, records raw header text, name, author, license text, dependencies, missing dependencies, malformed lines, and SHA-256.

License policy is configurable in `ml/config/approved_licenses.example.json`. Exact accepted values become `accepted`; exact rejected values become `rejected`; matching review patterns become `review_required`; absent license becomes `missing`; all other values use the configured default.

Only assets with an accepted license, successful parsing, and no missing dependencies can be valid beta candidates. This is a provenance workflow, not legal advice. Unknown does not mean accepted.
