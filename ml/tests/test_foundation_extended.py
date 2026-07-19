import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from brickwise_ml.catalog.import_rebrickable import import_csv
from brickwise_ml.catalog.models import PartRecord
from brickwise_ml.catalog.select_beta_parts import select_beta
from brickwise_ml.catalog.validate_catalog import validate_catalog
from brickwise_ml.ldraw.asset_validator import validate_parts, write_attribution
from brickwise_ml.ldraw.header_parser import parse_header
from brickwise_ml.provenance.hashing import sha256_file
from brickwise_ml.provenance.manifest import Manifest, manifest_for
from brickwise_ml.cli.doctor import run_checks

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "rebrickable" / "parts_test_fixture.csv"
POLICY = ROOT / "config" / "approved_licenses.example.json"
STAMP = "2026-01-01T00:00:00+00:00"

def test_utf8_bom_and_string_ids(tmp_path):
    source = tmp_path / "bom.csv"
    source.write_text("\ufeffpart_num,name,category\n001,Brick,Basic Brick\n", encoding="utf-8")
    result = import_csv(source, tmp_path / "out.json", timestamp=STAMP)
    assert result["records"][0]["design_id"] == "001"

def test_missing_id_is_reported(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("part_num,name,category\n,Missing ID,Brick\n", encoding="utf-8")
    result = import_csv(source, tmp_path / "out.json", timestamp=STAMP)
    assert result["import_report"]["errors"][0]["reason"] == "missing design_id"

def test_missing_name_is_reported(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("part_num,name,category\nX,,Brick\n", encoding="utf-8")
    result = import_csv(source, tmp_path / "out.json", timestamp=STAMP)
    assert result["import_report"]["errors"][0]["reason"] == "missing name"

def test_conflicting_names_are_reported(tmp_path):
    source = tmp_path / "conflict.csv"
    source.write_text("part_num,name,category\nX,One,Brick\nX,Two,Brick\n", encoding="utf-8")
    result = import_csv(source, tmp_path / "out.json", timestamp=STAMP)
    assert result["import_report"]["conflicts"] == {"X": ["One", "Two"]}

def test_colors_are_only_imported_from_explicit_relationship(tmp_path):
    source = tmp_path / "parts.csv"
    colors = tmp_path / "colors.csv"
    source.write_text("part_num,name,category\nX,Brick,Brick\n", encoding="utf-8")
    colors.write_text("part_num,color_id,color_name\nX,1,Red\n", encoding="utf-8")
    result = import_csv(source, tmp_path / "out.json", colors, timestamp=STAMP)
    assert result["records"][0]["supported_colors"][0]["color_id"] == "1"

def test_complete_catalog_file_is_byte_deterministic(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    import_csv(FIXTURE, first, timestamp=STAMP)
    import_csv(FIXTURE, second, timestamp=STAMP)
    assert sha256_file(first) == sha256_file(second)

def test_source_date_epoch_is_supported(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    result = import_csv(FIXTURE, tmp_path / "out.json")
    assert result["import_report"]["retrieved_at"].startswith("1970-01-01")

def test_report_path_is_written(tmp_path):
    report = tmp_path / "reports" / "import.json"
    import_csv(FIXTURE, tmp_path / "out.json", report_output=report, timestamp=STAMP)
    assert json.loads(report.read_text())["network_requests"] == 0

def test_csv_mode_does_not_open_network(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")))
    result = import_csv(FIXTURE, tmp_path / "out.json", timestamp=STAMP)
    assert result["import_report"]["network_requests"] == 0

def _record():
    result = import_csv(FIXTURE, Path("/tmp/unused.json"), dry_run=True, timestamp=STAMP)
    record = result["records"][0]
    record["ldraw"]["file_sha256"] = "a" * 64
    record["source"]["source_sha256"] = "b" * 64
    return record

def test_schema_accepts_valid_complete_record():
    PartRecord.model_validate(_record())

def test_schema_rejects_missing_design_id():
    record = _record()
    del record["design_id"]
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_schema_rejects_empty_design_id():
    record = _record()
    record["design_id"] = ""
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_schema_rejects_empty_name():
    record = _record()
    record["name"] = ""
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_schema_rejects_extra_field():
    record = _record()
    record["unexpected"] = True
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_schema_rejects_missing_provenance():
    record = _record()
    del record["provenance"]
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_schema_rejects_missing_recognition():
    record = _record()
    del record["recognition"]
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_schema_allows_unknown_geometry():
    record = _record()
    assert record["geometry"]["bounding_box_ldu"] == {"x": None, "y": None, "z": None}

def test_schema_rejects_invalid_sha256():
    record = _record()
    record["ldraw"]["file_sha256"] = "bad"
    with pytest.raises(Exception):
        PartRecord.model_validate(record)

def test_json_schema_and_pydantic_agree():
    path = Path("/tmp/catalog-agreement.json")
    path.write_text(json.dumps({"records": [_record()]}), encoding="utf-8")
    assert validate_catalog(path)["valid"]

def test_ldraw_header_parses_raw_header():
    header = parse_header(ROOT / "data" / "fixtures" / "ldraw" / "accepted.dat")
    assert "TEST FIXTURE ONLY" in header["raw_header"]

def test_ldraw_missing_license_is_not_accepted():
    report = validate_parts(ROOT / "data" / "fixtures" / "ldraw", POLICY)
    asset = next(item for item in report["assets"] if item["filename"] == "missing-license.dat")
    assert asset["license_status"] == "missing"

def test_ldraw_review_license_is_not_accepted():
    report = validate_parts(ROOT / "data" / "fixtures" / "ldraw", POLICY)
    asset = next(item for item in report["assets"] if item["filename"] == "review.dat")
    assert asset["license_status"] == "review_required"

def test_ldraw_dependency_is_valid(tmp_path):
    (tmp_path / "child.dat").write_text("0 FILE child.dat\n0 !LICENSE Licensed under CC BY 4.0\n", encoding="utf-8")
    (tmp_path / "parent.dat").write_text("0 FILE parent.dat\n0 !LICENSE Licensed under CC BY 4.0\n1 16 0 0 0 1 0 0 0 0 1 0 0 0 1 child.dat\n", encoding="utf-8")
    report = validate_parts(tmp_path, POLICY)
    parent = next(item for item in report["assets"] if item["filename"] == "parent.dat")
    assert parent["missing_dependencies"] == []

def test_ldraw_missing_dependency_is_reported(tmp_path):
    (tmp_path / "parent.dat").write_text("0 FILE parent.dat\n0 !LICENSE Licensed under CC BY 4.0\n1 16 0 0 0 1 0 0 0 0 1 0 0 0 1 missing.dat\n", encoding="utf-8")
    report = validate_parts(tmp_path, POLICY)
    assert report["assets"][0]["missing_dependencies"] == ["missing.dat"]

def test_ldraw_cycle_is_reported(tmp_path):
    for name, child in [("a.dat", "b.dat"), ("b.dat", "a.dat")]:
        (tmp_path / name).write_text(f"0 FILE {name}\n0 !LICENSE Licensed under CC BY 4.0\n1 16 0 0 0 1 0 0 0 0 1 0 0 0 1 {child}\n", encoding="utf-8")
    assert validate_parts(tmp_path, POLICY)["cycles"]

def test_ldraw_malformed_reference_is_reported(tmp_path):
    (tmp_path / "bad.dat").write_text("0 FILE bad.dat\n0 !LICENSE Licensed under CC BY 4.0\n1 16 malformed\n", encoding="utf-8")
    assert validate_parts(tmp_path, POLICY)["assets"][0]["malformed_lines"]

def test_attribution_uses_validated_headers(tmp_path):
    report = validate_parts(ROOT / "data" / "fixtures" / "ldraw", POLICY)
    out = tmp_path / "ATTRIBUTION.md"
    write_attribution(report, out)
    text = out.read_text()
    assert "accepted.dat" in text
    assert "missing-license.dat" not in text

def test_beta_blocks_without_evidence(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"records": [_record()]}), encoding="utf-8")
    report = tmp_path / "ldraw.json"
    report.write_text(json.dumps({"assets": []}), encoding="utf-8")
    result = select_beta(catalog, report, tmp_path / "beta.json", ROOT / "config" / "catalog_selection_v1.yaml")
    assert result["blocked"]

def test_beta_rejects_review_required_asset(tmp_path):
    record = _record()
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"records": [record]}), encoding="utf-8")
    report = tmp_path / "ldraw.json"
    report.write_text(json.dumps({"assets": [{"design_id": record["design_id"], "license_status": "review_required", "validation_status": "review_required"}]}), encoding="utf-8")
    result = select_beta(catalog, report, tmp_path / "beta.json", ROOT / "config" / "catalog_selection_v1.yaml")
    assert result["selected_count"] == 0

