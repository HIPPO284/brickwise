import hashlib
import json
from pathlib import Path

import yaml

from brickwise_ml.catalog.models import BetaSelectionOutput, PartRecord
from brickwise_ml.catalog.select_beta_parts import select_beta


def _record(design_id: str, category: str) -> dict:
    return {
        "schema_version": "1.0",
        "catalog_version": "v1",
        "design_id": design_id,
        "name": f"Test {design_id}",
        "aliases": [],
        "category": category,
        "subcategory": None,
        "source": {
            "provider": "manual_verified",
            "source_record_id": design_id,
            "retrieved_at": "2026-01-01T00:00:00+00:00",
            "source_version": "fixture",
            "source_sha256": "a" * 64,
        },
        "ldraw": {
            "filename": f"{design_id}.dat",
            "file_sha256": "b" * 64,
            "header_name": f"Test {design_id}",
            "license_raw": "CC BY 2.0",
            "license_status": "accepted",
            "attribution_required": True,
            "validation_status": "valid",
        },
        "geometry": {
            "length_studs": 1,
            "width_studs": 1,
            "height_plates": 1,
            "bounding_box_ldu": {"x": 1, "y": 1, "z": 1},
            "geometry_source": "ldraw_computed",
        },
        "visual_features": {
            "stud_count": 1,
            "round_hole_count": 0,
            "axle_hole_count": 0,
            "pin_hole_count": 0,
            "is_curved": False,
            "is_flexible": False,
            "is_printed": False,
            "is_assembly": False,
            "feature_source": "computed",
        },
        "supported_colors": [],
        "recognition": {
            "status": "planned",
            "difficulty": "easy",
            "exclusion_reason": None,
        },
        "provenance": {
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "created_by": "importer",
            "notes": [],
        },
    }


def _run(tmp_path: Path, records: list[dict], mapping: dict, quotas: dict, target: int) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    catalog = tmp_path / "catalog.json"
    report = tmp_path / "ldraw.json"
    config = tmp_path / "config.yaml"
    output = tmp_path / "selected.json"
    catalog.write_text(json.dumps({"records": records}), encoding="utf-8")
    report.write_text(json.dumps({
        "assets": [
            {
                "design_id": record["design_id"],
                "filename": record["ldraw"]["filename"],
                "license_status": "accepted",
                "validation_status": "valid",
                "missing_dependencies": [],
            }
            for record in records
        ]
    }), encoding="utf-8")
    config.write_text(yaml.safe_dump({
        "beta_target_count": target,
        "excluded_categories": [],
        "category_group_mapping": mapping,
        "beta_category_targets": quotas,
        "required_design_ids": [],
    }, sort_keys=False), encoding="utf-8")
    return select_beta(catalog, report, output, config_path=config)


def test_every_selected_part_is_a_valid_part_record(tmp_path):
    result = _run(tmp_path, [_record("1", "Basic Brick")],
                  {"Basic Brick": "basic_brick"}, {"basic_brick": 1}, 1)

    assert result["selected_count"] == 1
    assert all(isinstance(entry.part, PartRecord)
               for entry in BetaSelectionOutput.model_validate(result).entries)


def test_beta_selection_output_validates_against_its_own_model(tmp_path):
    result = _run(tmp_path, [_record("1", "Basic Brick")],
                  {"Basic Brick": "basic_brick"}, {"basic_brick": 1}, 1)

    validated = BetaSelectionOutput.model_validate(result)
    assert validated.entries[0].selection.category_group == "basic_brick"
    assert "selection_reason" not in validated.entries[0].part.model_dump()
    assert "unresolved_review_issues" not in validated.entries[0].part.model_dump()


def test_quotas_use_explicit_category_group_mapping(tmp_path):
    result = _run(tmp_path, [_record("1", "Basic Brick"), _record("2", "Brick")],
                  {"Basic Brick": "basic_brick", "Brick": "basic_brick"},
                  {"basic_brick": 1}, 2)

    assert result["selected_count"] == 1
    assert result["category_counts"] == {"basic_brick": 1}
    assert result["entries"][0]["selection"]["category_group"] == "basic_brick"


def test_unmapped_categories_are_review_required_and_not_selected(tmp_path):
    result = _run(tmp_path, [_record("1", "Unreviewed Raw Label")],
                  {"Basic Brick": "basic_brick"}, {"basic_brick": 1}, 1)

    assert result["selected_count"] == 0
    assert any("review_required: unmapped category" in issue
               for item in result["rejected"] for issue in item["issues"])


def test_selection_output_is_deterministic(tmp_path):
    records = [_record("2", "Basic Brick"), _record("1", "Basic Brick")]
    first = _run(tmp_path / "first", records, {"Basic Brick": "basic_brick"},
                 {"basic_brick": 2}, 2)
    second = _run(tmp_path / "second", records, {"Basic Brick": "basic_brick"},
                  {"basic_brick": 2}, 2)

    first_bytes = json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    second_bytes = json.dumps(second, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert hashlib.sha256(first_bytes.encode()).hexdigest() == hashlib.sha256(second_bytes.encode()).hexdigest()
    assert [entry["part"]["design_id"] for entry in first["entries"]] == ["1", "2"]
