# Step 1 report

Status: foundation implemented; real catalog data remains blocked pending owner-supplied permitted Rebrickable CSV and LDraw Parts Library.

Completed: deterministic CSV importer with optional colors CSV, JSON Schema/Pydantic agreement checks, LDraw recursive dependency/license validation, explicit category-group beta policy selection, typed beta output, typed provenance manifests, environment doctor, focused foundation tests, production smoke harness, and GitHub Actions for Python 3.11/3.12.

Previous validation reference:
- Current head tested: 7ca1107ef760c204257bb2418925dc90cf4ccd6a
- GitHub Actions run: 29686291755

Validation after this cleanup is reported below once the new branch head completes CI:
- Python 3.11 GitHub Actions: pending
- Python 3.12 GitHub Actions: pending
- compileall on committed ml/brickwise_ml and ml/tests: pending
- node --check server.js: pending
- production smoke: /api/health, /, /admin, /privacy: pending
- pytest: 45 baseline tests plus cleanup tests: pending

Counts: verified catalog records 0; planned records 0; beta_v1 records 0; rejected 0; review_required 0. These are truthful blocker counts, not fabricated catalog output.

Candidate 41239: blocked pending permitted metadata and LDraw evidence. It is not inserted into the catalog or beta list.

Privacy baseline clarification:
- `privacy.html` existed in the baseline.
- The extensionless `/privacy` mapping was missing.
- This PR adds only the minimal mapping from `/privacy` to `privacy.html`.
SQLite schema, existing HTML/CSS, package.json, Railway configuration, production data, and environment variables were not changed. CUSTOM_MODEL_ENABLED remains false and no PyTorch dependency was added.

Beta selection now requires an explicit configurable raw-category-to-category-group mapping. Unknown mappings are reported as `review_required` and are not guessed or selected. Selection metadata is held in typed `BetaSelectionEntry` objects whose nested `part` remains a strict `PartRecord`.

PR #1 remains Draft and unmerged.

Required next input: provide a permitted Rebrickable CSV export and a licensed LDraw Parts Library path. Then run the documented import, validation, LDraw report, and beta selection commands. No model training occurs in Step 1.