def test_beta_does_not_mutate_source(tmp_path):
    record = _record()
    before = copy.deepcopy(record)
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"records": [record]}), encoding="utf-8")
    report = tmp_path / "ldraw.json"
    report.write_text(json.dumps({"assets": [{"design_id": record["design_id"], "license_status": "accepted", "validation_status": "valid"}]}), encoding="utf-8")
    result = select_beta(catalog, report, tmp_path / "beta.json", ROOT / "config" / "catalog_selection_v1.yaml")
    assert record == before
    assert result["selected_count"] == 1
    assert result["records"][0]["recognition"]["status"] == "beta_v1"

def test_beta_selection_is_deterministic(tmp_path):
    record = _record()
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"records": [record]}), encoding="utf-8")
    report = tmp_path / "ldraw.json"
    report.write_text(json.dumps({"assets": [{"design_id": record["design_id"], "license_status": "accepted", "validation_status": "valid"}]}), encoding="utf-8")
    one = select_beta(catalog, report, tmp_path / "one.json", ROOT / "config" / "catalog_selection_v1.yaml")
    two = select_beta(catalog, report, tmp_path / "two.json", ROOT / "config" / "catalog_selection_v1.yaml")
    assert one == two

def test_hash_same_file_is_stable(tmp_path):
    path = tmp_path / "data"
    path.write_text("same", encoding="utf-8")
    assert sha256_file(path) == sha256_file(path)

