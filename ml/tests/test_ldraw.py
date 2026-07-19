from pathlib import Path
from brickwise_ml.ldraw.header_parser import parse_header
from brickwise_ml.ldraw.asset_validator import license_status,validate_parts
ROOT=Path(__file__).parents[1]
POLICY=ROOT/"config/approved_licenses.example.json"
def test_header_and_accepted_license():
    h=parse_header(ROOT/"data/fixtures/ldraw/accepted.dat"); assert h["name"]; assert h["license_raw"]
    assert license_status(h["license_raw"],__import__("json").loads(POLICY.read_text()))=="accepted"
def test_missing_and_unknown_are_not_accepted(tmp_path):
    p=tmp_path/"policy.json"; p.write_text(POLICY.read_text())
    r=validate_parts(ROOT/"data/fixtures/ldraw",p)
    states={x["filename"]:x["license_status"] for x in r["assets"]}
    assert states["missing-license.dat"]=="missing"; assert states["review.dat"]=="review_required"
