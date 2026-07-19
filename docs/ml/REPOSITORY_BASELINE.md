# Repository baseline

Remote repository: HIPPO284/brickwise. Default branch: main. Baseline commit before Step 1: 2765a9bbe6eee01977b75b66a30b96bb623ebf74.

The production app is a dependency-free Node server using `node:sqlite`, starts with `npm start` (`node server.js`), and persists at `data/brickwise.sqlite` / Railway `/app/data`.

Existing source routes are `/`, `/admin`, and `/privacy`; `/scan` was not present in the baseline and is not changed by Step 1. No test script or test directory was present. Production files and Railway configuration were not modified.
