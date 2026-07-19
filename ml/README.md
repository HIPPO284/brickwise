# Brickwise ML foundation

Step 1 is an offline-first data foundation. It does not train or deploy a model.

## Windows CMD

```cmd
cd ml
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m brickwise_ml.cli.doctor
python -m pytest
```

Import permitted Rebrickable metadata CSV (no images are read or downloaded):

```cmd
python -m brickwise_ml.cli.catalog_import --mode csv --parts-csv C:\path\parts.csv --output data\catalog\catalog.v1.json
python -m brickwise_ml.cli.catalog_validate --catalog data\catalog\catalog.v1.json
python -m brickwise_ml.cli.ldraw_validate --parts-dir C:\path\ldraw\parts --policy config\approved_licenses.example.json --report reports\ldraw_validation.json
python -m brickwise_ml.cli.beta_select --catalog data\catalog\catalog.v1.json --ldraw-report reports\ldraw_validation.json --output data\catalog\beta_v1.json
```

API mode is an explicit adapter stub and requires `REBRICKABLE_API_KEY`; it never downloads images.

The committed catalog examples are intentionally empty/blocker fixtures. Do not claim 100 verified parts or 20 beta parts until the owner supplies permitted metadata and an LDraw Parts Library.

Generated reports are local artifacts unless deliberately reviewed for commit. Clean local generated files by deleting `ml/.pytest_cache`, `ml/**/__pycache__`, and files under `ml/data/raw`, `ml/data/downloads`, and `ml/artifacts`.
