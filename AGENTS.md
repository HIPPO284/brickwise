# Agent rules

- Preserve all existing production routes and Node startup behavior.
- Never commit production SQLite data, credentials, email addresses, feedback, or user images.
- Never scrape or download third-party images. Rebrickable is metadata-only.
- LDraw assets require header, dependency, hash, and license-policy validation.
- Unknown or missing licenses are never silently accepted.
- Keep `CUSTOM_MODEL_ENABLED=false` until a validated model and evaluation report exist.
- Do not install PyTorch or change Railway configuration in Step 1.
- Run existing Node validation before and after production changes; run the ML tests under `ml/`.
- See `docs/ml/` and `ml/README.md` for the complete workflow.