def test_hash_changes_when_file_changes(tmp_path):
    path = tmp_path / "data"
    path.write_text("one", encoding="utf-8")
    first = sha256_file(path)
    path.write_text("two", encoding="utf-8")
    assert first != sha256_file(path)

def test_manifest_contains_required_fields(tmp_path):
    path = tmp_path / "asset.dat"
    path.write_text("fixture", encoding="utf-8")
    manifest = manifest_for(path, asset_type="ldraw", source_provider="fixture",
                            retrieved_at=STAMP, imported_at=STAMP, license_status="accepted")
    required = {"manifest_version", "asset_type", "local_path", "sha256", "byte_size", "source_provider",
                "source_identifier", "source_version", "retrieved_at", "imported_at", "license_raw",
                "license_status", "processing_steps", "parent_assets", "generated_by_tool_version"}
    assert required <= set(manifest)

def test_manifest_is_typed():
    assert Manifest.model_fields["sha256"]

def test_manifest_parent_relationships_round_trip(tmp_path):
    path = tmp_path / "asset.dat"
    path.write_text("fixture", encoding="utf-8")
    manifest = manifest_for(path, asset_type="ldraw", source_provider="fixture",
                            retrieved_at=STAMP, imported_at=STAMP, license_status="accepted",
                            parent_assets=["parent.dat"])
    assert manifest["parent_assets"] == ["parent.dat"]

def test_doctor_reports_model_disabled():
    checks = run_checks(ROOT)
    assert any(item["name"] == "custom model" and item["status"] == "PASS" for item in checks)

def test_doctor_warns_without_api_key():
    checks = run_checks(ROOT)
    assert any(item["name"] == "api key" and item["status"] == "WARN" for item in checks)
