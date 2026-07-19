import json
from pathlib import Path
import pytest
from brickwise_ml.catalog.import_rebrickable import import_csv
from brickwise_ml.catalog.validate_catalog import validate_catalog
ROOT=Path(__file__).parents[1]
def test_import_ignores_images_and_is_deterministic(tmp_path):
    a=import_csv(ROOT/"data/fixtures/rebrickable/parts_test_fixture.csv",tmp_path/"a.json")
    b=import_csv(ROOT/"data/fixtures/rebrickable/parts_test_fixture.csv",tmp_path/"b.json")
    assert a["records"]==b["records"]; assert "image_url" not in json.dumps(a)
    assert a["import_report"]["duplicates"]==["TEST-0002"]
def test_dry_run_writes_no_output(tmp_path):
    out=tmp_path/"out.json"; import_csv(ROOT/"data/fixtures/rebrickable/parts_test_fixture.csv",out,True); assert not out.exists()
def test_invalid_record_fails(tmp_path):
    p=tmp_path/"bad.json"; p.write_text(json.dumps({"records":[{"design_id":"x"}]}))
    assert not validate_catalog(p)["valid"]
